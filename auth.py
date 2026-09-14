from pathlib import Path

import yaml

from config import USERS_FILE


def load_users():
    if not USERS_FILE.is_file():
        raise FileNotFoundError(f"Missing {USERS_FILE}")
    with USERS_FILE.open(encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def authenticate(username: str, password: str) -> dict | None:
    users = load_users()
    record = users.get(username.strip())
    if not record:
        return None
    if (record.get("password") or "") != password:
        return None
    role = record.get("role")
    if not role:
        return None
    return {"username": username.strip(), "role": role}
