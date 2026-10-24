# 10: Complete Repository File Map

## Purpose
This document provides a comprehensive structural inventory of the **Meridian Certificate Registry** repository, detailing the location, purpose, and design rationale for every directory and file.

---

## Directory Hierarchy & Purpose

```
certificate-platform/
├── app/
│   ├── crypto/                 # Pure cryptographic primitives and operations
│   │   ├── __init__.py         # Package declaration
│   │   ├── canonical.py        # Deterministic canonical JSON serialization
│   │   ├── keys.py             # RSA-2048 keypair generation, PEM I/O, fingerprinting
│   │   └── signing.py          # RSASSA-PSS SHA-256 signing and verification
│   ├── routers/                # Web and API routing layers
│   │   ├── __init__.py         # Package declaration
│   │   ├── api.py              # REST API endpoints (health, public key, certs, verify)
│   │   ├── demo.py             # Tamper lab demonstration routes (loopback only)
│   │   ├── issuer.py           # Administrative issuance, listing, revocation (loopback only)
│   │   └── public.py           # Public landing, verify, PDF, QR, bundle download routes
│   ├── services/               # Core business logic and workflow orchestration
│   │   ├── __init__.py         # Package declaration
│   │   ├── audit.py            # Hash-chained append-only event logging and chain verification
│   │   ├── demo_tools.py       # Record tampering, hash recomputation, and restoration helpers
│   │   ├── ids.py              # Cryptographically random ID generation (MIAS-YYYY-XXXX)
│   │   ├── issuance.py         # Certificate creation, canonical signing, and search filters
│   │   ├── pdf.py              # ReportLab A4 diploma generation with QR and borders
│   │   ├── qr.py               # QR code PNG generation and URL formatting
│   │   ├── revocation.py       # Certificate revocation without altering signed records
│   │   └── verification.py     # End-to-end verification logic (ID and bundle methods)
│   ├── static/                 # Offline assets (CSS & JS; no external CDNs)
│   │   ├── css/
│   │   │   ├── tokens.css      # Core design tokens (warm ivory, navy, teal, spacing)
│   │   │   ├── base.css        # CSS reset, typography, header/footer, 2-column layout
│   │   │   └── components.css  # Panels, buttons, fields, badges, kv-lists, tables, dialogs
│   │   └── js/
│   │       └── app.js          # Clipboard copy, accessible tab switching, modal dialogs
│   ├── templates/              # Jinja2 HTML templates (CSP-compliant; zero inline styles/scripts)
│   │   ├── base.html           # Universal layout shell (top bar, main container, footer)
│   │   ├── demo.html           # Tamper lab interface (classroom demonstration)
│   │   ├── error.html          # Standardized error page (403, 404, 422, 429, 500)
│   │   ├── index.html          # Institutional landing page & cryptographic explanation
│   │   ├── verify.html         # Verification entry portal (Certificate ID and Bundle tabs)
│   │   ├── verify_result.html  # Verification proof result with status badge & technical details
│   │   ├── components/
│   │   │   └── macros.html     # Reusable Jinja2 UI macros (SVGs, headers, badges, kv-rows)
│   │   └── issuer/
│   │       ├── audit.html      # Audit history table and hash-chain integrity indicator
│   │       ├── dashboard.html  # Issued certificates list with search, filter, and status tags
│   │       ├── detail.html     # Detailed certificate view with QR, download links, revocation
│   │       └── new.html        # Credential issuance form with live validation feedback
│   ├── __init__.py             # Package declaration
│   ├── config.py               # Pydantic BaseSettings configuration management
│   ├── db.py                   # SQLite connection provider, row factories, table schemas
│   ├── main.py                 # FastAPI application factory, middleware, and exception handlers
│   └── security.py             # CSP headers, loopback guard, CSRF double-submit, rate limiting
├── docs/                       # Comprehensive technical and defense documentation
│   ├── diagrams/               # Hand-crafted offline SVG diagrams
│   │   ├── architecture.svg    # System architecture and layer boundaries diagram
│   │   ├── issuance-sequence.svg   # Issuance sequence flow diagram
│   │   └── verification-sequence.svg # Verification sequence flow diagram
│   ├── 00-abstract-problem-statement.md      # Problem statement, forgery risks, and solution overview
│   ├── 01-objectives-scope-requirements.md   # Project scope, functional & non-functional requirements
│   ├── 02-architecture.md                    # Architecture, components, ER diagram, sequence flows
│   ├── 03-cryptography.md                    # Algorithmic rationales, PSS, salt, canonicalization
│   ├── 04-threat-model.md                    # Assets, attacker profiles, honest limitations
│   ├── 05-api.md                             # Complete REST API endpoint reference
│   ├── 06-setup-and-run.md                   # Installation, setup, run commands, and LAN testing
│   ├── 07-testing.md                         # Pytest test suite and automated demo check logs
│   ├── 08-demo-script.md                     # Timed 5 to 7 minute evaluation presentation script
│   ├── 09-viva-qa.md                         # 30 technical questions and answers for viva defense
│   └── 10-file-map.md                        # Complete repository structural file map (this file)
├── keys/                       # Local cryptographic key store (git-ignored in production)
│   ├── issuer_private.pem      # 2048-bit RSA private signing key (PKCS#8 encrypted)
│   └── issuer_public.pem       # SubjectPublicKeyInfo public key in PEM format
├── scripts/                    # Automation and administrative CLI scripts
│   ├── demo_check.py           # Automated 11-step end-to-end HTTP verification script
│   ├── generate_keys.py        # Generates fresh RSA-2048 keypair with passphrase
│   ├── init_db.py              # Creates SQLite database schema and tables
│   ├── reset_demo.py           # Clears database and resets state for clean testing
│   ├── seed_demo.py            # Seeds realistic demonstration certificates
│   └── verify_offline.py       # Standalone CLI verifier using public key only
├── tests/                      # Automated test suite (pytest)
│   ├── conftest.py             # Test fixtures (temporary databases, test keypairs, clients)
│   ├── test_audit.py           # Hash chain validation and tamper detection tests
│   ├── test_canonical.py       # Deterministic canonical JSON tests
│   ├── test_demo_tools.py      # Tampering and restoration service tests
│   ├── test_issuance.py        # Certificate issuance and database persistence tests
│   ├── test_keys.py            # Key generation, PEM serialization, fingerprint tests
│   ├── test_pdf_qr.py          # PDF generation, layout bounds, and QR code tests
│   ├── test_revocation.py      # Revocation service and double-revocation guard tests
│   ├── test_security_routes.py # Loopback isolation, CSRF, rate-limiting, and lifecycle tests
│   ├── test_signing.py         # RSASSA-PSS digital signature and verification tests
│   └── test_verification.py    # Verification service, bundle parser, and tampered hash tests
├── .env.example                # Example environment configuration template
├── README.md                   # Project overview, quickstart instructions, and feature summary
└── requirements.txt            # Python dependencies (pinned versions)
```
