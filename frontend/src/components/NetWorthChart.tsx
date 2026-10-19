import { useMemo, useRef, useState, type KeyboardEvent, type PointerEvent } from "react";
import type { HistoryPoint } from "../api";
import { axisKrw, fullDate, krw, niceTicks, num, won } from "../format";
import { TableView } from "./TableView";
import { useWidth } from "./useWidth";

const H = 240;
const M = { top: 16, right: 96, bottom: 28, left: 52 };

export function NetWorthChart({ points }: { points: HistoryPoint[] }) {
  const ref = useRef<HTMLDivElement>(null);
  const width = useWidth(ref);
  const [idx, setIdx] = useState<number | null>(null);

  const g = useMemo(() => {
    const data = points.map((p) => ({
      date: p.date, t: new Date(`${p.date}T00:00:00`).getTime(),
      v: num(p.net_worth_krw), a: num(p.assets_krw), l: num(p.liabilities_krw),
    }));
    const vs = data.map((d) => d.v);
    let lo = Math.min(...vs), hi = Math.max(...vs);
    // 0에서 멀지 않으면 0부터 그려 크기를 과장하지 않는다
    if (lo >= 0 && lo < hi * 0.6) lo = 0;
    const ticks = niceTicks(lo, hi, 4);
    const y0 = ticks[0], y1 = ticks[ticks.length - 1];
    const pw = Math.max(10, width - M.left - M.right);
    const ph = H - M.top - M.bottom;
    const t0 = data[0].t, t1 = data[data.length - 1].t;
    const x = (t: number) => M.left + (t1 === t0 ? pw / 2 : ((t - t0) / (t1 - t0)) * pw);
    const y = (v: number) => M.top + ph - ((v - y0) / (y1 - y0 || 1)) * ph;
    const line = data.map((d, i) => `${i ? "L" : "M"}${x(d.t).toFixed(1)},${y(d.v).toFixed(1)}`).join("");
    const area = y0 === 0 && lo >= 0 && data.length > 1
      ? `${line}L${x(t1).toFixed(1)},${y(0)}L${x(t0).toFixed(1)},${y(0)}Z` : null;
    const spanDays = (t1 - t0) / 864e5;
    const nLabels = Math.max(2, Math.min(6, Math.floor(pw / 110)));
    const xTicks = data.length > 1
      ? Array.from({ length: nLabels }, (_, i) => t0 + ((t1 - t0) * i) / (nLabels - 1)) : [t0];
    const fmtX = (t: number) => {
      const d = new Date(t);
      return spanDays <= 120 ? `${d.getMonth() + 1}/${d.getDate()}` : `${d.getFullYear()}.${String(d.getMonth() + 1).padStart(2, "0")}`;
    };
    return { data, ticks, x, y, line, area, xTicks, fmtX, pw, ph };
  }, [points, width]);

  if (!points.length) return <div className="empty">거래를 올리면 순자산 추이가 그려집니다.</div>;
  const { data, ticks, x, y, line, area, xTicks, fmtX, ph } = g;
  const last = data[data.length - 1];
  const active = idx == null ? null : data[idx];

  const nearest = (px: number) => {
    let best = 0, bd = Infinity;
    data.forEach((d, i) => { const dd = Math.abs(x(d.t) - px); if (dd < bd) { bd = dd; best = i; } });
    return best;
  };
  const onMove = (e: PointerEvent<SVGRectElement>) => {
    const box = e.currentTarget.ownerSVGElement!.getBoundingClientRect();
    setIdx(nearest(e.clientX - box.left));
  };
  const onKey = (e: KeyboardEvent<SVGRectElement>) => {
    if (e.key === "ArrowLeft" || e.key === "ArrowRight") {
      e.preventDefault();
      const cur = idx ?? data.length - 1;
      setIdx(Math.max(0, Math.min(data.length - 1, cur + (e.key === "ArrowLeft" ? -1 : 1))));
    } else if (e.key === "Escape") setIdx(null);
  };
  const tipX = active ? Math.min(Math.max(x(active.t), 90), width - 90) : 0;

  return (
    <>
      <div className="chart" ref={ref}>
        <svg width={width} height={H} role="img" aria-label={`순자산 추이. 마지막 값 ${won(last.v)}`}>
          {ticks.map((t) => (
            <g key={t}>
              <line className={t === 0 ? "baseline" : "gridline"} x1={M.left} x2={width - M.right} y1={y(t)} y2={y(t)} />
              <text className="axis-text" x={M.left - 8} y={y(t)} dy="0.32em" textAnchor="end">{axisKrw(t)}</text>
            </g>
          ))}
          {xTicks.map((t, i) => (
            <text key={i} className="axis-text" x={x(t)} y={H - 8}
              textAnchor={i === 0 ? "start" : i === xTicks.length - 1 ? "end" : "middle"}>{fmtX(t)}</text>
          ))}
          {area && <path d={area} fill="var(--series-1-wash)" />}
          {data.length > 1 && <path d={line} fill="none" stroke="var(--series-1)" strokeWidth={2}
            strokeLinejoin="round" strokeLinecap="round" />}
          <circle cx={x(last.t)} cy={y(last.v)} r={4} fill="var(--series-1)" stroke="var(--surface)" strokeWidth={2} />
          <text className="label-text" x={x(last.t) + 10} y={y(last.v)} dy="0.32em">{krw(last.v)}</text>
          {active && (
            <g pointerEvents="none">
              <line className="crosshair" x1={x(active.t)} x2={x(active.t)} y1={M.top} y2={M.top + ph} />
              <circle cx={x(active.t)} cy={y(active.v)} r={5} fill="var(--series-1)" stroke="var(--surface)" strokeWidth={2} />
            </g>
          )}
          <rect className="overlay" x={M.left} y={M.top} width={g.pw} height={ph} tabIndex={0}
            aria-label="순자산 추이. 좌우 화살표로 날짜 이동"
            onPointerMove={onMove} onPointerLeave={() => setIdx(null)} onKeyDown={onKey}
            onFocus={() => setIdx(data.length - 1)} onBlur={() => setIdx(null)} />
        </svg>
        {active && (
          <div className={`tooltip${y(active.v) < 110 ? " below" : ""}`} style={{ left: tipX, top: y(active.v) }}>
            <div className="t-title">{fullDate(active.date)}</div>
            <div className="t-row"><span className="t-name"><i className="key-line" style={{ background: "var(--series-1)" }} />순자산</span><strong>{won(active.v)}</strong></div>
            <div className="t-row"><span className="t-name">자산</span><strong>{won(active.a)}</strong></div>
            <div className="t-row"><span className="t-name">부채</span><strong>{won(active.l)}</strong></div>
          </div>
        )}
      </div>
      <TableView head={["날짜", "순자산", "자산", "부채"]}
        rows={[...data].reverse().map((d) => [d.date, won(d.v), won(d.a), won(d.l)])} />
    </>
  );
}
