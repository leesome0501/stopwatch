import shutil

import psycopg
import pytest

from assethub.migrate import MIGRATIONS_DIR, MigrationError, applied, migrate

quiet = dict(log=lambda m: None)


@pytest.fixture
def econn(empty_db_url):
    with psycopg.connect(empty_db_url, autocommit=True) as c:
        yield c


@pytest.fixture
def mdir(tmp_path):
    d = tmp_path / "migrations"
    shutil.copytree(MIGRATIONS_DIR, d)
    return d


def col_exists(conn, table, col):
    return conn.execute("SELECT 1 FROM information_schema.columns WHERE table_name = %s AND column_name = %s",
                        (table, col)).fetchone() is not None


def test_fresh_database_gets_everything_once(econn):
    assert migrate(econn, **quiet) == ["0001", "0002"]
    assert econn.execute("SELECT count(*) FROM institution").fetchone()[0] > 10
    assert migrate(econn, **quiet) == []
    assert applied(econn) == ["0001", "0002"]


def test_database_made_before_migrations_is_adopted(econn):
    # 예전 setup 처럼 schema.sql + seed.sql 을 직접 실행한 DB
    for name in ("0001_init.sql", "0002_seed.sql"):
        econn.execute((MIGRATIONS_DIR / name).read_text(encoding="utf-8"))
    econn.execute("INSERT INTO household (name) VALUES ('기존 데이터')")
    logs = []
    assert migrate(econn, log=logs.append) == []
    assert applied(econn) == ["0001", "0002"]
    assert econn.execute("SELECT name FROM household").fetchone()[0] == "기존 데이터"
    assert any("기존 데이터베이스" in m for m in logs)


def test_new_migration_applies_on_existing_data(econn, mdir):
    migrate(econn, directory=mdir, **quiet)
    econn.execute("INSERT INTO household (name) VALUES ('우리집')")
    (mdir / "0003_household_note.sql").write_text("ALTER TABLE household ADD COLUMN note text;\n", encoding="utf-8")
    assert migrate(econn, directory=mdir, **quiet) == ["0003"]
    assert col_exists(econn, "household", "note")
    assert econn.execute("SELECT name FROM household").fetchone()[0] == "우리집"


def test_failed_migration_is_rolled_back_entirely(econn, mdir):
    migrate(econn, directory=mdir, **quiet)
    (mdir / "0003_broken.sql").write_text(
        "ALTER TABLE household ADD COLUMN half_done text;\nSELECT 1 / 0;\n", encoding="utf-8")
    (mdir / "0004_after.sql").write_text("ALTER TABLE household ADD COLUMN later text;\n", encoding="utf-8")
    with pytest.raises(MigrationError, match="0003_broken.sql"):
        migrate(econn, directory=mdir, **quiet)
    assert not col_exists(econn, "household", "half_done")   # 구조 변경까지 취소
    assert not col_exists(econn, "household", "later")       # 뒤 파일은 적용하지 않음
    assert applied(econn) == ["0001", "0002"]


def test_bad_names_and_unknown_versions(econn, mdir):
    (mdir / "3_oops.sql").write_text("SELECT 1;", encoding="utf-8")
    with pytest.raises(MigrationError, match="이름"):
        migrate(econn, directory=mdir, **quiet)
    (mdir / "3_oops.sql").unlink()
    migrate(econn, directory=mdir, **quiet)
    econn.execute("INSERT INTO schema_migrations (version, name) VALUES ('0099', '0099_future')")
    with pytest.raises(MigrationError, match="git pull"):
        migrate(econn, directory=mdir, **quiet)


def test_requires_autocommit(empty_db_url):
    with psycopg.connect(empty_db_url) as c, pytest.raises(MigrationError, match="autocommit"):
        migrate(c, **quiet)


def test_server_start_applies_migrations(empty_db_url):
    from fastapi.testclient import TestClient

    from assethub.config import Settings
    from assethub.main import create_app

    with TestClient(create_app(Settings(database_url=empty_db_url))) as client:
        assert client.get("/api/households").json() == []
    with psycopg.connect(empty_db_url, autocommit=True) as c:
        assert applied(c) == ["0001", "0002"]
