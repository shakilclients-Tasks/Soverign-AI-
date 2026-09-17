"""Unified single-host launcher for Sovereign AI.

Runs Frontend, Backend API, and Local Sovereign LLM together on ONE host link:
  -> http://127.0.0.1:8000
"""

import os
import subprocess
import sys
import time
import urllib.request
import webbrowser
from pathlib import Path

ROOT = Path(__file__).resolve().parent
FRONTEND_DIST = ROOT / "frontend" / "dist"
OLLAMA_URL = "http://127.0.0.1:11434"
HOST = "127.0.0.1"
PORT = 8000
APP_URL = f"http://{HOST}:{PORT}"


def is_ollama_running() -> bool:
    try:
        with urllib.request.urlopen(f"{OLLAMA_URL}/api/tags", timeout=2) as resp:
            return resp.status == 200
    except Exception:
        return False


def ensure_ollama():
    if is_ollama_running():
        print("[+] Ollama service is already running on port 11434.")
        return

    print("[*] Starting Ollama local background daemon...")
    try:
        if sys.platform == "win32":
            subprocess.Popen(
                ["ollama", "serve"],
                creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, "CREATE_NO_WINDOW") else 0,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        else:
            subprocess.Popen(
                ["ollama", "serve"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        for _ in range(10):
            time.sleep(1)
            if is_ollama_running():
                print("[+] Ollama started successfully.")
                return
    except Exception as exc:
        print(f"[!] Warning: Could not auto-start Ollama: {exc}")


def ensure_frontend_built():
    if not FRONTEND_DIST.exists() or not (FRONTEND_DIST / "index.html").exists():
        print("[*] Building frontend static bundle for unified hosting...")
        frontend_dir = ROOT / "frontend"
        res = subprocess.run(["npm", "run", "build"], cwd=str(frontend_dir), shell=True)
        if res.returncode != 0:
            print("[!] Error building frontend bundle.")
            sys.exit(1)
        print("[+] Frontend build ready.")
    else:
        print("[+] Frontend bundle is ready.")


def open_browser_delayed(url: str):
    time.sleep(1.5)
    print(f"[+] Opening browser at {url} ...")
    webbrowser.open(url)


def main():
    print("=" * 65)
    print("      SOVEREIGN AI - UNIFIED ALL-IN-ONE HOST RUNNER")
    print("=" * 65)
    ensure_ollama()
    ensure_frontend_built()

    import threading
    threading.Thread(target=open_browser_delayed, args=(APP_URL,), daemon=True).start()

    print("\n" + "=" * 65)
    print(f"  >>> ALL SERVERS LIVE AT ONE HOST LINK: {APP_URL} <<<")
    print("  * Frontend UI:     http://127.0.0.1:8000/")
    print("  * Backend API:     http://127.0.0.1:8000/api/")
    print("  * Health Check:    http://127.0.0.1:8000/api/health")
    print("  * Active Model:    Sovereign LLM")
    print("=" * 65 + "\n")

    import uvicorn
    uvicorn.run("backend.main:app", host=HOST, port=PORT, reload=False)


if __name__ == "__main__":
    main()
