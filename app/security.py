import ipaddress
import secrets
import time
from collections import defaultdict, deque

from fastapi import HTTPException, Request
from starlette.middleware.base import BaseHTTPMiddleware

CSRF_COOKIE = "csrf_token"
_hits = defaultdict(deque)


def _client_ip(request: Request):
    host = request.client.host if request.client else None
    try:
        addr = ipaddress.ip_address(host)
    except (ValueError, TypeError):
        return None
    if addr.version == 6 and addr.ipv4_mapped:
        addr = addr.ipv4_mapped
    return addr


def is_loopback(request: Request) -> bool:
    addr = _client_ip(request)
    return bool(addr and addr.is_loopback)


def require_loopback(request: Request) -> None:
    """Dependency: issuer and demo routes are only for the local machine.
    This is access restriction by network location, NOT authentication."""
    if not is_loopback(request):
        raise HTTPException(status_code=403, detail="issuer_local_only")


def get_csrf_token(request: Request) -> str:
    return request.cookies.get(CSRF_COOKIE) or secrets.token_urlsafe(32)


def set_csrf_cookie(response, token: str) -> None:
    response.set_cookie(CSRF_COOKIE, token, httponly=False, samesite="strict", path="/")


def _is_allowed_origin(origin_str: str, request: Request) -> bool:
    if not origin_str or origin_str == "null":
        return True

    origin_str = origin_str.strip().rstrip("/")
    host_header = request.headers.get("host", "").strip().lower()

    # 1. Direct match with scheme://host
    if origin_str.endswith("://" + host_header):
        return True

    # 2. Match with request.base_url
    req_base = str(request.base_url).strip().rstrip("/").lower()
    if origin_str.lower() == req_base:
        return True

    # 3. Match with settings.base_url
    from app.config import settings
    setting_base = settings.base_url.strip().rstrip("/").lower()
    if origin_str.lower() == setting_base:
        return True

    # 4. Loopback equivalence (localhost, 127.0.0.1, [::1])
    try:
        from urllib.parse import urlsplit
        parsed_origin = urlsplit(origin_str)
        origin_hostname = (parsed_origin.hostname or "").lower()
        origin_port = parsed_origin.port

        parsed_host = urlsplit(f"//{host_header}")
        req_hostname = (parsed_host.hostname or "").lower()
        req_port = parsed_host.port

        loopback_hosts = {"localhost", "127.0.0.1", "::1"}
        if origin_hostname in loopback_hosts and req_hostname in loopback_hosts:
            if origin_port == req_port or origin_port is None or req_port is None:
                return True
    except Exception:
        pass

    return False


def check_csrf(request: Request, submitted: str | None) -> None:
    cookie = request.cookies.get(CSRF_COOKIE)
    if not cookie or not submitted or not secrets.compare_digest(cookie, submitted):
        raise HTTPException(status_code=403, detail="csrf_failed")
    origin = request.headers.get("origin")
    if origin:
        if not _is_allowed_origin(origin, request):
            raise HTTPException(status_code=403, detail="origin_mismatch")


def rate_limit(request: Request, limit: int = 30, window: int = 60) -> None:
    key = str(_client_ip(request) or "unknown")
    now = time.time()
    q = _hits[key]
    while q and now - q[0] > window:
        q.popleft()
    if len(q) >= limit:
        raise HTTPException(status_code=429, detail="rate_limited")
    q.append(now)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; img-src 'self' data:; style-src 'self'; "
            "script-src 'self'; frame-ancestors 'none'; base-uri 'self'; form-action 'self'"
        )
        return response
