import { useState } from "react";
import { api, type Member, type Relation } from "../../api";
import { RELATIONS } from "../../labels";
import { ErrorNote, useAction } from "../../ui";

function MemberRow({ m, onChanged }: { m: Member; onChanged: () => void }) {
  const [form, setForm] = useState({ name: m.name, relation: m.relation, birth_date: m.birth_date ?? "", is_dependent: m.is_dependent });
  const act = useAction();
  const dirty = form.name !== m.name || form.relation !== m.relation || (form.birth_date || null) !== m.birth_date
    || form.is_dependent !== m.is_dependent;
  const save = async () => {
    const r = await act.run(() => api.updateMember(m.id, { ...form, name: form.name.trim(), birth_date: form.birth_date || null }));
    if (r) onChanged();
  };
  const del = async () => {
    if (!window.confirm(`${m.name}을(를) 구성원에서 지울까요?`)) return;
    if (await act.run(async () => { await api.deleteMember(m.id); return true; })) onChanged();
  };
  return (
    <>
      <tr>
        <td><input aria-label="이름" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} /></td>
        <td>
          <select aria-label="관계" value={form.relation} onChange={(e) => setForm({ ...form, relation: e.target.value as Relation })}>
            {RELATIONS.map(([k, l]) => <option key={k} value={k}>{l}</option>)}
          </select>
        </td>
        <td><input aria-label="생년월일" type="date" value={form.birth_date} onChange={(e) => setForm({ ...form, birth_date: e.target.value })} /></td>
        <td><input aria-label="부양가족" type="checkbox" checked={form.is_dependent} onChange={(e) => setForm({ ...form, is_dependent: e.target.checked })} /></td>
        <td className="num">
          <button className="btn small primary" disabled={!dirty || act.busy || !form.name.trim()} onClick={save}>저장</button>{" "}
          <button className="btn small" disabled={act.busy} onClick={del}>삭제</button>
        </td>
      </tr>
      {act.error && <tr><td colSpan={5}><ErrorNote error={act.error} /></td></tr>}
    </>
  );
}

export function MembersSection({ hid, members, reload, error }: {
  hid: number; members: Member[]; reload: () => void; error: string | null;
}) {
  const [name, setName] = useState("");
  const [relation, setRelation] = useState<Relation>("spouse");
  const act = useAction();
  const add = async (e: React.FormEvent) => {
    e.preventDefault();
    if (await act.run(() => api.createMember(hid, { name: name.trim(), relation }))) { setName(""); reload(); }
  };
  return (
    <section className="card">
      <h2>가족 구성원</h2>
      <p className="sub">계좌 명의와 구성원별 순자산에 쓰입니다. 부양가족 표시는 연말정산 기능에서 씁니다.</p>
      <ErrorNote error={error} />
      <div className="table-wrap">
        <table className="medium">
          <thead><tr><th>이름</th><th>관계</th><th>생년월일</th><th>부양가족</th><th /></tr></thead>
          <tbody>{members.map((m) => <MemberRow key={`${m.id}-${m.name}-${m.relation}-${m.birth_date}-${m.is_dependent}`} m={m} onChanged={reload} />)}</tbody>
        </table>
      </div>
      <form className="toolbar" style={{ marginTop: 12 }} onSubmit={add}>
        <input aria-label="새 구성원 이름" placeholder="이름" value={name} onChange={(e) => setName(e.target.value)} required />
        <select aria-label="새 구성원 관계" value={relation} onChange={(e) => setRelation(e.target.value as Relation)}>
          {RELATIONS.map(([k, l]) => <option key={k} value={k}>{l}</option>)}
        </select>
        <button className="btn" disabled={act.busy}>구성원 추가</button>
      </form>
      <ErrorNote error={act.error} />
    </section>
  );
}
