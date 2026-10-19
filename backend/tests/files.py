"""테스트용 파일 만들기."""
from __future__ import annotations

import html
import io


def xlsx_bytes(rows: list[list], sheet: str = "Sheet1", extra_sheets: dict[str, list[list]] | None = None) -> bytes:
    import openpyxl

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = sheet
    for r in rows:
        ws.append(r)
    for name, more in (extra_sheets or {}).items():
        s = wb.create_sheet(name)
        for r in more:
            s.append(r)
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def html_xls_bytes(rows: list[list], encoding: str = "cp949", title: str | None = None) -> bytes:
    """은행 사이트가 내려주는 '.xls 인 척하는 HTML 표'."""
    parts = ['<html><head><meta charset="euc-kr"></head><body>']
    if title:
        parts.append(f'<table><tr><td colspan="3">{html.escape(title)}</td></tr></table>')
    parts.append("<table>")
    for r in rows:
        parts.append("<tr>" + "".join(f"<td>{html.escape(str(c))}</td>" for c in r) + "</tr>")
    parts.append("</table></body></html>")
    return "".join(parts).encode(encoding)


def csv_bytes(rows: list[list], encoding: str = "utf-8") -> bytes:
    return "\n".join(",".join(f'"{c}"' if "," in str(c) else str(c) for c in r) for r in rows).encode(encoding)
