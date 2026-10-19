"""시트들 중에서 읽을 수 있는 표를 찾아 형식에 맞게 파싱한다."""
from __future__ import annotations

from .bank_formats import parse_bank_matrix
from .reader import read_sheets
from .rows import ParseResult
from .standard import SKIP_SHEET_WORDS, parse_standard_matrix

NOT_FOUND = "거래내역 표를 찾지 못했습니다. 지원하지 않는 형식이면 AssetHub 표준 양식을 사용해 주세요."


def parse_file(data: bytes) -> ParseResult:
    sheets = read_sheets(data)
    account_number = None
    empty_match: ParseResult | None = None
    for name, matrix in sheets:
        if any(w in name for w in SKIP_SHEET_WORDS):
            continue
        result = parse_standard_matrix(matrix) or parse_bank_matrix(matrix)
        if result is None:
            continue
        account_number = account_number or result.account_number
        if result.rows or result.errors:
            result.account_number = result.account_number or account_number
            return result
        empty_match = empty_match or result
    if empty_match is not None:
        empty_match.warnings.append("표는 찾았지만 거래 행이 없습니다.")
        return empty_match
    return ParseResult(format=None, rows=[], account_number=account_number, warnings=[NOT_FOUND])
