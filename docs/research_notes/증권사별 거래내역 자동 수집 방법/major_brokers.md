# 대형 증권사(미래에셋·NH·삼성·KB·신한·하나) 개인 계좌 데이터 자동 수집 방법 (as of 2026-10-19)

> Research-environment note: most Korean domains (sisajournal-e, newspim, investchosun, blog.kbsec.com, nhplug.com, wikidocs.net, securities.miraeasset.com) could NOT be fetched directly from this sandbox (DNS/proxy 403). Many findings below therefore come from search-engine result summaries/snippets of those pages rather than full-page reads. Only github.com/PLUG-OpenAPI/nhplug-sdk was read in full. Treat details (especially numbers) as "snippet-level" and re-verify on the official portals before building.

## Q1. Does each brokerage offer an official open API for individuals as of 2026? (product, launch, status, application, eligibility, cost)

### Takeaway
As of Oct 2026, three of the six offer individual-usable APIs: **NH투자증권** (new REST "Namuh PLUG / N2 PLUG", launched 2026-08-10, plus legacy Windows-DLL "QV OpenAPI"), **KB증권** (individual Open API in open beta since 2026-07-20, full launch planned within 2026), and **하나증권** (legacy Windows OCX "1Q Open API"/1Q Pro). **신한투자증권** has the legacy Windows OCX "신한i Indi" API (no 2026 REST launch found). **미래에셋증권** and **삼성증권** have no individual open API that could be found; 2026 industry articles listing new entrants do not name either.

### Cited Findings

