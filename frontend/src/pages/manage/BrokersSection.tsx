import { useState } from "react";
import { api, type Account, type BrokerAccountItem, type BrokerConnection, type BrokerProvider, type Member, type SyncResult } from "../../api";
import { dateTime, num, won } from "../../format";
import { ErrorNote, Field, todayKst, useAction, useLoad } from "../../ui";

const GUIDE: Record<BrokerProvider, string[]> = {
  kiwoom: [
    "키움 Open API 홈페이지(openapi.kiwoom.com)에서 계좌를 등록하고 앱키를 발급받습니다.",
    "발급 전에 이 PC의 공인 IP를 등록해야 합니다. 집 인터넷 IP가 바뀌면 다시 등록하세요.",
    "3개월 동안 접속하지 않으면 키움이 자동 해지하므로, 매일 자동 수집(collect.cmd)을 켜 두는 것이 좋습니다.",
    "입출금·배당·이자·세금·수수료까지 거래내역으로 받습니다. 해외주식은 아직 지원하지 않습니다.",
  ],
  kis: [
    "KIS Developers(apiportal.koreainvestment.com)에서 HTS ID에 연결된 계좌로 실전 앱키를 신청합니다.",
    "토큰을 발급할 때마다 카카오톡 알림이 옵니다. AssetHub는 토큰을 저장해 하루에 한 번만 발급받습니다.",
    "체결 내역은 받지만 입출금·배당·수수료는 API에 없어서, 동기화 때 증권사 잔고와 맞추는 '잔고 맞춤' 거래로 채웁니다.",
    "계좌번호는 '종합계좌 8자리-상품코드 2자리'(예: 12345678-01)로 입력합니다. 퇴직연금 DC 계좌는 조회되지 않습니다.",
  ],
};
const ENV_LABEL = { real: "실전", mock: "모의투자" } as const;

function yearAgo(): string {
  const d = new Date(`${todayKst()}T00:00:00Z`);
  d.setUTCFullYear(d.getUTCFullYear() - 1);
  return d.toISOString().slice(0, 10);
}

function SyncReport({ result }: { result: SyncResult }) {
  return (
    <div className={result.status === "failed" ? "notice error" : "ok-note"} role="status">
      {result.error && <div>{result.error}</div>}
      {result.accounts.map((a) => (
        <div key={a.account_id} style={{ marginTop: 4 }}>
          <strong>{a.account_name}</strong>: 새 거래 {a.new}건, 이미 있던 거래 {a.duplicate}건
          {a.adjustments.length > 0 && <> · 잔고 맞춤 {a.adjustments.map((x) => x.type === "cash"
            ? `현금 ${num(x.diff) > 0 ? "+" : ""}${won(num(x.diff))}` : `${x.name} ${num(x.diff) > 0 ? "+" : ""}${x.diff}주`).join(", ")}</>}
          {a.broker_total && <> · 증권사 평가 {won(num(a.broker_total))}</>}
          {[...a.warnings, ...a.errors].map((w) => <div key={w} className="field-hint">{w}</div>)}
        </div>
      ))}
      {result.failures.map((f) => <div key={f.account_id}>{f.account_name}: {f.error}</div>)}
    </div>
  );
}

