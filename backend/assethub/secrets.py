"""증권사 앱키처럼 민감한 값을 DB에 넣기 전에 암호화한다.

암호화 키(ASSETHUB_SECRET_KEY)는 DB가 아니라 backend/.env 에 둔다. DB만 유출돼도 키가 없으면 풀 수 없다.
키가 없으면 처음 쓸 때 만들어 .env 에 적는다. .env 를 잃어버리면 저장된 앱키를 다시 입력해야 한다.
"""
from __future__ import annotations

import json
import os

from cryptography.fernet import Fernet, InvalidToken

from .config import ENV_FILE, read_env_file

ENV_NAME = "ASSETHUB_SECRET_KEY"


class SecretError(RuntimeError):
    pass


def _key() -> bytes:
    key = os.environ.get(ENV_NAME) or read_env_file().get(ENV_NAME)
    if not key:
        key = Fernet.generate_key().decode()
        ENV_FILE.parent.mkdir(parents=True, exist_ok=True)
        existing = ENV_FILE.read_text(encoding="utf-8") if ENV_FILE.exists() else ""
        sep = "" if not existing or existing.endswith("\n") else "\n"
        ENV_FILE.write_text(f"{existing}{sep}{ENV_NAME}={key}\n", encoding="utf-8")
        os.environ[ENV_NAME] = key
    return key.encode()


def encrypt_json(value: dict) -> bytes:
    return Fernet(_key()).encrypt(json.dumps(value, ensure_ascii=False).encode())


def decrypt_json(token: bytes | memoryview | None) -> dict:
    if token is None:
        return {}
    try:
        return json.loads(Fernet(_key()).decrypt(bytes(token)))
    except InvalidToken as e:
        raise SecretError("저장된 인증정보를 풀 수 없습니다. backend/.env 의 암호화 키가 바뀌었다면 앱키를 다시 입력하세요.") from e
