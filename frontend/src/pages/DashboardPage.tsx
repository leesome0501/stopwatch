import { useCallback, useEffect, useState } from "react";
import { api, type Dashboard, type RefreshResult } from "../api";
import { BarList } from "../components/BarList";
import { CashflowChart } from "../components/CashflowChart";
import { NetWorthChart } from "../components/NetWorthChart";
import { AccountsTable, HoldingsTable } from "../components/Tables";
import { TableView } from "../components/TableView";
import { arrow, dateTime, direction, krw, monthLabel, num, share, signedPct, won } from "../format";
import { navigate } from "../router";

const RANGES = [["1m", "1개월"], ["3m", "3개월"], ["6m", "6개월"], ["1y", "1년"], ["3y", "3년"], ["all", "전체"]] as const;
const RANGE_KEY = "assethub.range";

function loadRange(): string {
  try { return localStorage.getItem(RANGE_KEY) ?? "1y"; } catch { return "1y"; }
}

export function DashboardPage({ hid }: { hid: number }) {
  const [range, setRange] = useState<string>(loadRange);
  const [data, setData] = useState<Dashboard | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [refreshing, setRefreshing] = useState(false);
  const [refreshResult, setRefreshResult] = useState<RefreshResult | null>(null);

  const load = useCallback(() => {
    setLoading(true);
    try { localStorage.setItem(RANGE_KEY, range); } catch { /* 저장 안 되는 환경 */ }
    api.dashboard(hid, range)
      .then((d) => { setData(d); setError(null); })
      .catch((e) => setError(String(e.message ?? e)))
      .finally(() => setLoading(false));
  }, [hid, range]);
  useEffect(load, [load]);

  const refresh = async () => {
    setRefreshing(true);
    try { setRefreshResult(await api.refreshMarket()); load(); }
    catch (e) { setError(`시세 새로고침 실패: ${(e as Error).message}`); }
    finally { setRefreshing(false); }
  };

  const last = data?.market.last_run;
  return (
    <div className={loading && data ? "loading" : ""}>
      <div className="filters">
        <div className="segmented" role="group" aria-label="기간">
          {RANGES.map(([k, label]) => (
            <button key={k} aria-pressed={range === k} onClick={() => setRange(k)}>{label}</button>
          ))}
        </div>
        <div className="market">
          {last ? <span>시세 {dateTime(last.started_at)} {last.status === "succeeded" ? "수집" : last.status === "running" ? "수집 중" : "일부 실패"}</span>
            : <span>시세를 아직 수집하지 않았습니다</span>}
          <button className="btn" onClick={refresh} disabled={refreshing}>{refreshing ? "수집 중…" : "시세 새로고침"}</button>
        </div>
      </div>

      {error && <div className="notice error" role="alert">{error}</div>}
      {refreshResult && refreshResult.errors.length > 0 && (
        <div className="notice" role="status">
          시세를 받지 못한 항목이 있습니다.
          <ul>{refreshResult.errors.map((e) => <li key={e.target}>{e.target}: {e.message}</li>)}</ul>
        </div>
      )}
      {data && data.accounts.length === 0 && (
        <div className="ok-note">
          아직 계좌가 없습니다. <button className="btn link" onClick={() => navigate("/manage")}>관리</button>에서 가족과 계좌를 등록하고,{" "}
          <button className="btn link" onClick={() => navigate("/import")}>가져오기</button>에서 거래 파일을 올리세요.
        </div>
      )}
      {data && <Main data={data} />}
    </div>
  );
}

