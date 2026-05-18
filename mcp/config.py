import os

# ── PI Web API connection ──────────────────────────────────────────────────────
PI_HOST   = os.getenv("PI_HOST",   "https://localhost")
PI_BASE   = f"{PI_HOST}/piwebapi"
PI_SERVER = os.getenv("PI_SERVER", "PI-SYSTEM")

# ── Credentials ────────────────────────────────────────────────────────────────
PI_USER = os.getenv("PI_USER", "piadmin")
PI_PASS = os.getenv("PI_PASS", "your-password-here")

# ── AF Database ────────────────────────────────────────────────────────────────
AF_DATABASE = os.getenv("AF_DATABASE", "GoogleManualLogger")