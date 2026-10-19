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

async function call<T>(path: string, init?: RequestInit): Promise<T> {
  const r = await fetch(path, init);
  if (!r.ok) {
    let detail = `${r.status}`;
    try { detail = (await r.json()).detail ?? detail; } catch { /* 본문 없음 */ }
    throw new Error(typeof detail === "string" ? detail : JSON.stringify(detail));
  }
  return r.json() as Promise<T>;
}

export const api = {
  households: () => call<Household[]>("/api/households"),
  dashboard: (id: number, range: string) =>
    call<Dashboard>(`/api/households/${id}/dashboard?range=${encodeURIComponent(range)}`),
  refreshMarket: () => call<RefreshResult>("/api/market/refresh", { method: "POST" }),
};
