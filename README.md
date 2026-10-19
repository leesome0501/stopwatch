# AssetHub · 우리집 자산허브

가족 모두의 금융 자산, 거래, 세금 자료를 한곳에 모아 현황과 수익률을 자동으로 관리하는 자가 호스팅 웹 프로그램입니다.
가족 데이터만 다루며 외부에 서비스하지 않습니다.

## 구조

```
[소스]       증권사 API · CODEF(은행·카드·홈택스·연금) · 업비트 · 시세 · 엑셀/수동
   │
[수집층]     소스별 어댑터, 원본 보관(raw_record)
   │
[정규화층]   스키마 통일 · 중복 제거 · 이체 짝 맞춤 · 자동 분류
   │
[데이터 모델] 가구 > 구성원 > 계좌 > 거래 / 종목 · 시세 · 환율
   │
[계산 엔진]  평가액 · 수익률(TWR, XIRR) · 실현/미실현 손익 · 세금 추정
   │
[화면]       순자산 대시보드 · 자산배분 · 수입/지출 · 세금 캘린더 · 알림
```

## 로드맵

1. **기반** (진행 중): 데이터 모델 ✅, API·엑셀 가져오기 ✅, 시세·환율 수집, 순자산 대시보드
2. **자동 수집**: 한국투자증권 API, 업비트, CODEF 은행·카드, 이체 매칭, 자동 분류, 원가·수익률 엔진
3. **세금·기타 자산**: 홈택스, 국민연금, 보험, 부동산 시세, 세금 추정
4. **가족 운영**: 구성원별 권한, 수집 실패·인증서 만료 알림, 월간 리포트

## 폴더

| 경로 | 내용 |
| --- | --- |
| `db/schema.sql` | PostgreSQL 스키마 (테이블, 함수, 뷰) |
| `db/seed.sql` | 주요 금융기관, 기본 카테고리 |
| `db/sample.sql` | 예제 가구 데이터 |
| `db/tests.sql` | 예제 데이터 기준 검증 |
| `docs/data-model.md` | 데이터 모델 설계 설명 |
| `scripts/db-check.sh` | 빈 DB에 스키마를 올리고 검증 실행 |
| `backend/` | FastAPI 백엔드 (`assethub` 패키지, 테스트) |
| `backend/assethub/importer/` | 엑셀·CSV 가져오기 (형식 판별, 순서·잔액 검증, 중복 판정) |

## 백엔드 실행

PostgreSQL 16 이상과 [uv](https://docs.astral.sh/uv/)가 필요합니다.

```bash
createdb assethub
psql assethub -f db/schema.sql -f db/seed.sql

cd backend
uv sync
DATABASE_URL=postgresql:///assethub uv run uvicorn assethub.main:app --reload
```

`http://localhost:8000/docs` 에서 모든 API를 바로 시험할 수 있습니다.
아직 로그인 기능이 없으므로 집 안 네트워크나 VPN 뒤에서만 띄우세요.

## 주요 API

| 기능 | 경로 |
| --- | --- |
| 가구·구성원 | `POST /api/households`, `POST /api/households/{id}/members` |
| 계좌 (공동명의 지분 포함) | `POST /api/households/{id}/accounts`, `PATCH /api/accounts/{id}` |
| 종목·시세·환율 | `POST /api/instruments`, `PUT /api/instruments/{id}/prices`, `PUT /api/fx-rates` |
| 거래 | `GET·POST /api/accounts/{id}/transactions`, `PATCH·DELETE /api/transactions/{id}` |
| 현황 | `GET /api/households/{id}/summary`, `/cashflow?month=YYYY-MM`, `/unmatched-transfers` |
| 엑셀 가져오기 | `POST /api/accounts/{id}/imports/preview`, `POST /api/accounts/{id}/imports` |
| 표준 양식 | `GET /api/import-template` |

금액은 정밀도를 지키려고 JSON에서 문자열(`"1145000.0000"`)로 주고받습니다.

## 엑셀 가져오기

계좌 화면에서 파일을 올리면 미리보기로 행마다 새 거래, 중복, 오류와 자동 분류 결과를 보여주고, 확인하면 새 거래만 저장합니다.

- **읽는 파일**: `.xlsx`, 옛 `.xls`, 은행이 내려주는 "HTML 표로 된 .xls", CSV(UTF-8, CP949). 확장자가 아니라 내용으로 판별합니다.
- **은행 형식**: 우리, 신한, 하나(법인·개인), IBK, 이체내역 형식을 알아보고, 그 밖의 은행은 헤더 이름(거래일시, 출금, 입금, 잔액, 적요 등)으로 컬럼을 찾습니다.
- **AssetHub 표준 양식**: 증권 매매, 배당, 환전, 기초잔액처럼 은행 형식으로 표현할 수 없는 자료를 채워 올리는 양식입니다.
- **순서**: 최신이 위에 있는 은행 파일도 과거→최신 순서로 바로잡아 저장합니다.
- **중복**: 거래 후 잔액이 있으면 "한국 날짜 + 금액 + 잔액"으로 판정합니다. 시각이 있는 파일과 날짜만 있는 파일이 겹쳐도 같은 거래로 알아봅니다. 같은 파일을 다시 올려도 안전합니다.
- **기초잔액**: 계좌의 첫 업로드라면 첫 거래의 잔액에서 기초잔액을 계산해 넣어, 계산 잔액이 은행 잔액과 맞게 합니다.
- **잔액 검증**: 파일 안에서 잔액이 이어지지 않거나, 저장 후 계산 잔액이 파일의 마지막 잔액과 다르면 경고합니다. 빠진 거래나 다른 계좌의 파일을 잡아냅니다. 파일의 계좌번호가 계좌와 다를 때도 경고합니다.
- **자동 분류**: 파일에 적힌 카테고리, 가구의 분류 규칙, 같은 적요의 과거 거래, 같은 거래처의 과거 거래 순서로 카테고리를 채웁니다.

은행 형식, 중복 판정, 순서·잔액 검증 규칙은 사업자관리 프로젝트의 은행 거래내역 가져오기에서 실제로 겪은 사례를 옮겨 왔습니다.

## 검증 실행

```bash
scripts/db-check.sh                 # 스키마와 뷰를 예제 가구로 검증
cd backend && uv run pytest         # 가져오기·API 테스트 (임시 PostgreSQL 사용, root 불가)
TEST_DATABASE_URL=postgresql:///postgres uv run pytest   # 기존 서버 사용 (CREATE DATABASE 권한 필요)
```
