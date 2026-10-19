-- 기본 데이터: 주요 금융기관, 기본 카테고리 (household_id = NULL 은 전 가구 공통)

INSERT INTO institution (code, name, kind) VALUES
  ('KB',        'KB국민은행',     'bank'),
  ('SHINHAN',   '신한은행',       'bank'),
  ('WOORI',     '우리은행',       'bank'),
  ('HANA',      '하나은행',       'bank'),
  ('NH',        'NH농협은행',     'bank'),
  ('IBK',       'IBK기업은행',    'bank'),
  ('KAKAOBANK', '카카오뱅크',     'bank'),
  ('TOSSBANK',  '토스뱅크',       'bank'),
  ('KBANK',     '케이뱅크',       'bank'),
  ('KIS',       '한국투자증권',   'securities'),
  ('MIRAE',     '미래에셋증권',   'securities'),
  ('SAMSUNGSEC','삼성증권',       'securities'),
  ('KIWOOM',    '키움증권',       'securities'),
  ('NHSEC',     'NH투자증권',     'securities'),
  ('TOSSSEC',   '토스증권',       'securities'),
  ('KBCARD',    'KB국민카드',     'card'),
  ('SHINHANCARD','신한카드',      'card'),
  ('SAMSUNGCARD','삼성카드',      'card'),
  ('HYUNDAICARD','현대카드',      'card'),
  ('HANACARD',  '하나카드',       'card'),
  ('UPBIT',     '업비트',         'crypto_exchange'),
  ('BITHUMB',   '빗썸',           'crypto_exchange'),
  ('NPS',       '국민연금공단',   'pension'),
  ('NTS',       '국세청 홈택스',  'government'),
  ('SAMSUNGLIFE','삼성생명',      'insurance'),
  ('HANWHALIFE','한화생명',       'insurance');

-- 최상위 카테고리
INSERT INTO category (household_id, parent_id, name, kind, sort_order) VALUES
  (NULL, NULL, '근로소득',   'income',  10),
  (NULL, NULL, '사업소득',   'income',  20),
  (NULL, NULL, '금융소득',   'income',  30),
  (NULL, NULL, '기타수입',   'income',  90),
  (NULL, NULL, '식비',       'expense', 110),
  (NULL, NULL, '주거·통신',  'expense', 120),
  (NULL, NULL, '교통·차량',  'expense', 130),
  (NULL, NULL, '쇼핑',       'expense', 140),
  (NULL, NULL, '의료·건강',  'expense', 150),
  (NULL, NULL, '교육',       'expense', 160),
  (NULL, NULL, '문화·여가',  'expense', 170),
  (NULL, NULL, '경조사·선물','expense', 180),
  (NULL, NULL, '보험료',     'expense', 190),
  (NULL, NULL, '세금·공과금','expense', 200),
  (NULL, NULL, '이자비용',   'expense', 210),
  (NULL, NULL, '기타지출',   'expense', 290),
  (NULL, NULL, '내부이체',   'transfer', 900);

-- 하위 카테고리
INSERT INTO category (household_id, parent_id, name, kind, sort_order)
SELECT NULL, p.id, c.name, p.kind, c.ord
  FROM (VALUES
    ('근로소득',  '급여', 1), ('근로소득', '상여', 2),
    ('금융소득',  '배당금', 1), ('금융소득', '이자', 2), ('금융소득', '매매차익', 3),
    ('식비',      '외식', 1), ('식비', '장보기', 2), ('식비', '카페', 3), ('식비', '배달', 4),
    ('주거·통신', '관리비', 1), ('주거·통신', '월세', 2), ('주거·통신', '통신비', 3),
    ('교통·차량', '대중교통', 1), ('교통·차량', '주유', 2), ('교통·차량', '차량유지', 3),
    ('교육',      '학원', 1), ('교육', '등록금', 2),
    ('세금·공과금','소득세', 1), ('세금·공과금', '재산세', 2), ('세금·공과금', '자동차세', 3),
    ('내부이체',  '계좌이체', 1), ('내부이체', '카드대금', 2), ('내부이체', '투자이체', 3),
    ('내부이체',  '대출상환', 4), ('내부이체', '가족간이체', 5)
  ) AS c(parent, name, ord)
  JOIN category p ON p.name = c.parent AND p.household_id IS NULL AND p.parent_id IS NULL;
