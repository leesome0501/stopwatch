-- 예제 가구 데이터. 데이터 모델이 실제 상황을 어떻게 담는지 보여주고,
-- db/tests.sql 이 손으로 계산한 값과 뷰 결과를 대조한다.
BEGIN;

INSERT INTO household (name) VALUES ('우리집');

INSERT INTO member (household_id, name, relation, birth_date, is_dependent)
SELECT h.id, m.name, m.rel, m.bd::date, m.dep
  FROM household h,
       (VALUES ('홍길동','self','1985-03-01',false),
               ('김영희','spouse','1987-07-15',false),
               ('홍아름','child','2018-05-20',true)) AS m(name, rel, bd, dep)
 WHERE h.name = '우리집';

INSERT INTO data_source (household_id, provider, label)
SELECT id, 'manual', '수동 입력' FROM household WHERE name = '우리집';

-- 계좌
INSERT INTO account (household_id, institution_id, name, account_type, valuation_method, data_source_id)
SELECT h.id, i.id, a.name, a.type, a.vm, ds.id
  FROM household h
  JOIN data_source ds ON ds.household_id = h.id
  JOIN (VALUES ('KB',          'KB 월급통장',      'checking',    'transactions'),
               ('KIS',         '한투 위탁',        'brokerage',   'transactions'),
               ('SHINHANCARD', '영희 신한카드',    'credit_card', 'transactions'),
               ('UPBIT',       '업비트',           'crypto',      'transactions'),
               (NULL,          '우리집 아파트',    'real_asset',  'transactions'),
               ('SAMSUNGLIFE', '영희 종신보험',    'insurance',   'reported'),
               ('KB',          '주택담보대출',     'loan',        'transactions')
       ) AS a(inst, name, type, vm) ON true
  LEFT JOIN institution i ON i.code = a.inst
 WHERE h.name = '우리집';

INSERT INTO account_owner (account_id, member_id, share)
SELECT a.id, m.id, o.share
  FROM (VALUES ('KB 월급통장','홍길동',1.0), ('한투 위탁','홍길동',1.0),
               ('영희 신한카드','김영희',1.0), ('업비트','홍길동',1.0),
               ('우리집 아파트','홍길동',0.5), ('우리집 아파트','김영희',0.5),
               ('영희 종신보험','김영희',1.0), ('주택담보대출','홍길동',1.0)
       ) AS o(acct, member, share)
  JOIN account a ON a.name = o.acct
  JOIN member m  ON m.name = o.member;

-- 종목
INSERT INTO instrument (kind, asset_class, symbol, market, isin, name, currency, country, household_id) VALUES
  ('stock','equity','005930','KRX','KR7005930003','삼성전자','KRW','KR',NULL),
  ('stock','equity','AAPL','NASDAQ','US0378331005','Apple','USD','US',NULL),
  ('crypto','crypto','KRW-BTC','UPBIT',NULL,'비트코인','KRW',NULL,NULL);
INSERT INTO instrument (kind, asset_class, symbol, market, name, currency, country, household_id)
SELECT 'real_estate','real_estate',NULL,'PRIVATE','우리집 아파트 84㎡','KRW','KR', id
  FROM household WHERE name = '우리집';

-- 시세, 환율
INSERT INTO price (instrument_id, price_date, close, source)
SELECT i.id, p.d::date, p.close, p.src
  FROM (VALUES ('삼성전자','2026-10-12',60000,'krx'), ('삼성전자','2026-10-15',70000,'krx'),
               ('Apple','2026-10-13',200,'kis'),      ('Apple','2026-10-15',220,'kis'),
               ('비트코인','2026-10-01',100000000,'upbit'), ('비트코인','2026-10-15',120000000,'upbit'),
               ('우리집 아파트 84㎡','2026-10-01',1000000000,'manual')
       ) AS p(name, d, close, src)
  JOIN instrument i ON i.name = p.name;

INSERT INTO fx_rate (currency, rate_date, krw_rate, source) VALUES
  ('USD','2026-10-13',1390,'kis'), ('USD','2026-10-15',1400,'kis');

