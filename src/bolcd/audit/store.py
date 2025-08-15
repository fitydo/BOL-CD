from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, asdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
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
            # add hash-chain pointer into diff for immutability checks
            "diff": self._with_prev_hash_in_diff(diff),
        }
        h = self._compute_hash(base)
        entry = AuditEntry(hash=h, **base)  # type: ignore[arg-type]
        with self.path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(asdict(entry), ensure_ascii=False) + "\n")
        return entry

    def _with_prev_hash_in_diff(self, diff: Dict[str, Any]) -> Dict[str, Any]:
        # Read last non-empty JSON line to get previous hash if available
        prev_hash: str | None = None
        try:
            with self.path.open("r", encoding="utf-8") as f:
                last = ""
                for line in f:
                    if line.strip():
                        last = line
                if last:
                    payload = json.loads(last)
                    prev_hash = payload.get("hash")
        except Exception:
            prev_hash = None
        out = dict(diff)
        if prev_hash and "_prev" not in out:
            out["_prev"] = prev_hash
        return out

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

    def verify_chain(self, limit: Optional[int] = None) -> Dict[str, Any]:
        """Verify hash chain integrity.
        Checks that each entry hash matches recomputation and that diff._prev
        links to previous entry's hash. If limit is provided, checks only last N.
        """
        entries: List[Dict[str, Any]] = []
        try:
            with self.path.open("r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        entries.append(json.loads(line))
                    except Exception:
                        continue
        except FileNotFoundError:
            return {"ok": True, "entries": 0}
        if limit is not None and limit > 0:
            entries = entries[-limit:]
        prev_hash: Optional[str] = None
        for idx, e in enumerate(entries):
            base = {k: e[k] for k in ("ts", "actor", "action", "diff") if k in e}
            h = self._compute_hash(base)
            if h != e.get("hash"):
                return {"ok": False, "entries": idx + 1, "failure_index": idx, "reason": "hash_mismatch"}
            d = e.get("diff", {})
            link = d.get("_prev") if isinstance(d, dict) else None
            if prev_hash and link != prev_hash:
                return {"ok": False, "entries": idx + 1, "failure_index": idx, "reason": "prev_link_mismatch"}
            prev_hash = e.get("hash")
        return {"ok": True, "entries": len(entries), "last_hash": prev_hash}


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
            "diff": self._with_prev_hash_in_diff(diff),
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

    def _with_prev_hash_in_diff(self, diff: Dict[str, Any]) -> Dict[str, Any]:
        prev_hash: str | None = None
        try:
            with self._lock:
                cur = self._db.execute("SELECT hash FROM audit ORDER BY id DESC LIMIT 1")
                row = cur.fetchone()
                if row:
                    prev_hash = row[0]
        except Exception:
            prev_hash = None
        out = dict(diff)
        if prev_hash and "_prev" not in out:
            out["_prev"] = prev_hash
        return out

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

    def verify_chain(self, limit: Optional[int] = None) -> Dict[str, Any]:
        with self._lock:
            cur = self._db.execute(
                "SELECT ts,actor,action,diff,hash FROM audit ORDER BY id ASC"
            )
            rows = cur.fetchall()
        if limit is not None and limit > 0:
            rows = rows[-limit:]
        prev_hash: Optional[str] = None
        for idx, (ts, actor, action, diff_txt, h) in enumerate(rows):
            try:
                diff = json.loads(diff_txt)
            except Exception:
                diff = {"raw": diff_txt}
            base = {"ts": ts, "actor": actor, "action": action, "diff": diff}
            recomputed = self._compute_hash(base)
            if recomputed != h:
                return {"ok": False, "entries": idx + 1, "failure_index": idx, "reason": "hash_mismatch"}
            link = diff.get("_prev") if isinstance(diff, dict) else None
            if prev_hash and link != prev_hash:
                return {"ok": False, "entries": idx + 1, "failure_index": idx, "reason": "prev_link_mismatch"}
            prev_hash = h
        return {"ok": True, "entries": len(rows), "last_hash": prev_hash}