**Industry context (2026)**
- Aug 2026 article: "some brokerages have run open APIs for years; latecomers 다올투자증권, KB증권, 토스증권 are introducing or pursuing open APIs"; KB started with a beta in July 2026. 미래에셋/삼성/신한/하나 not named as new entrants. — [시사저널e, 2026-08-08](https://www.sisajournal-e.com/news/articleView.html?idxno=422947) (snippet only; also [Daum mirror](https://v.daum.net/v/20260808100002260))
- Another Aug 2026 summary lists 한국투자·KB·NH투자·토스·DB증권 as having launched open API services; 메리츠증권 also launched one. — [시사오늘](https://www.sisaon.co.kr/news/articleView.html?idxno=204260); [SBS Biz](https://biz.sbs.co.kr/article/20000339624) (snippet only)
- Industry concern: server/security costs rise without separate fees; API-key exposure risks accounts. — [인베스트조선, 2026-08-19](https://www.investchosun.com/site/data/html_dir/2026/08/19/2026081980116.html) (snippet only)

**NH투자증권 (나무증권 / QV)**
- NH launched OpenAPI services "Namuh PLUG (나무 플러그)" and "N2 PLUG" on 2026-08-10; described as a platform to connect customer-built programs to NH's trading system for quotes, balance checks, and orders. — [농민신문, 2026-08-10](https://www.nongmin.com/article/20260810500525); [socialvalue.kr](https://www.socialvalue.kr/news/view/1065589951804775); [이데일리 마켓인](https://marketin.edaily.co.kr/News/ReadE?newsId=03673606645546008)
- Fees: domestic stock 0.01%, overseas stock 0.09% for API trades; API applicants get API-only commission discounts; new customers get "국내주식 24개월 완전무료 수수료". No API usage fee was reported. — [농민신문](https://www.nongmin.com/article/20260810500525); search summary of [nate 뉴스](https://m.news.nate.com/view/20260810n25719)
- Eligibility/application: need an NH투자증권 account; apply at nhplug.com via "API 사용신청" (login by QR via 나무증권 MTS or certificate, agree to terms), then receive APPKEY/APP Secret → issue Access Token. One APP KEY per 고객번호, usable for all of that customer's accounts. Support: Q&A board or apisupport@nhsec.com. — [nhplug.com 서비스 이용안내](https://www.nhplug.com/howto-use) (snippet only)
- REST + WebSocket. Production domain api.nhplug.com:8443, mock moapi.nhplug.com:8443; brand domains nhplug.com (나무) / n2plug.com (N2). acct_type 01 = 운영 일반, 02 = 운영 주문대리인, 03 = 모의투자. — [GitHub PLUG-OpenAPI/nhplug-sdk](https://github.com/PLUG-OpenAPI/nhplug-sdk)
- Unofficial count: "REST 49개, 실시간 27채널" — [ajussiguide blog (2026)](https://ajussiguide.com/ko/%EB%82%98%EB%AC%B4%EC%A6%9D%EA%B6%8C-api-%ED%94%8C%EB%9F%AC%EA%B7%B8-%ED%81%B4%EB%A1%9C%EB%93%9C-%EC%97%B0%EA%B2%B0/) (snippet; the SDK README also references 27 realtime channels)
- Legacy QV Open API: DLL-based Windows API; a Rust wrapper project notes it can run under Wine/Docker on Linux, but because it is Windows-event-driven it does not work properly in a headless (no display) environment. — [GitHub bekker/qvopenapi-rs](https://github.com/bekker/qvopenapi-rs) (search summary); [알뜰 송송 매거진](https://mg.jnomy.com/whatis-diff-stock-open-api)

**KB증권**
- Individual-customer Open API in **open beta since 2026-07-20**, announced 2026-08-04. Includes domestic & overseas stock quotes, order/modify/cancel, holdings balance, 체결내역 조회. — [뉴스핌, 2026-08-04](https://www.newspim.com/news/view/20260804000270); [파이낸셜뉴스](https://www.fnnews.com/news/202608041339192032); [뉴시스](https://www.newsis.com/view/NISX20260804_0003735986); [머니투데이](https://www.mt.co.kr/stock/2026/08/04/2026080414364184356)
- Application: KB증권 homepage "고객서비스 → Open API" menu, online after identity verification; requires a KB증권 account. — [뉴스핌](https://www.newspim.com/news/view/20260804000270); [KB증권 블로그](https://blog.kbsec.com/about/kb%EC%A6%9D%EA%B6%8C-open-api-%EC%82%AC%EC%9A%A9%EB%B2%95/) (snippet)
- Roadmap: follow-up upgrades through **November 2026** to expand API scope and eligible users; KB blog says formal (정식) launch is planned within 2026 and that schedule, features, call limits and service hours may change. — [뉴스핌](https://www.newspim.com/news/view/20260804000270); [KB증권 블로그](https://blog.kbsec.com/about/kb%EC%A6%9D%EA%B6%8C-open-api-%EC%82%AC%EC%9A%A9%EB%B2%95/) (snippet)
- Background: KB already ran a B2B Open API business with ~20 partners (fintechs, 투자일임·자문사, platforms) for embedded finance before opening to individuals. — [뉴스핌](https://www.newspim.com/news/view/20260804000270)
- Costs: no concrete amount found; KB blog says API usage fees and trading commissions may be applied on separate bases (check the Open API portal). — [KB증권 블로그](https://blog.kbsec.com/about/kb%EC%A6%9D%EA%B6%8C-open-api-%EC%82%AC%EC%9A%A9%EB%B2%95/) (snippet)
- **Conflict:** press releases say overseas-stock APIs are included in the beta; the KB official blog says overseas stocks are "향후 확대 예정". — [뉴스핌](https://www.newspim.com/news/view/20260804000270) vs [KB증권 블로그](https://blog.kbsec.com/about/kb%EC%A6%9D%EA%B6%8C-open-api-%EC%82%AC%EC%9A%A9%EB%B2%95/)
- REST vs other transport: not stated in the press articles found. — (search summary of KB articles)

**하나증권**
- "1Q Pro(API)" / 1Q Open API, offered as OCX (ActiveX) usable from any language supporting ActiveX Automation. — [하나증권 1Q Pro 소개](https://www.hanaw.com/main/customer/customer/CS_050600_T1.cmd) (snippet)
- Setup (third-party guides): download latest API module from 공지사항, register API in HTS (screen 0550); 공동인증서 required (금융인증서 not usable). — [wikidocs 머니스플릿 1-3](https://wikidocs.net/262167); [wikidocs 매직스플릿 1-4](https://wikidocs.net/269383) (snippets)
- Windows only; open-source projects instruct installing **32-bit (x86) Python**; K021/hana Python wrapper targets Python 3.7 + PyQt 5.9. — [GitHub K021/hana](https://github.com/K021/hana); [GitHub CodeIslet/hana-1Q](https://github.com/CodeIslet/hana-1Q) (search summaries)
- No 2026 REST API launch for 하나증권 found. 하나은행 launched "Hana API On" in Mar 2026 but it is a bank API (FX, loans, account opening), not securities. — [한국경제, 2026-03](https://www.hankyung.com/article/202603051561P); 하나금융 group API market lists a "하나금융투자 API" without details — [hanafnapimarket.com](https://www.hanafnapimarket.com/)

**신한투자증권**
- "신한i Indi(인디)" API: GUI/OCX-based like 키움 OpenAPI+, supports orders and inquiries, no realtime 조건검색; requires signing a 신한i Indi 사용계약서 first. Guide is 1–3 years old. — [wikidocs 신한i인디 파이썬 매뉴얼](https://wikidocs.net/21911); [book index](https://wikidocs.net/book/2167) (snippets)
- The "신한 Open API" portal (openapi.shinhan.com) is a group-level market for fintechs/developers, mostly bank/partner APIs; no individual-investor securities REST API found there. — [신한 Open API](https://openapi.shinhan.com/); [신한DS Open API](https://www.shinhands.co.kr/work/open-api)
- No 2026 news of a 신한투자증권 individual REST API found; 신한 not listed among 2026 entrants. — [시사저널e](https://www.sisajournal-e.com/news/articleView.html?idxno=422947) (snippet)

**미래에셋증권**
- Official page describes "AnyLink", a 매개 프로그램 that lets a customer's own strategy system connect to the Kairos HTS — not a modern open API. — [미래에셋 imf401](https://securities.miraeasset.com/imf/200/imf401.do) (snippet)
- Community post (~2023, "about 1005 days old") says 미래에셋 has no API support. — [클리앙](https://www.clien.net/service/board/cm_stock/18535784) (snippet; possibly outdated)
- An S저널 brief (~early 2026) mentions "연결 계좌 수 44만 돌파" attributed to an optimized open-API service, but context (which service/whose API) is unclear and it does not describe an individual retail API. — [S저널](https://www.s-journal.co.kr/news/articleView.html?idxno=38556) (snippet; treat as unverified)

**삼성증권**
- 나무위키: "삼성증권: 기관투자자한테만 API를 제공한다. 유료다." (undated). — [나무위키 알고리즘 트레이딩](https://namu.wiki/w/%EC%95%8C%EA%B3%A0%EB%A6%AC%EC%A6%98%20%ED%8A%B8%EB%A0%88%EC%9D%B4%EB%94%A9) (snippet)
- 삼성선물 (separate entity) runs an Open API developer center for overseas futures/options — not 삼성증권 stock accounts. — [openapi.ssfutures.com](https://openapi.ssfutures.com/)
- No 2026 news of a 삼성증권 individual API found. — (searches 2026-10-19)

### Inferences
- For a FastAPI app on Linux, **NH PLUG** (REST, pip-installable SDK) and **KB Open API** (beta) are the only realistic official API paths among these six. 하나 1Q and 신한 Indi require a Windows 32-bit Python process with GUI/event loop — feasible only as a separate Windows "collector" agent pushing data to the FastAPI server.
- NH QV OpenAPI is effectively superseded for new development by PLUG.
- 미래에셋/삼성 accounts will need non-API methods (Q3/Q4).

### Gaps
- KB Open API: transport (REST/WebSocket), portal URL, rate limits, fees, and whether 연금/ISA accounts are supported — articles and blog could not be fully read.
- NH PLUG: official eligibility for 연금저축/ISA/IRP accounts and corporate/minor accounts not confirmed.
- 하나 1Q / 신한 Indi current (2026) status, fees, and whether still accepting new applicants — only older guides found.
- Whether 미래에셋 or 삼성 have announced 2026–2027 plans for individual APIs — none found.

## Q2. If an API exists: which account-data queries are available, max history, rate limits, OS, Python usability, ToS restrictions?

### Takeaway
NH PLUG clearly exposes domestic and overseas **balance/holdings**, account list, asset status, realized P&L and realtime fill notifications, with ~5 req/s REST limit, 24h tokens and an official Python SDK; a dedicated cash-transaction (입출금/배당/이자/세금) history endpoint was not confirmed. KB's beta covers balance and 체결내역 (overseas disputed). Legacy OCX APIs (하나, 신한) offer inquiry TRs but are Windows-32-bit-bound; specific 거래내역 TRs were not confirmed.

### Cited Findings

**NH PLUG (from SDK README, spec version "260911"/2026-09)**
- Domestic: `/krstock/inquiry/v1/balance` (잔고), buyable/sellable quantity; account list `/n2/acctinfo`, `/common/list_accounts`; README also mentions `period`, `assetStatus`, `realizedPnl`, `currentExecution`. — [nhplug-sdk](https://github.com/PLUG-OpenAPI/nhplug-sdk)
- Overseas: `current_price`, `balance`, `buyable_amount`, `sellable_quantity`, `order_buy`. — [nhplug-sdk](https://github.com/PLUG-OpenAPI/nhplug-sdk)
- Realtime notification channels incl. `d2` 체결통보 (plus d0–d3, de, dj, dk, dv, dn); 27 channels total. — [nhplug-sdk](https://github.com/PLUG-OpenAPI/nhplug-sdk)
- No 거래내역/입출금(예수금 history) endpoint described in the README (details in docs/ and llms.txt, which could not be retrieved). — [nhplug-sdk](https://github.com/PLUG-OpenAPI/nhplug-sdk)
- Rate limits: REST measured limit 5 calls/s (SDK throttles at 4/s by default, configurable via `NHPLUG_RATE_LIMIT`); WebSocket subscription sends ≤10/s. — [nhplug-sdk](https://github.com/PLUG-OpenAPI/nhplug-sdk)
- Auth: APP_KEY/APP_SECRET env vars; access token valid 24h, cached at `~/.nhplug/token-*.json`, reissued only on 401; token endpoint only on production (moapi does not issue tokens). — [nhplug-sdk](https://github.com/PLUG-OpenAPI/nhplug-sdk)
- Python: `pip install nhplug` (extras `nhplug[instruments]` for pandas master files, `nhplug[tls]` for Windows TLS issues); functions `call`, `paginate` (연속조회), `subscribe`, `load_master`. OS not formally listed; README mentions Windows paths/TLS but REST itself is OS-agnostic. — [nhplug-sdk](https://github.com/PLUG-OpenAPI/nhplug-sdk)
- Realtime ports: domestic 7070, overseas 7080, mock notifications 17070 (relevant for firewalls). — [nhplug-sdk](https://github.com/PLUG-OpenAPI/nhplug-sdk)

**KB Open API (beta)**
- Beta APIs include 보유 잔고 확인 and 체결 내역 조회 (domestic; overseas disputed — see Q1). — [뉴스핌](https://www.newspim.com/news/view/20260804000270); [KB증권 블로그](https://blog.kbsec.com/about/kb%EC%A6%9D%EA%B6%8C-open-api-%EC%82%AC%EC%9A%A9%EB%B2%95/)
- Call limits and service hours "may change per operating policy" (no numbers found). — [KB증권 블로그](https://blog.kbsec.com/about/kb%EC%A6%9D%EA%B6%8C-open-api-%EC%82%AC%EC%9A%A9%EB%B2%95/) (snippet)

**하나 1Q Open API / 신한 Indi**
- 하나: OCX/ActiveX, Windows only, 32-bit Python, HTS registration + 공동인증서; CodeIslet/hana-1Q is described as a trade-data collector built on the 1Q Pro HTS API (possible reference for 거래내역 collection). — [GitHub CodeIslet/hana-1Q](https://github.com/CodeIslet/hana-1Q); [GitHub K021/hana](https://github.com/K021/hana) (search summaries)
- 신한 Indi: supports 주문 and 조회 via GUI OCX; no realtime 조건검색. — [wikidocs 21911](https://wikidocs.net/21911) (snippet)

**Reference for comparison (not in scope, only for context)**
- 한국투자증권 API: use period 1 year from application; may be terminated after 3+ months of no trading — illustrates the kind of ToS conditions to check on NH/KB portals. — [한국투자증권 Open API 안내](https://securities.koreainvestment.com/main/customer/systemdown/OpenAPI.jsp) (snippet)

### Inferences
- With NH PLUG, a nightly job can snapshot holdings/cash (domestic + overseas) and realized P&L; reconstructing deposits/withdrawals, dividends, interest, taxes and FX conversions may still require HTS export unless a 거래내역 endpoint exists in the full spec (check docs/ in the SDK repo or nhplug.com API guide).
- `acct_type 02 (주문대리인)` suggests delegated access may be supported, potentially useful for family accounts — but needs verification against ToS.
- Using an API key for family members' accounts likely requires each account holder to apply individually (one APP KEY per 고객번호).

### Gaps
- Max retrievable history periods for NH PLUG and KB endpoints — not found.
- Whether NH PLUG/KB cover 연금저축, IRP, ISA, 해외주식 통합증거금, 외화 예수금/환전 내역 — not found.
- ToS clauses on non-trading (data-only) use, inactivity termination, or third-party/family use for NH/KB — not found.
- Specific 하나 1Q / 신한 Indi TR codes for 거래내역(입출금·배당·세금) and max history — not found.

## Q3. If no API (or API lacks history): what can be exported manually from HTS/MTS/website, and is certificate-based scraping practical?

### Takeaway
All brokerages offer on-screen 거래내역 inquiry with Excel download on HTS/web; 삼성증권 and 미래에셋 (Kairos [0650]) are documented. These include 매매, 입출금 and 입출고 filtered by period — making periodic manual Excel export the most reliable fallback for 미래에셋/삼성 (and for cash-flow history at others). No evidence of automated periodic statement e-mail was found; scraping is technically possible but fragile (공동인증서/보안 프로그램).

### Cited Findings
- 삼성증권 web 거래내역: choose account + period, then "[엑셀파일다운로드]" to print or download Excel. — [삼성증권 도움말 bb003](https://www.samsungpop.com/help/bb003.html) (snippet); HTS help page [4513] 거래내역 also exists — [samsungpop 4513](https://www.samsungpop.com/contents/popdts/help/4513.html)
- 삼성 mPOP requires 공동인증서 for login (issued on phone or copied from PC). — [삼성증권 스마트폰 인증서 안내](https://www.samsungpop.com/ux/kor/customer/certificate/smarttablet/smartPhone.do) (snippet)
- 미래에셋 Kairos HTS [0650] 거래내역 조회: set period by date entry or buttons; searchable by 매매 plus 입출금 and 주식 입출고; filters 거래구분 (전체/입출금/입출고/매매), order (최근순/과거순), 종목코드; double-click opens 상세거래내역. Excel export and max period not stated on the page. — [미래에셋 Kairos 0650](https://securities.miraeasset.com/kairos/0650.htm) (snippet)
- Generic: brokerages' HTS/MTS allow 계좌 거래내역 inquiry and Excel download; widen the period to get full history. — [머니북 Q&A](http://www.moneybook.co.kr/pages/index.php?mid=qna&order_type=desc&page=147&sort_index=regdate&document_srl=551506) (snippet)
- Comparison point (out-of-scope broker): 한국투자 [7451] allows up to 10 years and customer-center e-mail/post delivery of 거래내역 on request — illustrates that 고객센터 can send historical statements. — [truefriend 7451](http://truefriend.com/pro_help/7451.html)
- NH QV-type Windows APIs fail in headless environments (relevant to any GUI automation/scraping approach on Linux). — [qvopenapi-rs](https://github.com/bekker/qvopenapi-rs)

### Inferences
- Practical fallback for 미래에셋/삼성/신한/하나: monthly (or quarterly) manual HTS/web Excel export of 거래내역 (구분=전체) per account, uploaded to the FastAPI app with a per-broker column-mapping parser. Excel columns typically include 거래일자, 거래구분/적요, 종목명, 수량, 단가, 거래금액, 수수료, 세금, 정산금액, 예수금 잔액 — **unverified; obtain real sample files** to build parsers.
- Direct login scraping of Korean brokerage websites is impractical for a family app: 공동인증서 + keyboard-security/anti-tamper plugins, frequent UI changes, and ToS risk.

### Gaps
- Exact Excel column sets for each broker's 거래내역 export — not obtainable from web sources; needs sample downloads.
- Max inquiry period for 미래에셋 [0650], 삼성 web 거래내역, NH/KB/신한/하나 HTS screens — not found.
- Whether any of these six send monthly 거래보고서/잔고통보 by e-mail in machine-readable form (PDF vs Excel) — not found (only postal/e-mail on request referenced for an out-of-scope broker).

## Q4. Partnerships / MyData / third-party aggregators an individual could leverage

### Takeaway
MyData (마이데이터 2.0, since 2025-06-18) lets consumers aggregate securities holdings in licensed apps (e.g., 미래에셋 "MY자산"), but MyData APIs are only available to licensed MyData operators, not to an individual's own app; brokerage B2B APIs (e.g., KB's ~20 partners) are partner-only. No evidence found that scraping-API vendors (CODEF) support securities 거래내역 for these brokers.

### Cited Findings
- MyData 2.0 launched 2025-06-18: users can select an industry (bank, insurance, securities) to view scattered assets at once; consent steps cut from 2 to 1; periodic transmission selectable from 1 week to 1 month; consent validity extendable from 1 year up to 5 years; transmissions stop after 6 months of inactivity and user data is deleted after 1+ year. — [금융위원회 보도자료 2025-06-18](https://fsc.go.kr/no010107/84785); [Daum 기사](https://v.daum.net/v/20250618145631437)
- 미래에셋증권 runs a MyData service "MY자산" that collects other institutions' asset info with consent. — [미래에셋 MY자산 약관](https://securities.miraeasset.com/hki/hki3031/n89.do); [미래에셋 마이데이터](https://digital.securities.miraeasset.com/my-data/) (snippets)
- KB증권 operates Open API-based embedded finance with ~20 B2B partners (fintechs, 투자일임·자문사, platforms) — partner, not individual, access. — [뉴스핌](https://www.newspim.com/news/view/20260804000270)
- 삼성증권 API reportedly institution-only and paid. — [나무위키](https://namu.wiki/w/%EC%95%8C%EA%B3%A0%EB%A6%AC%EC%A6%98%20%ED%8A%B8%EB%A0%88%EC%9D%B4%EB%94%A9) (undated)
- CODEF materials found (2019) describe bank/card/insurance/public data; no securities 거래내역 product or broker list was found. — [CODEF 소개 (theteams, 2019)](https://www.theteams.kr/teams/8383/post/70230); [easycodefpy](https://github.com/codef-io/easycodefpy)

### Inferences
- An individual cannot call MyData APIs directly (requires 본허가 MyData license); the realistic way to "leverage" MyData is to use an existing aggregator app for viewing only — it does not provide export into a custom app.
- For 미래에셋/삼성 accounts, the only programmatic-ish routes are manual exports or a Windows RPA script driving HTS export (fragile).

### Gaps
- Exact MyData 증권 data scope (거래내역 length, dividend/tax fields) — standard specification not retrieved.
- Whether any MyData-licensed app offers CSV/Excel export of aggregated securities transactions — not found.
- Whether CODEF or similar (e.g., Hyphen) currently supports 증권사 거래내역 scraping for these six — not confirmed.
