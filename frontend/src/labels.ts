export const ACCOUNT_TYPES: { code: string; label: string; group: string; reported?: boolean }[] = [
  { code: "checking", label: "입출금", group: "은행" },
  { code: "savings", label: "예금(자유)", group: "은행" },
  { code: "time_deposit", label: "정기예금", group: "은행" },
  { code: "installment_savings", label: "적금", group: "은행" },
  { code: "cma", label: "CMA", group: "투자" },
  { code: "brokerage", label: "위탁(주식)", group: "투자" },
  { code: "isa", label: "ISA", group: "투자" },
  { code: "pension_savings", label: "연금저축", group: "연금" },
  { code: "irp", label: "IRP", group: "연금" },
  { code: "dc_pension", label: "퇴직연금(DC)", group: "연금" },
  { code: "crypto", label: "가상자산", group: "투자" },
  { code: "credit_card", label: "신용카드", group: "부채" },
  { code: "loan", label: "대출", group: "부채" },
  { code: "insurance", label: "보험", group: "기타", reported: true },
  { code: "real_asset", label: "부동산·실물", group: "기타" },
  { code: "cash", label: "현금", group: "기타" },
  { code: "other", label: "기타", group: "기타" },
];
export const accountTypeLabel = (code: string) => ACCOUNT_TYPES.find((t) => t.code === code)?.label ?? code;

export const RELATIONS: [string, string][] = [
  ["self", "본인"], ["spouse", "배우자"], ["child", "자녀"], ["parent", "부모"], ["sibling", "형제자매"], ["other", "기타"],
];
export const relationLabel = (r: string) => RELATIONS.find(([k]) => k === r)?.[1] ?? r;

export const MARKETS: { code: string; label: string; currency: string; kind: string; asset_class: string; hint: string }[] = [
  { code: "KRX", label: "국내 (코스피·ETF)", currency: "KRW", kind: "stock", asset_class: "equity", hint: "종목코드 6자리 예: 005930" },
  { code: "KOSDAQ", label: "국내 (코스닥)", currency: "KRW", kind: "stock", asset_class: "equity", hint: "종목코드 6자리" },
  { code: "NASDAQ", label: "미국 나스닥", currency: "USD", kind: "stock", asset_class: "equity", hint: "티커 예: AAPL" },
  { code: "NYSE", label: "미국 뉴욕", currency: "USD", kind: "stock", asset_class: "equity", hint: "티커 예: KO" },
  { code: "AMEX", label: "미국 아멕스(ETF)", currency: "USD", kind: "etf", asset_class: "equity", hint: "티커 예: SPY" },
  { code: "UPBIT", label: "업비트", currency: "KRW", kind: "crypto", asset_class: "crypto", hint: "마켓 코드 예: KRW-BTC" },
  { code: "PRIVATE", label: "부동산·비상장 (시세 직접 입력)", currency: "KRW", kind: "real_estate", asset_class: "real_estate", hint: "종목코드 없이 이름만" },
];

export const INSTRUMENT_KINDS: [string, string][] = [
  ["stock", "주식"], ["etf", "ETF"], ["etn", "ETN"], ["fund", "펀드"], ["bond", "채권"], ["reit", "리츠"],
  ["crypto", "가상자산"], ["gold", "금"], ["real_estate", "부동산"], ["vehicle", "차량"], ["other", "기타"],
];
export const ASSET_CLASSES: [string, string][] = [
  ["equity", "주식"], ["bond", "채권"], ["cash_equiv", "현금성"], ["commodity", "원자재"], ["crypto", "가상자산"],
  ["real_estate", "부동산"], ["alternative", "대체투자"], ["mixed", "혼합"],
];
export const assetClassLabel = (c: string) => ASSET_CLASSES.find(([k]) => k === c)?.[1] ?? c;

export const KIND_LABEL: Record<string, string> = {
  cash_in: "입금", cash_out: "출금", buy: "매수", sell: "매도", dividend: "배당", interest: "이자", fee: "수수료",
  tax: "세금", fx: "환전", instrument_in: "입고", instrument_out: "출고", split: "분할", adjustment: "잔액조정",
};

export const CATEGORY_KIND_LABEL = { income: "수입", expense: "지출", transfer: "이체" } as const;

export const INSTITUTION_KIND_LABEL: Record<string, string> = {
  bank: "은행", securities: "증권", card: "카드", insurance: "보험", crypto_exchange: "가상자산",
  pension: "연금", government: "공공", other: "기타",
};
