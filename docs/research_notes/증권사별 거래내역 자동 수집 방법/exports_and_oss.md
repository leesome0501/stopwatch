# 한국 증권사 거래내역/잔고 파일 내보내기 형식과 오픈소스 수집 도구 (기준일 2026-10-19)

> 조사 환경 메모: 이 세션에서는 대부분의 증권사 도메인(securities.miraeasset.com, truefriend.com, help2.kbsec.com 등)과 news.hada.io, algolab.co.kr를 직접 가져올 수 없었습니다(DNS 실패 또는 프록시 403). GitHub REST API도 막혀 있었습니다. 그래서 증권사 화면 경로는 검색 결과의 요약과 발췌에만 근거하고, 오픈소스 유지보수 상태는 주로 PyPI JSON 메타데이터(pypi.org/pypi/<pkg>/json, 2026-10-19 조회)와 github.com 페이지 가져오기 결과에 근거합니다. 아래에서 "확인 못 함"으로 표시한 항목은 정말로 확인하지 못한 것이며, 정보가 없다는 뜻이 아닙니다.

## Q1. 증권사별 거래내역·잔고 파일 다운로드 경로, 형식, 열 머리글, 기간 제한, 특이점

### Takeaway
요청한 12개 증권사 중 출처로 확인한 것은 일부뿐입니다. 미래에셋 HTS [0650] 거래내역 조회 화면, 한국투자증권 홈페이지·HTS 거래내역 조회(엑셀 다운로드 가능), KB증권 HTS의 범용 내보내기(엑셀/CSV/HTML/TXT) 정도입니다. 증권사별 정확한 메뉴 경로, 열 머리글, 다운로드당 최대 기간은 이번 조사에서 대부분 확인하지 못했습니다. 실제 파일 표본을 모아 파서를 만드는 단계가 따로 필요합니다.

