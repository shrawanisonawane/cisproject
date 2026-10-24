import io
from pathlib import Path
from reportlab.lib.colors import HexColor
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas

from app.config import settings
from app.crypto import keys as keylib
from app.services.qr import qr_png_bytes, verification_url


def _get_fonts():
    fonts_dir = Path(__file__).resolve().parent.parent / "static" / "fonts"
    serif = "Times-Roman"
    sans = "Helvetica"
    mono = "Courier"

    try:
        serif_file = fonts_dir / "SourceSerif4-Regular.ttf"
        if serif_file.exists():
            pdfmetrics.registerFont(TTFont("AppSerif", str(serif_file)))
            serif = "AppSerif"
    except Exception:
        pass

    try:
        sans_file = fonts_dir / "Inter-Regular.ttf"
        if sans_file.exists():
            pdfmetrics.registerFont(TTFont("AppSans", str(sans_file)))
            sans = "AppSans"
    except Exception:
        pass

    try:
        mono_file = fonts_dir / "IBMPlexMono-Regular.ttf"
        if mono_file.exists():
            pdfmetrics.registerFont(TTFont("AppMono", str(mono_file)))
            mono = "AppMono"
    except Exception:
        pass

    return serif, sans, mono


def build_certificate_pdf(row: dict, public_key) -> bytes:
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=landscape(A4))
    width, height = landscape(A4)  # ~ 841.89 x 595.28 pt

    serif_font, sans_font, mono_font = _get_fonts()

    authority = row.get("issuing_authority") or settings.issuing_authority
    title = row.get("certificate_title") or "Certificate of Completion"
    student_name = row.get("student_name") or ""
    course = row.get("course") or ""
    program = row.get("program") or ""
    grade = (row.get("grade_or_result") or "").strip()
    cert_id = row.get("certificate_id") or ""
    issue_date = row.get("issue_date") or ""
    sig_b64 = row.get("signature_b64") or ""
    kid = row.get("key_id") or keylib.key_id(public_key)

    c.setTitle(title)
    c.setAuthor(authority)

    # Outer border: rectangle inset 28pt, line width 1.2, colour #14213D
    c.saveState()
    c.setStrokeColor(HexColor("#14213D"))
    c.setLineWidth(1.2)
    c.rect(28, 28, width - 56, height - 56)
    c.restoreState()

    # Inner thin border: inset 36pt, line width 0.4, colour #CFC7B6
    c.saveState()
    c.setStrokeColor(HexColor("#CFC7B6"))
    c.setLineWidth(0.4)
    c.rect(36, 36, width - 72, height - 72)
    c.restoreState()

    centre_x = width / 2.0  # ~420.94 pt

    # Top centre y=520: issuing authority in small caps style, 11pt serif, colour #5B6478, letter-spaced
    c.saveState()
    c.setFillColor(HexColor("#5B6478"))
    c.setFont(serif_font, 11)
    spaced_auth = "  ".join(authority.upper().split())
    # letter spaced with single spaces between letters
    letter_spaced_auth = " ".join(list(authority.upper()))
    c.drawCentredString(centre_x, 520, letter_spaced_auth)
    c.restoreState()

    # y=470: "CERTIFICATE" 11pt sans, colour #1F6F78, spaced
    c.saveState()
    c.setFillColor(HexColor("#1F6F78"))
    c.setFont(sans_font, 11)
    c.drawCentredString(centre_x, 470, "C  E  R  T  I  F  I  C  A  T  E")
    c.restoreState()

    # y=430: certificate title 30pt serif, colour #14213D, centred. Shrink the font until the title fits within 640pt width.
    c.saveState()
    c.setFillColor(HexColor("#14213D"))
    title_size = 30
    while title_size > 6 and c.stringWidth(title, serif_font, title_size) > 640:
        title_size -= 1
    c.setFont(serif_font, title_size)
    c.drawCentredString(centre_x, 430, title)
    c.restoreState()

    # y=380: "This is to certify that" 12pt, centre
    c.saveState()
    c.setFillColor(HexColor("#14213D"))
    c.setFont(sans_font, 12)
    c.drawCentredString(centre_x, 380, "This is to certify that")
    c.restoreState()

    # y=340: student name 34pt serif, centred, with a 0.6pt rule underneath (width 360pt)
    c.saveState()
    c.setFillColor(HexColor("#14213D"))
    name_size = 34
    while name_size > 10 and c.stringWidth(student_name, serif_font, name_size) > 640:
        name_size -= 1
    c.setFont(serif_font, name_size)
    c.drawCentredString(centre_x, 340, student_name)
    c.setStrokeColor(HexColor("#14213D"))
    c.setLineWidth(0.6)
    c.line(centre_x - 180, 332, centre_x + 180, 332)
    c.restoreState()

    # y=300: "has successfully completed" 12pt
    c.saveState()
    c.setFillColor(HexColor("#14213D"))
    c.setFont(sans_font, 12)
    c.drawCentredString(centre_x, 300, "has successfully completed")
    c.restoreState()

    # y=275: course 18pt serif
    c.saveState()
    c.setFillColor(HexColor("#14213D"))
    c.setFont(serif_font, 18)
    c.drawCentredString(centre_x, 275, course)
    c.restoreState()

    # y=252: program 12pt sans
    c.saveState()
    c.setFillColor(HexColor("#14213D"))
    c.setFont(sans_font, 12)
    c.drawCentredString(centre_x, 252, program)
    c.restoreState()

    # y=232: grade/result 12pt (only if not empty)
    if grade:
        c.saveState()
        c.setFillColor(HexColor("#14213D"))
        c.setFont(sans_font, 12)
        c.drawCentredString(centre_x, 232, f"Grade / Result: {grade}")
        c.restoreState()

    # Bottom-left block (x=50, y=136 downward), 9pt mono: Certificate ID and Issue date (must not overlap centre block)
    c.saveState()
    c.setFillColor(HexColor("#14213D"))
    c.setFont(mono_font, 9)
    c.drawString(50, 136, "Certificate ID:")
    c.drawString(50, 122, cert_id)
    c.drawString(50, 102, "Issue Date:")
    c.drawString(50, 88, issue_date)
    c.restoreState()

    # Bottom-centre block: ends at least 20pt to the left of x=690 (<= 670)
    c.saveState()
    c.setFillColor(HexColor("#14213D"))
    c.setFont(mono_font, 8)
    c.drawString(240, 136, f"Digital signature (first 16 chars): {sig_b64[:16]}")
    c.drawString(240, 122, f"Key ID: {kid}")
    c.drawString(240, 108, "Public key fingerprint (SHA-256):")
    fp = keylib.fingerprint_colon(public_key)
    fp_parts = fp.split(":")
    line1 = ":".join(fp_parts[:16]) + ":"
    line2 = ":".join(fp_parts[16:])
    c.drawString(240, 96, line1)
    c.drawString(240, 84, line2)
    c.restoreState()

    # Rule 3: QR code 80 x 80 pt at x=700, y=96
    v_url = verification_url(cert_id)
    qr_bytes = qr_png_bytes(v_url)
    img_reader = ImageReader(io.BytesIO(qr_bytes))
    c.drawImage(img_reader, 700, 96, width=80, height=80)

    # Rule 4: "Scan to verify" caption, 8pt, centred under the QR (centre x=740) at y=86
    c.saveState()
    c.setFillColor(HexColor("#14213D"))
    c.setFont(sans_font, 8)
    c.drawCentredString(740, 86, "Scan to verify")
    c.restoreState()

    # Rule 5: Verification URL: drawRightString at x=790, y=74, 7pt mono; reduce down to 5.5pt if wider than 250pt
    url_size = 7.0
    while url_size > 5.5 and c.stringWidth(v_url, mono_font, url_size) > 250.0:
        url_size = round(url_size - 0.5, 1)

    c.saveState()
    c.setFillColor(HexColor("#14213D"))
    c.setFont(mono_font, url_size)
    c.drawRightString(790, 74, v_url)
    c.restoreState()

    # Rule 1: Footer line 1 at y=54, footer line 2 at y=44, centred, 7.5pt, colour #5B6478
    c.saveState()
    c.setFillColor(HexColor("#5B6478"))
    c.setFont(sans_font, 7.5)
    c.drawCentredString(
        centre_x,
        54,
        "This certificate carries a digital signature. Authenticity is established by verifying the signature at the address shown, not by the appearance of this document.",
    )
    c.drawCentredString(centre_x, 44, "Demonstration data. Not a real credential.")
    c.restoreState()

    c.showPage()
    c.save()
    return buf.getvalue()
