import { useEffect, useRef, useState } from "react";
import { api, type ImportResult } from "../api";
import { dateTime, num, won } from "../format";
import { accountTypeLabel, KIND_LABEL } from "../labels";
import { navigate } from "../router";
import { ErrorNote, useAction, useLoad } from "../ui";

const STATUS = { new: "새 거래", duplicate: "중복", error: "오류" } as const;
const SOURCE = { file: "파일", rule: "규칙", history: "지난 분류" } as const;
const SHOW_ROWS = 300;

function amountText(amount: string | null, currency: string | null) {
  if (amount == null) return "";
  const v = num(amount);
  return currency && currency !== "KRW" ? `${v > 0 ? "+" : ""}${v.toLocaleString("en-US", { maximumFractionDigits: 4 })} ${currency}`
    : `${v > 0 ? "+" : ""}${won(v)}`;
}

export function ImportPage({ hid, params }: { hid: number; params: URLSearchParams }) {
  const accounts = useLoad(() => api.accounts(hid), [hid]);
  const usable = (accounts.data ?? []).filter((a) => a.valuation_method === "transactions");
  const fromUrl = Number(params.get("account")) || null;
  const [accountId, setAccountId] = useState<number | null>(fromUrl);
  const [file, setFile] = useState<File | null>(null);
  const [result, setResult] = useState<ImportResult | null>(null);
  const [over, setOver] = useState(false);
  const input = useRef<HTMLInputElement>(null);
  const act = useAction();
  const batches = useLoad(() => (accountId ? api.importBatches(accountId) : Promise.resolve([])), [accountId]);

  useEffect(() => {
    if (accountId == null && usable.length === 1) setAccountId(usable[0].id);
  }, [accountId, usable]);

  const choose = async (f: File | undefined) => {
    if (!f || accountId == null) return;
    setFile(f); setResult(null);
    const r = await act.run(() => api.previewImport(accountId, f));
    if (r) setResult(r);
  };
  const commit = async () => {
    if (!file || accountId == null) return;
    const r = await act.run(() => api.commitImport(accountId, file));
    if (r) { setResult(r); batches.reload(); }
  };
  const reset = () => { setFile(null); setResult(null); act.setError(null); if (input.current) input.current.value = ""; };
  const account = usable.find((a) => a.id === accountId);
  const uncategorized = result?.committed ? result.rows.filter((r) => r.status === "new" && !r.category_id && (r.kind === "cash_in" || r.kind === "cash_out")).length : 0;

  return (
    <div className="grid">
      <section className="card">
        <h2>거래 파일 가져오기</h2>
        <p className="sub">
          은행에서 받은 거래내역 엑셀(우리·신한·하나·IBK 등)이나 AssetHub 표준 양식을 올립니다.
          먼저 미리보기로 확인하고, 저장하면 새 거래만 들어갑니다. 같은 파일을 다시 올려도 중복으로 들어가지 않습니다.
        </p>
        <div className="toolbar">
          <select aria-label="계좌" value={accountId ?? ""} onChange={(e) => { setAccountId(Number(e.target.value) || null); reset(); }}>
            <option value="">계좌를 고르세요</option>
            {usable.map((a) => <option key={a.id} value={a.id}>{a.name} · {accountTypeLabel(a.account_type)}</option>)}
          </select>
          <a className="btn" href="/api/import-template">표준 양식 내려받기</a>
          {usable.length === 0 && !accounts.loading && (
            <span className="field-hint">먼저 <button className="btn link" onClick={() => navigate("/manage")}>관리</button>에서 계좌를 만드세요.</span>
          )}
        </div>
        {accountId != null && !result && (
          <div className={`dropzone${over ? " over" : ""}`} role="button" tabIndex={0}
            onClick={() => input.current?.click()} onKeyDown={(e) => { if (e.key === "Enter" || e.key === " ") input.current?.click(); }}
            onDragOver={(e) => { e.preventDefault(); setOver(true); }} onDragLeave={() => setOver(false)}
            onDrop={(e) => { e.preventDefault(); setOver(false); choose(e.dataTransfer.files[0]); }}>
            {act.busy ? "읽는 중…" : <><strong>여기에 파일을 끌어 놓거나 눌러서 고르세요</strong><br />.xlsx · .xls · .csv</>}
            <input ref={input} type="file" accept=".xlsx,.xls,.csv,.htm,.html" hidden onChange={(e) => choose(e.target.files?.[0])} />
          </div>
        )}
        <ErrorNote error={act.error} />
      </section>

      {result && (
        <section className="card">
          <div className="section-head">
            <h2>{result.committed ? "저장했습니다" : "미리보기"}</h2>
            <span className="muted" style={{ color: "var(--text-muted)", fontSize: 13 }}>
              {file?.name} · {result.format ?? "알 수 없는 형식"}{result.file_direction === "newest-first" ? " · 최신 거래가 위에 있는 파일" : ""}
            </span>
            <span className="spacer" />
            {!result.committed && (
              <button className="btn primary" disabled={act.busy || result.counts.new === 0} onClick={commit}>
                {result.counts.new}건 저장
              </button>
            )}
            <button className="btn" onClick={reset}>{result.committed ? "다른 파일 올리기" : "취소"}</button>
          </div>
          <div className="summary-line">
            <span>새 거래 <strong>{result.counts.new}</strong></span>
            <span>중복 <strong>{result.counts.duplicate}</strong></span>
            <span>오류 <strong>{result.counts.error}</strong></span>
            {result.opening_balance != null && <span>기초잔액 <strong>{won(num(result.opening_balance))}</strong> 자동 입력</span>}
          </div>
          {result.warnings.length > 0 && (
            <div className="notice"><ul style={{ margin: 0 }}>{result.warnings.map((w) => <li key={w}>{w}</li>)}</ul></div>
          )}
          {result.committed && account && (
            <div className="ok-note">
              {account.name}에 {result.counts.new}건을 저장했습니다.{" "}
              <button className="btn link" onClick={() => navigate("/transactions", { account: account.id })}>거래내역 보기</button>
              {uncategorized > 0 && <> · <button className="btn link" onClick={() => navigate("/transactions", { account: account.id, uncategorized: 1 })}>
                미분류 {uncategorized}건 분류하기</button></>}
            </div>
          )}
          <div className="table-wrap">
            <table className="wide">
              <thead><tr><th>상태</th><th>날짜</th><th>내용</th><th>카테고리</th><th className="num">금액</th><th className="num">거래 후 잔액</th></tr></thead>
              <tbody>
                {result.rows.slice(0, SHOW_ROWS).map((r) => (
                  <tr key={`${r.status}-${r.file_index}`} className={r.status === "duplicate" ? "void" : ""}>
                    <td><span className={`chip ${r.status}`}>{STATUS[r.status]}</span></td>
                    <td>{r.trade_date ?? ""}</td>
                    <td>
                      {r.kind && r.kind !== "cash_in" && r.kind !== "cash_out" && <span className="tag" style={{ marginLeft: 0, marginRight: 6 }}>{KIND_LABEL[r.kind] ?? r.kind}</span>}
                      {r.description}{r.instrument_symbol && ` ${r.instrument_symbol}`}
                      {r.counterparty && r.counterparty !== r.description && <div className="muted">{r.counterparty}</div>}
                      {r.message && <div className="muted">{r.message}</div>}
                    </td>
                    <td>{r.category_name ?? ""}{r.category_source && <div className="muted">{SOURCE[r.category_source]}</div>}</td>
                    <td className="num">{amountText(r.amount, r.currency)}</td>
                    <td className="num">{r.balance_after == null ? "" : won(num(r.balance_after))}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          {result.rows.length > SHOW_ROWS && <p className="field-hint">처음 {SHOW_ROWS}행만 보여줍니다 (전체 {result.rows.length}행).</p>}
        </section>
      )}

      {accountId != null && (batches.data ?? []).length > 0 && (
        <section className="card">
          <h2>이 계좌의 업로드 기록</h2>
          <table className="medium">
            <thead><tr><th>시각</th><th>파일</th><th className="num">새 거래</th><th className="num">중복</th><th>결과</th></tr></thead>
            <tbody>
              {batches.data!.map((b) => (
                <tr key={b.id}>
                  <td>{dateTime(b.started_at)}</td><td>{b.file_name}</td>
                  <td className="num">{b.records_new}</td><td className="num">{b.records_duplicate}</td>
                  <td>{b.status === "succeeded" ? "완료" : b.status === "partial" ? "일부 오류" : b.status}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </section>
      )}
    </div>
  );
}
