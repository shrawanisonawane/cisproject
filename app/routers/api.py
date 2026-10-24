from typing import Any
from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response
from pydantic import ValidationError

from app.crypto import keys as keylib
from app.db import db
from app.security import check_csrf, rate_limit, require_loopback
from app.services.issuance import CertificateIn, issue_certificate, list_certificates
from app.services.revocation import revoke_certificate
from app.services.verification import BundleFormatError, verify_bundle, verify_by_id

router = APIRouter()


# --- Public API routes ---

@router.get("/api/health")
def api_health():
    return {"status": "ok"}


@router.get("/api/public-key")
def api_public_key(request: Request):
    pub = request.app.state.public_key
    return {
        "pem": keylib.public_key_pem(pub),
        "key_id": keylib.key_id(pub),
        "fingerprint": keylib.fingerprint_colon(pub),
        "algorithm": "RSASSA-PSS/SHA-256/MGF1-SHA-256/salt32",
    }


@router.get("/api/verify/{certificate_id}")
def api_verify_id(request: Request, certificate_id: str):
    rate_limit(request)
    with db() as conn:
        res = verify_by_id(
            conn, certificate_id, request.app.state.public_key, method="API"
        )
        return res.to_dict()


@router.post("/api/verify/bundle")
async def api_verify_bundle(request: Request):
    rate_limit(request)
    try:
        bundle = await request.json()
    except Exception:
        raise HTTPException(
            status_code=422,
            detail={"error_code": "bad_bundle", "message": "Invalid JSON body"},
        )

    with db() as conn:
        try:
            res = verify_bundle(
                conn, bundle, request.app.state.public_key, method="API_BUNDLE"
            )
            return res.to_dict()
        except BundleFormatError as exc:
            raise HTTPException(
                status_code=422,
                detail={"error_code": "bad_bundle", "message": str(exc)},
            )


# --- Issuer API routes (Loopback + CSRF on state changes) ---

def _require_api_csrf(request: Request):
    token = request.headers.get("X-CSRF-Token")
    check_csrf(request, token)


@router.get("/api/certificates", dependencies=[Depends(require_loopback)])
def api_list_certificates(
    q: str | None = Query(default=None),
    status: str = Query(default="all"),
    program: str | None = Query(default=None),
    sort: str = Query(default="issue_date_desc"),
):
    with db() as conn:
        certs = list_certificates(conn, q=q, status=status, program=program, sort=sort)
        return certs


@router.post(
    "/api/certificates",
    status_code=201,
    dependencies=[Depends(require_loopback), Depends(_require_api_csrf)],
)
async def api_issue_certificate(request: Request):
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(
            status_code=422,
            detail={"error_code": "bad_request", "message": "Invalid JSON body"},
        )

    try:
        cert_in = CertificateIn(**body)
    except ValidationError as exc:
        raise HTTPException(
            status_code=422,
            detail={"error_code": "validation_error", "message": str(exc)},
        )

    with db() as conn:
        row = issue_certificate(
            conn,
            cert_in,
            request.app.state.private_key,
            request.app.state.public_key,
        )
        return row


@router.post(
    "/api/certificates/{certificate_id}/revoke",
    dependencies=[Depends(require_loopback), Depends(_require_api_csrf)],
)
async def api_revoke_certificate(request: Request, certificate_id: str):
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(
            status_code=422,
            detail={"error_code": "bad_request", "message": "Invalid JSON body"},
        )

    reason = body.get("reason", "")
    with db() as conn:
        try:
            revoke_certificate(conn, certificate_id, reason)
            return {"status": "revoked", "certificate_id": certificate_id}
        except LookupError as exc:
            raise HTTPException(
                status_code=404,
                detail={"error_code": "not_found", "message": str(exc)},
            )
        except FileExistsError as exc:
            raise HTTPException(
                status_code=409,
                detail={"error_code": "already_revoked", "message": str(exc)},
            )
        except ValueError as exc:
            raise HTTPException(
                status_code=422,
                detail={"error_code": "bad_request", "message": str(exc)},
            )
