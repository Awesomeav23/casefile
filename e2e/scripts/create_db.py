"""Create the E2E database named in DATABASE_URL if it doesn't exist yet."""

import os
from urllib.parse import urlparse

import psycopg
from psycopg import sql

url = urlparse(os.environ["DATABASE_URL"])
name = url.path.lstrip("/")
admin = url._replace(path="/postgres").geturl()
with psycopg.connect(admin, autocommit=True) as conn:
    exists = conn.execute(
        "SELECT 1 FROM pg_database WHERE datname = %s", (name,)
    ).fetchone()
    if not exists:
        conn.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(name)))
        print(f"created database {name}")