function Main({ data }: { data: Dashboard }) {
  const k = data.kpi;
  const net = num(k.net_worth_krw);
  const change = k.change_1m;
  const stale = data.market.stale;
  const allocTotal = data.allocation.reduce((s, a) => s + num(a.value_krw), 0);

  return (
    <div className="grid">
      <section className="card hero" aria-label="요약">
        <div>
          <div className="hero-label">순자산</div>
          <div className="hero-value">{krw(net)}<span className="unit">원</span></div>
          {change && (
            <div className="delta">
              <span className={direction(num(change.amount_krw))}>
                {arrow(num(change.amount_krw))} {krw(Math.abs(num(change.amount_krw)))}
                {change.pct != null && ` (${signedPct(num(change.pct))})`}
              </span>{" "}
              지난 30일
            </div>
          )}
        </div>
        <div className="kpis">
          <div className="kpi"><div className="label">자산</div><div className="value">{krw(num(k.assets_krw))}</div></div>
          <div className="kpi"><div className="label">부채</div><div className="value">{krw(num(k.liabilities_krw))}</div></div>
          <div className="kpi"><div className="label">{monthLabel(k.month)} 수입</div><div className="value">{krw(num(k.month_income_krw))}</div></div>
          <div className="kpi"><div className="label">{monthLabel(k.month)} 지출</div><div className="value">{krw(num(k.month_expense_krw))}</div></div>
        </div>
      </section>

      <section className="card">
        <h2>순자산 추이</h2>
        <p className="sub">자산에서 부채를 뺀 값 · 그날 종가와 환율로 평가</p>
        <NetWorthChart points={data.history.points} />
      </section>

      <div className="grid two">
        <section className="card">
          <h2>자산 구성</h2>
          <p className="sub">부채를 빼기 전 자산 {krw(allocTotal)}원 기준</p>
          <BarList items={data.allocation.map((a) => ({ label: a.asset_class, value: num(a.value_krw), note: share(num(a.share)) }))}
            format={krw} empty="자산이 없습니다." />
          <TableView head={["구분", "금액", "비율"]}
            rows={data.allocation.map((a) => [a.asset_class, won(num(a.value_krw)), share(num(a.share))])} />
        </section>
        <section className="card">
          <h2>구성원별 순자산</h2>
          <p className="sub">공동명의는 지분만큼 나눔</p>
          <BarList items={data.members.map((m) => ({ label: m.name, value: num(m.net_worth_krw) }))}
            format={krw} empty="명의가 지정된 계좌가 없습니다." />
          {data.members.some((m) => num(m.net_worth_krw) <= 0) && (
            <p className="sub" style={{ marginTop: 10 }}>
              순자산이 0 이하인 구성원: {data.members.filter((m) => num(m.net_worth_krw) <= 0).map((m) => `${m.name} ${won(num(m.net_worth_krw))}`).join(", ")}
            </p>
          )}
          <TableView head={["구성원", "순자산"]} rows={data.members.map((m) => [m.name, won(num(m.net_worth_krw))])} />
        </section>
      </div>

      <div className="grid two">
        <section className="card">
          <h2>수입과 지출</h2>
          <p className="sub">최근 6개월 · 내부이체 제외</p>
          <CashflowChart months={data.cashflow.months} />
        </section>
        <section className="card">
          <h2>{monthLabel(k.month)} 지출</h2>
          <p className="sub">카테고리별</p>
          <BarList items={data.cashflow.this_month_by_category.map((c) => ({ label: c.category, value: num(c.amount_krw) }))}
            format={krw} empty="이번 달 분류된 지출이 없습니다." />
          <TableView head={["카테고리", "금액"]}
            rows={data.cashflow.this_month_by_category.map((c) => [c.category, won(num(c.amount_krw))])} />
        </section>
      </div>

      <section className="card">
        <h2>보유 종목</h2>
        <p className="sub">평균단가는 이동평균 · 손익은 매수일 환율 기준 원화</p>
        {stale.length > 0 && (
          <div className="notice">
            최신 시세가 아닌 종목이 있습니다.
            <ul>{stale.map((s) => <li key={s.name}>{s.name}: {s.reason}{!s.auto && " · 수동 입력 대상"}</li>)}</ul>
          </div>
        )}
        <HoldingsTable holdings={data.holdings} />
      </section>

      <section className="card">
        <h2>계좌</h2>
        <p className="sub">평가액 큰 순서</p>
        <AccountsTable accounts={data.accounts} />
      </section>
    </div>
  );
}
