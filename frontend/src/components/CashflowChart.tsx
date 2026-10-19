import { useRef, useState } from "react";
import { axisKrw, krw, monthLabel, niceTicks, num, won } from "../format";
import { TableView } from "./TableView";
import { useWidth } from "./useWidth";

interface Month { month: string; income_krw: string; expense_krw: string }

const H = 220;
const M = { top: 22, right: 8, bottom: 26, left: 48 };
const SERIES = [
  { key: "income" as const, name: "수입", color: "var(--series-1)" },
  { key: "expense" as const, name: "지출", color: "var(--series-2)" },
];

/** 위만 둥근 기둥 (아래는 기준선에 붙는다). */
function column(x: number, y: number, w: number, h: number): string {
  const r = Math.min(4, w / 2, h);
  return `M${x},${y + h}V${y + r}A${r},${r} 0 0 1 ${x + r},${y}H${x + w - r}A${r},${r} 0 0 1 ${x + w},${y + r}V${y + h}Z`;
}

export function CashflowChart({ months }: { months: Month[] }) {
  const ref = useRef<HTMLDivElement>(null);
  const width = useWidth(ref);
  const [hover, setHover] = useState<number | null>(null);
  const data = months.map((m) => ({ month: m.month, income: num(m.income_krw), expense: num(m.expense_krw) }));
  const max = Math.max(0, ...data.flatMap((d) => [d.income, d.expense]));
  if (max === 0) return <div className="empty">카테고리가 붙은 수입·지출이 아직 없습니다.</div>;

  const ticks = niceTicks(0, max, 3);
  const top = ticks[ticks.length - 1];
  const pw = width - M.left - M.right, ph = H - M.top - M.bottom;
  const band = pw / data.length;
  const w = Math.min(24, band * 0.3);
  const y = (v: number) => M.top + ph - (v / top) * ph;
  const lastI = data.length - 1;

  return (
    <>
      <div className="legend">
        {SERIES.map((s) => <span key={s.key}><i className="swatch" style={{ background: s.color }} />{s.name}</span>)}
      </div>
      <div className="chart" ref={ref}>
        <svg width={width} height={H} role="img" aria-label="월별 수입과 지출">
          {ticks.map((t) => (
            <g key={t}>
              <line className={t === 0 ? "baseline" : "gridline"} x1={M.left} x2={width - M.right} y1={y(t)} y2={y(t)} />
              <text className="axis-text" x={M.left - 8} y={y(t)} dy="0.32em" textAnchor="end">{axisKrw(t)}</text>
            </g>
          ))}
          {data.map((d, i) => {
            const cx = M.left + band * i + band / 2;
            return (
              <g key={d.month} opacity={hover == null || hover === i ? 1 : 0.55}>
                {SERIES.map((s, j) => {
                  const v = d[s.key];
                  const x0 = cx - w - 1 + j * (w + 2);   // 두 기둥 사이 2px 간격
                  return (
                    <g key={s.key}>
                      {v > 0 && <path d={column(x0, y(v), w, y(0) - y(v))} fill={s.color} />}
                      {i === lastI && v > 0 && (
                        <text className="label-muted" x={j === 0 ? x0 + w : x0} y={y(v) - 6} textAnchor={j === 0 ? "end" : "start"}>{krw(v)}</text>
                      )}
                    </g>
                  );
                })}
                <text className="axis-text" x={cx} y={H - 6} textAnchor="middle">{monthLabel(d.month)}</text>
                <rect x={M.left + band * i} y={M.top} width={band} height={ph} fill="transparent" tabIndex={0}
                  aria-label={`${monthLabel(d.month)} 수입 ${won(d.income)}, 지출 ${won(d.expense)}`}
                  onPointerEnter={() => setHover(i)} onPointerLeave={() => setHover(null)}
                  onFocus={() => setHover(i)} onBlur={() => setHover(null)} />
              </g>
            );
          })}
        </svg>
        {hover != null && (
          <div className={`tooltip${y(Math.max(data[hover].income, data[hover].expense)) < 110 ? " below" : ""}`} style={{
            left: Math.min(Math.max(M.left + band * hover + band / 2, 80), width - 80),
            top: y(Math.max(data[hover].income, data[hover].expense)),
          }}>
            <div className="t-title">{data[hover].month.replace("-", "년 ")}월</div>
            {SERIES.map((s) => (
              <div className="t-row" key={s.key}>
                <span className="t-name"><i className="key-line" style={{ background: s.color }} />{s.name}</span>
                <strong>{won(data[hover][s.key])}</strong>
              </div>
            ))}
            <div className="t-row"><span className="t-name">차액</span><strong>{won(data[hover].income - data[hover].expense)}</strong></div>
          </div>
        )}
      </div>
      <TableView head={["월", "수입", "지출", "차액"]}
        rows={data.map((d) => [d.month, won(d.income), won(d.expense), won(d.income - d.expense)])} />
    </>
  );
}
