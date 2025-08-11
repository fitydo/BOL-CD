from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, asdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Dict, List
import threading


@dataclass
class AuditEntry:
    ts: str
    actor: str
    action: str
    diff: Dict[str, Any]
    hash: str


class JSONLAuditStore:
    """A very small persistent audit store using JSONL on disk.

    Each call to append() writes one line JSON object with an integrity hash
    computed over {ts, actor, action, diff} using SHA256.
    """

    def __init__(self, path: Path) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            self.path.touch()

    def _compute_hash(self, payload: Dict[str, Any]) -> str:
        blob = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
        return hashlib.sha256(blob).hexdigest()

    def append(self, actor: str, action: str, diff: Dict[str, Any]) -> AuditEntry:
        base = {
            "ts": datetime.now(UTC).isoformat(),
            "actor": actor,
            "action": action,
            "diff": diff,
        }
        h = self._compute_hash(base)
        entry = AuditEntry(hash=h, **base)  # type: ignore[arg-type]
        with self.path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(asdict(entry), ensure_ascii=False) + "\n")
        return entry

    def tail(self, limit: int = 100) -> List[Dict[str, Any]]:
        if limit <= 0:
            return []
        # Simple tail without loading whole file for typical small CI/demo sizes
        lines: List[str] = []
        try:
            with self.path.open("r", encoding="utf-8") as f:
                for line in f:
                    lines.append(line)
                    if len(lines) > limit:
                        lines.pop(0)
        except FileNotFoundError:
            return []
        out: List[Dict[str, Any]] = []
        for line in lines[-limit:]:
            line = line.strip()
            if not line:
                continue
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError:
                continue
        return out


class SQLiteAuditStore:
    """SQLite-based audit store with simple schema and integrity hash.

    Schema:
      CREATE TABLE IF NOT EXISTS audit(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        ts TEXT NOT NULL,
        actor TEXT NOT NULL,
        action TEXT NOT NULL,
        diff TEXT NOT NULL,
        hash TEXT NOT NULL
      );
    """

    def __init__(self, path: Path) -> None:
        import sqlite3

        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        # Allow usage across threads in TestClient / ASGI; guard with a lock
        self._db = sqlite3.connect(str(self.path), check_same_thread=False)
        try:
            self._db.execute("PRAGMA journal_mode=WAL;")
        except Exception:
            pass
        self._lock = threading.Lock()
        self._db.execute(
            """
            CREATE TABLE IF NOT EXISTS audit(
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              ts TEXT NOT NULL,
              actor TEXT NOT NULL,
              action TEXT NOT NULL,
              diff TEXT NOT NULL,
              hash TEXT NOT NULL
            )
            """
        )
        self._db.commit()

    def _compute_hash(self, payload: Dict[str, Any]) -> str:
        blob = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
        return hashlib.sha256(blob).hexdigest()

    def append(self, actor: str, action: str, diff: Dict[str, Any]) -> AuditEntry:
        base = {
            "ts": datetime.now(UTC).isoformat(),
            "actor": actor,
            "action": action,
            "diff": diff,
        }
        h = self._compute_hash(base)
        entry = AuditEntry(hash=h, **base)  # type: ignore[arg-type]
        with self._lock:
            self._db.execute(
                "INSERT INTO audit(ts,actor,action,diff,hash) VALUES (?,?,?,?,?)",
                (entry.ts, entry.actor, entry.action, json.dumps(entry.diff, ensure_ascii=False), entry.hash),
            )
            self._db.commit()
        return entry

    def tail(self, limit: int = 100) -> List[Dict[str, Any]]:
        with self._lock:
            cur = self._db.execute(
                "SELECT ts,actor,action,diff,hash FROM audit ORDER BY id DESC LIMIT ?",
                (max(0, limit),),
            )
            rows = cur.fetchall()
        out: List[Dict[str, Any]] = []
        for ts, actor, action, diff_txt, h in rows:
            try:
                diff = json.loads(diff_txt)
            except Exception:
                diff = {"raw": diff_txt}
            out.append({"ts": ts, "actor": actor, "action": action, "diff": diff, "hash": h})
        return out


