# Third-party aggregation channels (CODEF / Hyphen / COOCON / Hecto) and MyData for multi-brokerage securities data — individual developer, Korea, as of 2026-10-19

> Research method note: The researcher's network could not reach developer.codef.io, codef.io, hyphen.im, help.banksalad.com, mydatacenter.or.kr, techbaekgwa.co.kr or news.nate.com. The proxy refused the connections or DNS failed. Findings below come from search-engine extracts of those pages, not full page reads. Treat specific field lists and numbers as "seen in a search snippet". Verify them against the live page before relying on them. Source dates are given where known.

## Q1. CODEF (코드에프, codef.io): coverage, securities endpoints, auth, tiers, pricing, individual eligibility, limits

### Takeaway
CODEF does have a securities (업무구분 "ST") product family. It is an "증권사 전계좌" API with endpoints for 등록여부, 입출금내역, 전계좌 종합자산 and 주식잔고조회. It authenticates via connectedId, created from a 공동인증서 (loginType 0) or ID/PW (loginType 1). Individuals can sign up, but only for the Demo tier (100 calls/day). The unlimited production tiers (Business/Partner) require registering 사업자 정보 and project details, followed by a review. A non-commercial family app is therefore realistically limited to the demo tier. The demo tier may also be time-limited (3 months in 2021–22 reports).

