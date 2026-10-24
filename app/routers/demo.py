import json
from fastapi import APIRouter, Depends, Form, HTTPException, Query, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from app.config import settings
from app.db import db
from app.security import check_csrf, get_csrf_token, require_loopback, set_csrf_cookie
from app.services.demo_tools import restore_original, tamper_field
from app.services.issuance import build_bundle
from app.services.verification import BundleFormatError, verify_bundle, verify_by_id


def require_demo_mode():
    if not settings.demo_mode:
        raise HTTPException(status_code=404, detail="demo_mode_disabled")


router = APIRouter(dependencies=[Depends(require_demo_mode), Depends(require_loopback)])


@router.get("/demo")
def demo_lab_view(request: Request, cert: str | None = Query(default=None)):
    with db() as conn:
        certs = conn.execute(
            "SELECT * FROM certificates ORDER BY issue_date DESC, certificate_id DESC"
        ).fetchall()
        certs_list = [dict(c) for c in certs]

        selected_cert = None
        if cert:
            for c in certs_list:
                if c["certificate_id"] == cert:
                    selected_cert = c
                    break
        if selected_cert is None and certs_list:
            selected_cert = certs_list[0]

        verification_result = None
        has_backup = False
        bundle_json = ""

        if selected_cert:
            cert_id = selected_cert["certificate_id"]
            verification_result = verify_by_id(
                conn, cert_id, request.app.state.public_key, method="ID"
            )
            has_backup = (
                conn.execute(
                    "SELECT 1 FROM demo_backups WHERE certificate_id = ?", (cert_id,)
                ).fetchone()
                is not None
            )
            bundle_obj = build_bundle(selected_cert)
            bundle_json = json.dumps(bundle_obj, indent=2)

    token = get_csrf_token(request)
    resp = request.app.state.templates.TemplateResponse(
        request,
        "demo.html",
        {
            "certificates": certs_list,
            "selected_cert": selected_cert,
            "verification_result": verification_result,
            "has_backup": has_backup,
            "bundle_json": bundle_json,
            "bundle_result": None,
            "csrf_token": token,
        },
    )
    set_csrf_cookie(resp, token)
    return resp


@router.post("/demo/tamper")
def demo_tamper_submit(
    request: Request,
    certificate_id: str = Form(...),
    field: str = Form(...),
    new_value: str = Form(...),
    recompute_hash: str | None = Form(default=None),
    csrf_token: str | None = Form(default=None),
):
    check_csrf(request, csrf_token)
    recompute_bool = recompute_hash in {"on", "true", "1", "yes"}

    with db() as conn:
        try:
            tamper_field(conn, certificate_id, field, new_value, recompute_bool)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc))
        except LookupError as exc:
            raise HTTPException(status_code=404, detail=str(exc))

    return RedirectResponse(f"/demo?cert={certificate_id}", status_code=303)


@router.post("/demo/restore")
def demo_restore_submit(
    request: Request,
    certificate_id: str = Form(...),
    csrf_token: str | None = Form(default=None),
):
    check_csrf(request, csrf_token)

    with db() as conn:
        try:
            restore_original(conn, certificate_id)
        except LookupError as exc:
            raise HTTPException(status_code=404, detail=str(exc))

    return RedirectResponse(f"/demo?cert={certificate_id}", status_code=303)


@router.post("/demo/bundle-check")
def demo_bundle_check_submit(
    request: Request,
    bundle_text: str = Form(...),
    csrf_token: str | None = Form(default=None),
):
    check_csrf(request, csrf_token)

    try:
        bundle_obj = json.loads(bundle_text)
    except Exception:
        raise HTTPException(status_code=422, detail="Invalid JSON in bundle")

    with db() as conn:
        certs = conn.execute(
            "SELECT * FROM certificates ORDER BY issue_date DESC, certificate_id DESC"
        ).fetchall()
        certs_list = [dict(c) for c in certs]

        cert_id_in_bundle = None
        if isinstance(bundle_obj, dict):
            payload = bundle_obj.get("payload")
            if isinstance(payload, dict):
                cert_id_in_bundle = payload.get("certificate_id")

        selected_cert = None
        if cert_id_in_bundle:
            for c in certs_list:
                if c["certificate_id"] == cert_id_in_bundle:
                    selected_cert = c
                    break
        if selected_cert is None and certs_list:
            selected_cert = certs_list[0]

        verification_result = None
        has_backup = False
        if selected_cert:
            cid = selected_cert["certificate_id"]
            verification_result = verify_by_id(
                conn, cid, request.app.state.public_key, method="ID"
            )
            has_backup = (
                conn.execute(
                    "SELECT 1 FROM demo_backups WHERE certificate_id = ?", (cid,)
                ).fetchone()
                is not None
            )

        try:
            bundle_res = verify_bundle(conn, bundle_obj, request.app.state.public_key, method="BUNDLE")
        except BundleFormatError as exc:
            raise HTTPException(status_code=422, detail=str(exc))

    token = get_csrf_token(request)
    resp = request.app.state.templates.TemplateResponse(
        request,
        "demo.html",
        {
            "certificates": certs_list,
            "selected_cert": selected_cert,
            "verification_result": verification_result,
            "has_backup": has_backup,
            "bundle_json": bundle_text,
            "bundle_result": bundle_res,
            "csrf_token": token,
        },
    )
    set_csrf_cookie(resp, token)
    return resp
