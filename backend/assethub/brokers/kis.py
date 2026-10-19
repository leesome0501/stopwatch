"""한국투자증권 KIS Developers (https://apiportal.koreainvestment.com).

- 실전 https://openapi.koreainvestment.com:9443, 모의 https://openapivts.koreainvestment.com:29443
- 토큰: POST /oauth2/tokenP. 유효 1일, 발급할 때마다 카카오톡 알림이 가고 1분에 1회만 발급된다.
  그래서 발급받은 토큰을 암호화해 저장해 두고 만료 직전까지 다시 쓴다.
- 조회 헤더: authorization, appkey, appsecret, tr_id, custtype=P, tr_cont. 연속조회는 응답 헤더 tr_cont 가
  M/F 이면 본문의 ctx_area_fk100/nk100 을 넘겨 다시 부른다.
- 계좌번호는 '종합계좌 8자리-상품코드 2자리' 를 사용자가 입력한다 (계좌 목록 API 없음).
- 체결은 3개월 이내(TTTC0081R)와 이전(CTSC9215R) TR 이 다르다. 수수료·세금·입출금·배당은 주지 않아서
  동기화 때 잔고 맞춤이 차액으로 채운다.
필드 이름은 한국투자증권 공식 예제 저장소(open-trading-api)의 컬럼 매핑에 따른다.
"""
from __future__ import annotations

import re
from datetime import date, datetime, timedelta

from ..importer.parsing import KST, ParsedMoment
from ..importer.rows import ImportRow
from .base import BrokerAccount, BrokerError, Connector, SnapHolding, Snapshot, kst_moment, num

HOSTS = {"real": "https://openapi.koreainvestment.com:9443", "mock": "https://openapivts.koreainvestment.com:29443"}
ACCOUNT_RE = re.compile(r"^(\d{8})-?(\d{2})$")
INNER_DAYS = 90          # 이보다 최근은 '3개월 이내' TR, 이전은 '이전' TR
CHUNK_DAYS = 90
MAX_PAGES = 200


def split_account(ref: str) -> tuple[str, str]:
    m = ACCOUNT_RE.match(ref.strip())
    if not m:
        raise BrokerError(f"한국투자 계좌번호 형식이 아닙니다: {ref!r} (예: 12345678-01)")
    return m.group(1), m.group(2)


