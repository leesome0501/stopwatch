import { useCallback, useEffect, useState } from "react";
import { api, type Category, type Txn, type TxnPage, type TxnQuery } from "../api";
import { num, quantity, won } from "../format";
import { KIND_LABEL } from "../labels";
import { navigate } from "../router";
import { CategorySelect, cleanNumber, ErrorNote, Field, monthRange, todayKst, useAction, useLoad } from "../ui";

const PAGE = 100;
type Period = "this" | "last" | "3m" | "year" | "all" | "custom";
const PERIODS: [Period, string][] = [["this", "이번 달"], ["last", "지난 달"], ["3m", "최근 3개월"], ["year", "올해"], ["all", "전체"], ["custom", "직접"]];

function periodRange(p: Period, custom: [string, string]): [string | undefined, string | undefined] {
  const today = todayKst();
  if (p === "this") return monthRange(0);
  if (p === "last") return monthRange(-1);
  if (p === "3m") return [monthRange(-2)[0], today];
  if (p === "year") return [`${today.slice(0, 4)}-01-01`, today];
  if (p === "custom") return [custom[0] || undefined, custom[1] || undefined];
  return [undefined, undefined];
}

function amountCell(t: Txn) {
  const v = num(t.amount);
  if (t.currency === "KRW") return `${v > 0 ? "+" : ""}${won(v)}`;
  return `${v > 0 ? "+" : ""}${v.toLocaleString("en-US", { maximumFractionDigits: 4 })} ${t.currency}`;
}

const CATEGORIZABLE = new Set(["cash_in", "cash_out", "dividend", "interest", "fee", "tax"]);

interface RuleSuggestion { text: string; field: "description" | "counterparty"; category: Category }

function MemoInput({ t, onSave }: { t: Txn; onSave: (memo: string | null) => void }) {
  const [v, setV] = useState(t.memo ?? "");
  const commit = () => { if ((v.trim() || null) !== t.memo) onSave(v.trim() || null); };
  return <input className="memo" aria-label="메모" value={v} placeholder="메모" onChange={(e) => setV(e.target.value)}
    onBlur={commit} onKeyDown={(e) => { if (e.key === "Enter") (e.target as HTMLInputElement).blur(); }} />;
}

function AddTransaction({ hid, accountId, categories, onAdded }: {
  hid: number; accountId: number | null; categories: Category[]; onAdded: () => void;
}) {
  const accounts = useLoad(() => api.accounts(hid), [hid]);
  const usable = (accounts.data ?? []).filter((a) => a.valuation_method === "transactions");
  const [f, setF] = useState({ account: accountId ?? 0, date: todayKst(), dir: "out", amount: "", description: "", category: null as number | null });
  const act = useAction();
  const save = async (e: React.FormEvent) => {
    e.preventDefault();
    const account = f.account || usable[0]?.id;
    if (!account) { act.setError("계좌가 없습니다."); return; }
    const amt = cleanNumber(f.amount).replace(/^-/, "");
    const r = await act.run(() => api.createTransaction(account, {
      occurred_at: `${f.date}T12:00:00`, kind: f.dir === "in" ? "cash_in" : "cash_out",
      amount: f.dir === "in" ? amt : `-${amt}`, description: f.description.trim() || null, category_id: f.category,
    }));
    if (r) { setF({ ...f, amount: "", description: "" }); onAdded(); }
  };
  return (
    <form className="panel" onSubmit={save}>
      <h3>직접 입력</h3>
      <div className="form">
        <Field label="계좌">
          <select value={f.account || usable[0]?.id || ""} onChange={(e) => setF({ ...f, account: Number(e.target.value) })}>
            {usable.map((a) => <option key={a.id} value={a.id}>{a.name}</option>)}
          </select>
        </Field>
        <Field label="날짜"><input type="date" value={f.date} onChange={(e) => setF({ ...f, date: e.target.value })} required /></Field>
        <Field label="구분">
          <select value={f.dir} onChange={(e) => setF({ ...f, dir: e.target.value })}>
            <option value="out">나간 돈 (지출·출금)</option><option value="in">들어온 돈 (수입·입금)</option>
          </select>
        </Field>
        <Field label="금액"><input inputMode="numeric" value={f.amount} onChange={(e) => setF({ ...f, amount: e.target.value })} required placeholder="예: 12,000" /></Field>
        <Field label="내용"><input value={f.description} onChange={(e) => setF({ ...f, description: e.target.value })} placeholder="예: 현금 경조사비" /></Field>
        <Field label="카테고리">
          <CategorySelect categories={categories} value={f.category} onChange={(c) => setF({ ...f, category: c })}
            kinds={f.dir === "in" ? ["income", "transfer"] : ["expense", "transfer"]} />
        </Field>
      </div>
      <div className="actions"><button className="btn primary" disabled={act.busy}>추가</button></div>
      <ErrorNote error={act.error} />
    </form>
  );
}

