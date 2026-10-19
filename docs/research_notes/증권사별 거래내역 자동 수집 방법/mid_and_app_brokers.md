# 중소형·앱 기반 증권사: 본인 계좌 데이터 자동 수집 방법 (기준일 2026-10-19)

Scope: 유안타, 메리츠, 한화투자, DB증권(구 DB금융투자), 교보, 유진투자, 현대차, IBK투자, SK, 다올투자, 신영, 부국, 상상인, 토스증권, 카카오페이증권, and others not covered elsewhere (iM증권(구 하이투자), 우리투자증권, BNK투자 etc.).

Method note: direct page fetches to most Korean domains (news sites, codef.io, hyphen.im, eugenefn.com, tossinvest.com) failed in this environment (DNS failure or proxy 403). Many findings below therefore come from search-engine result summaries of the cited page, not a full read. GitHub and PyPI could be read directly. Items read only via search summary are marked "(search summary)".

## Q1. Official open API for individuals (per brokerage, as of Oct 2026)

### Takeaway
2026 brought a wave of REST open APIs from mid-size and app brokers. **DB증권, 메리츠증권, 토스증권 and 다올투자증권 now offer individual-usable REST APIs (or a REST-backed MCP) with balance/holdings and order/fill queries.** 유안타 and 유진 still offer only legacy Windows DLL/COM/OCX APIs. For 한화, 교보, 현대차, IBK, SK, 신영, 부국, 상상인, 카카오페이, iM, 우리투자 I found **no individual open API**. None of the APIs found clearly expose a full cash-transaction ledger (입출금/배당/세금 내역); they focus on balances, holdings and order/fill history.

### Comparison table

