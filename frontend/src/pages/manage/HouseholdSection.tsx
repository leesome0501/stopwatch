import { useState } from "react";
import { api, type Household } from "../../api";
import { navigate } from "../../router";
import { ErrorNote, useAction } from "../../ui";

export function HouseholdSection({ household, onChanged }: { household: Household; onChanged: () => void }) {
  const [name, setName] = useState(household.name);
  const act = useAction();
  const save = async (e: React.FormEvent) => {
    e.preventDefault();
    if (await act.run(() => api.renameHousehold(household.id, name.trim()))) onChanged();
  };
  return (
    <section className="card">
      <h2>가구</h2>
      <form className="toolbar" onSubmit={save}>
        <input aria-label="가구 이름" value={name} onChange={(e) => setName(e.target.value)} required />
        <button className="btn" disabled={act.busy || name.trim() === household.name}>이름 바꾸기</button>
      </form>
      <ErrorNote error={act.error} />
    </section>
  );
}

/** 가구 삭제 (예제 데이터 정리용). 가구 이름을 그대로 입력해야 지워진다. */
export function DangerZone({ household, onDeleted }: { household: Household; onDeleted: () => void }) {
  const [open, setOpen] = useState(false);
  const [typed, setTyped] = useState("");
  const act = useAction();
  const del = async () => {
    const ok = await act.run(async () => { await api.deleteHousehold(household.id, typed); return true; });
    if (ok) { onDeleted(); navigate("/"); }
  };
  return (
    <section className="card">
      <h2>가구 전체 삭제</h2>
      <p className="sub">
        예제 데이터를 지우고 새로 시작할 때 씁니다. 이 가구의 구성원, 계좌, 거래, 업로드 기록이 모두 지워지고 되돌릴 수 없습니다.
        공용 종목과 시세는 남습니다.
      </p>
      {!open ? <button className="btn danger" onClick={() => setOpen(true)}>가구 삭제…</button> : (
        <div className="panel">
          <p style={{ margin: "0 0 8px" }}>확인을 위해 가구 이름 <strong>{household.name}</strong>을(를) 그대로 입력하세요.</p>
          <div className="toolbar">
            <input aria-label="확인용 가구 이름" value={typed} onChange={(e) => setTyped(e.target.value)} autoFocus />
            <button className="btn danger" disabled={typed !== household.name || act.busy} onClick={del}>영구 삭제</button>
            <button className="btn" onClick={() => { setOpen(false); setTyped(""); }}>취소</button>
          </div>
          <ErrorNote error={act.error} />
        </div>
      )}
    </section>
  );
}