class Kis(Connector):
    provider = "kis"
    name = "한국투자증권"
    ledger_has_cash = False

    @property
    def host(self) -> str:
        return HOSTS.get(self.creds.environment, HOSTS["real"])

    def tr(self, real_id: str) -> str:
        # 모의투자는 실전 TR 의 첫 글자를 V 로 바꾼다 (공식 예제와 같은 규칙)
        return "V" + real_id[1:] if self.creds.environment == "mock" and real_id[0] in "TJC" else real_id

    # ------------------------------------------------------------ 인증
    def token(self) -> str:
        if self._token_valid():
            return self.creds.token
        self.throttle.wait()
        try:
            r = self.client.post(f"{self.host}/oauth2/tokenP", json={
                "grant_type": "client_credentials", "appkey": self.creds.app_key, "appsecret": self.creds.app_secret},
                headers={"Content-Type": "application/json"})
        except Exception as e:
            raise BrokerError(f"한국투자 서버에 연결하지 못했습니다: {e.__class__.__name__}") from e
        try:
            body = r.json()
        except ValueError as e:
            raise BrokerError(f"한국투자 토큰 응답을 읽을 수 없습니다 (HTTP {r.status_code})") from e
        token = body.get("access_token")
        if r.status_code != 200 or not token:
            msg = body.get("error_description") or body.get("msg1") or r.text[:200]
            if "1분" in msg or "EGW00133" in str(body):
                msg += " (토큰은 1분에 한 번만 발급됩니다. 잠시 뒤 다시 시도하세요.)"
            raise BrokerError(f"한국투자 토큰 발급 실패: {msg}")
        try:
            expires = datetime.strptime(body.get("access_token_token_expired", ""), "%Y-%m-%d %H:%M:%S").replace(tzinfo=KST)
        except ValueError:
            expires = datetime.now(KST) + timedelta(seconds=int(body.get("expires_in") or 86400))
        self.creds.token, self.creds.token_expires = token, expires.isoformat()
        self.on_token(self.creds)
        return token

    def get(self, path: str, tr_id: str, params: dict, *, list_key: str = "output1") -> tuple[list[dict], dict]:
        """연속조회를 따라가 (목록 행 전체, 마지막 페이지 본문) 을 돌려준다."""
        rows: list[dict] = []
        tr_cont, last = "", {}
        params = dict(params)
        for _ in range(MAX_PAGES):
            self.throttle.wait()
            headers = {"content-type": "application/json; charset=utf-8", "authorization": f"Bearer {self.token()}",
                       "appkey": self.creds.app_key, "appsecret": self.creds.app_secret,
                       "tr_id": self.tr(tr_id), "custtype": "P", "tr_cont": tr_cont}
            try:
                r = self.client.get(f"{self.host}{path}", params=params, headers=headers)
            except Exception as e:
                raise BrokerError(f"한국투자 서버에 연결하지 못했습니다: {e.__class__.__name__}") from e
            try:
                body = r.json()
            except ValueError as e:
                raise BrokerError(f"한국투자 응답을 읽을 수 없습니다 (HTTP {r.status_code})") from e
            if r.status_code != 200 or str(body.get("rt_cd", "0")) != "0":
                code = body.get("msg_cd", "")
                msg = body.get("msg1") or r.text[:200]
                hint = " (초당 호출 한도 초과)" if code == "EGW00201" else ""
                raise BrokerError(f"한국투자 오류 {code}: {msg.strip()}{hint}")
            last = body
            out = body.get(list_key) or []
            rows.extend(out if isinstance(out, list) else [out])
            if r.headers.get("tr_cont") in ("M", "F"):
                params["CTX_AREA_FK100"] = body.get("ctx_area_fk100", "")
                params["CTX_AREA_NK100"] = body.get("ctx_area_nk100", "")
                tr_cont = "N"
            else:
                break
        return rows, last

    # ------------------------------------------------------------ 조회
    def accounts(self) -> list[BrokerAccount]:
        out = []
        for ref in self.creds.accounts:
            cano, prdt = split_account(ref)
            out.append(BrokerAccount(ref=f"{cano}-{prdt}", label=f"{cano}-{prdt}"))
        if not out:
            raise BrokerError("한국투자 계좌번호를 하나 이상 입력하세요 (예: 12345678-01).")
        self.token()   # 앱키 확인
        return out

    def _balance(self, ref: str) -> tuple[list[dict], dict]:
        cano, prdt = split_account(ref)
        rows, last = self.get("/uapi/domestic-stock/v1/trading/inquire-balance", "TTTC8434R", {
            "CANO": cano, "ACNT_PRDT_CD": prdt, "AFHR_FLPR_YN": "N", "OFL_YN": "", "INQR_DVSN": "02",
            "UNPR_DVSN": "01", "FUND_STTL_ICLD_YN": "N", "FNCG_AMT_AUTO_RDPT_YN": "N", "PRCS_DVSN": "00",
            "CTX_AREA_FK100": "", "CTX_AREA_NK100": ""})
        summary = last.get("output2") or [{}]
        return rows, summary[0] if isinstance(summary, list) and summary else (summary or {})

    def snapshot(self, ref: str) -> Snapshot:
        rows, s = self._balance(ref)
        holdings = []
        for h in rows:
            qty = num(h.get("hldg_qty"))
            if qty == 0:
                continue
            holdings.append(SnapHolding(symbol=(h.get("pdno") or "").strip(), name=(h.get("prdt_name") or "").strip(),
                                        quantity=qty, avg_price=num(h.get("pchs_avg_pric")) or None,
                                        price=num(h.get("prpr")) or None))
        # 가수도정산금액 = 결제 예정분까지 반영한 D+2 예수금
        cash = num(s.get("prvs_rcdl_excc_amt") if s.get("prvs_rcdl_excc_amt") not in (None, "") else s.get("dnca_tot_amt"))
        total = num(s.get("tot_evlu_amt")) if s.get("tot_evlu_amt") not in (None, "") else None
        return Snapshot(cash={"KRW": cash}, total_value=total, holdings=holdings, raw={"output2": s})

    def ledger(self, ref: str, start: date, end: date) -> list[ImportRow]:
        """체결 내역만 준다 (KIS 는 입출금·배당 내역 API 가 확인되지 않음)."""
        cano, prdt = split_account(ref)
        boundary = self.today - timedelta(days=INNER_DAYS)
        rows: list[ImportRow] = []
        seen: set[str] = set()
        cur = start
        while cur <= end:
            chunk_end = min(end, cur + timedelta(days=CHUNK_DAYS - 1))
            if cur < boundary <= chunk_end:
                chunk_end = boundary - timedelta(days=1)   # 경계에서 TR 이 바뀐다
            tr_id = "CTSC9215R" if chunk_end < boundary else "TTTC0081R"
            items, _ = self.get("/uapi/domestic-stock/v1/trading/inquire-daily-ccld", tr_id, {
                "CANO": cano, "ACNT_PRDT_CD": prdt, "INQR_STRT_DT": f"{cur:%Y%m%d}", "INQR_END_DT": f"{chunk_end:%Y%m%d}",
                "SLL_BUY_DVSN_CD": "00", "PDNO": "", "CCLD_DVSN": "01", "INQR_DVSN": "01", "INQR_DVSN_3": "00",
                "ORD_GNO_BRNO": "", "ODNO": "", "INQR_DVSN_1": "", "CTX_AREA_FK100": "", "CTX_AREA_NK100": "",
                "EXCG_ID_DVSN_CD": "ALL"})
            for it in items:
                row = self._fill_row(len(rows), it)
                if row is not None and row.external_id not in seen:
                    seen.add(row.external_id)
                    rows.append(row)
            cur = chunk_end + timedelta(days=1)
        rows.sort(key=lambda r: r.moment.at)
        return rows

    def _fill_row(self, idx: int, it: dict) -> ImportRow | None:
        qty = num(it.get("tot_ccld_qty"))
        if qty <= 0:
            return None
        side = (it.get("sll_buy_dvsn_cd") or "").strip()
        if side not in ("01", "02"):
            return None
        amount = num(it.get("tot_ccld_amt"))
        if amount == 0:
            amount = qty * num(it.get("avg_prvs"))
        buy = side == "02"
        day = it.get("ord_dt") or ""
        moment = kst_moment(day, it.get("ord_tmd"))
        name = (it.get("prdt_name") or "").strip()
        return ImportRow(
            file_index=idx, moment=ParsedMoment(moment, bool(it.get("ord_tmd"))),
            kind="buy" if buy else "sell", amount=-amount if buy else amount,
            description=f"{name} {'매수' if buy else '매도'}".strip(),
            instrument_symbol=(it.get("pdno") or "").strip(), instrument_market="KRX", instrument_name=name or None,
            quantity=qty if buy else -qty, unit_price=num(it.get("avg_prvs")) or None,
            raw={k: str(v) for k, v in it.items() if v not in (None, "")},
            external_id=f"kis:{day}:{(it.get('odno') or '').strip()}",
        )


__all__ = ["Kis", "split_account"]
