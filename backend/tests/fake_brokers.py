"""키움·한국투자 API 를 흉내 내는 가짜 서버 (httpx.MockTransport). 공식 스펙의 필드 이름을 그대로 쓴다."""
from __future__ import annotations

import json
from datetime import date, datetime, timedelta

import httpx


def pad(n: int) -> str:
    """키움식 '부호 포함 0-padding 15자리' 숫자."""
    return f"{'-' if n < 0 else ''}{abs(n):0{15 - (1 if n < 0 else 0)}d}"


class FakeKiwoom:
    def __init__(self):
        self.token_calls = 0
        self.calls: list[tuple[str, dict]] = []
        self.ledger = [
            dict(trde_dt="20260905", trde_no="000000001", rmrk_nm="이체입금", io_tp_nm="입금", exct_amt=pad(1_000_000),
                 entra_remn=pad(1_500_000), crnc_cd="KRW", rcpmnyer="홍길동", proc_tm="09:00:00"),
            dict(trde_dt="20260910", trde_no="000000002", rmrk_nm="장내매수", io_tp_nm="매수", stk_cd="A005930",
                 stk_nm="삼성전자", trde_qty_jwa_cnt=pad(10), trde_unit="60000", exct_amt=pad(600_090), cmsn=pad(90),
                 entra_remn=pad(899_910), crnc_cd="KRW", proc_tm="09:30:00"),
            dict(trde_dt="20261001", trde_no="000000003", rmrk_nm="배당금입금", io_tp_nm="입금", stk_cd="A005930",
                 stk_nm="삼성전자", exct_amt=pad(3_610), incm_resi_tax=pad(556), entra_remn=pad(903_520), crnc_cd="KRW"),
            dict(trde_dt="20261005", trde_no="000000004", rmrk_nm="장내매도", io_tp_nm="매도", stk_cd="A005930",
                 stk_nm="삼성전자", trde_qty_jwa_cnt=pad(4), trde_unit="70000", exct_amt=pad(279_250), cmsn=pad(42),
                 trde_agri_tax=pad(708), entra_remn=pad(1_182_770), crnc_cd="KRW", proc_tm="10:00:00"),
            dict(trde_dt="20261008", trde_no="000000005", rmrk_nm="해외주식매수", io_tp_nm="매수", stk_cd="AAPL",
                 crnc_cd="USD", fc_exct_amt="100.00", fc_entra="0.00"),
            dict(trde_dt="20261010", trde_no="000000006", rmrk_nm="이체출금", io_tp_nm="출금", exct_amt=pad(200_000),
                 entra_remn=pad(982_770), crnc_cd="KRW"),
            dict(trde_dt="20261012", trde_no="000000007", rmrk_nm="예탁금이용료", io_tp_nm="입금", exct_amt=pad(120),
                 entra_remn=pad(982_890), crnc_cd="KRW"),
        ]
        self.cash = 982_890
        self.holdings = [
            dict(stk_cd="A005930", stk_nm="삼성전자", rmnd_qty=pad(6), pur_pric=pad(60009), cur_prc=pad(71000)),
            dict(stk_cd="A000660", stk_nm="SK하이닉스", rmnd_qty=pad(3), pur_pric=pad(150000), cur_prc=pad(160000)),
        ]

    def __call__(self, request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content or b"{}")
        api_id = request.headers.get("api-id")
        self.calls.append((api_id, body))
        if request.url.path == "/oauth2/token":
            self.token_calls += 1
            if body.get("appkey") == "BAD":
                return httpx.Response(200, json={"return_code": 3, "return_msg": "앱키가 유효하지 않습니다"})
            return httpx.Response(200, json={"token": "kw-token", "expires_dt": "20991231235959",
                                              "token_type": "bearer", "return_code": 0})
        if request.headers.get("authorization") != "Bearer kw-token":
            return httpx.Response(200, json={"return_code": 3, "return_msg": "토큰 오류"})
        if api_id == "ka00001":
            return httpx.Response(200, json={"acctNo": "5012345678", "return_code": 0})
        if api_id == "kt00015":
            rows = [r for r in self.ledger if body["strt_dt"] <= r["trde_dt"] <= body["end_dt"]]
            page = 2 if request.headers.get("next-key") == "p2" else 1
            chunk = rows[:3] if page == 1 else rows[3:]
            headers = {"cont-yn": "Y", "next-key": "p2"} if page == 1 and len(rows) > 3 else {"cont-yn": "N"}
            return httpx.Response(200, json={"trst_ovrl_trde_prps_array": chunk, "return_code": 0}, headers=headers)
        if api_id == "kt00001":
            return httpx.Response(200, json={"entr": pad(self.cash), "d2_entra": pad(self.cash), "return_code": 0,
                                             "stk_entr_prst": [{"crnc_cd": "USD", "fx_entr": "0", "d2_fx_entr": "0"}]})
        if api_id == "kt00018":
            return httpx.Response(200, json={"prsm_dpst_aset_amt": pad(self.cash + 6 * 71000 + 3 * 160000),
                                             "acnt_evlt_remn_indv_tot": self.holdings, "return_code": 0})
        return httpx.Response(200, json={"return_code": 1, "return_msg": f"unknown {api_id}"})


