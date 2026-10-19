# 마이그레이션

데이터베이스 구조 변경은 이 폴더에 번호를 붙인 SQL 파일로 쌓는다.

- 파일 이름: `NNNN_설명.sql` (예: `0003_add_card_installment.sql`). 번호는 이어서 붙인다.
- 이미 배포된 파일은 고치지 않는다. 바꿀 것이 있으면 다음 번호 파일을 새로 만든다.
- 파일 하나가 트랜잭션 하나로 실행된다. 중간에 실패하면 그 파일 전체가 취소된다 (PostgreSQL 은 구조 변경도 되돌린다).
  그래서 파일 안에 `BEGIN`/`COMMIT` 을 쓰지 않는다. `CREATE INDEX CONCURRENTLY` 처럼 트랜잭션 안에서 못 쓰는 문장도 피한다.
- 적용 기록은 `schema_migrations` 테이블에 남는다.

적용은 자동이다. 서버가 시작할 때(`start.cmd`, `uvicorn`), `setup.cmd`, `update.cmd` 가 아직 적용되지 않은 파일을 차례로 적용한다.
직접 적용하려면:

```bash
cd backend && uv run python -m assethub.migrate
```

마이그레이션 장치가 생기기 전에 `db/schema.sql` 로 만든 데이터베이스는 `0001`, `0002` 가 적용된 것으로 간주한다.