function LinkPanel({ con, accounts, onDone }: { con: BrokerConnection; accounts: Account[]; onDone: () => void }) {
  const items = useLoad(() => api.brokerAccounts(con.id), [con.id]);
  const act = useAction();
  const [choice, setChoice] = useState<Record<string, { target: string; name: string; start: string }>>({});
  const free = accounts.filter((a) => a.valuation_method === "transactions" && !a.closed_on && !a.data_source_id);
  const get = (b: BrokerAccountItem) => choice[b.ref] ?? { target: "new", name: `${con.provider_name} ${b.label}`, start: yearAgo() };
  const set = (b: BrokerAccountItem, patch: Partial<{ target: string; name: string; start: string }>) =>
    setChoice({ ...choice, [b.ref]: { ...get(b), ...patch } });
  const link = async (b: BrokerAccountItem) => {
    const c = get(b);
    const ok = await act.run(() => api.linkAccount(con.id, {
      ref: b.ref, start_date: c.start, ...(c.target === "new" ? { create_name: c.name } : { account_id: Number(c.target) }) }));
    if (ok) { items.reload(); onDone(); }
  };
  const unlink = async (b: BrokerAccountItem) => {
    if (!window.confirm(`${b.account_name} 계좌와 증권사 연결을 끊을까요? 이미 받은 거래는 남습니다.`)) return;
    if (await act.run(() => api.unlinkAccount(con.id, b.ref))) { items.reload(); onDone(); }
  };
  return (
    <div className="panel" style={{ background: "var(--surface)" }}>
      <h3>증권사 계좌 연결</h3>
      <p className="field-hint" style={{ margin: "0 0 10px" }}>
        증권사 계좌를 AssetHub 계좌에 연결하면 동기화할 때 거래와 잔고가 그 계좌로 들어옵니다.
        시작일부터의 거래를 받고, 그 전부터 있던 보유 종목과 현금은 '기초 보유'로 맞춥니다.
      </p>
      <ErrorNote error={act.error ?? items.error} />
      {items.loading && !items.data && <div className="field-hint">증권사에서 계좌 목록을 받는 중…</div>}
      {(items.data ?? []).map((b) => {
        const c = get(b);
        return (
          <div key={b.ref} className="owner-row" style={{ alignItems: "flex-end", marginBottom: 12 }}>
            <strong style={{ minWidth: 120 }}>{b.label}</strong>
            {b.account_id ? (
              <>
                <span>→ {b.account_name}</span>
                <button className="btn small" onClick={() => unlink(b)} disabled={act.busy}>연결 끊기</button>
              </>
            ) : (
              <>
                <select aria-label="연결할 계좌" value={c.target} onChange={(e) => set(b, { target: e.target.value })}>
                  <option value="new">새 위탁 계좌 만들기</option>
                  {free.map((a) => <option key={a.id} value={a.id}>{a.name}</option>)}
                </select>
                {c.target === "new" && <input aria-label="새 계좌 이름" value={c.name} onChange={(e) => set(b, { name: e.target.value })} />}
                <label className="field" style={{ minWidth: 150 }}>
                  <span className="field-label">이 날부터 거래 받기</span>
                  <input type="date" value={c.start} onChange={(e) => set(b, { start: e.target.value })} />
                </label>
                <button className="btn small primary" onClick={() => link(b)} disabled={act.busy}>연결</button>
              </>
            )}
          </div>
        );
      })}
    </div>
  );
}

function KeyForm({ con, onDone, onCancel }: { con: BrokerConnection; onDone: () => void; onCancel: () => void }) {
  const [f, setF] = useState({ app_key: "", app_secret: "", accounts: con.kis_accounts.join(", ") });
  const act = useAction();
  const save = async (e: React.FormEvent) => {
    e.preventDefault();
    const body: Record<string, unknown> = {};
    if (f.app_key.trim()) body.app_key = f.app_key.trim();
    if (f.app_secret.trim()) body.app_secret = f.app_secret.trim();
    if (con.provider === "kis") body.accounts = f.accounts.split(/[,\s]+/).filter(Boolean);
    if (await act.run(() => api.updateConnection(con.id, body))) onDone();
  };
  return (
    <form className="panel" style={{ background: "var(--surface)" }} onSubmit={save}>
      <h3>키 바꾸기</h3>
      <div className="form">
        <Field label="새 App Key" hint="비워 두면 그대로"><input value={f.app_key} onChange={(e) => setF({ ...f, app_key: e.target.value })} autoComplete="off" /></Field>
        <Field label="새 App Secret" hint="비워 두면 그대로"><input type="password" value={f.app_secret} onChange={(e) => setF({ ...f, app_secret: e.target.value })} autoComplete="new-password" /></Field>
        {con.provider === "kis" && (
          <Field label="계좌번호" hint="여러 개면 쉼표로"><input value={f.accounts} onChange={(e) => setF({ ...f, accounts: e.target.value })} /></Field>
        )}
      </div>
      <div className="actions"><button className="btn primary" disabled={act.busy}>저장</button><button type="button" className="btn" onClick={onCancel}>취소</button></div>
      <ErrorNote error={act.error} />
    </form>
  );
}

