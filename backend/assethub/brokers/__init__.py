"""증권사 API 어댑터.

어댑터는 증권사 응답을 엑셀 가져오기와 같은 표준 행(ImportRow)과 잔고 스냅샷(Snapshot)으로 바꾼다.
저장·중복 판정·자동 분류는 importer.service 가, 잔고 맞춤은 brokers.sync 가 맡는다.
어댑터는 조회만 한다. 주문 기능은 일부러 만들지 않는다.
"""
