# DE Lab Studio

Open-source, local-first Data Engineering learning dashboard for macOS and Docker.

**Status:** early public foundation. This repository does not claim that every DE technology or all exercises are implemented. The full legacy Studio v5 package has not been imported; this is a security-conscious starting point.

## Features
- Local-only browser dashboard; no account required
- Docker Compose profile start/stop with shared-service safety
- Local Ollama models discovered dynamically (no hardcoded personal model names)
- System-design reviewer, SQL/Python tutor, algorithm coach
- Original graded SQL exercises on temporary SQLite datasets
- Data stays on your computer; no telemetry
- CPU/RAM limits configured per container in Compose

## Quick start

Prerequisites: macOS/Linux, Python 3.11+, Docker Desktop or Docker Engine, optional Ollama.

```bash
git clone https://github.com/ynb4gang/de-lab-studio.git
cd de-lab-studio
python3 app.py
```

Open http://127.0.0.1:8765 . Docker technologies can then be started from the browser. If Ollama is already installed, AI features connect to http://127.0.0.1:11434 automatically.

```bash
python3 -m unittest discover -s tests -v
docker compose config
```

### Privacy
Do not commit .env files, API keys, personal documents, local model weights, notebooks containing personal data, or Docker volumes. Ollama is only contacted on localhost by default. The server is bound to 127.0.0.1.

### Roadmap
Full notebook workspace, more ARM64-verified services (Spark, Flink, NiFi, Hadoop), production-grade container sandboxing, broad multi-dataset autograding, RAG for user-owned books, deeper author-written technical notes and exercises, richer UI and CI. See ROADMAP.md.

**Caution:** This is educational infrastructure and not production-ready multi-user hosting. Never expose the local controller publicly.
