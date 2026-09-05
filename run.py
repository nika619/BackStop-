#!/usr/bin/env python3
"""
Backstop Single-Command Launcher
Razorpay AI Buildathon 2026 — Track 03: AI Revenue Recovery

Usage:
    python run.py
"""

import os
import subprocess
import sys
import time
import webbrowser

def main():
    print("=" * 70)
    print("⚡ LAUNCHING BACKSTOP 2.0 ENTERPRISE REVENUE RECOVERY ENGINE")
    print("   Razorpay AI Buildathon 2026 • Track 03")
    print("=" * 70)

    root_dir = os.path.dirname(os.path.abspath(__file__))
    console_dir = os.path.join(root_dir, "console")

    # 1. Seed benchmark dataset & database
    print("\n1️⃣  Initializing database & seeding benchmark dataset...")
    try:
        subprocess.run([sys.executable, "-m", "backstop.eval.report"], check=True, cwd=root_dir)
    except Exception as e:
        print(f"⚠️ Warning during seeding: {e}")

    # 2. Start FastAPI Backend Server
    print("\n2️⃣  Starting FastAPI API Server (http://localhost:8000)...")
    backend_proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "backstop.api:app", "--host", "0.0.0.0", "--port", "8000", "--reload"],
        cwd=root_dir,
    )

    # 3. Start Frontend Vite Console
    print("\n3️⃣  Starting Operations Console UI (http://localhost:5173)...")
    npm_cmd = "npm.cmd" if sys.platform == "win32" else "npm"
    frontend_proc = subprocess.Popen(
        [npm_cmd, "run", "dev"],
        cwd=console_dir,
    )

    print("\n⏳ Waiting 3 seconds for servers to start...")
    time.sleep(3)

    # 4. Open Browser Automatically
    print("🌐 Opening Operations Console in your default browser...")
    webbrowser.open("http://localhost:5173")

    print("\n" + "=" * 70)
    print("✅ BACKSTOP IS LIVE AND READY!")
    print("   • API Server & Swagger Docs: http://localhost:8000/docs")
    print("   • Operations Console UI:     http://localhost:5173")
    print("\n   Press Ctrl+C to stop both servers.")
    print("=" * 70 + "\n")

    try:
        backend_proc.wait()
        frontend_proc.wait()
    except KeyboardInterrupt:
        print("\n🛑 Shutting down Backstop servers cleanly...")
        backend_proc.terminate()
        frontend_proc.terminate()
        sys.exit(0)

if __name__ == "__main__":
    main()
