import { useState } from "react";
import { api } from "../api";
import { navigate } from "../router";
import { ErrorNote, Field, useAction } from "../ui";

/** 처음 실행: 가구와 본인을 만든다. */
export function Onboarding({ onDone }: { onDone: (householdId: number) => void }) {
  const [name, setName] = useState("우리집");
  const [me, setMe] = useState("");
  const act = useAction();
  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    const id = await act.run(async () => {
      const h = await api.createHousehold(name.trim());
      await api.createMember(h.id, { name: me.trim(), relation: "self" });
      return h.id;
    });
    if (id != null) { navigate("/manage"); onDone(id); }
  };
  return (
    <section className="card" style={{ maxWidth: 520, margin: "40px auto" }}>
      <h2>AssetHub 시작하기</h2>
      <p className="sub">가구 이름과 본인 이름을 정하면 다음 화면에서 가족과 계좌를 등록합니다.</p>
      <form onSubmit={submit} className="form">
        <Field label="가구 이름"><input value={name} onChange={(e) => setName(e.target.value)} required /></Field>
        <Field label="본인 이름"><input value={me} onChange={(e) => setMe(e.target.value)} required autoFocus /></Field>
        <div className="field wide"><button className="btn primary" disabled={act.busy}>시작하기</button></div>
      </form>
      <ErrorNote error={act.error} />
    </section>
  );
}
