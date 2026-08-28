"""SQLite-backed session vault."""

import sqlite3
import time
import threading
from typing import Dict, Optional
from contextlib import contextmanager


class SessionVault:
    def __init__(self, db_path: str = ":memory:"):
        self._db = db_path
        self._lock = threading.RLock()
        self._init_db()

    def _init_db(self):
        with self._connect() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS cookies (
                    domain TEXT NOT NULL,
                    name TEXT NOT NULL,
                    value TEXT,
                    path TEXT DEFAULT '/',
                    expires INTEGER,
                    secure INTEGER DEFAULT 0,
                    http_only INTEGER DEFAULT 0,
                    created_at INTEGER DEFAULT (unixepoch()),
                    PRIMARY KEY (domain, name)
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS tokens (
                    domain TEXT NOT NULL,
                    token_type TEXT NOT NULL,
                    token_value TEXT,
                    expires INTEGER,
                    created_at INTEGER DEFAULT (unixepoch()),
                    PRIMARY KEY (domain, token_type)
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_cookies_domain ON cookies(domain)")
            conn.commit()

    @contextmanager
    def _connect(self):
        conn = sqlite3.connect(self._db, check_same_thread=False)
        try:
            yield conn
        finally:
            conn.close()

    def get_cookies(self, domain: str) -> Dict[str, str]:
        with self._lock:
            with self._connect() as conn:
                cursor = conn.execute(
                    "SELECT name, value FROM cookies WHERE domain = ? AND (expires > ? OR expires IS NULL)",
                    (domain, int(time.time()))
                )
                return {row[0]: row[1] for row in cursor.fetchall()}

    def set_cookie(self, domain: str, name: str, value: str,
                   path: str = "/", expires: Optional[int] = None,
                   secure: bool = False, http_only: bool = False):
        with self._lock:
            with self._connect() as conn:
                conn.execute(
                    "INSERT OR REPLACE INTO cookies (domain, name, value, path, expires, secure, http_only) VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (domain, name, value, path, expires, int(secure), int(http_only))
                )
                conn.commit()

    def set_cookies_dict(self, domain: str, cookies: Dict[str, str], expires: Optional[int] = None):
        for name, value in cookies.items():
            self.set_cookie(domain, name, value, expires=expires)

    def get_token(self, domain: str, token_type: str) -> Optional[str]:
        with self._lock:
            with self._connect() as conn:
                cursor = conn.execute(
                    "SELECT token_value FROM tokens WHERE domain = ? AND token_type = ? AND (expires > ? OR expires IS NULL)",
                    (domain, token_type, int(time.time()))
                )
                row = cursor.fetchone()
                return row[0] if row else None

    def set_token(self, domain: str, token_type: str, value: str, expires: Optional[int] = None):
        with self._lock:
            with self._connect() as conn:
                conn.execute(
                    "INSERT OR REPLACE INTO tokens (domain, token_type, token_value, expires) VALUES (?, ?, ?, ?)",
                    (domain, token_type, value, expires)
                )
                conn.commit()

    def clear_domain(self, domain: str):
        with self._lock:
            with self._connect() as conn:
                conn.execute("DELETE FROM cookies WHERE domain = ?", (domain,))
                conn.execute("DELETE FROM tokens WHERE domain = ?", (domain,))
                conn.commit()

    def stats(self) -> Dict[str, int]:
        with self._lock:
            with self._connect() as conn:
                cookie_count = conn.execute("SELECT COUNT(*) FROM cookies").fetchone()[0]
                token_count = conn.execute("SELECT COUNT(*) FROM tokens").fetchone()[0]
                return {"cookies": cookie_count, "tokens": token_count}
