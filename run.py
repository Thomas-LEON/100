#!/usr/bin/env python3
# ============================================================
# run.py — Adverse News Platform Launcher
# Usage: python run.py
# ============================================================
import os
import sys
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).parent
FRONTEND_SRC = ROOT.parent / "adverse-news-platform"   # your existing HTML files
FRONTEND_DST = ROOT / "frontend"
ENV_FILE = ROOT / ".env"
ENV_EXAMPLE = ROOT / ".env.example"


def banner():
    print("""
╔══════════════════════════════════════════════════════════╗
║        ADVERSE NEWS PLATFORM — BNP Paribas              ║
║        Backend + AI Agent Pipeline                       ║
╚══════════════════════════════════════════════════════════╝
""")


def check_env():
    if not ENV_FILE.exists():
        print("⚠️  No .env file found. Copying from .env.example...")
        shutil.copy(ENV_EXAMPLE, ENV_FILE)
        print("📝 Please edit .env and add your ANTHROPIC_API_KEY, then re-run.")
        sys.exit(0)

    # Check critical keys
    from dotenv import dotenv_values
    env = dotenv_values(ENV_FILE)
    api_key = env.get("ANTHROPIC_API_KEY", "")
    if not api_key or api_key == "sk-ant-your-key-here":
        print("⚠️  ANTHROPIC_API_KEY not set in .env")
        print("   Get your key at https://console.anthropic.com")
        print("   The platform will start but AI agents will fail without it.\n")


def sync_frontend():
    """Copy HTML/CSS from the frontend build folder into backend/frontend/."""
    FRONTEND_DST.mkdir(exist_ok=True)

    # Copy static frontend files if they exist
    if FRONTEND_SRC.exists():
        for f in FRONTEND_SRC.glob("*.html"):
            shutil.copy(f, FRONTEND_DST / f.name)
        css = FRONTEND_SRC / "styles.css"
        if css.exists():
            shutil.copy(css, FRONTEND_DST / "styles.css")
        print(f"✅ Frontend files synced from {FRONTEND_SRC}")
    else:
        print(f"ℹ️  No frontend folder found at {FRONTEND_SRC}")
        print("   Place your HTML files in: frontend/")


def install_deps():
    req = ROOT / "requirements.txt"
    if req.exists():
        print("📦 Installing dependencies...")
        subprocess.run([sys.executable, "-m", "pip", "install", "-r", str(req), "-q"],
                       check=True)
        print("✅ Dependencies ready")


def run_server():
    print("\n🚀 Starting FastAPI server...")
    print("   API:   http://localhost:8000/api")
    print("   Docs:  http://localhost:8000/docs")
    print("   App:   http://localhost:8000\n")

    os.chdir(ROOT)
    subprocess.run([
        sys.executable, "-m", "uvicorn",
        "backend.main:app",
        "--host", "0.0.0.0",
        "--port", "8000",
        "--reload",
        "--log-level", "info",
    ])


if __name__ == "__main__":
    banner()
    check_env()
    sync_frontend()
    install_deps()
    run_server()
