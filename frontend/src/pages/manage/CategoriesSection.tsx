import { useState } from "react";
import { api } from "../../api";
import { CATEGORY_KIND_LABEL } from "../../labels";
import { CategorySelect, ErrorNote, Field, useAction, useLoad } from "../../ui";

const FIELD_LABEL = { description: "적요", counterparty: "거래처" } as const;
const TYPE_LABEL = { contains: "포함", equals: "일치", regex: "정규식" } as const;

export function CategoriesSection({ hid }: { hid: number }) {
  const cats = useLoad(() => api.categories(hid), [hid]);
  const rules = useLoad(() => api.rules(hid), [hid]);
  const [rule, setRule] = useState({ match_field: "description" as "description" | "counterparty", match_type: "contains" as "contains" | "equals" | "regex", pattern: "", category_id: null as number | null });
  const [cat, setCat] = useState({ name: "", parent_id: "" as string, kind: "expense" });
  const ruleAct = useAction();
  const catAct = useAction();
  const categories = cats.data ?? [];
  const tops = categories.filter((c) => c.parent_id == null);

  const addRule = async (e: React.FormEvent) => {
    e.preventDefault();
    if (rule.category_id == null) { ruleAct.setError("카테고리를 고르세요."); return; }
    if (await ruleAct.run(() => api.createRule(hid, { ...rule, pattern: rule.pattern.trim(), category_id: rule.category_id! }))) {
      setRule({ ...rule, pattern: "" }); rules.reload();
    }
  };
  const addCat = async (e: React.FormEvent) => {
    e.preventDefault();
    const body = cat.parent_id ? { name: cat.name.trim(), parent_id: Number(cat.parent_id) } : { name: cat.name.trim(), kind: cat.kind };
    if (await catAct.run(() => api.createCategory(hid, body))) { setCat({ ...cat, name: "" }); cats.reload(); }
  };

  return (
    <section className="card">
      <h2>분류</h2>
      <p className="sub">
        자동 분류 규칙은 엑셀을 올릴 때 먼저 적용됩니다. 규칙이 없으면 같은 적요·거래처의 지난 분류를 따라갑니다.
        거래내역 화면에서 카테고리를 바꾸면 규칙을 바로 만들 수도 있습니다.
      </p>
      <h3 style={{ fontSize: 14 }}>자동 분류 규칙</h3>
      <ErrorNote error={rules.error} />
      {(rules.data ?? []).length === 0 ? <div className="field-hint" style={{ marginBottom: 10 }}>아직 규칙이 없습니다.</div> : (
        <table className="medium" style={{ marginBottom: 10 }}>
          <thead><tr><th>조건</th><th>카테고리</th><th /></tr></thead>
          <tbody>
            {rules.data!.map((r) => (
              <tr key={r.id}>
                <td>{FIELD_LABEL[r.match_field]}에 "{r.pattern}" {TYPE_LABEL[r.match_type]}</td>
                <td>{r.category_name}</td>
                <td className="num"><button className="btn small" onClick={async () => { await ruleAct.run(() => api.deleteRule(hid, r.id)); rules.reload(); }}>지우기</button></td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
      <form className="toolbar" onSubmit={addRule}>
        <select aria-label="기준" value={rule.match_field} onChange={(e) => setRule({ ...rule, match_field: e.target.value as "description" | "counterparty" })}>
          <option value="description">적요에</option><option value="counterparty">거래처에</option>
        </select>
        <input aria-label="문구" placeholder="문구 (예: 스타벅스)" value={rule.pattern} onChange={(e) => setRule({ ...rule, pattern: e.target.value })} required />
        <select aria-label="방식" value={rule.match_type} onChange={(e) => setRule({ ...rule, match_type: e.target.value as "contains" | "equals" | "regex" })}>
          <option value="contains">포함되면</option><option value="equals">정확히 같으면</option><option value="regex">정규식</option>
        </select>
        <CategorySelect ariaLabel="카테고리" categories={categories} value={rule.category_id} emptyLabel="카테고리 선택"
          onChange={(id) => setRule({ ...rule, category_id: id })} />
        <button className="btn" disabled={ruleAct.busy}>규칙 추가</button>
      </form>
      <ErrorNote error={ruleAct.error} />

      <h3 style={{ fontSize: 14, marginTop: 20 }}>카테고리 추가</h3>
      <form className="form" onSubmit={addCat}>
        <Field label="상위 카테고리">
          <select value={cat.parent_id} onChange={(e) => setCat({ ...cat, parent_id: e.target.value })}>
            <option value="">(새 상위 카테고리)</option>
            {(["expense", "income", "transfer"] as const).map((k) => (
              <optgroup key={k} label={CATEGORY_KIND_LABEL[k]}>
                {tops.filter((t) => t.kind === k).map((t) => <option key={t.id} value={t.id}>{t.name}</option>)}
              </optgroup>
            ))}
          </select>
        </Field>
        {!cat.parent_id && (
          <Field label="구분">
            <select value={cat.kind} onChange={(e) => setCat({ ...cat, kind: e.target.value })}>
              <option value="expense">지출</option><option value="income">수입</option><option value="transfer">이체 (통계 제외)</option>
            </select>
          </Field>
        )}
        <Field label="이름"><input value={cat.name} onChange={(e) => setCat({ ...cat, name: e.target.value })} required /></Field>
        <div className="field"><span className="field-label">&nbsp;</span><button className="btn" disabled={catAct.busy}>추가</button></div>
      </form>
      <ErrorNote error={catAct.error ?? cats.error} />
    </section>
  );
}