class FakeKis:
    def __init__(self, today: date):
        self.today = today
        self.token_calls = 0
        self.ccld_calls: list[tuple[str, str, str]] = []
        self.fills = [
            dict(ord_dt="20260615", ord_tmd="093000", odno="0000000001", sll_buy_dvsn_cd="02", pdno="005930",
                 prdt_name="삼성전자", tot_ccld_qty="10", avg_prvs="55000", tot_ccld_amt="550000"),
            dict(ord_dt="20260920", ord_tmd="100000", odno="0000000002", sll_buy_dvsn_cd="01", pdno="005930",
                 prdt_name="삼성전자", tot_ccld_qty="5", avg_prvs="70000", tot_ccld_amt="350000"),
            dict(ord_dt="20260921", ord_tmd="100000", odno="0000000003", sll_buy_dvsn_cd="02", pdno="005930",
                 prdt_name="삼성전자", tot_ccld_qty="0", avg_prvs="0", tot_ccld_amt="0"),   # 미체결 (무시)
        ]
        self.cash = 1_234_567
        self.holdings = [
            dict(pdno="005930", prdt_name="삼성전자", hldg_qty="5", pchs_avg_pric="55000.0000", prpr="71000"),
            dict(pdno="035720", prdt_name="카카오", hldg_qty="2", pchs_avg_pric="50000.0000", prpr="45000"),
        ]

    def __call__(self, request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if path == "/oauth2/tokenP":
            self.token_calls += 1
            body = json.loads(request.content)
            if body.get("appkey") == "BAD":
                return httpx.Response(403, json={"error_code": "EGW00103", "error_description": "유효하지 않은 AppKey입니다."})
            return httpx.Response(200, json={"access_token": "kis-token", "token_type": "Bearer", "expires_in": 86400,
                                              "access_token_token_expired": "2099-12-31 23:59:59"})
        h = request.headers
        if h.get("authorization") != "Bearer kis-token" or h.get("custtype") != "P" or not h.get("appsecret"):
            return httpx.Response(500, json={"rt_cd": "1", "msg_cd": "EGW00123", "msg1": "기간이 만료된 token 입니다."})
        q = request.url.params
        if path.endswith("/inquire-daily-ccld"):
            tr = h["tr_id"]
            self.ccld_calls.append((tr, q["INQR_STRT_DT"], q["INQR_END_DT"]))
            boundary = (self.today - timedelta(days=90)).strftime("%Y%m%d")
            if (tr == "CTSC9215R") != (q["INQR_END_DT"] < boundary):
                return httpx.Response(200, json={"rt_cd": "1", "msg_cd": "OPSQ0001", "msg1": "조회기간 TR 오류"})
            rows = [f for f in self.fills if q["INQR_STRT_DT"] <= f["ord_dt"] <= q["INQR_END_DT"]]
            if q.get("CTX_AREA_NK100") == "next" or len(rows) <= 1:
                return httpx.Response(200, json={"rt_cd": "0", "msg1": "정상", "output1": rows[1:] if q.get("CTX_AREA_NK100") == "next" else rows,
                                                  "output2": {}}, headers={"tr_cont": "D"})
            return httpx.Response(200, json={"rt_cd": "0", "msg1": "정상", "output1": rows[:1], "output2": {},
                                              "ctx_area_fk100": "fk", "ctx_area_nk100": "next"}, headers={"tr_cont": "M"})
        if path.endswith("/inquire-balance"):
            assert h["tr_id"] == "TTTC8434R"
            return httpx.Response(200, json={"rt_cd": "0", "msg1": "정상", "output1": self.holdings, "output2": [
                {"dnca_tot_amt": "1300000", "prvs_rcdl_excc_amt": str(self.cash),
                 "tot_evlu_amt": str(self.cash + 5 * 71000 + 2 * 45000)}]})
        return httpx.Response(404, json={"rt_cd": "1", "msg1": "not found"})


def kst_today() -> date:
    from assethub.importer.parsing import KST
    return datetime.now(KST).date()