-- 거래
-- 같은 group 문자를 쓰는 행끼리 하나의 사건(이체, 환전)이다.
CREATE TEMP TABLE _t (
  seq int, acct text, d date, kind text, amount numeric, cur char(3),
  inst text, qty numeric, price numeric, fee numeric, tax numeric,
  cat text, cp text, grp text
);
INSERT INTO _t VALUES
  -- KB 월급통장
  ( 1,'KB 월급통장','2026-10-01','adjustment',  10000000,'KRW',NULL,NULL,NULL,0,0, NULL,'기초잔액',NULL),
  ( 2,'KB 월급통장','2026-10-10','cash_in',      5000000,'KRW',NULL,NULL,NULL,0,0,'급여','(주)회사',NULL),
  ( 3,'KB 월급통장','2026-10-11','cash_out',    -1200000,'KRW',NULL,NULL,NULL,0,0,'카드대금','신한카드','g1'),
  ( 4,'KB 월급통장','2026-10-12','cash_out',    -3000000,'KRW',NULL,NULL,NULL,0,0,'투자이체','한국투자증권','g2'),
  ( 5,'KB 월급통장','2026-10-13','cash_out',    -1000000,'KRW',NULL,NULL,NULL,0,0,'대출상환','주담대 원금','g3'),
  -- 신한카드: 사용은 -, 대금 결제는 +
  ( 6,'영희 신한카드','2026-10-05','cash_out',   -200000,'KRW',NULL,NULL,NULL,0,0,'외식','고깃집',NULL),
  ( 7,'영희 신한카드','2026-10-06','cash_out',  -1000000,'KRW',NULL,NULL,NULL,0,0,'쇼핑','백화점',NULL),
  ( 8,'영희 신한카드','2026-10-11','cash_in',    1200000,'KRW',NULL,NULL,NULL,0,0,'카드대금','KB 출금','g1'),
  ( 9,'영희 신한카드','2026-10-14','cash_out',   -300000,'KRW',NULL,NULL,NULL,0,0,'장보기','마트',NULL),
  -- 한투 위탁: 입금, 국내주식 매수, 환전, 해외주식 매수, 배당
  (10,'한투 위탁','2026-10-12','cash_in',        3000000,'KRW',NULL,NULL,NULL,0,0,'투자이체','KB 입금','g2'),
  (11,'한투 위탁','2026-10-12','buy',           -1200150,'KRW','삼성전자',20,60000,150,0,NULL,NULL,NULL),
  (12,'한투 위탁','2026-10-13','fx',            -1390000,'KRW',NULL,NULL,NULL,0,0,NULL,'환전','g4'),
  (13,'한투 위탁','2026-10-13','fx',                1000,'USD',NULL,NULL,NULL,0,0,NULL,'환전','g4'),
  (14,'한투 위탁','2026-10-13','buy',               -801,'USD','Apple',4,200,1,0,NULL,NULL,NULL),
  (15,'한투 위탁','2026-10-15','dividend',          3.40,'USD','Apple',NULL,NULL,0,0.60,'배당금',NULL,NULL),
  -- 업비트
  (16,'업비트','2026-10-01','adjustment',          500000,'KRW',NULL,NULL,NULL,0,0,NULL,'기초잔액',NULL),
  (17,'업비트','2026-10-01','buy',                -400200,'KRW','비트코인',0.004,100000000,200,0,NULL,NULL,NULL),
  -- 아파트: 현금 없이 수량 1 입고, 단가는 취득가
  (18,'우리집 아파트','2026-10-01','instrument_in',     0,'KRW','우리집 아파트 84㎡',1,800000000,0,0,NULL,'취득',NULL),
  -- 대출: 잔액은 음수
  (19,'주택담보대출','2026-10-01','adjustment', -300000000,'KRW',NULL,NULL,NULL,0,0,NULL,'기초잔액',NULL),
  (20,'주택담보대출','2026-10-13','cash_in',      1000000,'KRW',NULL,NULL,NULL,0,0,'대출상환','KB 출금','g3');

INSERT INTO txn (account_id, occurred_at, trade_date, kind, amount, currency,
                 instrument_id, quantity, unit_price, fee, tax, category_id,
                 counterparty, group_id, data_source_id, dedupe_key)
SELECT a.id, (t.d + time '09:00') AT TIME ZONE 'Asia/Seoul', t.d, t.kind, t.amount, t.cur,
       i.id, t.qty, t.price, t.fee, t.tax, c.id,
       t.cp, CASE WHEN t.grp IS NULL THEN NULL
                  ELSE md5('sample-' || t.grp)::uuid END,
       a.data_source_id, 'sample-' || t.seq
  FROM _t t
  JOIN account a         ON a.name = t.acct
  LEFT JOIN instrument i ON i.name = t.inst
  LEFT JOIN category c   ON c.name = t.cat AND c.household_id IS NULL
 ORDER BY t.seq;

-- 보험: 거래 내역 없이 보고된 해지환급금으로 평가
INSERT INTO reported_balance (account_id, as_of, currency, total_value)
SELECT id, '2026-10-10', 'KRW', 15000000 FROM account WHERE name = '영희 종신보험';

COMMIT;
