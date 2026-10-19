// 백엔드는 금액을 문자열로 준다(정밀도 보존). 화면에서는 num() 으로 바꿔 쓴다.
export type Money = string;

export interface Household { id: number; name: string }

export interface HistoryPoint { date: string; net_worth_krw: Money; assets_krw: Money; liabilities_krw: Money }
export interface AccountRow {
  id: number; name: string; account_type: string; type_label: string; institution: string | null;
  valuation_method: string; owners: { member_id: number; name: string; share: Money }[];
  value_krw: Money; reported_as_of: string | null;
}
export interface Holding {
  account_id: number; account_name: string; instrument_id: number; name: string; symbol: string | null;
  market: string | null; currency: string; asset_class: string; quantity: Money; avg_cost: Money | null;
  cost_krw: Money; price: Money | null; price_date: string | null; price_basis: "market" | "trade" | "none";
  value_krw: Money; pnl_krw: Money | null; pnl_pct: Money | null;
}
export interface SyncRun {
  id: number; started_at: string; finished_at: string | null; status: string;
  prices_upserted: number; fx_upserted: number; errors: { target: string; message: string }[];
}
export interface Dashboard {
  as_of: string;
  household: Household;
  kpi: {
    net_worth_krw: Money; assets_krw: Money; liabilities_krw: Money;
    change_1m: { from_date: string; amount_krw: Money; pct: Money | null } | null;
    month: string; month_income_krw: Money; month_expense_krw: Money;
  };
  history: { range: string; points: HistoryPoint[] };
  allocation: { asset_class: string; value_krw: Money; share: Money }[];
  accounts: AccountRow[];
  members: { member_id: number; name: string; net_worth_krw: Money }[];
  holdings: Holding[];
  cashflow: {
    months: { month: string; income_krw: Money; expense_krw: Money }[];
    this_month_by_category: { category: string; amount_krw: Money }[];
  };
  market: { last_run: SyncRun | null; stale: { name: string; reason: string; auto: boolean }[] };
}
export interface RefreshResult {
  status: string; prices_upserted: number; fx_upserted: number;
  errors: { target: string; message: string }[]; manual_only: string[];
}

export type Relation = "self" | "spouse" | "child" | "parent" | "sibling" | "other";
export interface Member { id: number; household_id: number; name: string; relation: Relation; birth_date: string | null; is_dependent: boolean }
export interface Institution { id: number; code: string; name: string; kind: string }
export interface OwnerShare { member_id: number; share: Money | number }
export interface Account {
  id: number; household_id: number; name: string; account_type: string; institution_code: string | null;
  institution_name: string | null; valuation_method: "transactions" | "reported"; base_currency: string;
  account_number_masked: string | null; visibility: string; opened_on: string | null; maturity_on: string | null;
  closed_on: string | null; interest_rate: Money | null; memo: string | null; owners: OwnerShare[];
  data_source_id: number | null; external_ref: string | null;
}
export interface AccountInput {
  name: string; account_type: string; institution_code?: string | null; valuation_method?: string;
  base_currency?: string; account_number_masked?: string | null; opened_on?: string | null;
  maturity_on?: string | null; interest_rate?: string | null; memo?: string | null; owners: OwnerShare[];
}
export interface Category { id: number; household_id: number | null; parent_id: number | null; name: string; kind: "income" | "expense" | "transfer" }
export interface CategoryRule {
  id: number; match_field: "description" | "counterparty"; match_type: "contains" | "equals" | "regex";
  pattern: string; category_id: number; category_name: string; account_id: number | null; priority: number; enabled: boolean;
}
export interface Instrument {
  id: number; kind: string; asset_class: string; name: string; currency: string; symbol: string | null;
  market: string | null; isin: string | null; country: string | null; household_id: number | null; price_code: string | null;
}
export interface PricePoint { price_date: string; close: Money; source: string }
export interface ReportedBalance { as_of: string; currency: string; total_value: Money; cash_amount: Money | null }
export interface Txn {
  id: number; account_id: number; occurred_at: string; trade_date: string; kind: string; amount: Money; currency: string;
  instrument_id: number | null; quantity: Money | null; unit_price: Money | null; balance_after: Money | null;
  fee: Money; tax: Money; category_id: number | null; counterparty: string | null; description: string | null;
  memo: string | null; group_id: string | null; status: string;
  account_name: string; category_name: string | null; category_parent: string | null; category_kind: string | null;
  instrument_name: string | null; instrument_symbol: string | null; amount_krw: Money;
}
export interface TxnPage { total: number; sum_in_krw: Money; sum_out_krw: Money; items: Txn[] }
export interface TxnQuery {
  account_id?: number; date_from?: string; date_to?: string; category_id?: number; uncategorized?: boolean;
  q?: string; direction?: "" | "in" | "out"; limit?: number; offset?: number;
}
export interface ImportRow {
  file_index: number; status: "new" | "duplicate" | "error"; occurred_at: string | null; trade_date: string | null;
  kind: string | null; amount: Money | null; currency: string | null; description: string | null;
  counterparty: string | null; balance_after: Money | null; instrument_symbol: string | null; quantity: Money | null;
  unit_price: Money | null; category_id: number | null; category_name: string | null;
  category_source: "file" | "rule" | "history" | "kind" | null; message: string | null;
}
export interface ImportResult {
  committed: boolean; batch_id: number | null; format: string | null; file_direction: string | null;
  account_number: string | null; counts: { total: number; new: number; duplicate: number; error: number };
  opening_balance: Money | null; warnings: string[]; rows: ImportRow[];
}
export interface ImportBatch {
  id: number; started_at: string; finished_at: string | null; status: string; file_name: string | null;
  records_total: number; records_new: number; records_duplicate: number; error: string | null;
}

