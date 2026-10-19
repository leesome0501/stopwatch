import type { ReactNode } from "react";

/** 모든 차트의 표 버전 (색이나 마우스 없이도 값을 읽을 수 있게). */
export function TableView({ head, rows }: { head: string[]; rows: ReactNode[][] }) {
  return (
    <details className="tableview">
      <summary>표로 보기</summary>
      <div className="scroll table-wrap">
        <table>
          <thead><tr>{head.map((h, i) => <th key={h} className={i ? "num" : ""}>{h}</th>)}</tr></thead>
          <tbody>
            {rows.map((r, i) => (
              <tr key={i}>{r.map((c, j) => <td key={j} className={j ? "num" : ""}>{c}</td>)}</tr>
            ))}
          </tbody>
        </table>
      </div>
    </details>
  );
}
