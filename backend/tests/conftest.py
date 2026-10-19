from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
import uuid
from pathlib import Path

import psycopg
import pytest
from fastapi.testclient import TestClient
from psycopg.rows import dict_row

from assethub.config import Settings
from assethub.db import apply_schema
from assethub.main import create_app

TEMPLATE_DB = "assethub_test_template"


def _start_temp_cluster(tmp: Path) -> str:
    initdb = shutil.which("initdb") or next(iter(sorted(Path("/usr/lib/postgresql").glob("*/bin/initdb"))), None)
    if initdb is None:
        pytest.skip("PostgreSQL 이 없어 DB 테스트를 건너뜁니다 (TEST_DATABASE_URL 로 지정 가능).")
    bindir = Path(initdb).parent
    subprocess.run([bindir / "initdb", "-D", tmp / "data", "-U", "postgres", "-A", "trust", "-E", "UTF8",
                    "--locale=C.UTF-8"], check=True, capture_output=True)
    subprocess.run([bindir / "pg_ctl", "-D", tmp / "data", "-o", f"-k {tmp} -c listen_addresses=''",
                    "-l", tmp / "log", "-w", "start"], check=True, capture_output=True)
    return f"postgresql:///postgres?host={tmp}&user=postgres"


@pytest.fixture(scope="session")
def admin_url():
    """TEST_DATABASE_URL (CREATE DATABASE 권한 필요) 이 있으면 쓰고, 없으면 임시 클러스터를 띄운다."""
    url = os.environ.get("TEST_DATABASE_URL")
    tmp = None
    if not url:
        if hasattr(os, "geteuid") and os.geteuid() == 0:
            pytest.skip("root 로는 임시 PostgreSQL 을 띄울 수 없습니다. TEST_DATABASE_URL 을 지정하세요.")
        tmp = Path(tempfile.mkdtemp(prefix="assethub-pg-"))
        url = _start_temp_cluster(tmp)
    with psycopg.connect(url, autocommit=True) as c:
        c.execute(f"DROP DATABASE IF EXISTS {TEMPLATE_DB}")
        c.execute(f"CREATE DATABASE {TEMPLATE_DB}")
    with psycopg.connect(_with_db(url, TEMPLATE_DB), autocommit=True) as c:
        apply_schema(c)
    yield url
    with psycopg.connect(url, autocommit=True) as c:
        c.execute(f"DROP DATABASE IF EXISTS {TEMPLATE_DB}")
    if tmp:
        bindir = Path(shutil.which("pg_ctl") or next(iter(sorted(Path("/usr/lib/postgresql").glob("*/bin/pg_ctl"))))).parent
        subprocess.run([bindir / "pg_ctl", "-D", tmp / "data", "-m", "immediate", "stop"], capture_output=True)
        shutil.rmtree(tmp, ignore_errors=True)


def _with_db(url: str, dbname: str) -> str:
    return psycopg.conninfo.make_conninfo(url, dbname=dbname)


@pytest.fixture
def db_url(admin_url):
    name = f"assethub_t_{uuid.uuid4().hex[:10]}"
    with psycopg.connect(admin_url, autocommit=True) as c:
        c.execute(f"CREATE DATABASE {name} TEMPLATE {TEMPLATE_DB}")
    yield _with_db(admin_url, name)
    with psycopg.connect(admin_url, autocommit=True) as c:
        c.execute(f"DROP DATABASE IF EXISTS {name} WITH (FORCE)")


@pytest.fixture
def client(db_url):
    with TestClient(create_app(Settings(database_url=db_url))) as c:
        yield c


@pytest.fixture
def conn(db_url):
    with psycopg.connect(db_url, row_factory=dict_row, autocommit=True) as c:
        yield c
