# Open APIs of Korean brokerages with strong retail developer support (한국투자증권, 키움증권, LS증권, 대신증권): pulling your own account data

Research date: 2026-10-19. Sources were accessed on that date unless noted otherwise.

Source quality legend:
- **[공식]** official portal, official sample code, or official help.
- **[미러]** a third-party copy of an official spec or catalog.
- **[3rd]** blog, library, or MCP README.

Several official portals (openapi.kiwoom.com, cybosplus.github.io, algolab.co.kr) could not be fetched directly from the research sandbox because of DNS or proxy blocks. Facts about them come from search-result snippets or GitHub mirrors and are marked as such.

---

## Q1. API products per brokerage, and which are current vs deprecated (as of 2026)

### Takeaway
KIS (REST + WebSocket) and Kiwoom REST (launched 2025) are current, HTTP-based, and OS-independent. LS also has a current REST Open API on port 8080 alongside the legacy xingAPI (COM/DLL). Daishin still offers only the CYBOS Plus / CREON Plus COM API. It requires 32-bit Windows with the HTS running, and no REST product was found as of 2026-10.

### Cited Findings
**한국투자증권 (KIS Developers)**
- The official sample repo `koreainvestment/open-trading-api` provides REST and WebSocket samples in these categories: `auth`, `domestic_stock`, `domestic_bond`, `domestic_futureoption`, `overseas_stock`, `overseas_futureoption`, `elw`, `etfetn`. It also has a `legacy/` folder plus `MCP/`, `backtester/` and `strategy_builder/` (an LLM- and AI-oriented 2025–26 restructure) — [공식 GitHub](https://github.com/koreainvestment/open-trading-api)
- Real and mock (모의) environments use separate app keys and secrets. The sample code switches between them with `ka.auth(svr="prod")` / `svr="vps"` — [공식 README](https://github.com/koreainvestment/open-trading-api)
- The repo has 414 commits, 1.7k stars and 835 forks. No explicit last-update date is shown on the page. — [GitHub](https://github.com/koreainvestment/open-trading-api)

**키움증권**
- Kiwoom REST API: hosts are `https://api.kiwoom.com` (실거래) and `https://mockapi.kiwoom.com` (모의투자). Token issuance is `POST /oauth2/token` with api-id `au10001` (grant_type=client_credentials, appkey, secretkey); revocation is api-id `au10002`. — [미러: KKimj/Kiwoom-REST-API openapi.json, spec version "2026-06-18"](https://github.com/KKimj/Kiwoom-REST-API)
- The REST categories in that spec are all domestic (`/api/dostk/...`): `acnt`, `chart`, `crdordr`, `elw`, `etf`, `frgnistt`, `mrkcond`, `ordr`, `rkinfo`, `sect`, `shsa`, `slb`, `stkinfo`, `thme`, `websocket`. The spec has no overseas-stock path. — [미러 spec](https://github.com/KKimj/Kiwoom-REST-API)
- However, the official service-info page (search snippet) lists rate limits for "미국주식(대분류)", including order, inquiry and FX TRs. This implies US-stock REST TRs were added at some point after or alongside that spec. — [공식 서비스 이용안내 (snippet)](https://openapi.kiwoom.com/intro/serviceInfo)
- How a call works: you POST to the category path (e.g. `https://api.kiwoom.com/api/dostk/acnt`) and put the TR code in the `api-id` header (example: `ka00001`). — [공식 가이드 목록 (snippet)](https://openapi.kiwoom.com/m/guide/apiguide?jobTpCode=15); [황현동 블로그 2026-03-11](https://hyundonghwang.github.io/2026/03/11/%ED%82%A4%EC%9B%80%EC%A6%9D%EA%B6%8C-rest-api-%ED%88%AC%EC%9E%90%EC%A0%95%EB%B3%B4-%EA%B0%80%EC%9D%B4%EB%93%9C/)
- The legacy 키움 Open API+ (OCX) still has an official download page — [키움 Open API+ 페이지](https://www.kiwoom.com/h/customer/download/VOpenApiInfoView)

**LS증권 (formerly 이베스트)**
- The LS Open API is REST at domain `https://openapi.ls-sec.co.kr:8080`. The official catalog has 41 API groups and 364 TRs, and account groups include `/stock/accno`, `/overseas-stock/accno`, `/futureoption/accno` and `/overseas-futureoption/accno`. Tokens use `/oauth2/token` and `/oauth2/revoke`. — [미러: LsApiHelper specs/catalog.json (copy of openapi.ls-sec.co.kr/apiservice)](https://github.com/xorrhks0216/LsApiHelper); [LS 공식 샘플 페이지](https://openapi.ls-sec.co.kr/howto-sample)
- A 2026 third-party guide covers "xingAPI·OpenAPI" side by side, which suggests both are still offered. It also notes that REST uses port 8080. — [algolab 2026 (3rd)](https://algolab.co.kr/blog/daeshin-ls-securities-algotrading-guide-2026); [algolab LS REST 주문 (3rd)](https://algolab.co.kr/blog/ls-securities-openapi-rest-order-2026)

**대신증권 (CYBOS Plus / CREON Plus)**
- The CYBOS Plus notice board was active into 2026, with no termination or REST launch notice seen:
  - Latest item: 2026-09-08 (KRX 거래시간 연장 안내)
  - 2026-01-20: FnGuide 계정 정의 변경
  - 2025-12-22: 법인 계좌고객 시세정보 API 서비스 제공 제한 주의사항
  — [대신 CYBOS 플러스 공지사항](https://money2.daishin.com/e5/mboard/ptype_basic/CREON_Plus_Notice/DW_Basic_List_Page.aspx?boardseq=283&m=9508&p=8822&v=8634)
- Third-party 2026 guides describe CybosPlus as "32bit COM·윈도우 전용·크레온 HTS 필요". They also report that the "Cybos Plus HTS 상시 실행 필수 — 종료 시 API 끊김". — [algolab 2026 (3rd)](https://algolab.co.kr/blog/daeshin-ls-securities-algotrading-guide-2026); [algolab 증권사 API 비교 2026 (3rd)](https://algolab.co.kr/blog/kr-broker-api-comparison)

### Inferences
- For a FastAPI server on Linux, KIS, Kiwoom REST and LS REST can be called directly. Kiwoom OpenAPI+, LS xingAPI and Daishin CYBOS Plus each need a separate 32-bit Windows agent: a Windows VM or PC running the HTS and login, which pushes data to the server.
- Kiwoom REST is the strategic product. OpenAPI+ (OCX) is effectively legacy, but no official termination date was found.

### Gaps
- No official announcement found that sets an end-of-life date for Kiwoom OpenAPI+ OCX or LS xingAPI.
- The exact launch date and TR list for Kiwoom REST US-stock (해외) TRs could not be confirmed. The official portal was unreachable from the sandbox, and the mirrored spec (2026-06-18) has only `dostk`.
- No evidence was found of a Daishin REST API as of 2026-10. This is absence of evidence, not confirmation.

---

## Q2. Exact endpoints / TR codes for balances, holdings, cash, fills, transaction history, overseas, and FX, and how far back you can query

### Takeaway
- **Kiwoom REST `kt00015` (위탁종합거래내역요청)** is the richest single feed. One call can filter by 입출금, 입출고, 매매, 환전 and 외화매수/매도. It returns fees, taxes (거래및농특세, 소득/주민세, 외국납부세액), interest, FX rate and 예수금잔고 per row.
- **LS `CDPCQ04700` (계좌 거래내역)** is the closest LS equivalent.
- **KIS** has strong holdings and fills APIs (fills split into 3개월 이내 / 이전 TR_IDs), an account-level 권리 (dividend) API, and an overseas 일별거래내역 API. No KIS cash 입출금내역 endpoint was found in the official sample code.
- **Daishin** exposes 잔고 and only today's or yesterday's fills (CpTd6033 / CpTd5341 / CpTd5342). No 입출금 TR was found.

### Cited Findings

#### 한국투자증권 — domestic (`/uapi/domestic-stock/v1/trading/...`)
All rows come from [공식 sample domestic_stock_functions.py](https://github.com/koreainvestment/open-trading-api/blob/main/examples_user/domestic_stock/domestic_stock_functions.py).

| Purpose | Path | TR_ID (실전 / 모의) |
|---|---|---|
| 주식잔고조회 (holdings + summary) | `inquire-balance` | `TTTC8434R` / `VTTC8434R` |
| 주식잔고조회_실현손익 (HTS [0800]) | `inquire-balance-rlz-pl` | `TTTC8494R` |
| 투자계좌자산현황조회 (HTS [0891] 자산비중) | `inquire-account-balance` | `CTRP6548R` |
| 주식일별주문체결조회 | `inquire-daily-ccld` | 3개월 이내 `TTTC0081R` (모의 `VTTC0081R`); 3개월 이전 `CTSC9215R` (모의 `VTSC9215R`) |
| 기간별손익일별합산조회 (HTS [0856]) | `inquire-period-profit` | `TTTC8708R` |
| 기간별매매손익현황조회 | `inquire-period-trade-profit` | `TTTC8715R` |
| 기간별계좌권리현황조회 (HTS [7344] 권리유형별 현황, i.e. account-level dividends/rights) | `period-rights` | `CTRGA011R` |
| 주식통합증거금 현황 (HTS [0867], 국내+해외 주문가능, CMA평가 포함 옵션) | `intgr-margin` | `TTTC0869R` |
| 매수가능조회 | `inquire-psbl-order` | `TTTC8908R` |
| 퇴직연금 잔고 | `pension/inquire-balance` | `TTTC2208R` |
| 퇴직연금 미체결/체결 | `pension/inquire-daily-ccld` | `TTTC2201R` |
| 퇴직연금 예수금 | `pension/inquire-deposit` | `TTTC0506R` |
| 퇴직연금 체결기준잔고 | `pension/inquire-present-balance` | `TTTC2202R` |

- `inquire-daily-ccld` returns up to **100 rows per call on 실전 and 15 on 모의**, with paging via `FK100` / `NK100` / `tr_cont`. Parameter `pd_dv` selects "3개월이전/이내".
- For the 3개월 이전 TR, KIS advises querying **after 15:30** and using a **short date range**, because of DB load.
- The docstring names the 3개월 이전 TR as `CTSC9115R`, while the code uses `CTSC9215R`. This is an internal inconsistency; verify against the portal.

#### 한국투자증권 — overseas (`/uapi/overseas-stock/v1/trading/...`)
All rows come from [공식 sample overseas_stock_functions.py](https://github.com/koreainvestment/open-trading-api/blob/main/examples_user/overseas_stock/overseas_stock_functions.py).

| Purpose | Path | TR_ID |
|---|---|---|
| 해외주식 잔고 | `inquire-balance` | `TTTS3012R` / `VTTS3012R` |
| 해외주식 주문체결내역 [v1_해외주식-007] | `inquire-ccnl` | `TTTS3035R` / `VTTS3035R` |
| 미체결 | `inquire-nccs` | `TTTS3018R` |
| 체결기준현재잔고 [v1_해외주식-008] | `inquire-present-balance` | `CTRP6504R` / `VTRP6504R` |
| 결제기준잔고 [해외주식-064] | `inquire-paymt-stdr-balance` | `CTRP6010R` |
| 해외주식 기간손익 [v1_해외주식-032] | `inquire-period-profit` | `TTTS3039R` |
| **해외주식 일별거래내역 [해외주식-063]** | `inquire-period-trans` | `CTOS4001R` |
| 해외증거금 통화별조회 [해외주식-035] | `foreign-margin` | `TTTC2101R` |

- `inquire-ccnl` uses dates in **local (현지) time**.
- `inquire-present-balance` supports `wcrc_frcr_dvsn_cd` (01 원화 / 02 외화), 국가 (US, HK, CN, JP, VN), and 미니스탁.
- `inquire-period-trans` takes `erlm_strt_dt` / `erlm_end_dt` and paginates.
- `/uapi/overseas-price/v1/quotations/period-rights` (`CTRGT011R`, HTS [7520]) returns market-level rights schedules, including 배당 (03) and 특별배당 (75). It is not per-account.

#### 키움증권 REST — account TRs (`/api/dostk/acnt`, `api-id` header)
All TR names come from the [미러 openapi.json, 2026-06-18](https://github.com/KKimj/Kiwoom-REST-API), cross-checked against the [공식 가이드 목록 snippet](https://openapi.kiwoom.com/m/guide/apiguide?jobTpCode=15).

| Group | TRs |
|---|---|
| Account list | `ka00001` 계좌번호조회 |
| Cash and assets | `kt00001` 예수금상세현황요청 (qry_tp 3 추정 / 2 일반); `kt00002` 일별추정예탁자산현황요청 (start_dt / end_dt); `kt00003` 추정자산조회 |
| Holdings | `kt00004` 계좌평가현황요청; `kt00018` 계좌평가잔고내역요청 (qry_tp 1 합산 / 2 개별, dmst_stex_tp KRX/NXT); `kt00005` 체결잔고 |
| Fills | `kt00007` 계좌별주문체결내역상세요청 (**single `ord_dt` date per call**; qry_tp 4 = 체결내역만; stk_bond_tp; KRX/NXT/SOR); `kt00009` 계좌별주문체결현황; `ka10076` 체결요청; `ka10075` 미체결 |
| Daily P&L | `ka10170` 당일매매일지 |
| Realized P&L | `ka10072` / `ka10073` 일자별종목별실현손익 (일자/기간); `ka10074` 일자별실현손익; `ka10077` 당일실현손익상세 |
| Returns | `ka10085` 계좌수익률; `ka01690` 일별잔고수익률 (qry_dt); `kt00016` 일별계좌수익률상세현황 (fr_dt / to_dt) |
| Settlement | `kt00008` 익일결제예정내역 |
| **Transaction history** | `kt00015` 위탁종합거래내역요청 (details below) |

`kt00015` request fields:
- `strt_dt`, `end_dt`
- `tp`: 0 전체, 1 입출금, 2 입출고, 3 매매, 4 매수, 5 매도, 6 입금, 7 출금, A 예탁담보대출입금, B 매도담보대출입금, C 현금상환, **F 환전**, **M 입출금+환전**, **G 외화매수**, **H 외화매도**, I 환전정산입금, J 환전정산출금
- `gds_tp`: 0 전체, 1 국내주식, 2 수익증권, **3 해외주식**, 4 금융상품
- `crnc_cd`, `frgn_stex_code`, `qry_sort_tp`

`kt00015` response array `trst_ovrl_trde_prps_array` fields:
- Identifiers and dates: `trde_dt`, `trde_no`, `proc_tm`, `cntr_dt`, `orig_deal_no`, `isin_cd`, `stk_cd`, `stk_nm`
- Description: `rmrk_nm` 적요명, `trde_kind_nm`, `io_tp_nm`, `rcpmnyer` 입금자
- Amounts: `trde_amt`, `exct_amt` 정산금액, `entra_remn` 예수금잔고
- Fees, taxes, interest: `cmsn` 수수료, `trde_agri_tax` 거래및농특세, `incm_resi_tax` 소득/주민세, `int_ls_usfe` 이자, `tax_sum_cmsn`
- FX: `crnc_cd`, `trde_unit` 거래단가/환율, `fc_trde_amt`, `fc_exct_amt`, `fc_cmsn`, `fc_trde_tax`, `fc_entra` 외화예수금잔고, `frgn_pay_txam` 외국납부세액(외)

Amounts are 15-character zero-padded strings with a sign.

- A wrapper changelog notes that `kt00015` gained a sort-type parameter, which was a breaking change. — [KiwoomRestApi.Net (3rd)](https://github.com/dongbin300/KiwoomRestApi.Net)

#### LS증권 Open API REST
All rows come from the [미러 catalog, copy of openapi.ls-sec.co.kr](https://github.com/xorrhks0216/LsApiHelper). Domestic stock account TRs live at `POST /stock/accno`:

| TR | Name |
|---|---|
| `CDPCQ04700` | **계좌 거래내역** |
| `CSPAQ12200` | 현물계좌예수금 주문가능금액 총평가 |
| `CSPAQ22200` | 현물계좌예수금 주문가능금액 총평가2 |
| `CSPAQ12300` | BEP단가조회 (holdings detail) |
| `CSPAQ13700` | 현물계좌 주문체결내역 조회 |
| `CSPAQ00600` | 계좌별신용한도 |
| `CSPBQ00200` | 증거금률별주문가능수량 |
| `FOCCQ33600` | 주식계좌 기간별수익률 상세 |
| `t0150` / `t0151` | 주식당일/전일 매매일지/수수료 |
| `t0424` | 주식잔고2 |
| `t0425` | 주식체결/미체결 |

- `CDPCQ04700` input (`CDPCQ04700InBlock1`): `RecCnt`, `QryTp`, `QrySrtDt`, `QryEndDt`, `SrtNo`, `PdptnCode`, `IsuLgclssCode`, `IsuNo`.
- `CDPCQ04700` outputs:
  - OutBlock3 holds the detail rows; its fields were not captured.
  - OutBlock4 holds the summary totals `PnlSumAmt`, `CtrctAsm` and `CmsnAmtSumAmt`.
  - OutBlock5 holds `MnyinAmt` (입금), `SecinAmt` (입고), `MnyoutAmt` (출금), `SecoutAmt`, `SellAmt`, `SellCmsn`, `EvrTax`, `BuyAmt`, `BuyCmsn`, `ExecTax`, `FcurrSellAdjstAmt` and `FcurrBuyAdjstAmt`.
  — [미러 spec](https://github.com/xorrhks0216/LsApiHelper)
- Overseas stock account TRs at `POST /overseas-stock/accno`:
  - `COSAQ00102` 해외주식 계좌주문체결내역조회
  - `COSAQ01400` 예약주문 처리결과
  - `COSOQ00201` 해외주식 종합잔고평가
  - `COSOQ02701` 해외주식 예수금 조회
  — [미러 catalog](https://github.com/xorrhks0216/LsApiHelper)
- Futures and options at `/futureoption/accno`: `CFOAQ50600`, `CFOAQ00600`, `CFOBQ10500`, `CFOEQ82600`, `CFOFQ02400`, `FOCCQ33700`, `CFOAQ10100`, `t0434`, `t0441`, `CFOEQ11100`, `CCENQ10100`, `CCENQ30100`, `CCENQ90200`. Overseas futures at `/overseas-futureoption/accno`: `CIDBQ01400`, `CIDBQ01500`, `CIDBQ01800`, `CIDBQ05300`, `CIDBQ03000`, `CIDEQ00800`, `CIDBQ02400`. — [미러 catalog](https://github.com/xorrhks0216/LsApiHelper)

#### 대신증권 CYBOS Plus (COM `CpTrade.*`)
- `CpTd6033` (계좌 잔고/평가): 14 rows by default, up to 50 per request. It **excludes** the valuation and 예수금 changes of non-stock products (펀드, RP). — [cybosplus 도움말 CpTd6033 (snippet)](https://cybosplus.github.io/cptrade_new_rtf_1_/cptd6033_.htm)
- `CpTd5341` returns **today's (금일)** 계좌별 주문/체결 내역, with paging via the `Continue` property. — [CpTd5341 (snippet)](https://cybosplus.github.io/cptrade_new_rtf_1_/cptd5341_.htm)
- `CpTd5342` returns the previous day's (전일) 체결 내역. — [CpTd5342 (snippet)](https://cybosplus.github.io/cptrade_new_rtf_1_/cptd5342_.htm)
- Account TRs need a 9-digit account number plus a 2-digit 상품구분 — [cybosplus 도움말 (snippet)](https://cybosplus.github.io/cptrade_new_rtf_1_/cptd6033_.htm)

### Inferences
- **Best coverage for 거래내역** (deposits, withdrawals, dividends via 적요, fees, taxes, FX) appears to be Kiwoom `kt00015`, then LS `CDPCQ04700`.
- For KIS, a ledger has to be assembled from three sources: fills (`inquire-daily-ccld`), account 권리현황 (`period-rights` `CTRGA011R`) for dividends, and overseas `inquire-period-trans` (`CTOS4001R`). Pure cash 입출금 (bank transfers) appears not to be exposed. Reconcile by diffing daily 예수금 snapshots.
- Daishin is suitable only for snapshotting holdings and cash plus capturing today's fills daily, going forward. Historical backfill would need HTS CSV export.

### Gaps
- **Maximum past period per call and overall** was not confirmed for any brokerage:
  - Kiwoom `kt00015`: no documented maximum range found.
  - LS `CDPCQ04700`: no documented maximum range found.
  - KIS: only the 3-month boundary between TR_IDs is confirmed; the total retention limit is unknown.
- KIS overseas `CTOS4001R`: response fields not captured, so it is unconfirmed whether it includes dividends, FX conversions, or taxes.
- **KIS cash 입출금내역 / 환전내역 endpoint**: none found among the official sample functions. One may exist on the portal and not in the samples.
- LS `CDPCQ04700` OutBlock3 row fields (e.g. 적요, 세금 per row) were not captured.
- Kiwoom REST overseas (US) account TR codes are unknown.
- Daishin: no TR for 입출금, 배당, or period fills (beyond 금일/전일) was found, and no overseas account TRs were found.

---

## Q3. Account types covered (위탁, ISA, 연금저축, IRP, CMA, 해외 통합증거금, 선물옵션), and whether one key covers multiple or family accounts

### Takeaway
KIS uses an 8-digit CANO plus a 2-digit 상품코드, and its samples show codes 01, 19, 21, 22 and 29 (퇴직연금). **DC가입자 55번 계좌 is explicitly not supported.** Kiwoom REST binds the account to the app key, and `ka00001` lists the accounts. No brokerage offers cross-customer access: each family member must apply under their own ID and keys.

### Cited Findings
- KIS pension APIs (`pension/*`) use 계좌상품코드 `29`. "**55번 계좌(DC가입자계좌)의 경우 해당 API 이용이 불가**", because KIS Developers requires the account to be linked to an **HTS ID**. — [공식 sample](https://github.com/koreainvestment/open-trading-api/blob/main/examples_user/domestic_stock/domestic_stock_functions.py)
- KIS sample examples for `acnt_prdt_cd` show "01", "01 or 22", "19 or 21", and "29" — [공식 sample](https://github.com/koreainvestment/open-trading-api/blob/main/examples_user/domestic_stock/domestic_stock_functions.py)
- The KIS 퇴직연금 잔고 API covers stocks, ETFs and ETNs only, not funds ("펀드는 조회 불가") — [공식 sample](https://github.com/koreainvestment/open-trading-api/blob/main/examples_user/domestic_stock/domestic_stock_functions.py)
- KIS `intgr-margin` (`TTTC0869R`) covers 일반계좌 and 통합증거금 신청계좌, with an option to include the CMA valuation (`cma_evlu_amt_icld_yn`) — [공식 sample](https://github.com/koreainvestment/open-trading-api/blob/main/examples_user/domestic_stock/domestic_stock_functions.py)
- The KIS config template has separate fields for a stock account and a futures/options account (e.g. `my_paper_stock`, `my_paper_future`). Each API call specifies `CANO` + `ACNT_PRDT_CD`. — [공식 README](https://github.com/koreainvestment/open-trading-api)
- Kiwoom REST: the "계좌는 앱키에 귀속" model means no account number is passed in requests, and `ka00001` returns the account numbers. — [kiwoom MCP README (3rd, glama)](https://glama.ai/mcp/servers/gi0iibvr9k); [미러 spec ka00001](https://github.com/KKimj/Kiwoom-REST-API)
- The Kiwoom key flow requires registering an account first. Otherwise the portal shows "인증된 계좌가 없습니다" and offers no key download. — [algolab 키 발급 가이드 (3rd)](https://algolab.co.kr/kiwoom-rest-key-guide)
- Kiwoom `kt00015` `gds_tp` covers 국내주식, 수익증권, 해외주식 and 금융상품 within the 위탁 account — [미러 spec](https://github.com/KKimj/Kiwoom-REST-API)
- LS REST has separate account groups for stock, futures/options, overseas stock and overseas futures — [미러 catalog](https://github.com/xorrhks0216/LsApiHelper)
- A 2025-12-22 Daishin notice restricts market-data API service for 법인 accounts — [대신 공지](https://money2.daishin.com/e5/mboard/ptype_basic/CREON_Plus_Notice/DW_Basic_List_Page.aspx?boardseq=283&m=9508&p=8822&v=8634)

### Inferences
- Because keys are bound to a person's HTS ID and certificate, a family app needs **one key set per family member**, stored securely and with each member's consent. Each member applies under their own login.
- Within one person, KIS can query multiple accounts by changing CANO and 상품코드 if they are registered to the app. Kiwoom ties accounts to the key. (Unverified whether one Kiwoom key can cover several of the same person's accounts.)
- ISA, 연금저축 and IRP: KIS shows IRP/퇴직연금 (29) support, but DC is excluded. For ISA and 연금저축, no explicit statement was found for any brokerage.

### Gaps
- Official per-brokerage tables of supported account product codes (ISA, 연금저축, IRP, CMA) were not found.
- Whether one KIS app key can cover multiple accounts, or needs one key per account, was not confirmed from official docs.
- Kiwoom: number of accounts per app key not confirmed.
- LS and Daishin multi-account behaviour not documented in the fetched sources.

---

## Q4. Application and approval process, tokens, and costs

### Takeaway
All four require an existing customer account plus online sign-up.
- **KIS**: tokens last about 1 day, re-issue is limited to 1 per minute, and each issuance sends a KakaoTalk 알림톡.
- **Kiwoom REST**: you must register an IP before issuing a key, real and mock keys are separate, and the service **auto-terminates after 3 months of no use**.
- **Costs**: no fees were found documented for any of them.

### Cited Findings
- KIS token behaviour, per a comment in the official auth code: "토큰 유효시간 1일, 6시간 이내 발급신청시는 기존 토큰값과 동일, 발급시 알림톡 발송" (valid for 1 day; a request within 6 hours returns the same token; each issuance triggers a 알림톡). — [공식 kis_auth.py](https://github.com/koreainvestment/open-trading-api/blob/main/examples_user/kis_auth.py)
- KIS token re-issue is limited to "1분당 1회" — [공식 README](https://github.com/koreainvestment/open-trading-api)
- KIS: preparing the app keys means applying for the 모의투자 and 실전투자 app keys separately. The KIS Developers service application page can be reached in 2 ways. — [공식 README](https://github.com/koreainvestment/open-trading-api); [wikidocs KIS 공식 예제 책 (1) 서비스 신청](https://wikidocs.net/164056)
- KIS requires the account to be linked to an HTS ID to apply for the API and get app info — [공식 sample docstring](https://github.com/koreainvestment/open-trading-api/blob/main/examples_user/domestic_stock/domestic_stock_functions.py)
- Kiwoom REST:
  - IP registration is required before issuing an App Key, and authentication works only from allowed IPs.
  - Real and mock keys are managed separately.
  - "3개월 단위로 키움 REST API 미접속 시 매월 첫영업일에 자동으로 해지" (service auto-cancels after 3 months without access, on the first business day of the month).
  — [공식 서비스 이용안내 (snippet)](https://openapi.kiwoom.com/intro/serviceInfo)
- Kiwoom: up to 10 IPs can be registered, and App Key/Secret download is one-time only. Both points come from a third party, not official docs. — [algolab 키 발급 가이드 (3rd)](https://algolab.co.kr/kiwoom-rest-key-guide)
- Kiwoom token issuance is `au10001` with grant_type=client_credentials, appkey and secretkey. — [미러 spec](https://github.com/KKimj/Kiwoom-REST-API)
- LS uses OAuth token endpoints `/oauth2/token` and `/oauth2/revoke` on `openapi.ls-sec.co.kr:8080` — [미러 catalog](https://github.com/xorrhks0216/LsApiHelper)

### Inferences
- A server deployment for Kiwoom needs a **static egress IP** registered in the portal.
- A scheduled daily sync keeps Kiwoom from auto-terminating and fits within KIS's one-token-per-day model. Cache the KIS token to avoid a 알림톡 on every run.

### Gaps
- Kiwoom REST token validity period: no official value found (the snippet was truncated).
- LS token validity and app-key application steps: not captured.
- Daishin CYBOS Plus application steps (HTS ID, certificate-based login, any "Plus 사용 신청") were not captured from official pages.
- Costs: no official statement of fees found for any of the four. They are commonly understood to be free for customers, but this was not verified.

---

## Q5. OS and runtime constraints, and Python library support with maintenance status

### Takeaway
REST products (KIS, Kiwoom REST, LS REST) run from Linux, Windows or macOS with plain HTTPS. The official KIS samples need Python ≥3.11 and give install instructions for both Linux and Windows. COM/OCX products (Kiwoom OpenAPI+, LS xingAPI, Daishin CYBOS Plus) are 32-bit-Windows-bound.

### Cited Findings
- The KIS official sample requires **Python 3.11+**, recommends `uv`, and gives install commands for Windows PowerShell and macOS/Linux — [공식 README](https://github.com/koreainvestment/open-trading-api)
- Daishin CybosPlus is 32-bit COM, Windows-only, and needs the CREON HTS running — [algolab 2026 (3rd)](https://algolab.co.kr/blog/daeshin-ls-securities-algotrading-guide-2026); [algolab 비교 (3rd)](https://algolab.co.kr/blog/kr-broker-api-comparison)
- The `kiwoom-client` README says it works "OpenAPI+ OCX 없이 Linux·macOS 에서 동작" (on Linux and macOS without OpenAPI+ OCX) — [kiwoom-client GitHub (3rd)](https://github.com/younghwan91/kiwoom-client)

Python wrapper status (PyPI JSON, checked 2026-10-19):

| Library | Target | Latest version | Last upload | Status / source |
|---|---|---|---|---|
| `python-kis` (Soju06) | KIS REST | 2.1.6 | 2025-10-13 | Maintained to late 2025 — [PyPI](https://pypi.org/project/python-kis/) |
| `mojito2` (sharebook-kr) | KIS REST | 0.1.6 | 2023-02-23 | **Stale** — [PyPI](https://pypi.org/project/mojito2/) |
| `pykiwoom` (sharebook-kr) | Kiwoom OpenAPI+ OCX | 0.1.6 | 2024-01-05 | Stale — [PyPI](https://pypi.org/project/pykiwoom/) |
| `kiwoom-client` (younghwan91) | Kiwoom REST, 186 domestic endpoints, sync+async, token refresh | 0.4.0 | **2026-09-13** | Active — [PyPI](https://pypi.org/project/kiwoom-client/) |
| `kiwoom-rest-api` | Kiwoom REST | 0.1.12 | 2025-06-27 | [PyPI](https://pypi.org/project/kiwoom-rest-api/) |
| `ebest` (teranum) | LS/eBest | 1.0.2 | 2025-05-09 | [PyPI](https://pypi.org/project/ebest/) |
| `xingAPI` (jeakwon) | xingAPI COM | 1.2.14 | 2020-07-29 | Abandoned — [PyPI](https://pypi.org/project/xingAPI/) |

Other wrappers and specs:
- `LsApiHelper` is a Python wrapper for LS REST with a built-in catalog of 364 TRs, OAuth2 and WebSocket — [GitHub (3rd)](https://github.com/xorrhks0216/LsApiHelper)
- `KKimj/Kiwoom-REST-API` is an OpenAPI 3.1 spec of Kiwoom REST plus an MCP server — [GitHub (3rd)](https://github.com/KKimj/Kiwoom-REST-API)
- A PyPI user named "Kiwoom" exists, last released 2026-07-22. This may be an official Kiwoom package, but that is not verified. — [pypi.org/user/Kiwoom](https://pypi.org/user/Kiwoom/)

### Inferences
- For a FastAPI backend: use direct `httpx` calls, or copy patterns from the KIS official `examples_user/*_functions.py`, `kiwoom-client`, and `LsApiHelper`.
- Avoid stale wrappers (`mojito2`, `pykiwoom`, `xingAPI`) for new builds.
- Daishin needs a Windows 32-bit Python bridge, for example the official samples from the [Daishin 파이썬 예제 게시판](https://money2.daishin.com/e5/mboard/ptype_basic/plusPDS/DW_Basic_Read.aspx?boardseq=299&seq=75&page=1&searchString=&prd=&lang=&p=8831&v=8638&m=9508) or [wikidocs 대신증권 API](https://wikidocs.net/2870), running on a Windows host that posts JSON to the server.

### Gaps
- No official KIS-published PyPI SDK was found. The official channel is the GitHub sample repo.
- The current maintenance state of `pycreon` and other Daishin wrappers is unknown (no PyPI entry for `pycreon`).

---

## Q6. Rate limits and terms of use

### Takeaway
- **Kiwoom REST** (official): 5 calls/sec per account or token for domestic orders and inquiries; 50/sec overall for US stocks; lower at peak times.
- **LS REST** (official catalog): **1 TPS** for most account TRs (`CDPCQ04700`, `CSPAQ*`) and 2 TPS for `t0424`, `t0425`, `t0150` and `t0151`.
- **KIS**: the official docs say mock limits are lower than real, and the error code is `EGW00201`; exact numbers were not verified.
- **Terms**: specific clauses on personal-use-only or third-party data sharing were not retrieved.

### Cited Findings
- Kiwoom: "국내주식은 계좌별(토큰별)로 주문 TR과 조회 TR 모두 1초당 5회". US stock: 50/sec overall per account or token, 20/sec for charts, and reduced limits at peak (KST 09–10). — [공식 서비스 이용안내 (snippet)](https://openapi.kiwoom.com/intro/serviceInfo)
- Third-party wrappers report Kiwoom limits that differ from official numbers ("약 1회/초, 버스트 2건" vs "초당 20회"). — [unohee/pykiwoom-rest API reference (3rd)](https://github.com/unohee/pykiwoom-rest/blob/master/docs/KIWOOM_API_REFERENCE.md)
- LS: per-TR `requestLimit` in the official catalog: `CDPCQ04700`, `CSPAQ12200`, `CSPAQ12300`, `CSPAQ13700`, `CSPAQ22200` and `FOCCQ33600` = 1/sec; `t0424`, `t0425`, `t0150` and `t0151` = 2/sec; overseas `COSAQ00102`, `COSOQ00201` and `COSOQ02701` = 1/sec. — [미러 catalog](https://github.com/xorrhks0216/LsApiHelper)
- KIS: mock (모의) has lower REST call limits than real, and exceeding the per-second limit returns `EGW00201`. — [공식 README](https://github.com/koreainvestment/open-trading-api)
- KIS sample-code disclaimer: the code is for reference only, may change without notice, and the company accepts no liability. — [공식 GitHub](https://github.com/koreainvestment/open-trading-api)
- KIS advises its own users to keep token files hard for others to find — [공식 kis_auth.py](https://github.com/koreainvestment/open-trading-api/blob/main/examples_user/kis_auth.py)

### Inferences
- Daily sync of a family's handful of accounts is far below every limit. Throttle to ≤1 call/sec for LS account TRs, and use pagination keys (`FK100`/`NK100`, `cont-yn`/`next-key`, `tr_cont`).
- Because keys are bound to a personal HTS ID, the app should act **as each owner**, using their own key for their own accounts. That is consistent with a personal or family use pattern; a service operated for unrelated third parties would likely conflict with brokerage terms (unverified).

### Gaps
- Exact KIS per-second limits (often cited as 20/sec real and 2/sec mock) were **not verified** from an official page in this session.
- The terms-of-use text (이용약관) of each portal was not retrieved, so clauses on personal-use-only, redistribution, or third-party use are unverified.

---

## Q7. Known gaps (data NOT available via API) and practical workarounds

### Takeaway
The most common gaps are cash 입출금 (bank transfers), dividends, and full long-range history.
- **Kiwoom `kt00015`** largely closes these for Kiwoom.
- **LS `CDPCQ04700`** gives deposit, withdrawal, tax and fee totals.
- **KIS** dividends come from `CTRGA011R`, but no 입출금 endpoint was found.
- **Daishin** offers only snapshots and today's or yesterday's fills.

Workarounds: daily snapshots with reconciliation, one-time HTS/MTS CSV exports for backfill, and 마이데이터-based sources.

### Cited Findings
- Daishin `CpTd6033` excludes 펀드/RP valuation and 예수금 changes — [CpTd6033 (snippet)](https://cybosplus.github.io/cptrade_new_rtf_1_/cptd6033_.htm)
- Daishin fill TRs are limited to 금일 (`CpTd5341`) and 전일 (`CpTd5342`) — [CpTd5341](https://cybosplus.github.io/cptrade_new_rtf_1_/cptd5341_.htm); [CpTd5342](https://cybosplus.github.io/cptrade_new_rtf_1_/cptd5342_.htm)
- KIS 퇴직연금 APIs do not cover funds, and DC(55) accounts are unsupported — [공식 sample](https://github.com/koreainvestment/open-trading-api/blob/main/examples_user/domestic_stock/domestic_stock_functions.py)
- For KIS 3개월 이전 fills, query after market close and in short ranges to avoid DB lag — [공식 sample](https://github.com/koreainvestment/open-trading-api/blob/main/examples_user/domestic_stock/domestic_stock_functions.py)
- KIS overseas `period-rights` (`CTRGT011R`) marks "예정" entries as subject to change (reference only) — [공식 sample](https://github.com/koreainvestment/open-trading-api/blob/main/examples_user/overseas_stock/overseas_stock_functions.py)
- Kiwoom `kt00015` returns 적요명, 입출구분, 세금, 수수료 and FX fields, with types including 환전 and 외화매수/매도 — [미러 spec](https://github.com/KKimj/Kiwoom-REST-API)

### Inferences
- **KIS workaround for 입출금**: take a daily snapshot of 예수금 (`inquire-balance` output2 / `intgr-margin` / `foreign-margin`). Then subtract the day's trade settlements (`inquire-daily-ccld`) and dividends (`CTRGA011R`). The residual is an inferred deposit or withdrawal (or interest). Mark these rows as "inferred".
- **Daishin**: run a daily job on a Windows host to capture `CpTd6033` and `CpTd5341`. Import history via the HTS export once.
- **For every brokerage**: do an initial backfill from HTS or MTS 거래내역 export files, then switch to incremental API sync. Use (date, 거래번호/주문번호) as idempotency keys; Kiwoom `kt00015` provides `trde_no` and `orig_deal_no`.

### Gaps
- No official confirmation was found of whether KIS has any cash-ledger (입출금/거래내역) REST API beyond the sample-code set.
- Kiwoom: unverified whether `kt00015` covers ISA or 연금 accounts, or only 위탁.
- How far back (years) each API can go was not found in any official doc for any brokerage.
- Whether LS `CDPCQ04700` rows include dividend (배당금 입금) entries with tax breakdowns: unknown, since the OutBlock3 schema was not captured.