export function TransactionsPage({ hid, params }: { hid: number; params: URLSearchParams }) {
  const accounts = useLoad(() => api.accounts(hid, true), [hid]);
  const cats = useLoad(() => api.categories(hid), [hid]);
  const categories = cats.data ?? [];
  const [accountId, setAccountId] = useState<number | null>(Number(params.get("account")) || null);
  const [period, setPeriod] = useState<Period>(params.get("uncategorized") ? "all" : "this");
  const [custom, setCustom] = useState<[string, string]>(["", ""]);
  const [categoryId, setCategoryId] = useState<number | null>(null);
  const [uncategorized, setUncategorized] = useState(!!params.get("uncategorized"));
  const [q, setQ] = useState("");
  const [qDebounced, setQDebounced] = useState("");
  const [page, setPage] = useState<TxnPage | null>(null);
  const [loading, setLoading] = useState(false);
  const [adding, setAdding] = useState(false);
  const [suggest, setSuggest] = useState<RuleSuggestion | null>(null);
  const act = useAction();

  useEffect(() => { const t = setTimeout(() => setQDebounced(q), 300); return () => clearTimeout(t); }, [q]);

  const query = useCallback((offset: number): TxnQuery => {
    const [from, to] = periodRange(period, custom);
    return { account_id: accountId ?? undefined, date_from: from, date_to: to, uncategorized,
      category_id: uncategorized ? undefined : categoryId ?? undefined, q: qDebounced, limit: PAGE, offset };
  }, [accountId, period, custom, uncategorized, categoryId, qDebounced]);

  const load = useCallback(() => {
    setLoading(true);
    api.transactions(hid, query(0)).then((p) => { setPage(p); act.setError(null); })
      .catch((e) => act.setError((e as Error).message)).finally(() => setLoading(false));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [hid, query]);
  useEffect(load, [load]);

  const more = async () => {
    if (!page) return;
    const next = await act.run(() => api.transactions(hid, query(page.items.length)));
    if (next) setPage({ ...next, items: [...page.items, ...next.items] });
  };
  const replace = (t: Txn) => setPage((p) => p && { ...p, items: p.items.map((x) => (x.id === t.id ? { ...x, ...t } : x)) });

  const setCategory = async (t: Txn, cid: number | null) => {
    const updated = await act.run(() => api.updateTransaction(t.id, { category_id: cid }));
    if (!updated) return;
    const c = categories.find((x) => x.id === cid);
    const parent = c?.parent_id ? categories.find((x) => x.id === c.parent_id) : undefined;
    replace({ ...t, category_id: cid, category_name: c?.name ?? null, category_parent: parent?.name ?? null, category_kind: c?.kind ?? null });
    const text = (t.counterparty || t.description || "").trim();
    setSuggest(c && text ? { text, field: t.counterparty ? "counterparty" : "description", category: c } : null);
  };

  const makeRule = async () => {
    if (!suggest || !page) return;
    const s = suggest;
    const ok = await act.run(() => api.createRule(hid, { match_field: s.field, match_type: "equals", pattern: s.text, category_id: s.category.id }));
    if (!ok) return;
    // 지금 보이는 미분류 거래 중 같은 것도 함께 바꾼다
    const same = page.items.filter((t) => t.category_id == null && CATEGORIZABLE.has(t.kind)
      && ((s.field === "counterparty" ? t.counterparty : t.description) ?? "").trim() === s.text);
    for (const t of same) await api.updateTransaction(t.id, { category_id: s.category.id });
    setSuggest(null);
    load();
  };

  const remove = async (t: Txn) => {
    if (!window.confirm(`${t.trade_date} ${t.description ?? ""} ${amountCell(t)} 거래를 지울까요?`)) return;
    if (await act.run(async () => { await api.voidTransaction(t.id); return true; })) load();
  };

  const acctList = accounts.data ?? [];
  return (
    <div className="grid">
      <section className="card">
        <div className="toolbar">
          <select aria-label="계좌" value={accountId ?? ""} onChange={(e) => setAccountId(Number(e.target.value) || null)}>
            <option value="">모든 계좌</option>
            {acctList.map((a) => <option key={a.id} value={a.id}>{a.name}{a.closed_on ? " (마감)" : ""}</option>)}
          </select>
          <div className="segmented" role="group" aria-label="기간">
            {PERIODS.map(([k, l]) => <button key={k} aria-pressed={period === k} onClick={() => setPeriod(k)}>{l}</button>)}
          </div>
          {period === "custom" && <>
            <input aria-label="시작일" type="date" value={custom[0]} onChange={(e) => setCustom([e.target.value, custom[1]])} />
            <input aria-label="종료일" type="date" value={custom[1]} onChange={(e) => setCustom([custom[0], e.target.value])} />
          </>}
        </div>
        <div className="toolbar">
          <input type="search" aria-label="검색" placeholder="적요·거래처·메모 검색" value={q} onChange={(e) => setQ(e.target.value)} />
          {!uncategorized && <CategorySelect ariaLabel="카테고리" categories={categories} value={categoryId} onChange={setCategoryId} emptyLabel="모든 카테고리" />}
          <label className="check"><input type="checkbox" checked={uncategorized} onChange={(e) => setUncategorized(e.target.checked)} />미분류만</label>
          <span style={{ flex: 1 }} />
          <button className="btn" onClick={() => setAdding(!adding)}>{adding ? "닫기" : "직접 입력"}</button>
          <button className="btn" onClick={() => navigate("/import", { account: accountId ?? undefined })}>파일 올리기</button>
        </div>
        {adding && <AddTransaction hid={hid} accountId={accountId} categories={categories} onAdded={load} />}
        {page && (
          <div className="summary-line">
            <span><strong>{page.total.toLocaleString()}</strong>건</span>
            <span>들어온 돈 <strong>{won(num(page.sum_in_krw))}</strong></span>
            <span>나간 돈 <strong>{won(num(page.sum_out_krw))}</strong></span>
            <span className="field-hint">계좌 간 이체도 포함된 합계입니다 (기초잔액 제외). 수입·지출 통계는 대시보드에서 보세요.</span>
          </div>
        )}
        <ErrorNote error={act.error ?? accounts.error ?? cats.error} />
        <div className={loading && page ? "loading" : ""}>
          {page && page.items.length === 0 && <div className="empty">조건에 맞는 거래가 없습니다.</div>}
          {page && page.items.length > 0 && (
            <div className="table-wrap">
              <table className="wide">
                <thead><tr><th>날짜</th><th>계좌</th><th>내용</th><th>카테고리</th><th className="num">금액</th><th>메모</th><th /></tr></thead>
                <tbody>
                  {page.items.map((t) => (
                    <tr key={t.id}>
                      <td className="num" style={{ textAlign: "left" }}>{t.trade_date.slice(5).replace("-", ".")}<div className="muted">{t.trade_date.slice(0, 4)}</div></td>
                      <td>{t.account_name}</td>
                      <td>
                        {t.kind !== "cash_in" && t.kind !== "cash_out"
                          ? <span className="tag" style={{ marginLeft: 0, marginRight: 6 }}>{KIND_LABEL[t.kind] ?? t.kind}</span> : null}
                        {t.instrument_name ? `${t.instrument_name}${t.quantity ? ` ${quantity(Math.abs(num(t.quantity)))}주` : ""}` : (t.description ?? "")}
                        {t.counterparty && t.counterparty !== t.description && <div className="muted">{t.counterparty}</div>}
                      </td>
                      <td>
                        {CATEGORIZABLE.has(t.kind) ? (
                          <CategorySelect ariaLabel="카테고리" categories={categories} value={t.category_id}
                            onChange={(cid) => setCategory(t, cid)}
                            kinds={num(t.amount) >= 0 ? ["income", "transfer"] : ["expense", "transfer"]} />
                        ) : <span className="muted">—</span>}
                      </td>
                      <td className={`num amount ${num(t.amount) >= 0 ? "in" : "out"}`}>{amountCell(t)}
                        {t.balance_after != null && <div className="muted">잔액 {won(num(t.balance_after))}</div>}</td>
                      <td><MemoInput t={t} onSave={async (memo) => { const r = await act.run(() => api.updateTransaction(t.id, { memo })); if (r) replace({ ...t, memo }); }} /></td>
                      <td className="num"><button className="btn small" aria-label="거래 지우기" onClick={() => remove(t)}>×</button></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
          {page && page.items.length < page.total && (
            <div className="actions"><button className="btn" onClick={more} disabled={act.busy}>더 보기 ({page.total - page.items.length}건 남음)</button></div>
          )}
        </div>
        {suggest && (
          <div className="rule-bar" role="status">
            <span>"{suggest.text}" 거래를 앞으로도 <strong>{suggest.category.name}</strong>(으)로 분류할까요?</span>
            <button className="btn primary small" onClick={makeRule} disabled={act.busy}>규칙 만들기</button>
            <button className="btn small" onClick={() => setSuggest(null)}>아니요</button>
          </div>
        )}
      </section>
    </div>
  );
}
