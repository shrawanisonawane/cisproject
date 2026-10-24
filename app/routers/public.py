import json
from fastapi import APIRouter, File, Form, HTTPException, Query, Request, Response, UploadFile
from fastapi.responses import HTMLResponse, PlainTextResponse, RedirectResponse

from app.config import settings
from app.crypto import keys as keylib
from app.db import db
from app.security import get_csrf_token, rate_limit, set_csrf_cookie
from app.services.issuance import build_bundle
from app.services.pdf import build_certificate_pdf
from app.services.qr import qr_png_bytes, verification_url
from app.services.verification import BundleFormatError, verify_bundle, verify_by_id

router = APIRouter()


@router.get("/")
def index(request: Request):
    token = get_csrf_token(request)
    resp = request.app.state.templates.TemplateResponse(
        request, "index.html", {"csrf_token": token}
    )
    set_csrf_cookie(resp, token)
    return resp


@router.get("/verify")
def verify_page(request: Request):
    token = get_csrf_token(request)
    resp = request.app.state.templates.TemplateResponse(
        request,
        "verify.html",
        {"csrf_token": token, "default_id": request.query_params.get("id", "")},
    )
    set_csrf_cookie(resp, token)
    return resp


@router.post("/verify/id")
def verify_id_submit(request: Request, certificate_id: str = Form(...)):
    cert_id = certificate_id.strip()
    return RedirectResponse(f"/verify/{cert_id}?m=id", status_code=303)


@router.get("/verify/{certificate_id}")
def verify_certificate_view(
    request: Request,
    certificate_id: str,
    m: str | None = Query(default=None),
):
    rate_limit(request)
    method = "ID" if m == "id" else "QR_LINK"
    with db() as conn:
        res = verify_by_id(
            conn, certificate_id, request.app.state.public_key, method=method
        )
    return request.app.state.templates.TemplateResponse(
        request, "verify_result.html", {"result": res}
    )


@router.post("/verify/bundle")
async def verify_bundle_view(
    request: Request,
    bundle_text: str | None = Form(default=None),
    bundle_file: UploadFile | None = File(default=None),
):
    rate_limit(request)
    content_bytes = None

    if bundle_file and bundle_file.filename:
        # Check size by reading up to max_upload_bytes + 1
        data = await bundle_file.read(settings.max_upload_bytes + 1)
        if len(data) > settings.max_upload_bytes:
            raise HTTPException(status_code=413, detail="Uploaded file exceeds maximum size")
        content_bytes = data
    elif bundle_text:
        encoded = bundle_text.encode("utf-8")
        if len(encoded) > settings.max_upload_bytes:
            raise HTTPException(status_code=413, detail="Submitted bundle exceeds maximum size")
        content_bytes = encoded
    else:
        raise HTTPException(status_code=422, detail="No bundle provided")

    try:
        bundle_obj = json.loads(content_bytes.decode("utf-8"))
    except Exception:
        raise HTTPException(status_code=422, detail="Invalid JSON in bundle")

    with db() as conn:
        try:
            res = verify_bundle(conn, bundle_obj, request.app.state.public_key, method="BUNDLE")
        except BundleFormatError as exc:
            raise HTTPException(status_code=422, detail=str(exc))

    return request.app.state.templates.TemplateResponse(
        request, "verify_result.html", {"result": res}
    )


@router.get("/certificates/{certificate_id}/pdf")
def certificate_pdf(request: Request, certificate_id: str):
    with db() as conn:
        row = conn.execute(
            "SELECT * FROM certificates WHERE certificate_id = ?", (certificate_id,)
        ).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="Certificate not found")
        pdf_data = build_certificate_pdf(dict(row), request.app.state.public_key)

    return Response(
        content=pdf_data,
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="{certificate_id}.pdf"'},
    )


@router.get("/certificates/{certificate_id}/qr.png")
def certificate_qr(request: Request, certificate_id: str):
    with db() as conn:
        row = conn.execute(
            "SELECT 1 FROM certificates WHERE certificate_id = ?", (certificate_id,)
        ).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="Certificate not found")

    v_url = verification_url(certificate_id)
    png_data = qr_png_bytes(v_url)
    return Response(content=png_data, media_type="image/png")


@router.get("/certificates/{certificate_id}/bundle.json")
def certificate_bundle(request: Request, certificate_id: str):
    with db() as conn:
        row = conn.execute(
            "SELECT * FROM certificates WHERE certificate_id = ?", (certificate_id,)
        ).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="Certificate not found")
        bundle = build_bundle(row)

    json_str = json.dumps(bundle, indent=2)
    return Response(
        content=json_str,
        media_type="application/json",
        headers={"Content-Disposition": f'attachment; filename="{certificate_id}-bundle.json"'},
    )


@router.get("/.well-known/issuer-public-key.pem")
def well_known_public_key(request: Request):
    pub = request.app.state.public_key
    pem = keylib.public_key_pem(pub)
    return PlainTextResponse(pem, media_type="text/plain")