export type BrokerProvider = "kiwoom" | "kis";
export interface BrokerConnection {
  id: number; provider: BrokerProvider; provider_name: string; label: string; member_id: number | null;
  member_name: string | null; environment: "real" | "mock" | null; key_hint: string | null; kis_accounts: string[];
  status: string; last_synced_at: string | null; last_error: string | null;
  linked: { account_id: number; account_name: string; ref: string; synced_until: string | null; start_date: string | null }[];
  last_run: { id: number; started_at: string; finished_at: string | null; status: string; error: string | null } | null;
}
export interface BrokerAccountItem { ref: string; label: string; account_id?: number | null; account_name?: string | null }
export interface SyncAccountResult {
  account_id: number; account_name: string; ref: string; period: [string, string]; new: number; duplicate: number;
  errors: string[]; warnings: string[]; broker_cash: Record<string, string>; broker_total: string | null;
  adjustments: ({ type: "cash"; currency: string; diff: string } | { type: "quantity"; symbol: string; name: string; diff: string })[];
}
export interface SyncResult {
  run_id: number; status: string; error: string | null; accounts: SyncAccountResult[];
  failures: { account_id: number; account_name: string; error: string }[];
}
export interface ConnectionInput {
  provider: BrokerProvider; member_id: number; environment: "real" | "mock"; app_key: string; app_secret: string;
  accounts?: string[]; label?: string;
}

async function call<T>(path: string, init?: RequestInit): Promise<T> {
  const r = await fetch(path, init);
  if (!r.ok) {
    let detail: unknown = `${r.status}`;
    try { detail = (await r.json()).detail ?? detail; } catch { /* 본문 없음 */ }
    if (Array.isArray(detail)) {
      // FastAPI 검증 오류: [{loc, msg}] → 읽을 수 있는 한 줄로
      detail = detail.map((d: { loc?: unknown[]; msg?: string }) => `${(d.loc ?? []).slice(1).join(".")}: ${d.msg}`).join(", ");
    }
    throw new Error(typeof detail === "string" ? detail : JSON.stringify(detail));
  }
  if (r.status === 204) return undefined as T;
  return r.json() as Promise<T>;
}

const json = (method: string, body: unknown): RequestInit => ({
  method, headers: { "Content-Type": "application/json" }, body: JSON.stringify(body),
});

function qs(params: object): string {
  const p = new URLSearchParams();
  for (const [k, v] of Object.entries(params)) {
    if (v === undefined || v === null || v === "" || v === false) continue;
    p.set(k, String(v));
  }
  const s = p.toString();
  return s ? `?${s}` : "";
}

function upload(file: File): RequestInit {
  const fd = new FormData();
  fd.append("file", file);
  return { method: "POST", body: fd };
}

