from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, asdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List


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


