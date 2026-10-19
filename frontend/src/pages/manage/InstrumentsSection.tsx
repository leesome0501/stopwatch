import { useState } from "react";
import { api, type Instrument } from "../../api";
import { num, price } from "../../format";
import { ASSET_CLASSES, assetClassLabel, INSTRUMENT_KINDS, MARKETS } from "../../labels";
import { cleanNumber, ErrorNote, Field, todayKst, useAction, useLoad } from "../../ui";

function PricePanel({ inst, onClose }: { inst: Instrument; onClose: () => void }) {
  const prices = useLoad(() => api.prices(inst.id, 8), [inst.id]);
  const [day, setDay] = useState(todayKst());
  const [value, setValue] = useState("");
  const act = useAction();
  const add = async () => {
    const ok = await act.run(async () => { await api.putPrice(inst.id, day, cleanNumber(value)); return true; });
    if (ok) { setValue(""); prices.reload(); }
  };
  return (
    <div className="panel">
      <h3>{inst.name} 시세</h3>
      <p className="field-hint" style={{ margin: "0 0 8px" }}>
        {inst.market === "PRIVATE" ? "실거래가나 KB시세를 보고 가끔 적어 주세요. 직접 적은 시세는 자동 수집이 덮어쓰지 않습니다."
          : "자동으로 수집되는 종목입니다. 필요하면 직접 적은 값이 우선합니다."}
      </p>
      <div className="toolbar">
        <input aria-label="날짜" type="date" value={day} onChange={(e) => setDay(e.target.value)} />
        <input aria-label="가격" inputMode="decimal" placeholder={`가격 (${inst.currency})`} value={value} onChange={(e) => setValue(e.target.value)} />
        <button className="btn" disabled={!value || act.busy} onClick={add}>기록</button>
        <button className="btn" onClick={onClose}>닫기</button>
      </div>
      <ErrorNote error={act.error ?? prices.error} />
      {prices.data && prices.data.length > 0 ? (
        <table><tbody>
          {prices.data.map((p) => (
            <tr key={p.price_date}><td>{p.price_date}</td><td className="num">{price(num(p.close), inst.currency)}</td>
              <td className="muted">{p.source === "manual" ? "직접 입력" : p.source}</td></tr>
          ))}
        </tbody></table>
      ) : <div className="field-hint">아직 시세가 없습니다.</div>}
    </div>
  );
}

export function InstrumentsSection({ hid }: { hid: number }) {
  const list = useLoad(() => api.instruments(hid), [hid]);
  const [adding, setAdding] = useState(false);
  const [priceFor, setPriceFor] = useState<number | null>(null);
  const [market, setMarket] = useState("KRX");
  const m = MARKETS.find((x) => x.code === market)!;
  const [f, setF] = useState({ symbol: "", name: "", kind: m.kind, asset_class: m.asset_class, currency: m.currency });
  const act = useAction();
  const chooseMarket = (code: string) => {
    const x = MARKETS.find((y) => y.code === code)!;
    setMarket(code);
    setF((cur) => ({ ...cur, kind: x.kind, asset_class: x.asset_class, currency: x.currency }));
  };
  const add = async (e: React.FormEvent) => {
    e.preventDefault();
    const priv = market === "PRIVATE";
    const r = await act.run(() => api.createInstrument({
      name: f.name.trim(), kind: f.kind, asset_class: f.asset_class, currency: f.currency,
      market, symbol: priv ? null : f.symbol.trim().toUpperCase(), household_id: priv ? hid : null,
      country: f.currency === "KRW" ? "KR" : f.currency === "USD" ? "US" : null,
    }));
    if (r) { setAdding(false); setF({ ...f, symbol: "", name: "" }); list.reload(); if (priv) setPriceFor(r.id); }
  };
  const items = list.data ?? [];
  return (
    <section className="card">
      <div className="section-head">
        <h2>종목</h2>
        <span className="spacer" />
        <button className="btn" onClick={() => setAdding(!adding)}>{adding ? "닫기" : "종목 등록"}</button>
      </div>
      <p className="sub">주식·ETF·코인은 종목코드로 등록하면 시세가 자동으로 모입니다. 아파트 같은 자산은 '부동산·비상장'으로 등록하고 시세를 직접 적습니다.</p>
      {adding && (
        <form className="panel" onSubmit={add}>
          <div className="form">
            <Field label="시장">
              <select value={market} onChange={(e) => chooseMarket(e.target.value)}>
                {MARKETS.map((x) => <option key={x.code} value={x.code}>{x.label}</option>)}
              </select>
            </Field>
            {market !== "PRIVATE" && (
              <Field label="종목코드" hint={m.hint}><input value={f.symbol} onChange={(e) => setF({ ...f, symbol: e.target.value })} required /></Field>
            )}
            <Field label="이름"><input value={f.name} onChange={(e) => setF({ ...f, name: e.target.value })} required placeholder={market === "PRIVATE" ? "예: 우리집 아파트 84㎡" : "예: 삼성전자"} /></Field>
            <Field label="종류">
              <select value={f.kind} onChange={(e) => setF({ ...f, kind: e.target.value })}>{INSTRUMENT_KINDS.map(([k, l]) => <option key={k} value={k}>{l}</option>)}</select>
            </Field>
            <Field label="자산군" hint="자산 구성 차트의 분류">
              <select value={f.asset_class} onChange={(e) => setF({ ...f, asset_class: e.target.value })}>{ASSET_CLASSES.map(([k, l]) => <option key={k} value={k}>{l}</option>)}</select>
            </Field>
            <Field label="통화"><input value={f.currency} maxLength={3} onChange={(e) => setF({ ...f, currency: e.target.value.toUpperCase() })} required /></Field>
          </div>
          <div className="actions"><button className="btn primary" disabled={act.busy}>등록</button></div>
          <ErrorNote error={act.error} />
        </form>
      )}
      <ErrorNote error={list.error} />
      {items.length === 0 ? <div className="empty">등록된 종목이 없습니다.</div> : (
        <div className="table-wrap">
          <table className="medium">
            <thead><tr><th>이름</th><th>코드·시장</th><th>자산군</th><th>통화</th><th /></tr></thead>
            <tbody>
              {items.map((i) => (
                priceFor === i.id ? (
                  <tr key={i.id}><td colSpan={5}><PricePanel inst={i} onClose={() => setPriceFor(null)} /></td></tr>
                ) : (
                  <tr key={i.id}>
                    <td>{i.name}</td>
                    <td>{[i.symbol, i.market].filter(Boolean).join(" · ")}</td>
                    <td>{assetClassLabel(i.asset_class)}</td>
                    <td>{i.currency}</td>
                    <td className="num"><button className="btn small" onClick={() => setPriceFor(i.id)}>시세</button></td>
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
