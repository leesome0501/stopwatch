#!/usr/bin/env bash
# 스키마 + 기본 데이터 + 예제 데이터를 빈 DB에 넣고 tests.sql 로 검증한다.
#
#   DATABASE_URL=postgres://... scripts/db-check.sh   # 기존 서버의 "빈" DB 사용
#   scripts/db-check.sh                                # 임시 클러스터를 띄워서 사용 (root 불가)
set -euo pipefail
cd "$(dirname "$0")/.."

run() {
  local url="$1"
  for f in db/schema.sql db/seed.sql db/sample.sql db/tests.sql; do
    echo "== $f"
    # tests.sql 은 결과 행 대신 NOTICE(ok/FAIL)만 보여준다
    if [[ "$f" == db/tests.sql ]]; then out=/dev/null; else out=/dev/stdout; fi
    psql "$url" -X -q -v ON_ERROR_STOP=1 -f "$f" -o "$out" 2>&1 | sed 's/^psql:[^ ]* NOTICE:  //' 
  done
}

if [[ -n "${DATABASE_URL:-}" ]]; then
  run "$DATABASE_URL"
  exit 0
fi

PG_BIN="${PG_BIN:-$(dirname "$(command -v initdb 2>/dev/null || ls /usr/lib/postgresql/*/bin/initdb | tail -1)")}"
tmp="$(mktemp -d)"
trap '"$PG_BIN/pg_ctl" -D "$tmp/data" -m immediate stop >/dev/null 2>&1 || true; rm -rf "$tmp"' EXIT
"$PG_BIN/initdb" -D "$tmp/data" -U postgres -A trust -E UTF8 --locale=C.UTF-8 >/dev/null
"$PG_BIN/pg_ctl" -D "$tmp/data" -o "-k $tmp -c listen_addresses=''" -l "$tmp/log" -w start >/dev/null
run "postgresql:///postgres?host=$tmp&user=postgres"