function ConnectionCard({ con, accounts, reload, onAccountsChanged }: {
  con: BrokerConnection; accounts: Account[]; reload: () => void; onAccountsChanged: () => void;
}) {
  const [mode, setMode] = useState<"none" | "link" | "keys">(con.linked.length ? "none" : "link");
  const [result, setResult] = useState<SyncResult | null>(null);
  const act = useAction();
  const sync = async () => {
    const r = await act.run(() => api.syncConnection(con.id));
    if (r) { setResult(r); reload(); onAccountsChanged(); }
  };
  const remove = async () => {
    if (!window.confirm(`${con.label} 연결을 해제할까요? 저장된 앱키를 지웁니다. 이미 받은 거래와 계좌는 남습니다.`)) return;
    if (await act.run(async () => { await api.deleteConnection(con.id); return true; })) { reload(); onAccountsChanged(); }
  };
  return (
    <div className="panel">
      <div className="section-head">
        <h3 style={{ margin: 0 }}>{con.label}</h3>
        {con.environment && <span className="tag">{ENV_LABEL[con.environment]}</span>}
        <span className="field-hint">앱키 {con.key_hint}</span>
        <span className="spacer" />
        <button className="btn small primary" onClick={sync} disabled={act.busy || !con.linked.length}>{act.busy ? "동기화 중…" : "지금 동기화"}</button>
        <button className="btn small" onClick={() => setMode(mode === "link" ? "none" : "link")}>계좌 연결</button>
        <button className="btn small" onClick={() => setMode(mode === "keys" ? "none" : "keys")}>키 바꾸기</button>
        <button className="btn small danger" onClick={remove} disabled={act.busy}>연결 해제</button>
      </div>
      <div className="field-hint" style={{ margin: "6px 0" }}>
        {con.last_synced_at ? `마지막 동기화 ${dateTime(con.last_synced_at)}` : "아직 동기화하지 않았습니다"}
        {con.status === "error" && con.last_error && <span style={{ color: "var(--up)" }}> · {con.last_error}</span>}
      </div>
      {con.linked.length > 0 && (
        <table className="medium"><tbody>
          {con.linked.map((l) => (
            <tr key={l.ref}><td>{l.account_name}</td><td className="muted">{l.ref}</td>
              <td className="muted">{l.synced_until ? `${l.synced_until}까지 받음` : `${l.start_date ?? ""}부터 받을 예정`}</td></tr>
          ))}
        </tbody></table>
      )}
      <ErrorNote error={act.error} />
      {result && <SyncReport result={result} />}
      {mode === "link" && <LinkPanel con={con} accounts={accounts} onDone={() => { reload(); onAccountsChanged(); }} />}
      {mode === "keys" && <KeyForm con={con} onDone={() => { setMode("none"); reload(); }} onCancel={() => setMode("none")} />}
    </div>
  );
}