### Cited Findings
- CODEF's developer guide has a "증권사 전계좌 API - 증권" spec page. It is the securities product: [developer.codef.io/products/stock/common/a/account](https://developer.codef.io/products/stock/common/a/account) (via search extract; page not directly fetchable).
- Per a search extract of that spec, the 증권 전계좌 API covers **등록여부 (registration check), 입출금내역 (deposit/withdrawal history), 전계좌 종합자산 (all-account total assets), 주식잔고조회 (stock balance/holdings)**. It lists separate demo and production endpoint addresses. Required parameters differ by brokerage and are kept in a separate per-brokerage spreadsheet: [CODEF 증권사 전계좌 API](https://developer.codef.io/products/stock/common/a/account).
- Another extract of the same page mentions 보유계좌 빠른조회, 수시입출 거래내역 and 펀드 거래내역 shown together. It is unclear whether those are securities or bank items, and this extract conflicts in detail with the one above: [CODEF 증권사 전계좌 API](https://developer.codef.io/products/stock/common/a/account).
- CODEF's 2023 service brochure lists the securities data items as **등록여부, 보유계좌, 종합자산, 입출금 내역**. It does not list per-trade 매매(체결) 거래내역 or 해외주식: [CODEF API 서비스 소개서 2023.03 (PDF)](https://codef.io/assets/pdf/202303_CODEF_API_%EC%86%8C%EA%B0%9C%EC%84%9C.pdf); [CODEF API 서비스 소개서 2023.08 (PDF, ⓒ Hectodata)](https://codef.io/assets/pdf/202308_CODEF%20API%20%EC%84%9C%EB%B9%84%EC%8A%A4%EC%86%8C%EA%B0%9C%EC%84%9C.pdf). The 2023 brochures are copyrighted by Hectodata Co., Ltd., which indicates CODEF is a Hecto Data (헥토데이터) product.
- Business-type codes: 은행·저축은행 BK, 카드 CD, **증권 ST**, 보험 IS: [CODEF 개발가이드 – connected-id](https://developer.codef.io/common-guide/connected-id/list); [glossary](https://developer.codef.io/common-guide/glossary).
- Authentication: you register the end user's credentials once (계정 등록) and receive a per-user **connectedId**. Later calls use only the connectedId, with no resending of credentials. loginType 0 = certificate (공동인증서), 1 = ID/PW. The certificate password is sent RSA-encrypted with CODEF's public key. After a certificate is renewed or reissued, the account info on the existing connectedId must be updated. A connectedId is tied to the institutions registered under it: [CODEF connected-id guide](https://developer.codef.io/common-guide/connected-id/list); [account list](https://developer.codef.io/common-guide/connected-id/list-account).
- Demo and production use different hosts: development.codef.io (demo) vs api.codef.io (production): [CODEF connected-id guide](https://developer.codef.io/common-guide/connected-id/list) (search extract).
- Official SDKs exist, including Python (`easycodefpy`, `codef-python`), Java and Node. Their README examples show bank and card product paths, not securities: [github.com/codef-io/easycodefpy](https://github.com/codef-io/easycodefpy); [github.com/codef-io/codef-python](https://github.com/codef-io/codef-python); [easycodef-node (npm)](https://www.npmjs.com/package/easycodef-node).
- Tiers: "Developer (데모버전) can use the CODEF API up to 100 times a day." "Business, Partner (정식버전) have no call-count limit." To get production, you register 사업자 정보 and 프로젝트 정보, CODEF ops reviews the application, and approval comes within 3 business days: [CODEF glossary](https://developer.codef.io/common-guide/glossary) (search extract).
- "CODEF can be used by both individuals and corporate customers. The free version alone lets you build and test a system using real financial-institution accounts": [CODEF Interview #01, theteams.kr](https://www.theteams.kr/teams/8383/post/69628) (company-authored post, c. 2019–2020).
- 2021–2022 press: free demo trial with up to 100 requests/day **for 3 months**. Production is a monthly subscription, and about 140+ member companies used it (2022): [전자신문 2022-06-16](https://www.etnews.com/20220616000220); [전자신문 2021-06-21](https://www.etnews.com/20210621000087?m=1). The current guide extract does not mention the 3-month limit, so the current policy is unconfirmed.
- 2019 CODEF intro lists bank products only (20 banks, 64 savings banks). It has no securities list: [CODEF API를 소개합니다 (2019-12-12)](https://www.theteams.kr/teams/8383/post/70230).
- A 2026 student project (Dongguk Univ. capstone) has an issue for integrating the CODEF card API. It shows that students and individuals do use the demo tier in 2026: [GitHub CSID-DGU/2026-2-CCD-RichReach-01 issue #8](https://github.com/CSID-DGU/2026-2-CCD-RichReach-01/issues/8).

### Inferences
- With 100 calls/day on demo, a family of about 4 people × about 5 brokerages × 2–3 endpoints (balance, holdings, 입출금) fits in a daily batch sync. It does not fit frequent polling. If demo is still time-limited (3 months), demo is not a durable long-term channel.
- Production requires 사업자 정보 and a monthly subscription. An individual without a business registration likely cannot get production, but this is not confirmed by a primary source. A sole proprietorship (개인사업자) registration might qualify. Contact CODEF to verify.
- The documented securities scope is 잔고/종합자산/주식잔고/입출금. Per-trade buy/sell execution history (매매내역) and overseas stock holdings were **not** seen in any extract. Assume they are unsupported until verified.

### Gaps
- Exact list of supported 증권사: the per-brokerage spreadsheet is referenced but could not be accessed.
- Whether 매매(체결) 거래내역, 해외주식 잔고, 펀드/ETF/채권 holdings or 간편인증 (카카오/PASS etc.) login are supported for 증권.
- Current pricing amounts (KRW/month) for Business and Partner. Search extracts said the guide points to the main-site pricing page, which was unreachable.
- Whether the 3-month demo limit still applies in 2026, and whether an individual (non-사업자) can get production approval.

## Q2. Other aggregators: 하이픈 (Hyphen), 쿠콘 (COOCON), 헥토데이터 (Hecto Data), 인포플러스/웹케시 etc.

### Takeaway
Hyphen sells a scraping-based "개인계좌 증권사 조회" product covering securities accounts, 거래내역 and 잔액. COOCON and Hecto Data are B2B data-API vendors aimed at companies, with metered/minimum-fee pricing. No source confirmed that any of them accepts an individual without a business registration for production use. 인포플러스 and 웹케시 were not researched successfully. All of them should be assumed B2B-contract-only.

### Cited Findings
- Hyphen's product catalog lists a "개인계좌 증권사 조회" product, marked as **scraping-based**. It is described as letting you see "증권사 계좌부터 거래내역, 잔액조회까지 한 눈에". The financial-info section also lists products named "TR슬림" and "TR시그니처": [하이픈 상품 페이지](https://www.hyphen.im/product/) (search extract; page unreachable).
- COOCON: a data API and payments company. Its API store, 쿠콘닷넷, offers about 200 API products, and its main customers are institutions and companies. Its corporate CMS business collects data from banks, 증권 and cards for corporations: [thevc.kr 쿠콘](https://thevc.kr/coocon); [쿠콘닷넷](https://www.coocon.net/); [전자신문 2021-05-21](https://www.etnews.com/20210521000116).
- Hecto Data: usage-based (종량제) pricing with a minimum fee. It says startups and pre-founders (예비창업자) can use it, though that context was mostly its OCR products: [hectodata.co.kr](https://hectodata.co.kr/) (search extract). Hecto Data is the copyright holder of the CODEF brochures, so CODEF is effectively Hecto Data's developer-facing channel: [CODEF 소개서 2023.08](https://codef.io/assets/pdf/202308_CODEF%20API%20%EC%84%9C%EB%B9%84%EC%8A%A4%EC%86%8C%EA%B0%9C%EC%84%9C.pdf).

### Inferences
- CODEF is the only aggregator found with a documented self-serve free tier that individuals can sign up for. Hyphen, COOCON and Hecto Data's other channels appear to be sales/contract-based.
- Hyphen's "개인계좌 증권사 조회" is the closest functional match (거래내역 + 잔액). Its access terms for individuals are unknown.

### Gaps
- Hyphen: supported brokerages, data fields (holdings vs cash only), pricing, and whether individuals can contract.
- COOCON / Hecto Data: whether a retail-securities (개인 증권계좌) scraping product exists for third parties, and its sign-up requirements.
- 인포플러스, 웹케시 (and other scraping-solution vendors such as 스크래핑 SDK sellers): no usable results were found. Their products historically target corporations (ERP/CMS) and fintechs; this is unverified.

## Q3. MyData (금융투자 마이데이터): scope, and whether an individual can access their own data without a license; consumer-app export

### Takeaway
금융투자 업권 MyData standard APIs cover 계좌 목록, 기본정보, 거래내역, 상품정보 (holdings) and 연금/IRP, with up to 5 years of history. They are available only to licensed 본인신용정보관리업자 (MyData operators) through 금융보안원/종합포털-governed onboarding. An individual developer cannot call them directly. The 개인정보보호법 본인전송요구권 (download-to-self) started its all-sector expansion in 2025–2026. It may eventually let individuals download their own brokerage data as encrypted files, but finance-sector application and timing are unconfirmed. Among consumer apps, only Banksalad has a documented export: 자산 + 가계부 to Excel, last 1 year, with securities detail unconfirmed.

### Cited Findings
- 금융투자 업권 정보제공 API 규격 includes 계좌 목록 조회v2, 계좌 기본정보 조회v2, 계좌 거래내역 조회v2, 계좌 상품정보 조회v2, 연금계좌 추가정보 and 계좌지정 자동이체 등록정보: [developers.mydatakorea.org 금융투자 업권 API 규격](https://developers.mydatakorea.org/mdtb/apg/mac/bas/FSAG0402?id=4).
- Transaction history is paginated (cursor-based, `limit` param). Under 신용정보법 시행령 제28조의3제4항 it provides **up to the most recent 5 years** within the requested FROM/TO: [마이데이터 표준 API 기본 규격](https://developers.mydatakorea.org/mdtb/apg/dgi/bas/FSAG0101); [금융투자 업권 API 규격](https://developers.mydatakorea.org/mdtb/apg/mac/bas/FSAG0402?id=4).
- The authentication spec defines transfer-request items for 투자상품계좌: 기본정보, 거래내역, 상품정보 and 개인형 IRP. Tokens are issued to MyData operators. The 정보제공자 (or 중계기관) must include the `<industry>.list` scope: [데이터 표준 API 인증규격](https://developers.mydatakorea.org/mdtb/apg/dgi/bas/FSAG0102); [참여자별 API 처리 절차](https://developers.mydatakorea.org/mdtb/apg/dgi/bas/FSAG0103).
- KFTC runs a 마이데이터 중계 API system for credit-information providers that cannot build their own MyData API system. It is a provider-side relay, not a consumer channel: [KFTC 오픈API – mydata](https://openapi.kftc.or.kr/service/mydata).
- In the MyData flow, the user requests transfer in a MyData app, and the 정보제공자 sends the data via API **to the MyData operator**. The 신용정보법 전송요구권 is the right to have data sent to a designated third party: [토스피드 – 마이데이터란](https://toss.im/tossfeed/article/what-is-mydata); [KIRI 보고서 2021-04](https://kiri.or.kr/report/downloadFile.do?docId=37789).
- Since 2022-01-05 16:00, MyData operators must use API only. Scraping is banned **for MyData operators**: using 전자금융거래법 접근매체 to collect customer credit info. The ban does not apply to everyone. 33 operators launched then: [금융위원회 보도자료](https://www.fsc.go.kr/no010101/77182); [ZDNet 2022-01-04](https://zdnet.co.kr/view/?no=20220104193433); [대한금융신문](https://www.kbanker.co.kr/news/articleView.html?idxno=89528); [뉴시스 2022-01-04](https://www.newsis.com/view/NISX20220104_0001712399).
- 마이데이터 종합포털 is defined as a web service supporting, among other things, 일괄조회 of a customer's 개인신용정보 전송요구 내역 (transfer-request history). This is a list of consents, not the data itself: [데이터 표준 API 인증규격](https://developers.mydatakorea.org/mdtb/apg/dgi/bas/FSAG0102).
- 개인정보보호법 제35조의2 전송요구권 (all-sector MyData) took effect with the 2025-03-13 시행령 amendment. It has two forms: **본인전송** (sent to the data subject directly) and 제3자 전송. 본인전송 may be done by downloading, as an encrypted file, information already viewable on the company's website. Data must be stored where only the subject can access it: [대륜 뉴스레터](https://www.daeryunlaw.com/newsletter/news/158); [브릿지경제 2025-06-23](https://www.viva100.com/article/20250623500769); [BKL 뉴스레터](https://www.bkl.co.kr/law/insight/newsletter/6143).
- A 2025 시행령 amendment proposal expands 본인전송 from 3 sectors (보건의료·통신·에너지) to **all sectors**, with grace periods. SMEs and startups are excluded as data transmitters. Derived or analysed data is excluded: [이투데이](https://www.etoday.co.kr/news/view/2498595); [korea.kr 사실은 이렇습니다](https://www.korea.kr/briefing/actuallyView.do?newsId=148955011).
- 2026-08 reports: PIPC expands 본인전송요구권 starting from the public sector on 8/20. It **bans unauthorized scraping**, temporarily allows only pre-agreed "약속된 스크래핑", and plans a phased move to API: [네이트뉴스 2026-08-13](https://m.news.nate.com/view/20260813n30830) (search extract only); [블로터](https://www.bloter.net/news/articleView.html?idxno=663539). This rule targets agents that scrape on a subject's behalf under the 개인정보보호법 regime. It is separate from the 신용정보법 MyData operator rules.
- Consumer app export — **Banksalad**: 가계부 → ⚙ → [파일로 받기] produces an Excel file containing **[자산] and [가계부]** by category, merchant, amount and payment method. It always covers the 1 year before the request date; the period cannot be set. MyData-linked asset values are shown as received and can't be edited in-app: [뱅크샐러드 고객센터 #207](https://help.banksalad.com/207) (search extract); [Threads user guide 2025](https://www.threads.com/@ruangday/post/DJZLcuuTfS1). Whether the file includes per-holding securities detail or securities trades was **not confirmed**.
- Brokerages' own HTS/MTS let you export 계좌별 거래내역 to Excel. Example: 한국투자증권 화면 7451: [truefriend 7451](http://truefriend.com/pro_help/7451.html).
- 오픈뱅킹 was expanded to include 17 증권사, so bank apps can show those securities accounts' cash balances. No export feature was mentioned: [카드고릴라](https://www.card-gorilla.com/contents/detail/1553).

### Inferences
- MyData proper is closed to an individual developer. Becoming a 본인신용정보관리업자 requires an FSC license, capital and security audits, which is unrealistic for a family app.
- The realistic MyData-derived channel is **indirect**. Let a licensed app (Banksalad, Toss, etc.) aggregate the data, then ingest that app's export file. That works only where an export exists, which is confirmed only for Banksalad, at 1-year granularity and with unconfirmed securities detail. Brokerage-native Excel/CSV exports (one per brokerage, manual) remain the most reliable source for full trade history.
- The 2025–2026 본인전송 expansion could later give a legal, machine-readable "download my data" button at each brokerage. Securities-sector timing is unknown, and SMEs are exempt.

### Gaps
- Exact list of brokerages that act as 금융투자 MyData 정보제공자. It is generally all major 증권사, but no current list was retrieved from mydatacenter.or.kr (unreachable).
- Whether the 계좌 상품정보 조회 response includes per-stock quantity, average cost and valuation, and whether overseas stocks are included.
- Whether Toss, 네이버페이 내자산, 카카오페이, 핀크 or 레몬트리 offer any CSV/Excel export of securities data. No source was found for any of them.
- Whether the 개인정보보호법 본인전송 duty applies to 증권사 (finance is primarily governed by 신용정보법), and the effective date for the finance sector.

## Q4. Legal constraints for scraping own/family accounts, and credential-security practices

### Takeaway
No source was found that prohibits an individual from automating access to **their own** accounts. The 신용정보법 scraping ban applies to licensed MyData operators. The main legal risks are threefold. (1) Handling family members' 접근매체 (공동인증서, passwords, OTP) touches 전자금융거래법 제6조 rules on transfer and lending of access media. Case law treats non-paid temporary lending differently from 양도, but paid lending and use for crime are punishable. (2) Brokerage 약관 commonly forbid letting third parties use your access media. (3) Sending credentials to a third-party aggregator such as CODEF relies on that vendor's terms. Each family member should register their own credentials and consent, rather than the developer holding everyone's 공동인증서.

### Cited Findings
- 전자금융거래법 접근매체 (통장, 카드, 비밀번호, OTP, 공동인증서 etc.) 양도·양수·대여 is punishable. Law-firm sources state 5년 이하 징역 or 3천만원 이하 벌금 (제49조 제4항). One source states 3년/2천만원, so they conflict and the statute should be checked: [법무법인 YK](https://www.yklawfirm-crime.co.kr/blog/detective/12590); [bh-law](https://bh-law.kr/ko/news/column/efta-violation-first-offender-penalty-statute-limitations); [고운법률](https://gounlaw.com/legal-information/legal-information/152).
- 대법원 2012. 7. 5. 선고 2011도16167: lending or allowing temporary use is not "양도" under the Act. Lending conditioned on payment (대가) is separately punishable (제6조 제3항 제2호, 제49조 제4항 제2호): [casenote 2011도16167](https://casenote.kr/%EB%8C%80%EB%B2%95%EC%9B%90/2011%EB%8F%8416167).
- 대법원 2021도17151 (2023): providing access media knowing they may be used for crime is punishable, and 미필적 인식 is sufficient: [bh-law](https://bh-law.kr/ko/news/column/bankbook-rental-defense) (secondary).
- 신용정보법 scraping restriction applies only to MyData operators using 접근매체 to collect credit info: [ZDNet 2022](https://zdnet.co.kr/view/?no=20220104193433); [대한금융신문](https://www.kbanker.co.kr/news/articleView.html?idxno=89528).
- PIPC 2026: unauthorized scraping by agents in the 본인전송 context is banned, and only pre-agreed scraping is temporarily allowed: [블로터](https://www.bloter.net/news/articleView.html?idxno=663539); [네이트뉴스 2026-08-13](https://m.news.nate.com/view/20260813n30830).
- CODEF credential handling: the certificate password is RSA-encrypted client-side with CODEF's public key before transmission. Afterward, only the connectedId is used. Certificate renewal requires an account update: [CODEF connected-id guide](https://developer.codef.io/common-guide/connected-id/list).
- 본인전송 data must be stored in a repository accessible only to the data subject (PIPC rule for 본인전송): [대륜 뉴스레터](https://www.daeryunlaw.com/newsletter/news/158).

### Inferences
- For a family app, keep these as practical safeguards (not legal advice). Each adult family member registers their own credentials through their own login and consents explicitly. Prefer the aggregator's connectedId model, which avoids storing raw 인증서 and passwords after registration. If credentials must be stored locally, encrypt them at rest with a key held outside the DB, e.g. OS keyring/age/SOPS, or a passphrase-derived key (Argon2id) plus AES-GCM. Restrict the self-hosted server to LAN/VPN, and log every access. Do not store minors' or non-consenting relatives' credentials.
- Using a family member's 공동인증서 without payment, for their own benefit and with consent, is likely not 양도 under 2011도16167. It may still breach brokerage 약관, and any misuse would put the operator at risk. This is an inference and not a legal opinion. A lawyer or the brokerage should confirm.
- Brokerage-direct Open APIs (e.g., 한국투자증권 KIS Developers) are a cleaner legal path for brokerages that offer them, but they cover only one brokerage each. This is outside this note's scope, and another researcher may cover it.

### Gaps
- Specific brokerage 약관 clauses on automated access or third-party scraping of one's own account were not retrieved.
- No court case or regulator guidance was found specifically on an individual scraping their own or family securities accounts.
- CODEF and Hyphen terms of service: liability, data retention, and whether consumer (non-business) use of production is permitted.
