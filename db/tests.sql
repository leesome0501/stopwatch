-- db/sample.sql 을 넣은 뒤 실행. 뷰 결과가 손 계산과 다르면 예외로 실패한다.
\set ON_ERROR_STOP on

CREATE OR REPLACE FUNCTION pg_temp.expect(label text, actual numeric, expected numeric)
RETURNS void LANGUAGE plpgsql AS $$
BEGIN
  IF actual IS DISTINCT FROM expected THEN
    RAISE EXCEPTION 'FAIL %: expected %, got %', label, expected, actual;
  END IF;
  RAISE NOTICE 'ok  %  = %', label, actual;
END $$;

SELECT pg_temp.expect('KB 월급통장 잔액', balance, 9800000)
  FROM v_cash_balance cb JOIN account a ON a.id = cb.account_id WHERE a.name = 'KB 월급통장';

SELECT pg_temp.expect('한투 KRW 예수금', balance, 409850)
  FROM v_cash_balance cb JOIN account a ON a.id = cb.account_id
 WHERE a.name = '한투 위탁' AND cb.currency = 'KRW';

SELECT pg_temp.expect('한투 USD 예수금', balance, 202.40)
  FROM v_cash_balance cb JOIN account a ON a.id = cb.account_id
 WHERE a.name = '한투 위탁' AND cb.currency = 'USD';

SELECT pg_temp.expect('삼성전자 보유수량', quantity, 20)
  FROM v_position p JOIN instrument i ON i.id = p.instrument_id WHERE i.name = '삼성전자';

-- 409,850 + 20*70,000 + (202.40 + 4*220) * 1,400
SELECT pg_temp.expect('한투 위탁 평가액', value_krw, 3325210)
  FROM v_account_value WHERE name = '한투 위탁';

SELECT pg_temp.expect('업비트 평가액', value_krw, 579800)
  FROM v_account_value WHERE name = '업비트';

SELECT pg_temp.expect('신한카드 미결제', value_krw, -300000)
  FROM v_account_value WHERE name = '영희 신한카드';

SELECT pg_temp.expect('보험 (보고 잔액)', value_krw, 15000000)
  FROM v_account_value WHERE name = '영희 종신보험';

SELECT pg_temp.expect('가구 자산', assets_krw, 1028705010) FROM v_net_worth;
SELECT pg_temp.expect('가구 부채', liabilities_krw, -299300000) FROM v_net_worth;
SELECT pg_temp.expect('가구 순자산', net_worth_krw, 729405010) FROM v_net_worth;

SELECT pg_temp.expect('홍길동 순자산', net_worth_krw, 214705010)
  FROM v_member_net_worth WHERE name = '홍길동';
SELECT pg_temp.expect('김영희 순자산', net_worth_krw, 514700000)
  FROM v_member_net_worth WHERE name = '김영희';

-- 수입: 급여 5,000,000 + 배당 3.40 USD * 1,400 = 5,004,760 (이체는 제외)
SELECT pg_temp.expect('10월 수입', sum(amount_krw), 5004760)
  FROM v_monthly_cashflow WHERE month = '2026-10-01' AND kind = 'income';
SELECT pg_temp.expect('10월 지출', sum(amount_krw), -1500000)
  FROM v_monthly_cashflow WHERE month = '2026-10-01' AND kind = 'expense';

SELECT pg_temp.expect('짝 안 맞는 이체 수', count(*), 0) FROM v_unmatched_transfer;

-- 제약 조건: 같은 거래 중복 입력은 거부되어야 한다
DO $$
BEGIN
  INSERT INTO txn (account_id, occurred_at, trade_date, kind, amount, currency, dedupe_key)
  SELECT id, now(), current_date, 'cash_in', 1, 'KRW', 'sample-1' FROM account WHERE name = 'KB 월급통장';
  RAISE EXCEPTION 'FAIL 중복 거래가 들어갔다';
EXCEPTION WHEN unique_violation THEN
  RAISE NOTICE 'ok  중복 거래 거부';
END $$;

-- 제약 조건: 매수인데 수량이 음수면 거부
DO $$
BEGIN
  INSERT INTO txn (account_id, occurred_at, trade_date, kind, amount, currency, instrument_id, quantity, dedupe_key)
  SELECT a.id, now(), current_date, 'buy', -1, 'KRW', i.id, -1, 'bad-buy'
    FROM account a, instrument i WHERE a.name = '한투 위탁' AND i.name = '삼성전자';
  RAISE EXCEPTION 'FAIL 잘못된 매수가 들어갔다';
EXCEPTION WHEN check_violation THEN
  RAISE NOTICE 'ok  음수 매수 거부';
END $$;

\echo 'ALL TESTS PASSED'
