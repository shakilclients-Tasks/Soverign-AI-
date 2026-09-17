"""Build and register the ChatGPT/Gemini-grade Sovereign Document Expert model in Ollama."""

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODELFILE = ROOT / "docker" / "Modelfile.doc-expert"


def create_model():
    if not MODELFILE.exists():
        print(f"Error: Modelfile not found at {MODELFILE}")
        sys.exit(1)

    print(f"Building Ollama model 'sovereign-doc-expert' from {MODELFILE}...")
    cmd = ["ollama", "create", "sovereign-doc-expert", "-f", str(MODELFILE)]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode == 0:
        print("Success! 'sovereign-doc-expert' created successfully.")
        print(result.stdout)
    else:
        print("Failed to create model via CLI:", result.stderr)
        print("Trying Ollama HTTP API...")
        import urllib.request
        import json
        
        req = urllib.request.Request(
            "http://127.0.0.1:11434/api/create",
            data=json.dumps({
                "model": "sovereign-doc-expert",
                "modelfile": MODELFILE.read_text(encoding="utf-8")
            }).encode("utf-8"),
            headers={"Content-Type": "application/json"}
        )
        try:
            with urllib.request.urlopen(req) as resp:
                print("API response status:", resp.status)
                for line in resp:
                    data = json.loads(line.decode("utf-8"))
                    print(data.get("status", ""))
        except Exception as e:
            print("API creation error:", e)
            sys.exit(1)


if __name__ == "__main__":
    create_model()
