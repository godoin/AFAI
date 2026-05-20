import os
from dotenv import load_dotenv

load_dotenv()

# ── PI Web API connection ──────────────────────────────────────────────────────
PI_HOST   = os.getenv("PI_HOST",   "https://192.168.254.50")
PI_BASE   = f"{PI_HOST}/piwebapi"
PI_SERVER = os.getenv("PI_SERVER", "PI-SYSTEM")

# ── Credentials ────────────────────────────────────────────────────────────────
PI_USER = os.getenv("PI_USER", "Administrator")
PI_PASS = os.getenv("PI_PASS", "C8@dm1n")

# ── AF Database ────────────────────────────────────────────────────────────────
AF_DATABASE = os.getenv("AF_DATABASE", "GoogleManualLogger")