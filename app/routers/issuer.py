from datetime import datetime, timezone
from fastapi import APIRouter, Depends, Form, HTTPException, Query, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from pydantic import ValidationError

from app.db import db
from app.security import check_csrf, get_csrf_token, require_loopback, set_csrf_cookie
from app.services import audit
from app.services.issuance import CertificateIn, issue_certificate, list_certificates
from app.services.qr import verification_url
from app.services.revocation import revoke_certificate
from app.services.verification import verify_by_id

router = APIRouter(dependencies=[Depends(require_loopback)])


@router.get("/issuer")
def issuer_dashboard(
    request: Request,
    q: str | None = Query(default=None),
    status: str = Query(default="all"),
    program: str | None = Query(default=None),
    sort: str = Query(default="issue_date_desc"),
):
    with db() as conn:
        certs = list_certificates(conn, q=q, status=status, program=program, sort=sort)
    token = get_csrf_token(request)
    resp = request.app.state.templates.TemplateResponse(
        request,
        "issuer/dashboard.html",
        {
            "certificates": certs,
            "q": q or "",
            "status": status,
            "program": program or "",
            "sort": sort,
            "csrf_token": token,
        },
    )
    set_csrf_cookie(resp, token)
    return resp


@router.get("/issuer/new")
def issuer_new_form(request: Request):
    token = get_csrf_token(request)
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    resp = request.app.state.templates.TemplateResponse(
        request,
        "issuer/new.html",
        {
            "csrf_token": token,
            "today_date": today,
            "form": None,
            "errors": None,
        },
    )
    set_csrf_cookie(resp, token)
    return resp


@router.post("/issuer/new")
def issuer_create_certificate(
    request: Request,
    student_name: str = Form(...),
    student_roll_no: str = Form(...),
    program: str = Form(...),
    course: str = Form(...),
    certificate_title: str = Form(...),
    grade_or_result: str = Form(default=""),
    issue_date: str = Form(...),
    csrf_token: str | None = Form(default=None),
):
    check_csrf(request, csrf_token)

    form_data = {
        "student_name": student_name,
        "student_roll_no": student_roll_no,
        "program": program,
        "course": course,
        "certificate_title": certificate_title,
        "grade_or_result": grade_or_result,
        "issue_date": issue_date,
    }

    try:
        cert_in = CertificateIn(**form_data)
    except ValidationError as err:
        errors = {}
        for e in err.errors():
            loc = str(e["loc"][-1])
            errors[loc] = e["msg"]
        token = get_csrf_token(request)
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        resp = request.app.state.templates.TemplateResponse(
            request,
            "issuer/new.html",
            {
                "csrf_token": token,
                "today_date": today,
                "form": form_data,
                "errors": errors,
            },
            status_code=422,
        )
        set_csrf_cookie(resp, token)
        return resp

    with db() as conn:
        row = issue_certificate(
            conn,
            cert_in,
            request.app.state.private_key,
            request.app.state.public_key,
        )
    return RedirectResponse(f"/issuer/certificates/{row['certificate_id']}", status_code=303)


@router.get("/issuer/certificates/{id}")
def issuer_certificate_detail(request: Request, id: str):
    with db() as conn:
        row = conn.execute("SELECT * FROM certificates WHERE certificate_id = ?", (id,)).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="Certificate not found")
        cert_dict = dict(row)
        res = verify_by_id(conn, id, request.app.state.public_key, method="ID")
        rev_row = conn.execute(
            "SELECT * FROM revocations WHERE certificate_id = ?", (id,)
        ).fetchone()
        revocation = dict(rev_row) if rev_row else None

    v_url = verification_url(id)
    token = get_csrf_token(request)
    resp = request.app.state.templates.TemplateResponse(
        request,
        "issuer/detail.html",
        {
            "cert": cert_dict,
            "result": res,
            "is_revoked": revocation is not None,
            "revocation": revocation,
            "verification_url": v_url,
            "csrf_token": token,
        },
    )
    set_csrf_cookie(resp, token)
    return resp


@router.post("/issuer/certificates/{id}/revoke")
def issuer_revoke_certificate(
    request: Request,
    id: str,
    reason: str = Form(...),
    csrf_token: str | None = Form(default=None),
):
    check_csrf(request, csrf_token)
    with db() as conn:
        try:
            revoke_certificate(conn, id, reason)
        except LookupError:
            raise HTTPException(status_code=404, detail="Certificate not found")
        except FileExistsError:
            pass
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc))

    return RedirectResponse(f"/issuer/certificates/{id}", status_code=303)


@router.get("/issuer/audit")
def issuer_audit_log(request: Request):
    with db() as conn:
        entries = audit.list_entries(conn)
        ok, msg = audit.verify_chain(conn)
    token = get_csrf_token(request)
    resp = request.app.state.templates.TemplateResponse(
        request,
        "issuer/audit.html",
        {
            "entries": entries,
            "chain_ok": ok,
            "chain_message": msg,
            "csrf_token": token,
        },
    )
    set_csrf_cookie(resp, token)
    return resp
