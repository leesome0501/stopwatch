import { useCallback, useEffect, useRef, useState, type ReactNode } from "react";
import type { Category } from "./api";
import { CATEGORY_KIND_LABEL } from "./labels";

/** 비동기 로딩 상태. reload() 로 다시 부른다. */
export function useLoad<T>(fn: () => Promise<T>, deps: unknown[]) {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const seq = useRef(0);
  // eslint-disable-next-line react-hooks/exhaustive-deps
  const run = useCallback(fn, deps);
  const reload = useCallback(() => {
    const my = ++seq.current;
    setLoading(true);
    run().then((d) => { if (my === seq.current) { setData(d); setError(null); } })
      .catch((e) => { if (my === seq.current) setError((e as Error).message); })
      .finally(() => { if (my === seq.current) setLoading(false); });
  }, [run]);
  useEffect(reload, [reload]);
  return { data, error, loading, reload, setData };
}

/** 버튼 동작을 감싸 진행 중 표시와 오류 메시지를 처리한다. */
export function useAction() {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const run = useCallback(async <T,>(fn: () => Promise<T>): Promise<T | undefined> => {
    setBusy(true); setError(null);
    try { return await fn(); }
    catch (e) { setError((e as Error).message); return undefined; }
    finally { setBusy(false); }
  }, []);
  return { busy, error, setError, run };
}

export function ErrorNote({ error }: { error: string | null | undefined }) {
  if (!error) return null;
  return <div className="notice error" role="alert">{error}</div>;
}

export function Field({ label, children, hint, wide }: { label: string; children: ReactNode; hint?: string; wide?: boolean }) {
  return (
    <label className={`field${wide ? " wide" : ""}`}>
      <span className="field-label">{label}</span>
      {children}
      {hint && <span className="field-hint">{hint}</span>}
    </label>
  );
}

export function todayKst(): string {
  const now = new Date(Date.now() + 9 * 3600e3);
  return now.toISOString().slice(0, 10);
}

export function monthRange(offsetMonths: number): [string, string] {
  const t = todayKst();
  const y = Number(t.slice(0, 4)), m = Number(t.slice(5, 7)) - 1 + offsetMonths;
  const first = new Date(Date.UTC(y, m, 1)), last = new Date(Date.UTC(y, m + 1, 0));
  return [first.toISOString().slice(0, 10), last.toISOString().slice(0, 10)];
}

/** 2단계 카테고리 선택 (상위 그룹 안에 하위 항목). */
export function CategorySelect({ categories, value, onChange, kinds, emptyLabel = "미분류", allowParents = true, id, ariaLabel }: {
  categories: Category[]; value: number | null; onChange: (id: number | null) => void;
  kinds?: Category["kind"][]; emptyLabel?: string; allowParents?: boolean; id?: string; ariaLabel?: string;
}) {
  const tops = categories.filter((c) => c.parent_id == null && (!kinds || kinds.includes(c.kind)));
  return (
    <select id={id} aria-label={ariaLabel} value={value ?? ""} onChange={(e) => onChange(e.target.value ? Number(e.target.value) : null)}>
      <option value="">{emptyLabel}</option>
      {(["expense", "income", "transfer"] as const).filter((k) => !kinds || kinds.includes(k)).map((kind) => (
        tops.filter((t) => t.kind === kind).map((t) => {
          const kids = categories.filter((c) => c.parent_id === t.id);
          return (
            <optgroup key={t.id} label={`${CATEGORY_KIND_LABEL[kind]} · ${t.name}`}>
              {(allowParents || !kids.length) && <option value={t.id}>{t.name}{kids.length ? " (전체)" : ""}</option>}
              {kids.map((k) => <option key={k.id} value={k.id}>{k.name}</option>)}
            </optgroup>
          );
        })
      ))}
    </select>
  );
}

/** 숫자 입력: 쉼표를 허용하고 문자열로 돌려준다 (백엔드가 Decimal 로 받는다). */
export function cleanNumber(s: string): string {
  return s.replace(/[,\s원]/g, "");
}
