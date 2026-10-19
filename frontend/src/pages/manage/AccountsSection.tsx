import { useState } from "react";
import { api, type Account, type Institution, type Member } from "../../api";
import { num, won } from "../../format";
import { ACCOUNT_TYPES, accountTypeLabel, INSTITUTION_KIND_LABEL } from "../../labels";
import { navigate } from "../../router";
import { cleanNumber, ErrorNote, Field, todayKst, useAction, useLoad } from "../../ui";

const CURRENCIES = ["KRW", "USD", "JPY", "EUR", "CNY"];

interface OwnerDraft { member_id: number; pct: string }

function ownersOf(a: Account | null, members: Member[]): OwnerDraft[] {
  if (a) return a.owners.map((o) => ({ member_id: o.member_id, pct: String(Math.round(num(o.share) * 10000) / 100) }));
  const me = members.find((m) => m.relation === "self") ?? members[0];
  return me ? [{ member_id: me.id, pct: "100" }] : [];
}

function AccountForm({ hid, account, members, institutions, onDone, onCancel }: {
  hid: number; account: Account | null; members: Member[]; institutions: Institution[];
  onDone: () => void; onCancel: () => void;
}) {
  const [f, setF] = useState({
    name: account?.name ?? "",
    account_type: account?.account_type ?? "checking",
    institution_code: account?.institution_code ?? "",
    base_currency: account?.base_currency ?? "KRW",
    valuation_method: account?.valuation_method ?? "transactions",
    account_number_masked: account?.account_number_masked ?? "",
    opened_on: account?.opened_on ?? "",
    maturity_on: account?.maturity_on ?? "",
    interest_rate: account?.interest_rate == null ? "" : String(num(account.interest_rate)),
    memo: account?.memo ?? "",
  });
  const [owners, setOwners] = useState<OwnerDraft[]>(() => ownersOf(account, members));
  const act = useAction();
  const total = owners.reduce((s, o) => s + (Number(o.pct) || 0), 0);
  const set = (k: keyof typeof f) => (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) => {
    const v = e.target.value;
    setF((cur) => {
      const next = { ...cur, [k]: v };
      // 보험은 보통 거래내역 없이 기관이 알려주는 평가액으로 본다
      if (k === "account_type" && !account) next.valuation_method = ACCOUNT_TYPES.find((t) => t.code === v)?.reported ? "reported" : "transactions";
      return next;
    });
  };
  const ownerPayload = owners.map((o) => ({ member_id: o.member_id, share: ((Number(o.pct) || 0) / 100).toFixed(4) }));

  const save = async (e: React.FormEvent) => {
    e.preventDefault();
    if (Math.abs(total - 100) > 0.01) { act.setError(`명의 지분 합계가 100%여야 합니다 (지금 ${total}%).`); return; }
    const body = {
      name: f.name.trim(), institution_code: f.institution_code || null,
      account_number_masked: f.account_number_masked.trim() || null, opened_on: f.opened_on || null,
      maturity_on: f.maturity_on || null, interest_rate: f.interest_rate ? cleanNumber(f.interest_rate) : null,
      memo: f.memo.trim() || null,
    };
    const ok = await act.run(async () => {
      if (account) {
        await api.updateAccount(account.id, body);
        await api.setOwners(account.id, ownerPayload);
      } else {
        await api.createAccount(hid, { ...body, account_type: f.account_type, base_currency: f.base_currency,
          valuation_method: f.valuation_method, owners: ownerPayload });
      }
      return true;
    });
    if (ok) onDone();
  };
  const toggleClosed = async () => {
    if (!account) return;
    const closing = !account.closed_on;
    if (closing && !window.confirm(`${account.name}을(를) 마감할까요? 대시보드와 합계에서 빠집니다. 거래 기록은 남습니다.`)) return;
    if (await act.run(() => api.updateAccount(account.id, { closed_on: closing ? todayKst() : null }))) onDone();
  };
  const del = async () => {
    if (!account || !window.confirm(`${account.name}을(를) 지울까요?`)) return;
    if (await act.run(async () => { await api.deleteAccount(account.id); return true; })) onDone();
  };

  const groups = [...new Set(ACCOUNT_TYPES.map((t) => t.group))];
  const instGroups = [...new Set(institutions.map((i) => i.kind))];
  return (
    <form className="panel" onSubmit={save}>
      <h3>{account ? `${account.name} 수정` : "새 계좌"}</h3>
      <div className="form">
        <Field label="이름"><input value={f.name} onChange={set("name")} placeholder="예: 월급통장" required autoFocus /></Field>
        <Field label="종류" hint={account ? "종류는 만든 뒤 바꿀 수 없습니다" : undefined}>
          <select value={f.account_type} onChange={set("account_type")} disabled={!!account}>
            {groups.map((g) => (
              <optgroup key={g} label={g}>
                {ACCOUNT_TYPES.filter((t) => t.group === g).map((t) => <option key={t.code} value={t.code}>{t.label}</option>)}
              </optgroup>
            ))}
          </select>
        </Field>
        <Field label="기관">
          <select value={f.institution_code} onChange={set("institution_code")}>
            <option value="">없음</option>
            {instGroups.map((g) => (
              <optgroup key={g} label={INSTITUTION_KIND_LABEL[g] ?? g}>
                {institutions.filter((i) => i.kind === g).map((i) => <option key={i.code} value={i.code}>{i.name}</option>)}
              </optgroup>
            ))}
          </select>
        </Field>
        <Field label="계좌번호 (표시용)" hint="뒤 4자리만 맞으면 엑셀 업로드 때 다른 계좌 파일을 알려줍니다">
          <input value={f.account_number_masked} onChange={set("account_number_masked")} placeholder="예: 1002-***-**6789" />
        </Field>
        {!account && (
          <Field label="기본 통화">
            <select value={f.base_currency} onChange={set("base_currency")}>{CURRENCIES.map((c) => <option key={c}>{c}</option>)}</select>
          </Field>
        )}
        {!account && (
          <Field label="평가 방식" hint="보험·연금처럼 거래내역을 받을 수 없으면 '평가액 직접 입력'">
            <select value={f.valuation_method} onChange={set("valuation_method")}>
              <option value="transactions">거래내역으로 계산</option>
              <option value="reported">평가액 직접 입력</option>
            </select>
          </Field>
        )}
        <Field label="개설일"><input type="date" value={f.opened_on} onChange={set("opened_on")} /></Field>
        <Field label="만기일"><input type="date" value={f.maturity_on} onChange={set("maturity_on")} /></Field>
        <Field label="금리 (연 %)"><input inputMode="decimal" value={f.interest_rate} onChange={set("interest_rate")} placeholder="예: 3.5" /></Field>
        <Field label="메모" wide><input value={f.memo} onChange={set("memo")} /></Field>
        <div className="field wide">
          <span className="field-label">명의 (공동명의는 지분을 나눠 입력, 합계 100%)</span>
          {owners.map((o, i) => (
            <div className="owner-row" key={i}>
              <select aria-label="명의자" value={o.member_id}
                onChange={(e) => setOwners(owners.map((x, j) => j === i ? { ...x, member_id: Number(e.target.value) } : x))}>
                {members.map((m) => <option key={m.id} value={m.id}>{m.name}</option>)}
              </select>
              <input aria-label="지분 %" type="number" min="0" max="100" step="0.01" value={o.pct}
                onChange={(e) => setOwners(owners.map((x, j) => j === i ? { ...x, pct: e.target.value } : x))} />%
              {owners.length > 1 && <button type="button" className="btn small" onClick={() => setOwners(owners.filter((_, j) => j !== i))}>빼기</button>}
            </div>
          ))}
          <div className="owner-row">
            {owners.length < members.length && (
              <button type="button" className="btn small" onClick={() => {
                const unused = members.find((m) => !owners.some((o) => o.member_id === m.id));
                if (unused) setOwners([...owners, { member_id: unused.id, pct: String(Math.max(0, 100 - total)) }]);
              }}>공동명의 추가</button>
            )}
            <span className="field-hint">합계 {Math.round(total * 100) / 100}%</span>
          </div>
        </div>
      </div>
      <div className="actions">
        <button className="btn primary" disabled={act.busy || !members.length}>{account ? "저장" : "계좌 만들기"}</button>
        <button type="button" className="btn" onClick={onCancel}>취소</button>
        {account && <span className="spacer" style={{ flex: 1 }} />}
        {account && <button type="button" className="btn" onClick={toggleClosed}>{account.closed_on ? "마감 취소" : "마감"}</button>}
        {account && <button type="button" className="btn danger" onClick={del}>삭제</button>}
      </div>
      {!members.length && <p className="field-hint">먼저 가족 구성원을 등록하세요.</p>}
      <ErrorNote error={act.error} />
      {account?.valuation_method === "reported" && <ReportedPanel account={account} />}
    </form>
  );
}