export const api = {
  households: () => call<Household[]>("/api/households"),
  createHousehold: (name: string) => call<Household>("/api/households", json("POST", { name })),
  renameHousehold: (id: number, name: string) => call<Household>(`/api/households/${id}`, json("PATCH", { name })),
  deleteHousehold: (id: number, confirm_name: string) => call<void>(`/api/households/${id}`, json("DELETE", { confirm_name })),
  dashboard: (id: number, range: string) =>
    call<Dashboard>(`/api/households/${id}/dashboard?range=${encodeURIComponent(range)}`),
  refreshMarket: () => call<RefreshResult>("/api/market/refresh", { method: "POST" }),

  members: (hid: number) => call<Member[]>(`/api/households/${hid}/members`),
  createMember: (hid: number, m: Partial<Member>) => call<Member>(`/api/households/${hid}/members`, json("POST", m)),
  updateMember: (id: number, m: Partial<Member>) => call<Member>(`/api/members/${id}`, json("PATCH", m)),
  deleteMember: (id: number) => call<void>(`/api/members/${id}`, { method: "DELETE" }),

  institutions: () => call<Institution[]>("/api/institutions"),
  accounts: (hid: number, includeClosed = false) =>
    call<Account[]>(`/api/households/${hid}/accounts${qs({ include_closed: includeClosed })}`),
  createAccount: (hid: number, a: AccountInput) => call<Account>(`/api/households/${hid}/accounts`, json("POST", a)),
  updateAccount: (id: number, a: Partial<AccountInput> & { closed_on?: string | null }) =>
    call<Account>(`/api/accounts/${id}`, json("PATCH", a)),
  setOwners: (id: number, owners: OwnerShare[]) => call<Account>(`/api/accounts/${id}/owners`, json("PUT", owners)),
  deleteAccount: (id: number) => call<void>(`/api/accounts/${id}`, { method: "DELETE" }),
  reportedBalances: (id: number) => call<ReportedBalance[]>(`/api/accounts/${id}/reported-balances`),
  putReportedBalance: (id: number, b: { as_of: string; total_value: string; currency?: string }) =>
    call<ReportedBalance[]>(`/api/accounts/${id}/reported-balances`, json("PUT", [b])),
  deleteReportedBalance: (id: number, asOf: string, currency = "KRW") =>
    call<void>(`/api/accounts/${id}/reported-balances/${asOf}${qs({ currency })}`, { method: "DELETE" }),

  categories: (hid: number) => call<Category[]>(`/api/households/${hid}/categories`),
  createCategory: (hid: number, c: { name: string; parent_id?: number | null; kind?: string }) =>
    call<Category>(`/api/households/${hid}/categories`, json("POST", c)),
  rules: (hid: number) => call<CategoryRule[]>(`/api/households/${hid}/category-rules`),
  createRule: (hid: number, r: Partial<CategoryRule>) =>
    call<CategoryRule>(`/api/households/${hid}/category-rules`, json("POST", r)),
  deleteRule: (hid: number, id: number) => call<void>(`/api/households/${hid}/category-rules/${id}`, { method: "DELETE" }),

  instruments: (hid: number, q = "") => call<Instrument[]>(`/api/instruments${qs({ household_id: hid, q, limit: 200 })}`),
  createInstrument: (i: Partial<Instrument>) => call<Instrument>("/api/instruments", json("POST", i)),
  updateInstrument: (id: number, i: Partial<Instrument>) => call<Instrument>(`/api/instruments/${id}`, json("PATCH", i)),
  prices: (id: number, limit = 10) => call<PricePoint[]>(`/api/instruments/${id}/prices${qs({ limit })}`),
  putPrice: (id: number, price_date: string, close: string) =>
    call<void>(`/api/instruments/${id}/prices`, json("PUT", [{ price_date, close, source: "manual" }])),

  transactions: (hid: number, q: TxnQuery) => call<TxnPage>(`/api/households/${hid}/transactions${qs(q)}`),
  createTransaction: (accountId: number, t: Record<string, unknown>) =>
    call<Txn>(`/api/accounts/${accountId}/transactions`, json("POST", t)),
  updateTransaction: (id: number, t: { category_id?: number | null; memo?: string | null }) =>
    call<Txn>(`/api/transactions/${id}`, json("PATCH", t)),
  voidTransaction: (id: number) => call<void>(`/api/transactions/${id}`, { method: "DELETE" }),

  previewImport: (accountId: number, file: File) => call<ImportResult>(`/api/accounts/${accountId}/imports/preview`, upload(file)),
  commitImport: (accountId: number, file: File) => call<ImportResult>(`/api/accounts/${accountId}/imports`, upload(file)),
  importBatches: (accountId: number) => call<ImportBatch[]>(`/api/accounts/${accountId}/imports`),

  connections: (hid: number) => call<BrokerConnection[]>(`/api/households/${hid}/connections`),
  createConnection: (hid: number, c: ConnectionInput) =>
    call<BrokerConnection & { broker_accounts: BrokerAccountItem[] }>(`/api/households/${hid}/connections`, json("POST", c)),
  updateConnection: (id: number, c: Partial<ConnectionInput>) => call<BrokerConnection>(`/api/connections/${id}`, json("PATCH", c)),
  deleteConnection: (id: number) => call<void>(`/api/connections/${id}`, { method: "DELETE" }),
  brokerAccounts: (id: number) => call<BrokerAccountItem[]>(`/api/connections/${id}/broker-accounts`),
  linkAccount: (id: number, body: { ref: string; account_id?: number | null; create_name?: string; start_date?: string }) =>
    call<BrokerConnection>(`/api/connections/${id}/link`, json("POST", body)),
  unlinkAccount: (id: number, ref: string) => call<BrokerConnection>(`/api/connections/${id}/unlink`, json("POST", { ref })),
  syncConnection: (id: number) => call<SyncResult>(`/api/connections/${id}/sync`, { method: "POST" }),
};