### Cited Findings
- **미래에셋증권 HTS [0650] "거래내역 조회"**: 계좌 거래내역 화면입니다. 매매내역뿐 아니라 입출금, 주식 입출고 내역도 기간별로 검색할 수 있습니다. 조회된 행을 더블클릭하면 상세거래내역 화면이 열립니다. 조회 기간과 거래구분을 먼저 설정하고, 화면 하단에 결과가 나열됩니다. 도움말 페이지에는 엑셀 저장 방법이 나오지 않습니다. — [미래에셋 [0650] 거래내역 조회](https://securities.miraeasset.com/kairos/0650.htm) (검색 발췌로만 확인, 원문 접근 실패)
- **한국투자증권**: HTS와 홈페이지에서 증권계좌의 거래내역과 입출고내역을 조회할 수 있습니다. 거래내역을 우편으로 받으려면 HTS에서 "거래내역 통보"를 신청해야 하며, 신청월분부터 익월 중순에 발송됩니다. — [한국투자증권 고객센터 안내](https://securities.koreainvestment.com/main/customer/bank/_static/TF04ba030000.jsp)
- **한국투자증권 홈페이지 마이페이지 도움말**: "조회된 내역의 인쇄 혹은 엑셀다운로드가 가능합니다." — [truefriend popup_mypage04](https://www.truefriend.com/main/help/popup_mypage04.jsp?d1=1&d2=4) (검색 발췌)
- **KB증권 HTS 도움말(1005.pdf)**: 출력된 데이터를 "엑셀, 엑셀(색상 그대로 반영), CSV, HTML, TXT"로 내보낼 수 있습니다. 화면 공통 내보내기 기능으로 보입니다. — [KB증권 help2 1005.pdf](https://help2.kbsec.com/pdf/1005.pdf) (검색 발췌)
- **키움증권**: kiwoom.com 메뉴에 '거래내역', '계좌정보', 'ISA 거래내역' 항목이 있다는 것만 확인했습니다. 화면번호(예: 0343)와 엑셀 저장 절차는 검색 결과에서 확인하지 못했습니다. — [키움 메뉴 페이지](https://www.kiwoom.com/wm/mnp/mnpStartMain?kind=isa)
- **미래에셋 M-STOCK(MTS)**: 앱 설명상 잔고현황 등을 MY자산·MY연금·MY펀드·MY정보 화면에서 확인할 수 있습니다. 엑셀 내보내기나 이메일 발송 기능은 설명되어 있지 않습니다. — [App Store M-STOCK](https://apps.apple.com/us/app/-/id1248716281)
- **토스증권**: 전체 메뉴 → 고객센터 → 토스증권 증명서 → 송금확인증 경로가 블로그에 나옵니다. 다만 이는 거래내역서 발급 경로가 아닙니다. 토스증권 거래내역서를 엑셀/CSV로 받는 방법은 검색에서 확인하지 못했습니다. — [foxcg 블로그](https://foxcg.com/toss-bank-transfer-receipt/)
- **토스증권 비공식 CLI(tossinvest-cli)**: 웹 세션을 재사용해 계좌, 포트폴리오, 미체결·체결 내역을 조회합니다. **CSV 내보내기**와 JSON 출력을 지원합니다(예: `tossctl orders completed --market all --output json`). 비공식이며 이용약관 위반 가능성이 있다고 스스로 밝힙니다. — [GeekNews Show GN: tossinvest-cli](https://news.hada.io/topic?id=27782); [skillsllm tossinvest-cli](https://skillsllm.com/skill/tossinvest-cli)
- **HTML을 .xls 확장자로 저장한 파일(일반론)**: 일부 시스템은 HTML 표를 .xls 이름으로 내려줍니다. 엑셀은 "파일 형식과 확장자가 일치하지 않음" 경고를 띄운 뒤 열어 줍니다. 증권사 특정 사례는 찾지 못했습니다. — [SumProduct "HTML Files with .xls"](https://sumproduct.com/blog/article/buggin-out-4-html-files-with-xls)
- **사용자 사례**: 증권사 거래내역을 엑셀로 정리해 포트폴리오 서비스에 올리면 거래일이 제대로 반영되지 않는다는 보고가 있습니다. 업로드 날짜 형식을 맞추라는 답변이 달렸습니다. — [etfshopping 커뮤니티](https://etfshopping.com/community/board/117)
- **PDF 명세서**: 증권사 명세서가 PDF로만 제공되는 경우가 있습니다. 한 증권사 명세서에 맞춘 템플릿은 다른 증권사에서는 작동하지 않는다는 지적이 있습니다. — [imagetotable.ai 투자명세서 변환](https://imagetotable.ai/ko/convert/investment-statement-to-excel); [valley.town 사례(Gemini로 PDF를 JSON으로 변환)](https://www.valley.town/space/@jhg123456/articles/69c3f5e129600ca1f2f2d109)

**연간 자료 / 해외주식 양도세 신고용 자료 / 정기 통보**
- 해외주식 양도소득은 연간 순이익(손익통산 후)이 250만 원을 넘는 부분에 22%(양도세 20% + 지방세 2%)가 과세됩니다. 신고는 다음 해 5월입니다. 2025년 귀속분은 2026-06-01(월)까지로 안내한 자료가 있습니다. — [wikidocs 해외주식 양도세 2026](https://wikidocs.net/blog/@Insight_Lab/22185/)
- NH투자증권, 신한투자증권, 메리츠증권 등은 해외주식 거래내역(양도세 계산내역) 안내를 5월 중 카카오톡과 이메일로 순차 발송합니다. 단순거래는 2026-05-01~05-31에 안내됩니다. 타사에서 입고했거나 증여받은 경우 등은 더 늦습니다. — [taxtimes 기사](https://www.taxtimes.co.kr/news/article.html?no=269378); [valuetax](https://www.valuetax.co.kr/?p=9552)
- 키움증권은 타 증권사 양도내역 무료 합산 서비스를 운영했습니다. 타사 인장이 찍힌 계산내역 파일을 첨부해 신청하는 방식이었습니다. 한화투자증권은 우수고객 대상 영업점 방문 신청을 받았습니다(2024년 기사). — [메트로서울 2024-03-22](https://www.metroseoul.co.kr/article/20240322500267)
- 증권사 신고대행은 대체로 해당 증권사 거래만 포함합니다. 여러 증권사를 쓴 경우 홈택스에서 직접 합산해야 할 수 있습니다. — [glasswallet 신고 절차](https://glasswallet.com/calculate/stock-capital-gains/declaration); [help-me.kr 홈택스 셀프신고](https://www.help-me.kr/blog/article/해외주식양도소득세홈택스셀프신고방법/)
- 한국투자증권은 HTS에서 거래내역 통보(우편)를 신청할 수 있습니다(위 인용). 월간 이메일 거래보고서의 형식(첨부 PDF/HTML 여부)은 확인하지 못했습니다. — [한국투자증권 고객센터 안내](https://securities.koreainvestment.com/main/customer/bank/_static/TF04ba030000.jsp)

### Inferences
- 미래에셋 [0650]이 입출금, 입출고, 매매를 한 화면에 섞어 보여주고 KB HTS 내보내기가 CSV/HTML/TXT를 모두 지원하는 점으로 보아, 국내 HTS 거래내역 화면은 대부분 **거래종류(거래구분) 열 하나로 매매/입금/출금/입고/출고/배당/이자를 구분하는 단일 테이블** 구조일 가능성이 높습니다. 정규화 단계에서는 증권사별 '거래종류' 문자열을 공통 enum으로 매핑하는 테이블이 핵심이 됩니다(추론, 검증 필요).
- 양도세 계산내역 파일은 증권사가 카카오톡/이메일로 보내는 PDF 또는 엑셀이 주력 채널로 보입니다. 연 1회 해외주식 손익 데이터를 확보하는 보조 소스로 쓸 수 있습니다(추론).
- 블로그·고객센터를 직접 열 수 없었기 때문에, 실제 구현 전에 각 증권사에서 **본인 계좌로 표본 파일을 내려받아 열 머리글, 인코딩, 병합 셀을 확인하는 수작업**이 필요합니다.

### Gaps
- 키움(영웅문4 화면번호, 영웅문S# 메뉴), NH(나무/QV), 삼성(mPOP), KB(M-able), 신한(SOL증권), 하나(1Q), 대신(크레온/CYBOS), 유안타(티레이더), 토스, 카카오페이증권: **거래내역·잔고 다운로드의 정확한 경로, 열 머리글, 1회 최대 조회 기간을 출처로 확인하지 못했습니다.** 증권사 도움말 도메인을 가져오지 못했고, 검색엔진이 tistory/naver 블로그를 거의 노출하지 않았습니다.
- 인코딩(CP949 vs UTF-8 CSV), 병합 헤더, 통화별 분리 시트 같은 특이점은 증권사 특정 출처가 없습니다.
- 토스증권·카카오페이증권 앱에서 거래내역서(PDF) 발급 기간 제한과 엑셀 제공 여부를 확인하지 못했습니다.
- 월간 거래보고서 이메일(자본시장법상 매매내역 통보)의 형식과 첨부파일 종류는 확인하지 못했습니다.

## Q2. 내역서가 입출금, 배당(국내/해외, 원천징수세), 이자, 수수료, 환전, 액면분할·유상증자 등을 구분하는가?

### Takeaway
미래에셋 [0650]이 매매, 입출금, 입출고를 기간별로 함께 검색할 수 있다는 점은 확인했습니다. 하지만 배당, 원천징수세, 환전, 권리 이벤트를 각각 어떤 거래종류 코드나 열로 표시하는지는 출처로 확인하지 못했습니다. API 쪽(키움 kt00015)은 체결일, 단가, 정산금액을 담는 '위탁종합거래내역' TR이 있다고 소개됩니다.

### Cited Findings
- 미래에셋 [0650] 거래내역 조회는 매매내역, 입출금, 주식 입출고 내역을 기간별로 검색하고 행별 상세거래내역을 제공합니다. — [미래에셋 0650](https://securities.miraeasset.com/kairos/0650.htm)
- 키움 REST API **kt00015 (위탁종합거래내역)**은 기간별 거래내역(체결일, 단가, 정산금액)을 조회하는 TR로 소개됩니다. 계좌는 앱키에 귀속되므로 계좌번호를 입력할 필요가 없습니다. 잔고 TR kt00018의 경로는 `POST /api/dostk/acnt`이고 도메인은 api.kiwoom.com입니다. — [glama MCP 서버 문서](https://glama.ai/mcp/servers/gi0iibvr9k); [AlgoLab 2026 kt00018](https://algolab.co.kr/blog/kiwoom-rest-api-balance-kt00018-2026) (검색 발췌)
- 한국투자 Open API의 일별주문체결조회(inquire-daily-ccld)는 실전/모의 × 3개월 이내/이전 조합으로 tr_id가 4개입니다. 공식 예제 기준(2025-06-01)으로 TTTC0081R, CTSC9215R, VTTC0081R, VTSC9215R이고, 구 자료에서는 TTTC8001R, CTSC9115R로 인용됩니다. 100건 단위 연속조회가 필요합니다. — [AlgoLab KIS inquire-daily-ccld 2026](https://algolab.co.kr/blog/kis-api-inquire-daily-ccld-order-status-2026) (검색 발췌, 자료 간 불일치 존재)
- python-kis `account.balance()`는 통화별(KRW, USD) 예수금, 보유종목, 매입금액, 평가금액, 손익, 수익률을 반환합니다. 튜토리얼에는 '기간 손익 조회', '일별 체결 내역 조회'가 있고, 배당 조회는 언급되어 있지 않습니다. — [Soju06/python-kis](https://github.com/Soju06/python-kis)

### Inferences
- 체결/주문 API(KIS inquire-daily-ccld 등)는 **매매만** 다룹니다. 배당, 입출금, 환전, 권리를 얻으려면 키움 kt00015 같은 '종합거래내역'형 TR이나 HTS 거래내역 파일이 필요해 보입니다(추론).
- KIS 일별체결조회가 3개월을 경계로 tr_id를 나누는 점으로 보아, 장기 이력은 3개월 이전 전용 경로로 나눠 조회해야 합니다(인용 근거 있음, 구현 영향은 추론).

### Gaps
- 국내배당과 해외배당(현지 원천징수 15% 등)이 별도 행으로 나오는지, 세금 열이 분리되는지에 대한 증권사별 출처가 없습니다.
- 환전 내역이 거래내역에 포함되는지, 별도 '환전내역' 화면인지 확인하지 못했습니다.
- 액면분할, 무상증자, 유상증자 입고가 '입고' 거래종류로 표시되는지 확인하지 못했습니다.

## Q3. 오픈소스 라이브러리: 2026년 유지보수 상태, 라이선스, 계좌이력 기능, OS 요구사항

### Takeaway
2026년에도 활발한 것은 REST 기반 래퍼입니다. 한국투자 공식 open-trading-api(2026 활동, Python 3.11+, 크로스플랫폼), 키움 REST 래퍼(kiwoom-restful 2026-05, pykiwoom-rest 2026-07, kiwoompy 2026-03), 토스증권 공식 Open API(2026-08 출시)와 그 래퍼(tossinvest 2026-06)가 해당합니다. 반면 OCX/COM 기반 래퍼(pykiwoom 2024-01, koapy 2022-09, xingapi 2020, pycybos 2020)는 정체 상태이며 Windows 32비트 Python이 필요합니다.

### Cited Findings

**PyPI 메타데이터 (pypi.org JSON API, 2026-10-19 조회)**

| 패키지 | 대상 | 최신 버전 | 마지막 업로드 | 라이선스 | 출처 |
|---|---|---|---|---|---|
| python-kis | 한국투자 REST | 2.1.6 | 2025-10-13 | MIT | [PyPI](https://pypi.org/project/python-kis/) / [GitHub Soju06](https://github.com/Soju06/python-kis) |
| mojito2 | 한국투자 REST ("증권사 REST 통합 래퍼" 표방) | 0.1.6 | 2023-02-23 | MIT(GitHub LICENSE) | [PyPI](https://pypi.org/project/mojito2/) / [GitHub](https://github.com/sharebook-kr/mojito) |
| pykis (pjueon) | 한국투자 REST | 0.7.0 | 2022-07-07 | Apache-2.0 | [PyPI](https://pypi.org/project/pykis/) |
| pykiwoom | 키움 Open API+ (OCX) | 0.1.6 | 2024-01-05 | MIT | [PyPI](https://pypi.org/project/pykiwoom/) |
| koapy | 키움 Open API+ (OCX) | 0.9.0 | 2022-09-13 | MIT OR Apache-2.0 OR GPL-3.0 | [PyPI](https://pypi.org/project/koapy/) |
| kiwoom (breadum) | 키움 Open API+ (OCX) | 1.5.0 | 2025-08-03 | MIT | [PyPI](https://pypi.org/project/kiwoom/) |
| kiwoom-restful (breadum) | 키움 REST API | 0.4.0 | **2026-05-10** | MIT | [PyPI](https://pypi.org/project/kiwoom-restful/) |
| kiwoom-rest-api | 키움 REST API | 0.1.12 | 2025-06-27 | (미기재) | [PyPI](https://pypi.org/project/kiwoom-rest-api/) |
| pykiwoom-rest (unohee) | 키움 REST + CLI + MCP 서버 | 2.2.0 | **2026-07-19** | MIT | [PyPI](https://pypi.org/project/pykiwoom-rest/) |
| kiwoompy | 키움 REST | 0.1.6 | **2026-03-06** | MIT | [PyPI](https://pypi.org/project/kiwoompy/) |
| ebest (teranum) | 이베스트(현 LS증권) API | 1.0.2 | 2025-05-09 | (미기재) | [PyPI](https://pypi.org/project/ebest/) |
| pyebest | 이베스트 API | 0.1.7 | 2022-07-24 | (미기재) | [PyPI](https://pypi.org/project/pyebest/) |
| xingapi (jeakwon) | 이베스트 xingAPI (COM) | 1.2.14 | 2020-07-29 | (미기재) | [PyPI](https://pypi.org/project/xingapi/) |
| pycybos | 대신 CYBOS Plus | 0.0.0 | 2020-10-21 | (미기재) | [PyPI](https://pypi.org/project/pycybos/) |
| tossinvest (SuhJae) | 토스증권 공식 Open API | 0.1.0 | **2026-06-16** | Apache-2.0 | [PyPI](https://pypi.org/project/tossinvest/) / [GitHub](https://github.com/SuhJae/tossinvest-py) |
| pykrx | KRX 시세 스크래핑(계좌 아님, 참고) | 1.2.9 | 2026-09-19 | MIT | [PyPI](https://pypi.org/project/pykrx/) |
| finance-datareader | 시세(계좌 아님, 참고) | 0.9.202 | 2026-05-13 | MIT | [PyPI](https://pypi.org/project/finance-datareader/) |

- 참고: PyPI 첫 업로드 기준으로 pykiwoom은 2016-12, koapy는 2020-09, python-kis는 2022-10, kiwoom-restful은 2025-08, pykiwoom-rest는 2026-07, tossinvest는 2026-06입니다(위 PyPI 페이지들). PyPI에서 이름 `kiwoom-rest`, `ls-openapi`, `koreainvestment-api`, `open-trading-api`로는 패키지가 조회되지 않았습니다.
- 키움증권 명의의 PyPI 사용자 페이지가 존재하며 "Last released Jul 22, 2026"으로 표시됩니다. 패키지명은 확인하지 못했습니다. — [pypi.org/user/Kiwoom](https://pypi.org/user/Kiwoom/)

**개별 프로젝트 상세**
- **koreainvestment/open-trading-api (한국투자 공식 예제)**: 커밋 414개, 1.7k stars, 835 forks, 열린 PR 13개, 페이지 푸터 "© 2026". 구조는 `examples_llm/`(API별 단일 호출 스크립트), `examples_user/`(REST/WebSocket 카테고리 모듈), `MCP/`, `strategy_builder/`, `backtester/`, `legacy/`, `llms.txt`입니다. Python 3.11+와 uv를 권장하고 Windows, macOS, Linux 설치를 안내합니다. 캡처 화면에서는 라이선스 표기를 확인하지 못했습니다. — [GitHub koreainvestment/open-trading-api](https://github.com/koreainvestment/open-trading-api)
- **python-kis (Soju06)**: MIT 라이선스, Python 3.11 기준, 커밋 304개, 열린 이슈 17개와 PR 5개. 2.0.0에서 전면 재작성되었습니다. 기능으로 잔고(통화별 예수금 포함), 기간 손익, 일별 체결 내역, 미체결 주문을 제공합니다. — [GitHub Soju06/python-kis](https://github.com/Soju06/python-kis)
- **mojito (sharebook-kr)**: MIT 라이선스, 커밋 92개, 릴리스 없음. 예제는 한국투자만 다룹니다. `fetch_balance()`(주식잔고조회)를 지원하고 체결내역 함수는 명시되어 있지 않습니다. PyPI 마지막 업로드가 2023-02여서 사실상 정체 상태입니다. — [GitHub sharebook-kr/mojito](https://github.com/sharebook-kr/mojito); [PyPI mojito2](https://pypi.org/project/mojito2/)
- **KIS-Agent (unohee/kis-agent)**: 한국투자 OpenAPI를 "pip 하나로" 쓰게 해 주는 2026년 GeekNews 소개 프로젝트입니다. 매매 내역과 잔고 기능을 제공한다고 소개됩니다. — [GitHub unohee/kis-agent](https://github.com/unohee/kis-agent); [GeekNews](https://news.hada.io/topic?id=27707)
- **R 패키지 kisopenapi (CRAN)**: 한국투자 Open Trading API용 R 래퍼입니다. — [CRAN README 미러](https://ftp.fau.de/cran/web/packages/kisopenapi/readme/README.html)
- **키움 REST .NET**: KiwoomRestApi.Net (NuGet). — [GitHub dongbin300/KiwoomRestApi.Net](https://github.com/dongbin300/KiwoomRestApi.Net); [NuGet](https://www.nuget.org/packages/KiwoomRestApi.Net). **키움 CLI (npm)**: @2oolkit/kiwoom-cli. — [socket.dev](https://socket.dev/npm/package/@2oolkit/kiwoom-cli/overview/0.1.2)
- **LS증권(구 이베스트)**: Windows 기반 xingAPI와 웹 기반 오픈API(REST)를 함께 제공합니다. 2026-10-01에 두 서비스 정보를 모은 'API 투자전략센터'를 열었습니다. 따라서 2026-10 기준 xingAPI는 종료되지 않았습니다. — [아시아경제 2026-10-01](https://core.asiae.co.kr/article/2026100110265573430). LS 구 방식(xingAPI)은 32비트 Python이 필요하고 신 REST는 64비트를 지원합니다(블로그 정리, 공식 문서 아님). — [AlgoLab 증권사 API 비교](https://algolab.co.kr/blog/kr-broker-api-comparison). .NET 래퍼로 RedoxNet.LsOpenApi.Core와 MCP 패키지가 있습니다. — [NuGet RedoxNet](https://www.nuget.org/profiles/RedoxNet)
- **대신증권 CybosPlus(크레온)**: 32bit COM(OCX) 컴포넌트라 키움 OCX처럼 32bit Python이 필요합니다. 64비트 지원 계획은 확인하지 못했습니다. — [AlgoLab 대신·LS 가이드 2026](https://algolab.co.kr/blog/daeshin-ls-securities-algotrading-guide-2026) (검색 발췌)
- **토스증권 공식 Open API**: 2026-08-13 출시 보도가 있습니다. 시세, 주문, **계좌 조회**, 종목·시장 정보를 제공하고 국내·해외주식을 단일 연동으로 다룹니다. LLM 연동을 지원하며 안내 페이지는 corp.tossinvest.com/ko/open-api, 스펙은 openapi.tossinvest.com입니다. OAuth 2.0 Client Credentials(client_id/secret) 방식입니다. — [이코노미스트 2026-08](https://economist.co.kr/article/view/ecn202608130015); [아시아경제 2026-08-13](https://core.asiae.co.kr/article/2026081310375054345); [K-skill toss-securities](https://openskillindex.com/skills/nomadamas-k-skill-toss-securities). 커뮤니티 도구로는 BEOKS/tossinvest-skill과 JeongSeongMok/tossinvest-openapi-mcp(주문은 기본 dry-run)가 있습니다. — [GitHub BEOKS/tossinvest-skill](https://github.com/BEOKS/tossinvest-skill); [enterprisedna MCP 디렉터리](https://enterprisedna.co/directories/mcp/jeongseongmok-tossinvest-openapi-mcp)
- **토스증권 비공식 CLI**: JungHoonGhae/tossinvest-cli(Go, Homebrew `tossctl`)는 Playwright로 로그인 세션을 한 번 확보한 뒤 쿠키로 내부 API를 호출합니다. 계좌, 포트폴리오, 월간 체결 내역, CSV 내보내기를 지원합니다. 비공식이며 ToS 위반 가능성이 있습니다. — [GeekNews](https://news.hada.io/topic?id=27782); [skillsllm](https://skillsllm.com/skill/tossinvest-cli)
- **REST 전환 흐름**: 증권사들이 OCX 한계를 풀기 위해 신 REST OpenAPI를 따로 내놓는 흐름이 진행 중입니다. 신규 프로젝트에는 REST가 권장되지만, 조건검색과 실시간 등록은 아직 구 OCX 쪽 기능이 더 풍부하다는 평가가 있습니다. — [AlgoLab 비교](https://algolab.co.kr/blog/kr-broker-api-comparison) (검색 발췌)

### Inferences
- 2026년 기준 **크로스플랫폼(macOS/Linux)에서 계좌 데이터를 자동 수집할 수 있는 공식 경로는 한국투자 REST, 키움 REST, LS 오픈API(REST), 토스 Open API** 네 곳으로 보입니다. 키움 OCX, 대신 CYBOS, LS xingAPI는 Windows와 32bit Python이 필요해 서버 자동화에 불리합니다(인용 근거 + 추론).
- 미래에셋, NH, 삼성, KB, 신한, 하나, 유안타, 카카오페이증권의 개인용 공개 REST API나 오픈소스 계좌 래퍼는 이번 검색에서 나오지 않았습니다. 이들 증권사는 **파일 내보내기 파싱이 사실상 유일한 경로**일 가능성이 높습니다(부재 근거에 기반한 추론).
- PyPI 업로드 날짜 기준으로 python-kis는 1년(2025-10 이후) 동안 릴리스가 없습니다. 활발하다고 단정하기 어렵고 "유지되지만 느림"으로 분류하는 편이 안전합니다(추론).

### Gaps
- GitHub API가 막혀 각 저장소의 마지막 커밋 날짜, 아카이브 여부, 정확한 star 수를 일괄 확인하지 못했습니다. PyPI 업로드일로 대체했습니다.
- kiwoom-restful, pykiwoom-rest, kiwoompy가 kt00015(위탁종합거래내역)를 래핑하는지 확인하지 못했습니다.
- 토스 Open API에 기간별 거래내역(입출금, 배당 포함) 엔드포인트가 있는지 확인하지 못했습니다. 보도에는 '계좌 조회'만 언급됩니다.
- LS 오픈API의 거래내역 TR(예: CDPCQ04700 류)은 확인하지 못했습니다.
- open-trading-api의 라이선스를 확인하지 못했습니다(페이지 캡처에 없음).

## Q4. 여러 한국 증권사 내보내기 파일을 공통 스키마로 정규화하는 프로젝트가 있는가?

### Takeaway
이번 조사에서는 **여러 한국 증권사의 거래내역 파일(엑셀/CSV)을 공통 스키마로 정규화하는 오픈소스 프로젝트를 찾지 못했습니다.** mojito가 "증권사 REST 통합 래퍼"를 표방했지만 실제로는 한국투자만 지원하고 2023년 이후 정체 상태입니다.

### Cited Findings
- mojito는 "대한민국 증권사의 Rest API 기반의 Open API에 대한 통합 파이썬 레퍼 모듈"을 표방합니다. 하지만 예제는 한국투자(`mojito.KoreaInvestment`)뿐이고 이베스트 지원은 확인되지 않습니다. — [GitHub sharebook-kr/mojito](https://github.com/sharebook-kr/mojito)
- "키움·미래에셋 거래내역 엑셀을 직접 파싱하는 GitHub 프로젝트"를 검색했지만 결과가 없었습니다. 관련 사례는 PDF를 LLM(Gemini)으로 JSON으로 바꾸는 개인 작업 정도였습니다. — [valley.town 사례](https://www.valley.town/space/@jhg123456/articles/69c3f5e129600ca1f2f2d109)
- 다른 증권사용으로 학습한 명세서 템플릿은 서로 호환되지 않는다는 지적이 있습니다. 즉 증권사별 파서가 필요합니다. — [imagetotable.ai](https://imagetotable.ai/ko/convert/investment-statement-to-excel)
- 다중 증권사 연결은 오픈소스 정규화보다 **에이전트 스킬/MCP 생태계**로 나타납니다. 예로 K-skill(nomadamas/k-skill)의 toss-securities 스킬, pykiwoom-rest의 MCP 서버, 한국투자 공식 MCP, RedoxNet LS MCP가 있습니다. — [K-skill toss-securities](https://claudemarket.ai/skills/nomadamas/k-skill/toss-securities); [PyPI pykiwoom-rest](https://pypi.org/project/pykiwoom-rest/); [GitHub open-trading-api](https://github.com/koreainvestment/open-trading-api); [NuGet RedoxNet](https://www.nuget.org/profiles/RedoxNet)

### Inferences
- 공통 스키마가 필요하다면 직접 설계해야 할 가능성이 높습니다. 출발점으로는 해외 개인재무 도구의 원장 모델(예: Beancount/Ghostfolio 류의 activity 타입 BUY/SELL/DIVIDEND/FEE/INTEREST/DEPOSIT/WITHDRAWAL/FX)을 참고할 수 있습니다. 이 도구들은 이번 조사에서 출처로 확인하지 않았으므로 별도 검증이 필요합니다.
- 한국 투자자용 상용 자산관리 앱(마이데이터 기반)이 실질적인 통합 경로일 수 있습니다. 다만 이는 이번 조사 범위(오픈소스, 파일) 밖이며 출처를 확인하지 않았습니다.

### Gaps
- GitHub 검색 API를 쓸 수 없어 "portfolio-tracker korea", "kiwoom excel parser", "증권 거래내역 파서" 같은 토픽을 전수 조사하지 못했습니다. 정규화 프로젝트가 정말 없다고 단정할 수는 없습니다.
- Ghostfolio, Portfolio Performance 등 해외 트래커가 한국 증권사 CSV 임포터를 갖고 있는지 확인하지 못했습니다.
