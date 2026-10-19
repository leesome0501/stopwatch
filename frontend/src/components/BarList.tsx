import { won } from "../format";

export interface BarItem { label: string; value: number; note?: string }

/** 한 가지 색 가로 막대. 값과 비율을 막대 끝에 바로 적는다 (색으로 구분할 필요가 없게). */
export function BarList({ items, format, empty }: {
  items: BarItem[]; format: (v: number) => string; empty: string;
}) {
  const shown = items.filter((i) => i.value > 0);
  if (!shown.length) return <div className="empty">{empty}</div>;
  const max = Math.max(...shown.map((i) => i.value));
  return (
    <div className="barlist" role="list">
      {shown.map((i) => (
        <div className="row" role="listitem" key={i.label} title={`${i.label} ${won(i.value)}`}>
          <span className="name">{i.label}</span>
          <span className="track">
            <span className="bar" style={{ display: "block", width: `${(i.value / max) * 100}%` }} />
          </span>
          <span className="val"><strong>{format(i.value)}</strong>{i.note}</span>
        </div>
      ))}
    </div>
  );
}
