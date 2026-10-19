-- =====================================================================
-- AssetHub 데이터 모델 (PostgreSQL 16+) · 첫 마이그레이션
-- 설계 설명: docs/data-model.md
-- 이후 변경은 이 파일을 고치지 말고 다음 번호의 마이그레이션 파일로 추가한다 (db/migrations/README.md).
--
-- 원칙
--  * 기준 통화는 KRW. 모든 합계·평가액은 KRW로 환산해서 본다.
--  * 금액은 NUMERIC (float 금지). 수량은 코인 대비 소수 10자리.
--  * 열거형은 PG ENUM 대신 text + CHECK (마이그레이션이 쉬움).
--  * txn(거래)이 진실의 원천. 잔고·보유·평가액은 뷰로 파생한다.
--  * 소스 원본(raw_record)은 버리지 않고 보관해 재처리할 수 있게 한다.
-- =====================================================================


-- ---------------------------------------------------------------------
-- 1. 사람: 가구, 구성원, 로그인 사용자
-- ---------------------------------------------------------------------
CREATE TABLE household (
    id          bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name        text        NOT NULL,
    created_at  timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE member (
    id            bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    household_id  bigint      NOT NULL REFERENCES household(id),
    name          text        NOT NULL,
    relation      text        NOT NULL
                  CHECK (relation IN ('self','spouse','child','parent','sibling','other')),
    birth_date    date,
    is_dependent  boolean     NOT NULL DEFAULT false,   -- 연말정산 부양가족 여부
    created_at    timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX ON member (household_id);

CREATE TABLE app_user (
    id             bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    member_id      bigint      NOT NULL UNIQUE REFERENCES member(id),
    email          text        NOT NULL UNIQUE,
    password_hash  text,                                -- argon2id 등
    totp_secret_enc bytea,                              -- 2단계 인증 비밀키(암호화)
    role           text        NOT NULL DEFAULT 'member'
                   CHECK (role IN ('admin','member','viewer')),
    created_at     timestamptz NOT NULL DEFAULT now(),
    last_login_at  timestamptz
);

-- ---------------------------------------------------------------------
-- 2. 기관과 계좌
-- ---------------------------------------------------------------------
CREATE TABLE institution (
    id    bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    code  text NOT NULL UNIQUE,                         -- 'KB', 'KIS', 'UPBIT' ...
    name  text NOT NULL,
    kind  text NOT NULL
          CHECK (kind IN ('bank','securities','card','insurance','crypto_exchange',
                          'pension','government','other'))
);

CREATE TABLE account (
    id                bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    household_id      bigint      NOT NULL REFERENCES household(id),
    institution_id    bigint      REFERENCES institution(id),
    name              text        NOT NULL,             -- 사용자 별칭
    account_type      text        NOT NULL
                      CHECK (account_type IN (
                        'checking',            -- 입출금
                        'savings',             -- 파킹/자유적립 예금
                        'time_deposit',        -- 정기예금
                        'installment_savings', -- 적금
                        'cma',
                        'brokerage',           -- 일반 위탁
                        'isa',
                        'pension_savings',     -- 연금저축
                        'irp',
                        'dc_pension',          -- 퇴직연금 DC
                        'crypto',
                        'credit_card',
                        'loan',
                        'insurance',           -- 저축성/보장성 보험 (해지환급금 기준)
                        'real_asset',          -- 부동산, 차량, 금 실물 등
                        'cash',
                        'other')),
    -- 'transactions': txn 합산으로 평가 / 'reported': 소스가 알려준 잔액으로 평가
    valuation_method  text        NOT NULL DEFAULT 'transactions'
                      CHECK (valuation_method IN ('transactions','reported')),
    base_currency     char(3)     NOT NULL DEFAULT 'KRW',
    account_number_masked text,                         -- '123-***-7890'
    external_ref      text,                             -- 소스 쪽 계좌 식별자
    data_source_id    bigint,                           -- FK는 아래에서 추가
    visibility        text        NOT NULL DEFAULT 'household'
                      CHECK (visibility IN ('household','owners')),
    opened_on         date,
    maturity_on       date,
    closed_on         date,
    interest_rate     numeric(7,4),                     -- 연 % (예금, 대출)
    memo              text,
    created_at        timestamptz NOT NULL DEFAULT now(),
    updated_at        timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX ON account (household_id);

-- 명의. 공동명의(부동산 50:50 등)를 지분으로 표현.
CREATE TABLE account_owner (
    account_id  bigint       NOT NULL REFERENCES account(id) ON DELETE CASCADE,
    member_id   bigint       NOT NULL REFERENCES member(id),
    share       numeric(5,4) NOT NULL DEFAULT 1 CHECK (share > 0 AND share <= 1),
    PRIMARY KEY (account_id, member_id)
);

-- ---------------------------------------------------------------------
-- 3. 종목 마스터, 시세, 환율
-- ---------------------------------------------------------------------
CREATE TABLE instrument (
    id            bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    kind          text    NOT NULL
                  CHECK (kind IN ('stock','etf','etn','fund','bond','reit','crypto',
                                  'gold','real_estate','vehicle','other')),
    asset_class   text    NOT NULL
                  CHECK (asset_class IN ('equity','bond','cash_equiv','commodity','crypto',
                                         'real_estate','alternative','mixed')),
    symbol        text,                                 -- '005930', 'AAPL', 'KRW-BTC'
    market        text,                                 -- 'KRX','NASDAQ','UPBIT','PRIVATE'
    isin          text UNIQUE,
    name          text    NOT NULL,
    currency      char(3) NOT NULL,                     -- 시세 통화
    country       char(2),                              -- 'KR','US'
    household_id  bigint  REFERENCES household(id),     -- 비상장/개인 자산(아파트 등)만 지정
    price_code    text,                                 -- 시세 소스 쪽 코드 ('AAPL.O' 등). 비우면 수집기가 찾아 채움
    created_at    timestamptz NOT NULL DEFAULT now(),
    UNIQUE (market, symbol)
);

-- 일별 종가. 부동산 시세처럼 수동 입력한 값도 source='manual'로 여기 저장.
CREATE TABLE price (
    instrument_id  bigint        NOT NULL REFERENCES instrument(id),
    price_date     date          NOT NULL,
    close          numeric(24,8) NOT NULL CHECK (close >= 0),
    source         text          NOT NULL,              -- 'krx','kis','upbit','manual' ...
    fetched_at     timestamptz   NOT NULL DEFAULT now(),
    PRIMARY KEY (instrument_id, price_date)
);

-- 1 단위 외화 = krw_rate 원
CREATE TABLE fx_rate (
    currency   char(3)       NOT NULL CHECK (currency <> 'KRW'),
    rate_date  date          NOT NULL,
    krw_rate   numeric(20,8) NOT NULL CHECK (krw_rate > 0),
    source     text          NOT NULL,
    PRIMARY KEY (currency, rate_date)
);

-- 시세·환율 수집 실행 기록 (가구와 무관한 공용 데이터)
CREATE TABLE market_sync_run (
    id               bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    started_at       timestamptz NOT NULL DEFAULT now(),
    finished_at      timestamptz,
    status           text        NOT NULL DEFAULT 'running'
                     CHECK (status IN ('running','succeeded','partial','failed')),
    prices_upserted  int         NOT NULL DEFAULT 0,
    fx_upserted      int         NOT NULL DEFAULT 0,
    errors           jsonb       NOT NULL DEFAULT '[]'      -- [{"target": "AAPL", "message": "..."}]
);

-- ---------------------------------------------------------------------
-- 4. 수집: 데이터 소스, 수집 배치, 원본 레코드
-- ---------------------------------------------------------------------
CREATE TABLE data_source (
    id              bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    household_id    bigint      NOT NULL REFERENCES household(id),
    member_id       bigint      REFERENCES member(id),  -- 누구의 인증정보인가
    institution_id  bigint      REFERENCES institution(id),
    provider        text        NOT NULL
                    CHECK (provider IN ('manual','file','kis','codef','upbit','krx','other')),
    label           text        NOT NULL,
    credential_enc  bytea,                              -- 봉투 암호화된 인증정보. 평문 저장 금지
    config          jsonb       NOT NULL DEFAULT '{}',  -- 엑셀 컬럼 매핑, 조회 옵션 등
    status          text        NOT NULL DEFAULT 'active'
                    CHECK (status IN ('active','paused','error','expired')),
    last_synced_at  timestamptz,
    last_error      text,
    created_at      timestamptz NOT NULL DEFAULT now()
);

ALTER TABLE account
    ADD FOREIGN KEY (data_source_id) REFERENCES data_source(id);

CREATE TABLE import_batch (
    id                 bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    data_source_id     bigint      NOT NULL REFERENCES data_source(id),
    account_id         bigint      REFERENCES account(id),  -- 파일 업로드처럼 대상 계좌가 하나일 때
    started_at         timestamptz NOT NULL DEFAULT now(),
    finished_at        timestamptz,
    status             text        NOT NULL DEFAULT 'running'
                       CHECK (status IN ('running','succeeded','partial','failed')),
    file_name          text,
    file_sha256        text,                            -- 같은 파일 재업로드 감지
    records_total      int         NOT NULL DEFAULT 0,
    records_new        int         NOT NULL DEFAULT 0,
    records_duplicate  int         NOT NULL DEFAULT 0,
    error              text
);
CREATE INDEX ON import_batch (data_source_id, started_at DESC);

-- 소스 응답/엑셀 한 행을 가공 없이 보관. 파서를 고치면 여기서 다시 돌린다.
CREATE TABLE raw_record (
    id               bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    import_batch_id  bigint      NOT NULL REFERENCES import_batch(id),
    record_type      text        NOT NULL
                     CHECK (record_type IN ('account','transaction','balance','holding','price')),
    payload          jsonb       NOT NULL,
    received_at      timestamptz NOT NULL DEFAULT now(),
    parse_status     text        NOT NULL DEFAULT 'pending'
                     CHECK (parse_status IN ('pending','parsed','skipped','error')),
    parse_error      text
);
CREATE INDEX ON raw_record (import_batch_id);

-- ---------------------------------------------------------------------
-- 5. 분류: 카테고리와 자동 분류 규칙
-- ---------------------------------------------------------------------
CREATE TABLE category (
    id            bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    household_id  bigint REFERENCES household(id),      -- NULL = 시스템 기본 카테고리
    parent_id     bigint REFERENCES category(id),
    name          text   NOT NULL,
    -- transfer는 가구 내부 이동이라 수입/지출 통계에서 빠진다.
    kind          text   NOT NULL CHECK (kind IN ('income','expense','transfer')),
    sort_order    int    NOT NULL DEFAULT 0,
    is_hidden     boolean NOT NULL DEFAULT false,
    UNIQUE NULLS NOT DISTINCT (household_id, parent_id, name)
);

CREATE TABLE category_rule (
    id            bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    household_id  bigint  NOT NULL REFERENCES household(id),
    priority      int     NOT NULL DEFAULT 100,         -- 작을수록 먼저
    account_id    bigint  REFERENCES account(id),       -- NULL이면 모든 계좌
    match_field   text    NOT NULL CHECK (match_field IN ('description','counterparty')),
    match_type    text    NOT NULL CHECK (match_type IN ('contains','equals','regex')),
    pattern       text    NOT NULL,
    category_id   bigint  NOT NULL REFERENCES category(id),
    enabled       boolean NOT NULL DEFAULT true
);

-- ---------------------------------------------------------------------
-- 6. 거래 (진실의 원천)
--
-- 한 행 = 한 계좌에서 일어난 사건 하나 (소스가 주는 단위 그대로).
-- 부호는 "그 계좌 입장"에서: 돈/수량이 들어오면 +, 나가면 -.
-- 계좌 간 이체·환전처럼 두 행이 한 사건이면 group_id로 묶는다.
-- ---------------------------------------------------------------------
CREATE TABLE txn (
    id              bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    account_id      bigint        NOT NULL REFERENCES account(id),
    occurred_at     timestamptz   NOT NULL,
    trade_date      date          NOT NULL,             -- 기준일 (KST)
    settle_date     date,                               -- 결제일 (주식 T+2 등)
    kind            text          NOT NULL
                    CHECK (kind IN (
                      'cash_in','cash_out',     -- 일반 입출금, 카드 사용/결제, 급여 등
                      'buy','sell',             -- 종목 매매
                      'dividend','interest',    -- 배당, 이자 (instrument는 선택)
                      'fee','tax',              -- 단독 수수료, 단독 세금
                      'fx',                     -- 환전의 한쪽 다리 (group_id 필수)
                      'instrument_in','instrument_out', -- 입고/출고, 증여, 초기 보유분
                      'split',                  -- 액면분할/병합 (수량만 변화)
                      'adjustment')),           -- 기초잔액, 잔액 보정
    -- 이 계좌 현금 변화량. 수수료와 세금을 이미 반영한 순액. 부호 포함.
    amount          numeric(20,4) NOT NULL DEFAULT 0,
    currency        char(3)       NOT NULL,
    instrument_id   bigint        REFERENCES instrument(id),
    quantity        numeric(28,10),                     -- 부호 포함
    unit_price      numeric(24,8),                      -- 종목 통화 기준 체결 단가
    balance_after   numeric(20,4),                      -- 소스가 알려준 거래 후 잔액 (대사·중복판정용)
    fee             numeric(20,4) NOT NULL DEFAULT 0 CHECK (fee >= 0),  -- 정보용, amount에 포함됨
    tax             numeric(20,4) NOT NULL DEFAULT 0 CHECK (tax >= 0),  -- 원천징수·거래세, amount에 포함됨
    category_id     bigint        REFERENCES category(id),
    counterparty    text,                               -- 가맹점, 송금인
    description     text,                               -- 소스 원문 적요
    memo            text,                               -- 사용자 메모
    group_id        uuid,                               -- 이체 짝, 환전 짝
    status          text          NOT NULL DEFAULT 'posted'
                    CHECK (status IN ('posted','pending','void')),
    data_source_id  bigint        REFERENCES data_source(id),
    raw_record_id   bigint        REFERENCES raw_record(id),
    -- 중복 방지 키: 소스 거래 ID가 있으면 그것, 없으면 (일시,금액,적요,순번) 해시
    dedupe_key      text          NOT NULL,
    created_at      timestamptz   NOT NULL DEFAULT now(),
    updated_at      timestamptz   NOT NULL DEFAULT now(),

    UNIQUE (account_id, dedupe_key),
    CHECK (kind NOT IN ('buy','sell','instrument_in','instrument_out','split')
           OR (instrument_id IS NOT NULL AND quantity IS NOT NULL)),
    CHECK (kind <> 'buy'  OR quantity > 0),
    CHECK (kind <> 'sell' OR quantity < 0),
    CHECK (kind <> 'cash_in'  OR amount >= 0),
    CHECK (kind <> 'cash_out' OR amount <= 0),
    CHECK (kind <> 'fx' OR group_id IS NOT NULL)
);
CREATE INDEX ON txn (account_id, trade_date);
CREATE INDEX ON txn (trade_date);
CREATE INDEX ON txn (group_id) WHERE group_id IS NOT NULL;
CREATE INDEX ON txn (category_id);
CREATE INDEX ON txn (instrument_id) WHERE instrument_id IS NOT NULL;

-- ---------------------------------------------------------------------
-- 7. 소스가 알려준 잔액·보유 (대사용, 그리고 reported 계좌의 평가 근거)
-- ---------------------------------------------------------------------
CREATE TABLE reported_balance (
    account_id     bigint        NOT NULL REFERENCES account(id),
    as_of          date          NOT NULL,
    currency       char(3)       NOT NULL,
    cash_amount    numeric(20,4),                       -- 예수금 등 현금성
    total_value    numeric(20,4) NOT NULL,              -- 평가금액 합계 (보험은 해지환급금)
    raw_record_id  bigint        REFERENCES raw_record(id),
    PRIMARY KEY (account_id, as_of, currency)
);

CREATE TABLE reported_holding (
    account_id     bigint         NOT NULL REFERENCES account(id),
    as_of          date           NOT NULL,
    instrument_id  bigint         NOT NULL REFERENCES instrument(id),
    quantity       numeric(28,10) NOT NULL,
    avg_cost       numeric(24,8),                       -- 증권사가 계산한 평균단가
    market_value   numeric(20,4),
    raw_record_id  bigint         REFERENCES raw_record(id),
    PRIMARY KEY (account_id, as_of, instrument_id)
);

-- ---------------------------------------------------------------------
-- 8. 파생 캐시: 일별 계좌 평가액 (언제든 txn·price·fx로 재계산 가능)
--    순자산 추이 그래프와 TWR 계산용.
-- ---------------------------------------------------------------------
CREATE TABLE daily_value (
    account_id        bigint        NOT NULL REFERENCES account(id),
    value_date        date          NOT NULL,
    value_krw         numeric(20,4) NOT NULL,           -- 그날 종가 기준 평가액
    cash_krw          numeric(20,4) NOT NULL,
    external_flow_krw numeric(20,4) NOT NULL DEFAULT 0, -- 그날 계좌 밖에서 들어온 순유입
    computed_at       timestamptz   NOT NULL DEFAULT now(),
    PRIMARY KEY (account_id, value_date)
);

-- =====================================================================
-- 함수: 특정일 기준 환율·시세 (그날 값이 없으면 직전 값)
-- =====================================================================
CREATE FUNCTION fx_to_krw(p_currency char(3), p_date date)
RETURNS numeric LANGUAGE sql STABLE AS $$
    SELECT CASE WHEN p_currency = 'KRW' THEN 1::numeric ELSE (
        SELECT krw_rate FROM fx_rate
         WHERE currency = p_currency AND rate_date <= p_date
         ORDER BY rate_date DESC LIMIT 1)
    END
$$;

CREATE FUNCTION price_asof(p_instrument_id bigint, p_date date)
RETURNS numeric LANGUAGE sql STABLE AS $$
    SELECT close FROM price
     WHERE instrument_id = p_instrument_id AND price_date <= p_date
     ORDER BY price_date DESC LIMIT 1
$$;

-- =====================================================================
-- 뷰: 현재 상태 (오늘 기준)
-- =====================================================================

-- 계좌·통화별 현금 잔액
CREATE VIEW v_cash_balance AS
SELECT account_id, currency, sum(amount) AS balance
  FROM txn
 WHERE status = 'posted'
 GROUP BY account_id, currency;

-- 계좌·종목별 보유 수량
CREATE VIEW v_position AS
SELECT account_id, instrument_id, sum(quantity) AS quantity
  FROM txn
 WHERE status = 'posted' AND instrument_id IS NOT NULL AND quantity IS NOT NULL
 GROUP BY account_id, instrument_id
HAVING sum(quantity) <> 0;

-- 거래별 KRW 환산 (거래일 환율)
CREATE VIEW v_txn_krw AS
SELECT t.*, round(t.amount * fx_to_krw(t.currency, t.trade_date), 0) AS amount_krw
  FROM txn t;

-- 계좌별 현재 평가액 (KRW)
CREATE VIEW v_account_value AS
WITH cash AS (
    SELECT cb.account_id,
           sum(cb.balance * fx_to_krw(cb.currency, current_date)) AS cash_krw
      FROM v_cash_balance cb
     GROUP BY cb.account_id
), pos AS (
    -- 시세가 없으면(부동산 등 아직 미입력) 마지막 거래 단가로 평가
    SELECT p.account_id,
           sum(p.quantity * coalesce(price_asof(p.instrument_id, current_date),
                                     (SELECT t.unit_price FROM txn t
                                       WHERE t.account_id = p.account_id AND t.instrument_id = p.instrument_id
                                         AND t.unit_price IS NOT NULL AND t.status = 'posted'
                                       ORDER BY t.occurred_at DESC, t.id DESC LIMIT 1))
                          * fx_to_krw(i.currency, current_date)) AS holdings_krw
      FROM v_position p JOIN instrument i ON i.id = p.instrument_id
     GROUP BY p.account_id
), reported AS (
    SELECT DISTINCT ON (rb.account_id, rb.currency)
           rb.account_id, rb.currency, rb.total_value, rb.as_of
      FROM reported_balance rb
     ORDER BY rb.account_id, rb.currency, rb.as_of DESC
), reported_sum AS (
    SELECT account_id,
           sum(total_value * fx_to_krw(currency, current_date)) AS reported_krw,
           max(as_of) AS as_of
      FROM reported GROUP BY account_id
)
SELECT a.id AS account_id,
       a.household_id,
       a.name,
       a.account_type,
       a.valuation_method,
       CASE WHEN a.valuation_method = 'reported' THEN NULL ELSE coalesce(c.cash_krw, 0) END     AS cash_krw,
       CASE WHEN a.valuation_method = 'reported' THEN NULL ELSE coalesce(p.holdings_krw, 0) END AS holdings_krw,
       round(CASE WHEN a.valuation_method = 'reported' THEN coalesce(r.reported_krw, 0)
                  ELSE coalesce(c.cash_krw, 0) + coalesce(p.holdings_krw, 0) END, 0)          AS value_krw,
       r.as_of AS reported_as_of
  FROM account a
  LEFT JOIN cash c         ON c.account_id = a.id
  LEFT JOIN pos p          ON p.account_id = a.id
  LEFT JOIN reported_sum r ON r.account_id = a.id
 WHERE a.closed_on IS NULL;

-- 가구 순자산
CREATE VIEW v_net_worth AS
SELECT household_id,
       sum(value_krw) FILTER (WHERE value_krw > 0)  AS assets_krw,
       sum(value_krw) FILTER (WHERE value_krw < 0)  AS liabilities_krw,
       sum(value_krw)                               AS net_worth_krw
  FROM v_account_value
 GROUP BY household_id;

-- 구성원별 순자산 (공동명의는 지분만큼)
CREATE VIEW v_member_net_worth AS
SELECT m.household_id, m.id AS member_id, m.name,
       round(sum(v.value_krw * o.share), 0) AS net_worth_krw
  FROM member m
  JOIN account_owner o   ON o.member_id = m.id
  JOIN v_account_value v ON v.account_id = o.account_id
 GROUP BY m.household_id, m.id, m.name;

-- 월별 수입·지출 (transfer 카테고리 제외, KRW)
CREATE VIEW v_monthly_cashflow AS
SELECT a.household_id,
       date_trunc('month', t.trade_date)::date AS month,
       c.kind,
       coalesce(pc.name, c.name)                 AS top_category,
       sum(t.amount_krw)                         AS amount_krw
  FROM v_txn_krw t
  JOIN account a       ON a.id = t.account_id
  JOIN category c      ON c.id = t.category_id
  LEFT JOIN category pc ON pc.id = c.parent_id
 WHERE t.status = 'posted' AND c.kind IN ('income','expense')
 GROUP BY 1, 2, 3, 4;

-- 짝이 안 맞는 이체: 이체 카테고리인데 group이 없거나, 같은 통화 group 합이 0이 아님
CREATE VIEW v_unmatched_transfer AS
SELECT t.*
  FROM txn t
  JOIN category c ON c.id = t.category_id AND c.kind = 'transfer'
 WHERE t.status = 'posted'
   AND (t.group_id IS NULL
        OR (SELECT sum(x.amount) FROM txn x
             WHERE x.group_id = t.group_id AND x.currency = t.currency
               AND x.status = 'posted') <> 0);
