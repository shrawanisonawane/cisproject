# 06: Setup & Execution Guide

## Purpose
This document provides exact, tested step-by-step commands to configure, initialize, and execute the **Meridian Certificate Registry** across Windows (PowerShell), macOS, and Linux, including local demonstration and multi-device LAN testing configurations.

---

## 1. Prerequisites
- **Python**: 3.10, 3.11, or 3.12.
- **Git** (optional).
- No external databases or internet access required.

---

## 2. Step-by-Step Installation

### Windows (PowerShell)

```powershell
# 1. Navigate to the project root directory
cd certificate-platform

# 2. Create Python virtual environment
python -m venv .venv

# 3. Activate the virtual environment
.venv\Scripts\Activate.ps1

# 4. Upgrade pip and install offline wheel dependencies
python -m pip install --upgrade pip
pip install -r requirements.txt

# 5. Initialize environment file
Copy-Item .env.example .env

# 6. Generate RSA-2048 keypair
python scripts/generate_keys.py

# 7. Initialize SQLite schema and tables
python scripts/init_db.py

# 8. Seed demonstration certificates (creates 3 demo records)
python scripts/seed_demo.py

# 9. Launch application server on localhost
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

---

### macOS & Linux (Bash / Zsh)

```bash
# 1. Navigate to the project root directory
cd certificate-platform

# 2. Create Python virtual environment
python3 -m venv .venv

# 3. Activate the virtual environment
source .venv/bin/activate

# 4. Upgrade pip and install dependencies
python3 -m pip install --upgrade pip
pip install -r requirements.txt

# 5. Initialize environment file
cp .env.example .env

# 6. Generate RSA-2048 keypair
python scripts/generate_keys.py

# 7. Initialize SQLite schema and tables
python scripts/init_db.py

# 8. Seed demonstration certificates
python scripts/seed_demo.py

# 9. Launch application server on localhost
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

---

## 3. Verifying the Local Installation

Once the server is running, open a browser:
1. **Public Landing Page**: [http://127.0.0.1:8000/](http://127.0.0.1:8000/)
2. **Public Verification Portal**: [http://127.0.0.1:8000/verify](http://127.0.0.1:8000/verify)
3. **Issuer Workspace (Local Only)**: [http://127.0.0.1:8000/issuer](http://127.0.0.1:8000/issuer)
4. **Tamper Lab (Demo Mode)**: [http://127.0.0.1:8000/demo](http://127.0.0.1:8000/demo)
5. **API Health Endpoint**: [http://127.0.0.1:8000/api/health](http://127.0.0.1:8000/api/health)

---

## 4. Multi-Device LAN Setup (Testing with a Mobile Phone)

To demonstrate scanning QR codes from a physical smartphone camera on the same WiFi network:

### Step 1: Find Your Computer's Local IP Address
- **Windows**: Run `ipconfig` in PowerShell and locate your IPv4 Address (e.g., `192.168.1.50`).
- **macOS / Linux**: Run `ipconfig getifaddr en0` or `hostname -I`.

### Step 2: Update `.env` Configuration
Open `.env` and set `BASE_URL` to your computer's LAN IP:
```env
BASE_URL=http://192.168.1.50:8000
```
*(This ensures that newly generated QR codes and PDFs encode `http://192.168.1.50:8000/verify/MIAS-...` instead of localhost).*

### Step 3: Allow Python Through Your Firewall
Ensure Windows Defender Firewall or macOS Application Firewall permits incoming TCP connections on port 8000.

### Step 4: Run Uvicorn Bound to All Interfaces
Start the server binding to `0.0.0.0`:
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### Step 5: Test Security Isolation
- **From your smartphone**:
  - Connect your smartphone to the same WiFi network.
  - Scan the QR code on a certificate or navigate directly to `http://192.168.1.50:8000/verify`. Verification loads smoothly.
  - Attempt to open `http://192.168.1.50:8000/issuer` on your smartphone: **The server returns HTTP 403 Forbidden ("Local access required")**. This proves that the loopback security guard successfully blocks unauthorized issuance over the local network.
- **From your laptop**:
  - Always access the Issuer Workspace via [http://127.0.0.1:8000/issuer](http://127.0.0.1:8000/issuer). Opening it via `http://192.168.1.50:8000/issuer` from the laptop will also be blocked by design, because the client IP is routed as a non-loopback LAN IP.

---

## 5. Offline CLI Verification Script

To verify credentials without any web server or database connection:

### Exact Command Syntax
```bash
python scripts/verify_offline.py <bundle.json> <issuer_public.pem>
```

### Running with Real Files
```bash
python scripts/verify_offline.py certificate-bundle.json keys/issuer_public.pem
```

### Real Terminal Output (When Valid)
```
Recomputed SHA-256: e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855
VALID: signature matches
```

### Real Terminal Output (When Tampered)
```
Recomputed SHA-256: 8f3b2a1c...
TAMPERED: signature does not match
```
(Exits with code 0 on VALID, code 1 on TAMPERED, and code 2 on missing files or invalid syntax).
