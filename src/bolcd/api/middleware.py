from __future__ import annotations

import os
import time
import uuid

from fastapi import FastAPI, Header, HTTPException, Request
from typing import Optional
import jwt
from pythonjsonlogger import jsonlogger
import logging

ROLES = {"viewer", "operator", "admin"}
OIDC_AUDIENCE = os.getenv("BOLCD_OIDC_AUD")
OIDC_ISSUER = os.getenv("BOLCD_OIDC_ISS")
OIDC_JWKS_URL = os.getenv("BOLCD_OIDC_JWKS")
OIDC_ENABLED = bool(OIDC_AUDIENCE and OIDC_ISSUER and OIDC_JWKS_URL)
_JWKS_CACHE: dict | None = None


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


def _fetch_jwks() -> dict:
    import json as _json
    import urllib.request as _http
    global _JWKS_CACHE
    if _JWKS_CACHE is not None:
        return _JWKS_CACHE
    with _http.urlopen(OIDC_JWKS_URL, timeout=10) as r:  # type: ignore[arg-type]
        data = _json.loads(r.read().decode("utf-8"))
    _JWKS_CACHE = data
    return data


def _get_public_key(token: str) -> Optional[str]:
    try:
        unverified = jwt.get_unverified_header(token)
        kid = unverified.get("kid")
        if not kid:
            return None
        jwks = _fetch_jwks()
        for k in jwks.get("keys", []):
            if k.get("kid") == kid:
                from jwt.algorithms import RSAAlgorithm
                return RSAAlgorithm.from_jwk(k)
    except Exception:
        return None
    return None


def verify_role(required: str):
    order = {"viewer": 0, "operator": 1, "admin": 2}

    async def dependency(request: Request, x_api_key: str | None = Header(default=None), authorization: str | None = Header(default=None)) -> None:
        mapping = os.getenv("BOLCD_API_KEYS", "").strip()
        # Prefer OIDC when configured
        if OIDC_ENABLED and authorization and authorization.startswith("Bearer "):
            token = authorization.split(" ", 1)[1]
            try:
                pub = _get_public_key(token)
                payload = jwt.decode(
                    token,
                    key=pub,
                    algorithms=["RS256", "RS384", "RS512"],
                    audience=OIDC_AUDIENCE,
                    options={"require": ["exp", "iat", "aud", "iss"]},
                )
                if payload.get("iss") != OIDC_ISSUER:
                    raise HTTPException(status_code=403, detail="forbidden")
                role = payload.get("role") or payload.get("x-bolcd-role") or "viewer"
                if role not in ROLES or order[role] < order[required]:
                    raise HTTPException(status_code=403, detail="forbidden")
                return None
            except Exception:
                raise HTTPException(status_code=403, detail="forbidden")
        # API key path
        if mapping == "":
            if not x_api_key:
                raise HTTPException(status_code=403, detail="forbidden")
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