export function BrokersSection({ hid, members, onAccountsChanged }: { hid: number; members: Member[]; onAccountsChanged: () => void }) {
  const list = useLoad(() => api.connections(hid), [hid]);
  const accounts = useLoad(() => api.accounts(hid, true), [hid]);
  const [adding, setAdding] = useState(false);
  const [f, setF] = useState({ provider: "kiwoom" as BrokerProvider, member_id: 0, environment: "real" as "real" | "mock",
    app_key: "", app_secret: "", accounts: "" });
  const act = useAction();
  const member = f.member_id || members.find((m) => m.relation === "self")?.id || members[0]?.id || 0;
  const add = async (e: React.FormEvent) => {
    e.preventDefault();
    const r = await act.run(() => api.createConnection(hid, {
      provider: f.provider, member_id: member, environment: f.environment, app_key: f.app_key.trim(),
      app_secret: f.app_secret.trim(), accounts: f.accounts.split(/[,\s]+/).filter(Boolean) }));
    if (r) { setAdding(false); setF({ ...f, app_key: "", app_secret: "", accounts: "" }); list.reload(); }
  };
  const refresh = () => { accounts.reload(); onAccountsChanged(); };
  return (
    <section className="card">
      <div className="section-head">
        <h2>증권사 연결</h2>
        <span className="spacer" />
        <button className="btn" onClick={() => setAdding(!adding)}>{adding ? "닫기" : "연결 추가"}</button>
      </div>
      <p className="sub">
        증권사 Open API 키를 등록하면 거래와 잔고를 자동으로 받습니다. 지금은 키움증권과 한국투자증권을 지원합니다.
        조회만 하고 주문은 하지 않습니다. 키는 암호화해서 저장하고, 암호화 키는 backend\.env 에 있으니 그 파일을 함께 백업하세요.
        가족 계좌는 각자 본인 명의 키로 연결합니다.
      </p>
      {adding && (
        <form className="panel" onSubmit={add}>
          <div className="form">
            <Field label="증권사">
              <select value={f.provider} onChange={(e) => setF({ ...f, provider: e.target.value as BrokerProvider })}>
                <option value="kiwoom">키움증권</option><option value="kis">한국투자증권</option>
              </select>
            </Field>
            <Field label="명의자 (키 주인)">
              <select value={member} onChange={(e) => setF({ ...f, member_id: Number(e.target.value) })}>
                {members.map((m) => <option key={m.id} value={m.id}>{m.name}</option>)}
              </select>
            </Field>
            <Field label="환경">
              <select value={f.environment} onChange={(e) => setF({ ...f, environment: e.target.value as "real" | "mock" })}>
                <option value="real">실전</option><option value="mock">모의투자 (시험용)</option>
              </select>
            </Field>
            <Field label="App Key"><input value={f.app_key} onChange={(e) => setF({ ...f, app_key: e.target.value })} required autoComplete="off" /></Field>
            <Field label={f.provider === "kiwoom" ? "Secret Key" : "App Secret"}>
              <input type="password" value={f.app_secret} onChange={(e) => setF({ ...f, app_secret: e.target.value })} required autoComplete="new-password" />
            </Field>
            {f.provider === "kis" && (
              <Field label="계좌번호" hint="예: 12345678-01. 여러 개면 쉼표로">
                <input value={f.accounts} onChange={(e) => setF({ ...f, accounts: e.target.value })} required />
              </Field>
            )}
            <div className="field wide">
              <ul className="field-hint" style={{ margin: 0, paddingLeft: 18 }}>{GUIDE[f.provider].map((g) => <li key={g}>{g}</li>)}</ul>
            </div>
          </div>
          <div className="actions"><button className="btn primary" disabled={act.busy || !members.length}>{act.busy ? "증권사에 확인 중…" : "확인 후 저장"}</button></div>
          <ErrorNote error={act.error} />
        </form>
      )}
      <ErrorNote error={list.error} />
      {(list.data ?? []).length === 0 && !list.loading && !adding && <div className="empty">연결된 증권사가 없습니다.</div>}
      {(list.data ?? []).map((con) => (
        <ConnectionCard key={con.id} con={con} accounts={accounts.data ?? []} reload={list.reload} onAccountsChanged={refresh} />
      ))}
    </section>
  );
}
