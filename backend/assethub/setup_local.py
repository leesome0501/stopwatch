"""내 PC에 AssetHub 데이터베이스를 준비한다 (Windows setup.cmd 가 부른다).

  1. PostgreSQL 접속 정보를 묻고 접속을 확인한다
  2. assethub 데이터베이스가 없으면 만든다
  3. 테이블과 기본 데이터를 넣는다 (이미 있으면 건너뜀, 지우지 않는다)
  4. 원하면 예제 가구 데이터를 넣는다
  5. 접속 정보를 backend/.env 에 저장한다

    uv run python -m assethub.setup_local
    uv run python -m assethub.setup_local --password 비밀번호 --sample --yes   (묻지 않고 진행)
"""
from __future__ import annotations

import argparse
import getpass
import sys
from pathlib import Path
from urllib.parse import quote

import psycopg
from psycopg import sql

from .config import DB_DIR, ENV_FILE, read_env_file
from .db import apply_schema


def ask(prompt: str, default: str, yes: bool) -> str:
    if yes:
        return default
    value = input(f"{prompt} [{default}]: ").strip()
    return value or default


def confirm(prompt: str, default: bool, yes: bool) -> bool:
    if yes:
        return default
    value = input(f"{prompt} ({'Y/n' if default else 'y/N'}): ").strip().lower()
    return default if not value else value.startswith("y")


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="AssetHub 데이터베이스 준비")
    p.add_argument("--host", default="localhost")
    p.add_argument("--port", default="5432")
    p.add_argument("--user", default="postgres")
    p.add_argument("--password")
    p.add_argument("--dbname", default="assethub")
    p.add_argument("--sample", action="store_true", help="예제 가구 데이터도 넣는다")
    p.add_argument("--yes", action="store_true", help="묻지 않고 기본값으로 진행")
    p.add_argument("--env-file", type=Path, default=ENV_FILE)
    a = p.parse_args(argv)

    print("\n=== AssetHub 데이터베이스 준비 ===\n")
    existing = read_env_file(a.env_file).get("DATABASE_URL")
    if existing:
        print(f"{a.env_file} 에 저장된 접속 정보를 사용합니다.")
        url = existing
        info = psycopg.conninfo.conninfo_to_dict(url)
        admin_url = psycopg.conninfo.make_conninfo(url, dbname="postgres")
        dbname = info.get("dbname", a.dbname)
    else:
        host = ask("PostgreSQL 주소", a.host, a.yes)
        port = ask("포트", a.port, a.yes)
        user = ask("사용자", a.user, a.yes)
        password = a.password if a.password is not None else getpass.getpass(
            "비밀번호 (PostgreSQL 설치할 때 정한 것, 입력해도 화면에 안 보임): ")
        dbname = a.dbname
        url = f"postgresql://{quote(user, safe='')}:{quote(password, safe='')}@{host}:{port}/{quote(dbname, safe='')}"
        admin_url = psycopg.conninfo.make_conninfo(url, dbname="postgres")

    try:
        with psycopg.connect(admin_url, autocommit=True, connect_timeout=5) as conn:
            version = conn.execute("SHOW server_version").fetchone()[0]
            print(f"PostgreSQL {version} 에 접속했습니다.")
            if int(version.split(".")[0]) < 16:
                print("PostgreSQL 16 이상이 필요합니다. 새 버전을 설치해 주세요.")
                return 1
            exists = conn.execute("SELECT 1 FROM pg_database WHERE datname = %s", (dbname,)).fetchone()
            if exists:
                print(f"데이터베이스 '{dbname}' 가 이미 있습니다.")
            else:
                conn.execute(sql.SQL("CREATE DATABASE {} ENCODING 'UTF8' TEMPLATE template0")
                             .format(sql.Identifier(dbname)))
                print(f"데이터베이스 '{dbname}' 를 만들었습니다.")
    except psycopg.OperationalError as e:
        print("\nPostgreSQL 에 접속하지 못했습니다.")
        print("  - PostgreSQL 이 설치되어 있고 서비스가 실행 중인지 확인해 주세요.")
        print("    설치: winget install -e --id PostgreSQL.PostgreSQL.17 --interactive")
        print("    (설치 화면에서 정한 비밀번호를 여기서 입력합니다. 포트는 5432 그대로 두세요.)")
        print("  - 비밀번호가 맞는지 확인해 주세요 (설치할 때 정한 postgres 사용자 비밀번호).")
        print(f"  자세한 오류: {str(e).strip().splitlines()[0] if str(e).strip() else e}")
        return 1

    with psycopg.connect(url, autocommit=True) as conn:
        has_schema = conn.execute("SELECT to_regclass('public.household') IS NOT NULL").fetchone()[0]
        if has_schema:
            print("테이블이 이미 있어 건너뜁니다 (기존 데이터는 그대로 둡니다).")
        else:
            apply_schema(conn)
            print("테이블과 기본 데이터(금융기관, 카테고리)를 넣었습니다.")
            if a.sample or confirm("예제 가구 데이터(통장·증권·아파트 등)를 넣어 화면을 먼저 볼까요?", False, a.yes):
                conn.execute((DB_DIR / "sample.sql").read_text(encoding="utf-8"))
                print("예제 가구 데이터를 넣었습니다. 실제로 쓰실 때는 데이터베이스를 새로 만드세요.")

    if not existing:
        a.env_file.write_text(f"DATABASE_URL={url}\n", encoding="utf-8")
        print(f"접속 정보를 {a.env_file} 에 저장했습니다.")
    print("\n준비가 끝났습니다.\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
