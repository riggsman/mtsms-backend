"""Parse MySQL host/credentials from DATABASE_URL for Docker/VPS (hostname ``db``)."""
from __future__ import annotations

import os
from urllib.parse import urlparse


def _normalize_sqlalchemy_url(url: str) -> str:
    if url.startswith("mysql+pymysql://"):
        return "mysql://" + url[len("mysql+pymysql://") :]
    if url.startswith("mysql+mysqlconnector://"):
        return "mysql://" + url[len("mysql+mysqlconnector://") :]
    return url


def get_mysql_params() -> dict:
    """
    Connection params for raw mysql.connector / tenant DB provisioning.
    Honors MYSQL_HOST if set; otherwise uses hostname from DATABASE_URL.
    """
    url = os.getenv("DATABASE_URL", "mysql+pymysql://root@localhost:3306/mtsms")
    parsed = urlparse(_normalize_sqlalchemy_url(url))
    host = os.getenv("MYSQL_HOST") or parsed.hostname or "localhost"
    port = int(os.getenv("MYSQL_PORT") or parsed.port or 3306)
    user = os.getenv("MYSQL_USER") or parsed.username or "root"
    password = os.getenv("MYSQL_PASSWORD")
    if password is None:
        password = parsed.password or ""
    return {
        "host": host,
        "port": port,
        "user": user,
        "password": password,
    }


def build_tenant_database_url(database_name: str) -> str:
    p = get_mysql_params()
    return (
        f"mysql+pymysql://{p['user']}:{p['password']}@{p['host']}:{p['port']}/{database_name}"
    )