function ReportedPanel({ account }: { account: Account }) {
  const list = useLoad(() => api.reportedBalances(account.id), [account.id]);
  const [asOf, setAsOf] = useState(todayKst());
  const [value, setValue] = useState("");
  const act = useAction();
  const add = async () => {
    const r = await act.run(() => api.putReportedBalance(account.id, { as_of: asOf, total_value: cleanNumber(value), currency: account.base_currency }));
    if (r) { list.setData(r); setValue(""); }
  };
  return (
    <div style={{ marginTop: 16 }}>
      <h3>평가액 기록</h3>
      <p className="field-hint" style={{ margin: "0 0 8px" }}>보험사·연금 앱에서 확인한 해지환급금이나 평가금액을 날짜별로 적습니다. 가장 최근 값이 순자산에 들어갑니다.</p>
      <div className="toolbar">
        <input aria-label="기준일" type="date" value={asOf} onChange={(e) => setAsOf(e.target.value)} />
        <input aria-label="평가액" inputMode="numeric" placeholder="금액 (예: 15,000,000)" value={value} onChange={(e) => setValue(e.target.value)} />
        <button type="button" className="btn" disabled={!value || act.busy} onClick={add}>기록</button>
      </div>
      <ErrorNote error={act.error ?? list.error} />
      {list.data && list.data.length > 0 && (
        <table>
          <tbody>
            {list.data.map((b) => (
              <tr key={`${b.as_of}-${b.currency}`}>
                <td>{b.as_of}</td>
                <td className="num">{b.currency === "KRW" ? won(num(b.total_value)) : `${num(b.total_value).toLocaleString()} ${b.currency}`}</td>
                <td className="num"><button type="button" className="btn small" onClick={async () => {
                  await act.run(() => api.deleteReportedBalance(account.id, b.as_of, b.currency)); list.reload();
                }}>지우기</button></td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}

export function AccountsSection({ hid, members }: { hid: number; members: Member[] }) {
  const accounts = useLoad(() => api.accounts(hid, true), [hid]);
  const institutions = useLoad(() => api.institutions(), []);
  const [editing, setEditing] = useState<number | "new" | null>(null);
  const done = () => { setEditing(null); accounts.reload(); };
  const name = (id: number) => members.find((m) => m.id === id)?.name ?? "?";
  const list = accounts.data ?? [];
  return (
    <section className="card">
      <div className="section-head">
        <h2>계좌</h2>
        <span className="spacer" />
        <button className="btn" onClick={() => setEditing("new")} disabled={editing === "new"}>계좌 추가</button>
      </div>
      <p className="sub">은행·증권·카드·대출뿐 아니라 부동산, 보험, 현금도 계좌로 등록합니다.</p>
      <ErrorNote error={accounts.error} />
      {editing === "new" && <AccountForm hid={hid} account={null} members={members} institutions={institutions.data ?? []} onDone={done} onCancel={() => setEditing(null)} />}
      {list.length === 0 && !accounts.loading && <div className="empty">아직 계좌가 없습니다.</div>}
      {list.length > 0 && (
        <div className="table-wrap">
          <table className="medium">
            <thead><tr><th>계좌</th><th>종류</th><th>명의</th><th>상태</th><th /></tr></thead>
            <tbody>
              {list.map((a) => (
                editing === a.id ? (
                  <tr key={a.id}><td colSpan={5}>
                    <AccountForm hid={hid} account={a} members={members} institutions={institutions.data ?? []} onDone={done} onCancel={() => setEditing(null)} />
                  </td></tr>
                ) : (
                  <tr key={a.id} className={a.closed_on ? "void" : ""}>
                    <td>{a.name}{a.institution_name && <div className="muted">{a.institution_name}</div>}</td>
                    <td>{accountTypeLabel(a.account_type)}{a.valuation_method === "reported" && <span className="tag">평가액 입력</span>}
                      {a.data_source_id && a.external_ref && <span className="tag">API 연결</span>}</td>
                    <td>{a.owners.map((o) => num(o.share) < 1 ? `${name(o.member_id)} ${Math.round(num(o.share) * 100)}%` : name(o.member_id)).join(", ")}</td>
                    <td>{a.closed_on ? `마감 ${a.closed_on}` : "사용 중"}</td>
                    <td className="num">
                      {a.valuation_method === "transactions" && !a.closed_on && (
                        <button className="btn small" onClick={() => navigate("/import", { account: a.id })}>파일 올리기</button>
                      )}{" "}
                      <button className="btn small" onClick={() => setEditing(a.id)}>수정</button>
                    </td>
                  </tr>
                )
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}
