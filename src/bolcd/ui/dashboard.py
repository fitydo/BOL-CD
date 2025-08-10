from __future__ import annotations

from fastapi import APIRouter

router = APIRouter()


@router.get("/dashboard")
def dashboard() -> str:
    # Minimal stub HTML; future: D3 visualization reading /api/graph
    return """
<!doctype html>
<html><head><title>BOL-CD Dashboard</title></head>
<body>
<h1>BOL-CD Dashboard</h1>
<p>Union graph: <a href='/api/graph'>/api/graph</a></p>
<p>Metrics: <a href='/metrics'>/metrics</a></p>
<p>Audit: <a href='/api/audit'>/api/audit</a></p>
</body></html>
"""