| 증권사 | Official API for individuals (2026) | Tech / OS | Account reads confirmed | Overseas stocks | Best fallback for full ledger |
|---|---|---|---|---|---|
| **DB증권** (renamed from DB금융투자) | Yes: DB증권 Open API (openapi.dbsec.co.kr) | REST + WebSocket, any OS; Python SDK | 국내 잔고, 체결내역, 예수금; 해외 잔고/증거금; 선물옵션·채권 잔고 | Yes (balance/margin, fills, orderable amount) | HTS/WTS export (not verified) |
| **메리츠증권** | Yes, in **beta**: Meritz Open API (openapi.imeritz.com) | REST (71 endpoints) + WebSocket (14), any OS | 예수금, 평가, 보유종목 (others in portal docs) | Not confirmed (has 환전 category) | Not verified |
| **토스증권** | Yes, GA on **2026-08-13** for all customers (developers.tossinvest.com) | REST/OpenAPI spec; LLM/MCP use promoted | Account, Asset, Order History categories; integrated domestic + US | Yes (domestic + US integrated) | In-app 증명서: 거래내역서/잔고증명서 PDF |
| **다올투자증권** | Yes (MCP-first): "MCP 트레이딩" GA **2026-10-01**; REST backend openapi.daolsecurities.com | OAuth2 REST behind a local MCP server; macOS/Win10-11 x64/Linux desktop | account-balance (예수금·평가·보유종목), order-list/detail (체결·미체결) | Overseas order endpoints exist; MCP docs say overseas "planned" | Not verified |
| **유안타증권** | Yes (legacy): 티레이더 Open API (since Dec 2017) | DLL (C/C++) and COM (VB/C#/Delphi), **Windows 7+ only**; Android API (3rd-party claim) | 시세·잔고·주문 TR | Not confirmed | HTS/MTS (not verified) |
| **유진투자증권** | Yes (legacy): 챔피언 Open API | OCX/DLL, **Windows only** | Not detailed (search summary) | Not confirmed | Not verified |
| **카카오페이증권** | **None found** | – | – | – | In-app 증권거래내역 (period selectable), PDF (unverified); MyData via 뱅크샐러드 etc. |
| 한화투자, 교보, 현대차, IBK투자, SK, 신영, 부국, 상상인, iM증권, 우리투자증권, BNK투자, 한양 etc. | **None found** | – | – | – | HTS/WTS Excel, 거래내역서; CODEF-type scraping (coverage unverified) |

### Cited Findings

**DB증권 (formerly DB금융투자)**
- Official portal openapi.dbsec.co.kr; REST at `https://openapi.dbsec.co.kr:8443` (same host for production and demo, app key decides), WebSocket on 7070 (prod) / 17070 (demo). Get APP_KEY/APP_SECRET by opening a DB증권 account and applying for the Open API service. The repo names "개인 투자자" as a target user — [DBsecurities/dbsec-open-api (GitHub)](https://github.com/DBsecurities/dbsec-open-api)
- SDK account functions: `kr_stock_inquire_balance`, `kr_stock_inquire_executions` (체결내역), `kr_stock_inquire_deposit` (예수금), `ov_stock_inquire_balance_margin` (해외주식 잔고/증거금, includes average purchase price), `kr_futopt_inquire_balance`, `bond_inquire_balance`. No named "거래내역 (cash ledger)" function was found. Access token valid 24h. Python 3.10+, setup steps given for macOS/Linux/Windows — [DBsecurities/dbsec-open-api](https://github.com/DBsecurities/dbsec-open-api)
- The portal has a "주식잔고조회" API page, and its list includes overseas balance/margin, overseas fills and orderable amount — [DB증권 OPEN API 주식잔고조회](https://openapi.dbsec.co.kr/apiservice?group_id=05ac28b8-624f-4115-8aed-cf55f24279dd&api_id=07a86b9a-0548-47cd-baa9-24395d4ea4bb) (search summary)
- Sept 2026 "Open API 웰컴 페스티벌" (until Oct 30) for new and dormant customers: 0.01% domestic commission via Open API until Dec 31. Press describes it as "웹 표준 REST, 별도 프로그램 설치 없이" — [Newspim 2026-09-08](https://www.newspim.com/news/view/20260908000926); [머니투데이 2026-09-08](https://www.mt.co.kr/stock/2026/09/08/2026090814105246478); [MTN 2026-09-08](https://news.mtn.co.kr/news-detail/2026090810595690126) (search summary)
- Launch date of DB's REST Open API: not found.

**메리츠증권**
- Open API: REST base `https://openapi.imeritz.com:9443`, WebSocket `wss://openapi.imeritz.com:29443/websocket`. Repo includes an OpenAPI 3.1 spec (71 REST endpoints) and an AsyncAPI 3.0 spec (14 real-time). Categories: 주문, 시세, 계좌, 실시간, 환전, 참조. App Key is tied to one securities account. **Service is in beta.** No paper trading. Sample `04_account.py` covers 예수금/평가/보유종목. Read-only mode is the default. The repo also ships an MCP server — [meritz-securities/open-api (GitHub)](https://github.com/meritz-securities/open-api); [Meritz GitHub org](https://github.com/meritz-securities)
- Portal: openapi.imeritz.com (`/apiservice` docs, `/api-apply`, `/qna`) — [meritz-securities/open-api](https://github.com/meritz-securities/open-api)
- SBS Biz: "AI가 주식 사고파는 시대…메리츠도 '오픈 API' 참전". No usage fee; existing account commissions apply. Per the GitHub org summary, it is open to any individual with a Meritz account — [SBS Biz](https://biz.sbs.co.kr/article/20000339624) (search summary; article date not captured, context indicates 2026)

**토스증권**
- Official Open API **formally launched 2026-08-13** for all customers, after pre-registration that began in May 2026. Features: 종목 정보 조회, **본인 계좌 정보 조회**, 일반·조건 주문, 실시간 시세. Can be connected to ChatGPT/Claude — [파이낸셜뉴스 2026-08-13](https://www.fnnews.com/news/202608131648502325); [인더스트리뉴스](https://www.industrynews.co.kr/news/articleView.html?idxno=84404); [토스증권 뉴스룸](https://corp.tossinvest.com/ko/news-room/detail?id=52615) (search summary)
- Pre-registration press coverage (May 2026) on 새벽 자동매매 and AI 계좌분석 — [Daum/2026-05-21](https://v.daum.net/v/20260521073602305) (search summary)
- Docs: https://developers.tossinvest.com/docs. Spec v1.2.17 has 13 categories, including **Account, Asset, Order, Order History, Order Info**, Conditional Order (History), Market Data and others. Individual endpoint names were not visible — [tossinvest-openapi-mcp (GitHub)](https://github.com/JeongSeongMok/tossinvest-openapi-mcp)
- Third-party guides: domestic and US stocks share one integrated API. Account calls need an account-identifier header in addition to the token — [juhoplayground](https://juhoplayground.github.io/posts/Toss-Invest-Open-API-Korean-US-Market-Data/); [zerry.co.kr](https://zerry.co.kr/blog/tossinvest-open-api-guide); [algolab](https://algolab.co.kr/blog/toss-securities-open-api-guide-2026) (search summary; secondary sources)
- Open API terms of service page exists — [토스증권 오픈 API 서비스 이용 약관](https://corp.tossinvest.com/en/terms/v2?id=752)
- Unofficial alternative: `tossinvest-cli` (`tossctl`, Go, by JungHoonGhae) reuses a Toss **web session** to read account, portfolio and quotes, outputs JSON, and has trading behind config flags. It uses internal web APIs, may violate the ToS and can break without notice — [typingmind MCP listing](https://www.typingmind.com/mcp/tossinvest-cli); [GeekNews Show GN](https://news.hada.io/topic?id=27782) (search summary)

**다올투자증권**
- "MCP 트레이딩" **formally opened 2026-10-01**: connects ChatGPT/Claude to the account for balance checks and orders. The connection key is issued in the MTS "Fi" app — [파이낸셜뉴스 2026-10-01](https://www.fnnews.com/news/202610011117396388) (search summary). Pre-reservation opened July 2026, with a stated plan to open the API to outside developers and partners in phases — [스마트투데이](https://www.smarttoday.co.kr/ko-kr/articles/109806); [시대 2026-07-27](https://www.sidae.com/article/2026072712581184387) (search summary)
- PyPI `daol-mcp` (v0.1.40, uploaded 2026-09-29) is the official local MCP server. **App Key/App Secret are issued in Fi app → 고객 서비스 → MCP 이용 신청.** Reads: 예수금·평가금액·총자산·평가손익, 보유종목, 체결·미체결 주문 목록/상세. "현재는 국내주식 우선, 해외주식 지원 예정". Platforms: macOS, Windows 10/11 x64, Linux desktop with Secret Service — [PyPI daol-mcp](https://pypi.org/project/daol-mcp/); repo [daol-securities/daol-mcp](https://github.com/daol-securities/daol-mcp)
- Inspecting the wheel shows it calls an OAuth2 REST backend at `https://openapi.daolsecurities.com/svc`. Paths include `/oauth2/token`, `/api/v1/account-balance`, `/api/v1/order-list`, `/api/v1/order-detail`, `/api/v1/overseas-order-list`, `/api/v1/overseas-quotes`, plus order endpoints — [PyPI daol-mcp package contents](https://pypi.org/project/daol-mcp/) (own inspection of v0.1.40 wheel, 2026-10-19)
- 2026-10-19: Daol supports US stock trading via a TradingView integration — [파이낸셜뉴스 2026-10-19](https://www.fnnews.com/news/202610191400481346) (search summary)

**유안타증권**
- 티레이더 OPEN API launched December 2017 — [뉴시스 2017-12-04](https://www.newsis.com/view/NISX20171204_0000166220); [EBN](https://www.ebn.co.kr/news/articleView.html?idxno=920207)
- Official service page flow: apply → download/install module → build strategy → test with "데뷰(Deview)" TR tester. The API handles 시세, 잔고 and 주문. PC versions are DLL (C/C++) and COM (VB, C#, Delphi), **Windows 7+**. Samples are built with Visual Studio 2010 — [유안타 서비스 소개](https://www.myasset.com/myasset/trading/apiSvc/TR_1604001_P1.cmd); [모듈 다운로드](https://www.myasset.com/myasset/trading/apiSvc/TR_1604003_P1.cmd) (search summary)
- A third-party comparison lists "티레이더 Open API (DLL, COM, Android API)" — [알뜰 송송 매거진](https://mg.jnomy.com/whatis-diff-stock-open-api) (search summary; about 2023)
- No 2024–2026 news of a REST API from Yuanta was found.

**유진투자증권**
- "챔피언 Open API": available to customers with a Eugene account and a linked HTS ID, after applying. OCX/DLL control, Windows — [유진투자증권 챔피언 Open API 신청](https://www.eugenefn.com/opapi/opapi100.do) (search summary)

**Brokers with no API found**
- 한화투자증권, 교보증권, iM증권, IBK투자증권: targeted searches found only MTS app listings and no Open API announcement — [App Store 한화투자증권 MTS](https://apps.apple.com/kr/app/steps-%EB%AA%A8%EB%91%90%EA%B0%80-%EB%B0%94%EB%9D%BC%EB%8D%98-%EC%B0%B8-%EC%89%AC%EC%9A%B4-%ED%88%AC%EC%9E%90/id1200606784); [App Store iM증권](https://apps.apple.com/kr/app/%ED%95%98%EC%9D%B4%ED%88%AC%EC%9E%90%EC%A6%9D%EA%B6%8C-im%ED%95%98%EC%9D%B4/id1671683542) (absence of evidence)
- 카카오페이증권: a Kakao DevTalk thread (about 4 years old) asks whether a REST API is planned, with no official answer. No official API documentation was found — [Kakao DevTalk](https://devtalk.kakao.com/t/api/122181) (search summary)
- Industry roundups (Aug–Sep 2026) list 토스, 다올, KB, NH and 한투 as launching or strengthening open APIs. 한화, 교보, 현대차, IBK, SK, 신영, 부국, 상상인 and 우리투자 are not mentioned — [시사저널e (2026-08-08)](https://www.sisajournal-e.com/news/articleView.html?idxno=422947); [뉴스투데이 2026-09-01](https://www.news2day.co.kr/article/20260901500312); [인베스트조선 2026-08-19](https://www.investchosun.com/site/data/html_dir/2026/08/19/2026081980116.html) (search summary). 인베스트조선 notes cost and security burdens and unclear monetization as reasons for hesitation.

### Inferences
- For a family asset app, **DB, Toss, Meritz and Daol are the realistic API targets** (REST, any OS, server-side friendly). Yuanta and Eugene require a Windows box running a 32/64-bit COM/OCX client, which is impractical for a web app unless you run a Windows agent.
- Daol's REST backend (openapi.daolsecurities.com) is reachable with the same App Key/Secret, so a custom client could call it directly. However, it is officially documented only through the MCP package, and the API may change without notice. Treat it as semi-official.
- Meritz is still "beta" and Toss's API is two months old (GA Aug 2026), so expect endpoint churn. Pin to the published openapi.json.
- None of the APIs confirmed a 입출금/배당/이자/세금 cash ledger endpoint. Dividends and cash transfers will probably still need statement or Excel import, even for API brokers. This should be verified in each portal's docs.

### Gaps
- Full endpoint lists for the Toss Account/Asset/Order History categories, and whether Toss exposes deposit/withdrawal/dividend history: not visible (developers.tossinvest.com could not be fetched).
- Meritz portal endpoint list, eligibility (e.g., corporate or foreign accounts) and rate limits: not stated on GitHub.
- DB: whether there is a cash-ledger (거래내역) API, and the API launch date.
- Yuanta: whether 티레이더 Open API is still accepting applications in 2026, 64-bit support, and the exact account TRs.
- 현대차, SK, 신영, 부국, 상상인, 우리투자, BNK, 한양, 리딩, 코리아에셋, 흥국: no API information found at all. Status as of 2026 (including any rename or merger of 상상인증권) was not verified.

## Q2. App-only brokers (토스증권, 카카오페이증권): developer API, export, MyData

### Takeaway
**토스증권 now has an official Open API (GA 2026-08-13)** with account and asset queries for domestic and US stocks, plus in-app PDF certificates (거래내역서, 잔고증명서, 거래확인서). **카카오페이증권 has no developer API.** Its data paths are the in-app transaction history and MyData-connected apps (뱅크샐러드, 토스 etc.). These apps show balances but give the user no export API.

### Cited Findings
- Toss Open API: see Q1 (GA 2026-08-13; account info, US + domestic) — [파이낸셜뉴스](https://www.fnnews.com/news/202608131648502325)
- Toss official FAQ: 앱 메뉴 → 설정 → 계좌관리 → **증명서 발급하기**. Documents: 잔고 증명서, **거래 내역서**, 거래확인서, 계좌 개설 확인서. Issued as **PDF** — [토스증권 FAQ](https://corp.tossinvest.com/ko/faq) (search summary)
- Blog walkthrough: 잔고증명서 can be issued in Korean or English for a chosen reference date, then saved as PDF or shared — [LiFe아미고](https://lifesotiming.com/%EC%A3%BC%EC%8B%9D-%EC%9E%94%EA%B3%A0%EC%A6%9D%EB%AA%85%EC%84%9C-%EB%B0%9C%EA%B8%89-%EB%B0%A9%EB%B2%95-%ED%86%A0%EC%8A%A4%EC%A6%9D%EA%B6%8C/) (search summary)
- Unofficial: tossinvest-cli reads account and portfolio via web session reuse (ToS risk) — [typingmind listing](https://www.typingmind.com/mcp/tossinvest-cli)
- KakaoPay Securities: transactions viewable in-app via 더보기 → 증권거래내역, with 1/3/6/12-month or custom ranges. One source claims PDF output. Reportedly app-only (no web) — [phongnhaexplorer Q&A](https://ko.phongnhaexplorer.com/ko/%EC%9D%80%ED%96%89/%EC%B9%B4%EC%B9%B4%EC%98%A4%ED%8E%98%EC%9D%B4%EC%A6%9D%EA%B6%8C%EC%97%90%EC%84%9C-%EB%82%B4-%EC%A6%9D%EA%B6%8C%EA%B1%B0%EB%9E%98-%EB%82%B4%EC%97%AD%EC%9D%84-%EC%96%B4%EB%96%BB%EA%B2%8C-%EC%A1%B0.html) (low-quality aggregator; unverified)
- KakaoPay Securities notice on 타사 거래내역 document submission (for account transfers, not an export feature) — [카카오페이증권 공지](https://www.kakaopaysec.com/customer/notice/dynamicBoardPageDetail.do?id=6195) (search summary)
- MyData: 뱅크샐러드 added 토스증권 and 카카오페이증권 asset data in January 2022 — [전자신문 2022-01-20](https://www.etnews.com/20220120000176). "마이데이터 2.0" launched 2025-06-19. 토스 can now load all assets by sector, including 증권 (previous limit: 50 institutions) — [디지털데일리 2025-06-19](https://m.ddaily.co.kr/page/view/2025061910444128214); [에너지경제](https://m.ekn.kr/view.php?key=20250619022208312)
- An anecdotal user post says 토스증권 trades and dividends are not reflected in the 토스 가계부, while other brokers' dividends arrive via MyData — [Threads post](https://www.threads.com/@fin__wisdom__/post/DHgoaMVB2l9/) (anecdote, undated)

### Inferences
- MyData is licensed B2B: an individual can't call it for their own app. The only individual route is to view data inside a licensed app (뱅크샐러드, 토스, 증권플러스 etc.), which offers no programmatic export. So MyData does not help a self-built family app unless the app itself becomes a licensed MyData operator.
- For Toss, the new Open API is the primary path for holdings and orders. Monthly 거래내역서 PDFs (parsed) can fill cash and dividend gaps.
- For KakaoPay, the realistic paths are manual (in-app history or PDF) or a commercial scraping aggregator, if one supports it (unverified).

### Gaps
- Whether Toss 거래내역서 is available as Excel, by email, and how far back it goes: not found.
- KakaoPay Securities Excel/email export and maximum history period: not confirmed from an official source.
- Whether either app supports dividend-only history export: not found.

## Q3. Manual exports (HTS/MTS/web Excel, statements, email reports)

### Takeaway
Little broker-specific, verifiable export information surfaced in this round. Only Toss (PDF certificates via official FAQ) and KakaoPay (in-app history, unofficial source) had any. Exports for traditional brokers (유안타, 한화, 교보 etc.) are generally done in HTS screens with Excel save, but **I could not verify menu names or retention periods for any specific broker in scope.**

### Cited Findings
- Toss: 거래내역서/잔고증명서/거래확인서 PDF via 설정 → 계좌관리 → 증명서 발급 — [토스증권 FAQ](https://corp.tossinvest.com/ko/faq) (search summary)
- KakaoPay Securities: in-app 증권거래내역 with selectable period, possible PDF — [phongnhaexplorer](https://ko.phongnhaexplorer.com/ko/%EC%9E%AC%EC%A0%95/%EC%B9%B4%EC%B9%B4%EC%98%A4%ED%8E%98%EC%9D%B4%EC%A6%9D%EA%B6%8C%EA%B3%84%EC%A2%8C-%EB%82%B4%EC%97%AD%EC%9D%80-%EC%96%B4%EB%96%BB%EA%B2%8C-%EC%A1%B0%ED%9A%8C%ED%95%98%EB%82%98%EC%9A%94.html) (unverified)
- 금융투자협회 describes 계좌정보통합관리서비스 (일괄조회 of own accounts across 22 brokerages). It is a lookup and closing service, not a data export — [KOFIA](https://www.kofia.or.kr:12443/brd/m_153/list.do) (search summary)

### Inferences
- Statutory monthly/quarterly 거래내역 통보 (email statements) and HTS Excel export likely exist at all traditional brokers, but this is **not evidenced** here and should be confirmed per broker (customer-center FAQ or phone).

### Gaps
- Per-broker HTS screen numbers, Excel/CSV availability, history depth and email statement formats for 유안타, 메리츠, 한화, DB, 교보, 유진, 현대차, IBK, SK, 다올, 신영, 부국, 상상인: **not found** (broker sites could not be fetched; searches returned nothing specific).

## Q4. Scraping aggregators (CODEF, 하이픈, 쿠콘) coverage

### Takeaway
CODEF has a "증권사 전계좌 API" (holdings, 수시입출 거래내역, 주식잔고) with **per-broker required parameters kept in a Google Sheet**. Its broker list could not be retrieved, so **coverage for each in-scope broker is unverified**. 쿠콘 claims connections to all domestic brokers for B2B use. Nothing was found for 하이픈.

### Cited Findings
- CODEF "증권사 전계좌 API": covers 보유계좌, 수시입출 거래내역 and 주식잔고조회. "각 증권사에서 요구하는 API 파라미터 필수 값이 다르다", with per-broker requirements in a linked Google spreadsheet. Endpoints: development.codef.io (demo) and api.codef.io (prod) — [CODEF 증권사 전계좌 API](https://developer.codef.io/products/stock/common/a/account) (search summary)
- CODEF connected-ID guide: business type code **ST = 증권** plus an institution code — [CODEF 계정 목록 가이드](https://developer.codef.io/common-guide/connected-id/list-account) (search summary)
- Older CODEF product list (2019) names 증권사 보유계좌, 종합자산, 입출금거래내역, 등록여부 — [theteams CODEF 소개 (2019-12-12)](https://www.theteams.kr/teams/8383/post/70230); 2023 brochures: [CODEF API 소개서 2023-03](https://www.codef.io/assets/pdf/202303_CODEF_API_%EC%86%8C%EA%B0%9C%EC%84%9C.pdf), [2023-07](https://codef.io/assets/pdf/202307_CODEF_API_%EC%86%8C%EA%B0%9C%EC%84%9C.pdf) (not readable here)
- 쿠콘 "국내 전 증권사 중계망 구축" (2023 company analysis); collects data from about 500 institutions including all 증권사; offered via the 쿠콘닷넷 API store, mainly for corporate CMS — [쿠콘 기업분석 PDF 2023-03](https://ssl.pstatic.net/imgstock/upload/research/company/1677732291550.pdf); [전자신문 2021-05-21](https://www.etnews.com/20210521000116)
- 하이픈 (hyphen.im): no search results; the site was blocked from this environment.

### Inferences
- CODEF is the most plausible scraping aggregator for retail brokers without APIs (한화, 교보, 현대차, IBK, SK, 신영, 부국 etc.), but the sheet must be checked. App-only brokers (Toss, KakaoPay) often lack the certificate-based web login that scrapers rely on, so their coverage is uncertain.
- Aggregators are B2B (business registration and contracts are typical). Individual hobby use may not be accepted. This is unconfirmed.

### Gaps
- Actual CODEF/쿠콘/하이픈 broker support lists for each in-scope broker, pricing, and whether individuals can sign up: **not found** (developer.codef.io, codef.io and hyphen.im were proxy-blocked; searches didn't surface the sheet).
