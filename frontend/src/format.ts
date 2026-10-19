export const num = (v: string | number | null | undefined): number => (v == null ? 0 : Number(v));

const MINUS = "−";

/** 1,234,567원 */
export function won(v: number): string {
  const r = Math.round(v);
  return `${r < 0 ? MINUS : ""}${Math.abs(r).toLocaleString("ko-KR")}원`;
}

/** 7억 2,941만 · 333만 · 8,500 (원 생략, 표·큰 숫자용) */
export function krw(v: number): string {
  const sign = v < 0 ? MINUS : "";
  const a = Math.abs(v);
  if (a >= 1e8) {
    let eok = Math.floor(a / 1e8);
    let man = Math.round((a - eok * 1e8) / 1e4);
    if (man === 10000) { eok += 1; man = 0; }
    return `${sign}${eok.toLocaleString("ko-KR")}억${man ? ` ${man.toLocaleString("ko-KR")}만` : ""}`;
  }
  if (a >= 1e4) return `${sign}${Math.round(a / 1e4).toLocaleString("ko-KR")}만`;
  return `${sign}${Math.round(a).toLocaleString("ko-KR")}`;
}

/** 축 눈금: 7.5억, 300만 */
export function axisKrw(v: number): string {
  const a = Math.abs(v);
  const sign = v < 0 ? MINUS : "";
  const trim = (x: number) => Number(x.toFixed(2)).toLocaleString("ko-KR");
  if (a >= 1e8) return `${sign}${trim(a / 1e8)}억`;
  if (a >= 1e4) return `${sign}${trim(a / 1e4)}만`;
  return `${sign}${trim(a)}`;
}

export function share(v: number): string {
  return v > 0 && v < 0.1 ? "0.1% 미만" : `${v.toFixed(1)}%`;
}

export function signedKrw(v: number): string {
  return `${v > 0 ? "+" : v < 0 ? MINUS : ""}${krw(Math.abs(v))}`;
}

export function signedPct(v: number): string {
  return `${v > 0 ? "+" : v < 0 ? MINUS : ""}${Math.abs(v).toFixed(2)}%`;
}

/** 한국 관례: 상승 ▲(빨강), 하락 ▼(파랑). 색만으로 구분하지 않도록 기호를 붙인다. */
export function direction(v: number): "up" | "down" | "flat" {
  return v > 0 ? "up" : v < 0 ? "down" : "flat";
}
export const arrow = (v: number) => (v > 0 ? "▲" : v < 0 ? "▼" : "");

export function quantity(v: number): string {
  return v.toLocaleString("ko-KR", { maximumFractionDigits: 8 });
}

export function price(v: number, currency: string): string {
  if (currency === "KRW") return `${Math.round(v).toLocaleString("ko-KR")}원`;
  return `${v.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 4 })} ${currency}`;
}

const d = (s: string) => new Date(`${s.slice(0, 10)}T00:00:00`);
export const dayLabel = (s: string) => { const x = d(s); return `${x.getMonth() + 1}월 ${x.getDate()}일`; };
export const fullDate = (s: string) => { const x = d(s); return `${x.getFullYear()}년 ${x.getMonth() + 1}월 ${x.getDate()}일`; };
export const monthLabel = (ym: string) => `${Number(ym.slice(5, 7))}월`;
export function dateTime(iso: string): string {
  const x = new Date(iso);
  return x.toLocaleString("ko-KR", { month: "numeric", day: "numeric", hour: "2-digit", minute: "2-digit" });
}

/** 깔끔한 축 눈금 (0, 2억, 4억 …) */
export function niceTicks(lo: number, hi: number, count = 4): number[] {
  if (hi === lo) { hi = lo === 0 ? 1 : lo + Math.abs(lo) * 0.1; lo = lo === 0 ? 0 : lo - Math.abs(lo) * 0.1; }
  const raw = (hi - lo) / count;
  const mag = 10 ** Math.floor(Math.log10(raw));
  const step = [1, 2, 2.5, 5, 10].map((m) => m * mag).find((s) => s >= raw) ?? 10 * mag;
  const start = Math.floor(lo / step) * step;
  const out: number[] = [];
  for (let v = start; v <= hi + step * 0.5; v += step) out.push(Number(v.toPrecision(12)));
  if (out[out.length - 1] < hi) out.push(out[out.length - 1] + step);
  return out;
}
