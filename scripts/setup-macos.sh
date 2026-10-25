#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
echo "DE Lab Studio — local Mac setup"
if [[ "$(uname -s)" != "Darwin" ]]; then echo "This helper targets macOS"; exit 1; fi
if [[ "$(uname -m)" != "arm64" ]]; then echo "Warning: not Apple Silicon"; fi
if ! command -v python3 >/dev/null; then echo "Install Python 3.11+ first"; exit 1; fi
if ! command -v docker >/dev/null; then echo "Install Docker Desktop first"; exit 1; fi
if ! docker info >/dev/null 2>&1; then echo "Start Docker Desktop first"; exit 1; fi
if ! docker compose config --quiet; then echo "Compose configuration invalid"; exit 1; fi
mkdir -p "$HOME/Applications"
cat > "$ROOT/OPEN DE LAB.command" <<'SCRIPT'
#!/bin/bash
cd "$(dirname "$0")"
exec python3 app.py
SCRIPT
chmod +x "$ROOT/OPEN DE LAB.command"
echo "Checking Ollama..."
if curl -fsS --max-time 3 http://127.0.0.1:11434/api/tags >/dev/null; then
  echo "Ollama API detected. Your existing models will appear in the UI."
else
  echo "Ollama not detected. Start Ollama to enable AI features."
fi
echo "Setup complete. Double-click OPEN DE LAB.command to launch."
