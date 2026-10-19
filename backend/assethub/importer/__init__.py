"""파일(엑셀·CSV) 가져오기.

흐름: reader(파일 → 셀 행렬) → formats(행렬 → 표준 행) → sequence(순서·잔액 검증)
→ dedupe(중복 판정) → service(DB 반영).
"""
