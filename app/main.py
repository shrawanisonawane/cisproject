from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.config import settings
from app.crypto import keys
from app.db import db, init_schema
from app.routers import api, demo, issuer, public
from app.security import SecurityHeadersMiddleware

APP_DIR = Path(__file__).resolve().parent


@asynccontextmanager
async def lifespan(app: FastAPI):
    with db() as conn:
        init_schema(conn)

    priv_path = settings.key_dir / "issuer_private.pem"
    pub_path = settings.key_dir / "issuer_public.pem"
    if not priv_path.exists() or not pub_path.exists():
        raise RuntimeError("Run: python scripts/generate_keys.py")

    app.state.private_key = keys.load_private_key(
        settings.key_dir, settings.key_passphrase
    )
    app.state.public_key = keys.load_public_key(settings.key_dir)
    yield


def create_app() -> FastAPI:
    application = FastAPI(
        title=settings.app_name,
        lifespan=lifespan,
    )

    application.add_middleware(SecurityHeadersMiddleware)

    static_dir = APP_DIR / "static"
    static_dir.mkdir(parents=True, exist_ok=True)
    application.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

    templates_dir = APP_DIR / "templates"
    templates_dir.mkdir(parents=True, exist_ok=True)
    application.state.templates = Jinja2Templates(directory=str(templates_dir))

    application.include_router(public.router)
    application.include_router(issuer.router)
    application.include_router(api.router)
    application.include_router(demo.router)

    @application.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException):
        accept = request.headers.get("accept", "")
        is_json = request.url.path.startswith("/api") or "application/json" in accept

        if isinstance(exc.detail, dict):
            error_code = exc.detail.get("error_code", "error")
            message = exc.detail.get("message", str(exc.detail))
        else:
            raw_detail = str(exc.detail)
            if exc.status_code == 403:
                error_code = raw_detail if raw_detail in {"issuer_local_only", "csrf_failed", "origin_mismatch"} else "forbidden"
                message = (
                    "Issuer routes are restricted to the local machine."
                    if error_code == "issuer_local_only"
                    else "CSRF token verification failed."
                    if error_code == "csrf_failed"
                    else "origin_mismatch: Cross-origin request blocked because the request origin does not match the server host."
                    if error_code == "origin_mismatch"
                    else raw_detail
                )
            elif exc.status_code == 404:
                error_code = "not_found"
                message = raw_detail
            elif exc.status_code == 413:
                error_code = "payload_too_large"
                message = raw_detail
            elif exc.status_code == 422:
                error_code = "validation_error"
                message = raw_detail
            elif exc.status_code == 429:
                error_code = "rate_limited"
                message = "Too many requests. Please slow down."
            else:
                error_code = "error"
                message = raw_detail

        if is_json:
            return JSONResponse(
                status_code=exc.status_code,
                content={"error_code": error_code, "message": message},
            )
        return request.app.state.templates.TemplateResponse(
            request,
            "error.html",
            {
                "status_code": exc.status_code,
                "error_code": error_code,
                "title": (
                    "Local access required"
                    if error_code == "issuer_local_only"
                    else f"Error {exc.status_code}"
                ),
                "message": (
                    "The issuer workspace is only available on the computer that runs this application."
                    if error_code == "issuer_local_only"
                    else message
                ),
            },
            status_code=exc.status_code,
        )

    @application.exception_handler(Exception)
    async def generic_exception_handler(request: Request, exc: Exception):
        accept = request.headers.get("accept", "")
        is_json = request.url.path.startswith("/api") or "application/json" in accept
        if is_json:
            return JSONResponse(
                status_code=500,
                content={"error_code": "internal_error", "message": "An internal server error occurred."},
            )
        return request.app.state.templates.TemplateResponse(
            request,
            "error.html",
            {
                "status_code": 500,
                "error_code": "internal_error",
                "title": "Internal Server Error",
                "message": "An internal server error occurred.",
            },
            status_code=500,
        )

    return application


app = create_app()
