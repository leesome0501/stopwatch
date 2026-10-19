"""데이터베이스 마이그레이션: db/migrations/NNNN_*.sql 을 번호 순서로, 아직 적용 안 된 것만 적용한다.

    uv run python -m assethub.migrate

파일 하나 = 트랜잭션 하나. 실패하면 그 파일은 통째로 취소되고 이후 파일은 적용하지 않는다.
여러 프로세스가 동시에 돌려도 advisory lock 으로 한 번만 적용된다.
"""
from __future__ import annotations

import re
import sys
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

import psycopg

from .config import DB_DIR, load_settings

MIGRATIONS_DIR = DB_DIR / "migrations"
NAME = re.compile(r"^(\d{4})_[a-z0-9_]+\.sql$")
LOCK_KEY = 0x41535345   # 'ASSE'
# 마이그레이션 장치 이전에 db/schema.sql(+seed.sql) 로 만든 DB 는 이 둘이 적용된 상태다
BASELINE = ("0001", "0002")


class MigrationError(RuntimeError):
    pass


@dataclass(frozen=True)
class Migration:
    version: str
    name: str
    path: Path


def available(directory: Path = MIGRATIONS_DIR) -> list[Migration]:
    found = []
    for p in sorted(directory.glob("*.sql")):
        m = NAME.match(p.name)
        if not m:
            raise MigrationError(f"마이그레이션 파일 이름이 규칙에 맞지 않습니다: {p.name} (NNNN_설명.sql)")
        found.append(Migration(m.group(1), p.stem, p))
    versions = [m.version for m in found]
    if len(set(versions)) != len(versions):
        raise MigrationError(f"마이그레이션 번호가 겹칩니다: {versions}")
    return found


def applied(conn: psycopg.Connection) -> list[str]:
    if conn.execute("SELECT to_regclass('public.schema_migrations')").fetchone()[0] is None:
        return []
    return [r[0] for r in conn.execute("SELECT version FROM schema_migrations ORDER BY version").fetchall()]


def migrate(conn: psycopg.Connection, *, directory: Path = MIGRATIONS_DIR,
            log: Callable[[str], None] = print) -> list[str]:
    """적용한 버전 목록을 돌려준다. conn 은 autocommit 이어야 한다."""
    if not conn.autocommit:
        raise MigrationError("migrate() 에는 autocommit 연결이 필요합니다.")
    migrations = available(directory)
    conn.execute("SELECT pg_advisory_lock(%s)", (LOCK_KEY,))
    try:
        if conn.execute("SELECT to_regclass('public.schema_migrations')").fetchone()[0] is None:
            legacy = conn.execute("SELECT to_regclass('public.household')").fetchone()[0] is not None
            with conn.transaction():
                conn.execute("""CREATE TABLE schema_migrations (
                                    version    text PRIMARY KEY,
                                    name       text NOT NULL,
                                    applied_at timestamptz NOT NULL DEFAULT now())""")
                if legacy:
                    for m in migrations:
                        if m.version in BASELINE:
                            conn.execute("INSERT INTO schema_migrations (version, name) VALUES (%s, %s)",
                                         (m.version, m.name))
            if legacy:
                log("기존 데이터베이스를 확인했습니다 (기존 데이터는 그대로 둡니다).")
        done = set(applied(conn))
        unknown = done - {m.version for m in migrations}
        if unknown:
            raise MigrationError(f"코드에 없는 마이그레이션이 DB에 적용되어 있습니다: {sorted(unknown)}. "
                                 "코드를 최신으로 받으세요 (git pull).")
        newly: list[str] = []
        for m in migrations:
            if m.version in done:
                continue
            sql = m.path.read_text(encoding="utf-8")
            try:
                with conn.transaction():
                    conn.execute(sql)
                    conn.execute("INSERT INTO schema_migrations (version, name) VALUES (%s, %s)", (m.version, m.name))
            except psycopg.Error as e:
                raise MigrationError(f"{m.path.name} 적용 실패 (이 파일의 변경은 모두 취소됨): {e}") from e
            log(f"적용: {m.path.name}")
            newly.append(m.version)
        return newly
    finally:
        conn.execute("SELECT pg_advisory_unlock(%s)", (LOCK_KEY,))


def main() -> int:
    from .db import utf8

    url = load_settings().database_url
    with psycopg.connect(utf8(url), autocommit=True) as conn:
        try:
            newly = migrate(conn)
        except MigrationError as e:
            print(f"오류: {e}")
            return 1
    print("새로 적용한 변경이 없습니다. 최신 상태입니다." if not newly else f"{len(newly)}개 변경을 적용했습니다.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
