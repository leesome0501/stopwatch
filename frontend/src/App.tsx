import { useCallback, useEffect, useState } from "react";
import { api, type Household } from "./api";
import { DashboardPage } from "./pages/DashboardPage";
import { ImportPage } from "./pages/ImportPage";
import { ManagePage } from "./pages/ManagePage";
import { Onboarding } from "./pages/Onboarding";
import { TransactionsPage } from "./pages/TransactionsPage";
import { useRoute } from "./router";

const HOUSEHOLD_KEY = "assethub.household";
const NAV = [["/", "대시보드"], ["/transactions", "거래내역"], ["/import", "가져오기"], ["/manage", "관리"]] as const;

function savedHousehold(): number | null {
  try { const v = localStorage.getItem(HOUSEHOLD_KEY); return v ? Number(v) : null; } catch { return null; }
}

export function App() {
  const route = useRoute();
  const [households, setHouseholds] = useState<Household[] | null>(null);
  const [hid, setHid] = useState<number | null>(savedHousehold);
  const [error, setError] = useState<string | null>(null);

  const loadHouseholds = useCallback(() => {
    api.households().then((hs) => {
      setHouseholds(hs);
      setHid((cur) => (hs.some((h) => h.id === cur) ? cur : hs[0]?.id ?? null));
    }).catch((e) => setError(String(e.message ?? e)));
  }, []);
  useEffect(loadHouseholds, [loadHouseholds]);
  // 지운 가구를 바로 목록에서 빼야 대시보드가 없는 가구를 부르지 않는다
  const onHouseholdDeleted = useCallback((id: number) => {
    setHouseholds((hs) => {
      const rest = (hs ?? []).filter((h) => h.id !== id);
      setHid(rest[0]?.id ?? null);
      return rest;
    });
  }, []);
  useEffect(() => {
    if (hid != null) try { localStorage.setItem(HOUSEHOLD_KEY, String(hid)); } catch { /* 무시 */ }
  }, [hid]);

  if (error) return <div className="app"><div className="notice error" role="alert">서버에 연결하지 못했습니다: {error}</div></div>;
  if (!households) return <div className="app"><div className="empty">불러오는 중…</div></div>;
  if (!households.length || hid == null) {
    return <div className="app"><Onboarding onDone={(id) => { setHid(id); loadHouseholds(); }} /></div>;
  }
  const household = households.find((h) => h.id === hid)!;
  const path = route.path;

  return (
    <div className="app">
      <header className="topbar">
        <h1>{household.name} 자산</h1>
        {households.length > 1 && (
          <select aria-label="가구 선택" value={hid} onChange={(e) => setHid(Number(e.target.value))}>
            {households.map((h) => <option key={h.id} value={h.id}>{h.name}</option>)}
          </select>
        )}
      </header>
      <nav className="nav" aria-label="화면">
        {NAV.map(([to, label]) => (
          <a key={to} href={`#${to}`} aria-current={path === to ? "page" : undefined}>{label}</a>
        ))}
      </nav>
      <main key={hid}>
        {path === "/transactions" ? <TransactionsPage hid={hid} params={route.params} />
          : path === "/import" ? <ImportPage hid={hid} params={route.params} />
          : path === "/manage" ? <ManagePage household={household} onHouseholdsChanged={loadHouseholds} onHouseholdDeleted={onHouseholdDeleted} />
          : <DashboardPage hid={hid} />}
      </main>
    </div>
  );
}
