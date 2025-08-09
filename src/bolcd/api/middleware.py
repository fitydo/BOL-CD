from __future__ import annotations

import os
import time
import uuid

from fastapi import FastAPI, Header, HTTPException, Request
from pythonjsonlogger import jsonlogger
import logging

ROLES = {"viewer", "operator", "admin"}


def setup_json_logging() -> None:
    handler = logging.StreamHandler()
    formatter = jsonlogger.JsonFormatter("%(asctime)s %(levelname)s %(message)s")
    handler.setFormatter(formatter)
    root = logging.getLogger()
    root.setLevel(logging.INFO)
    if not any(isinstance(h, logging.StreamHandler) for h in root.handlers):
        root.addHandler(handler)


def get_role_for_key(api_key: str | None) -> str | None:
    if not api_key:
        return None
    mapping = os.getenv("BOLCD_API_KEYS", "")
    for item in mapping.split(","):
        item = item.strip()
        if not item or ":" not in item:
            continue
        k, r = item.split(":", 1)
        if api_key == k and r in ROLES:
            return r
    return None


def verify_role(required: str):
    order = {"viewer": 0, "operator": 1, "admin": 2}

    async def dependency(request: Request, x_api_key: str | None = Header(default=None)) -> None:
        mapping = os.getenv("BOLCD_API_KEYS", "")
        if mapping.strip() == "":
            return None
        role = get_role_for_key(x_api_key)
        if role is None or order[role] < order[required]:
            raise HTTPException(status_code=403, detail="forbidden")
        return None

    return dependency


def install_middlewares(app: FastAPI) -> None:
    setup_json_logging()

    @app.middleware("http")
    async def add_request_id_and_log(request: Request, call_next):
        req_id = request.headers.get("X-Request-Id") or str(uuid.uuid4())
        start = time.perf_counter()
        response = await call_next(request)
        elapsed_ms = (time.perf_counter() - start) * 1000.0
        response.headers["X-Request-Id"] = req_id
        logging.info(
            "request",
            extra={
                "request_id": req_id,
                "method": request.method,
                "path": request.url.path,
                "status": response.status_code,
                "latency_ms": round(elapsed_ms, 2),
            },
        )
        return response
