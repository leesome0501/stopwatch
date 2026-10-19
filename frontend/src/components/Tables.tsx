import type { AccountRow, Holding } from "../api";
import { arrow, dayLabel, direction, krw, num, price, quantity, signedPct, won } from "../format";

export function AccountsTable({ accounts }: { accounts: AccountRow[] }) {
  if (!accounts.length) return <div className="empty">계좌가 없습니다.</div>;
  return (
    <div className="table-wrap">
      <table className="medium">
        <thead><tr><th>계좌</th><th>종류</th><th>명의</th><th className="num">평가액</th></tr></thead>
        <tbody>
          {accounts.map((a) => {
            const v = num(a.value_krw);
            return (
              <tr key={a.id}>
                <td>{a.name}{a.institution && <div className="muted">{a.institution}</div>}</td>
                <td>{a.type_label}</td>
                <td>{a.owners.map((o) => num(o.share) < 1 ? `${o.name} ${Math.round(num(o.share) * 100)}%` : o.name).join(", ")}</td>
                <td className="num">
                  <span className={v < 0 ? "neg" : ""}>{won(v)}</span>
                  {a.reported_as_of && <div className="muted">{dayLabel(a.reported_as_of)} 기관 보고</div>}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

export function HoldingsTable({ holdings }: { holdings: Holding[] }) {
  if (!holdings.length) return <div className="empty">보유 종목이 없습니다.</div>;
  return (
    <div className="table-wrap">
      <table className="wide">
        <thead>
          <tr>
            <th>종목</th><th>계좌</th><th className="num">수량</th><th className="num">평균단가</th>
            <th className="num">현재가</th><th className="num">평가금액</th><th className="num">평가손익</th>
          </tr>
        </thead>
        <tbody>
          {holdings.map((h) => {
            const pnl = h.pnl_krw == null ? null : num(h.pnl_krw);
            const dir = pnl == null ? "flat" : direction(pnl);
            return (
              <tr key={`${h.account_id}-${h.instrument_id}`}>
                <td>
                  {h.name}
                  {h.price_basis !== "market" && <span className="tag">시세 없음</span>}
                  <div className="muted">{[h.symbol, h.market].filter(Boolean).join(" · ") || h.asset_class}</div>
                </td>
                <td>{h.account_name}</td>
                <td className="num">{quantity(num(h.quantity))}</td>
                <td className="num">{h.avg_cost == null ? "–" : price(num(h.avg_cost), h.currency)}</td>
                <td className="num">
                  {h.price == null ? "–" : price(num(h.price), h.currency)}
                  {h.price_date && <div className="muted">{dayLabel(h.price_date)}</div>}
                  {h.price_basis === "trade" && <div className="muted">거래 단가</div>}
                </td>
                <td className="num">{krw(num(h.value_krw))}</td>
                <td className={`num pnl ${dir}`}>
                  {pnl == null ? "–" : <>{arrow(pnl)} {krw(Math.abs(pnl))}
                    <div className="muted">{signedPct(num(h.pnl_pct))}</div></>}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
