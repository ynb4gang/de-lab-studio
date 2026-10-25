# Mac mini M4 Pro (24 GB) setup

This guide uses your existing Ollama installation. **No model weights, prompts, personal data or credentials are uploaded to GitHub.**

## Hardware settings
In Docker Desktop → Settings → Resources, start with 8 CPUs, 14–16 GB RAM and 2 GB swap. Leave headroom for macOS and the Ollama GPU model.

## Installation
```bash
git clone https://github.com/ynb4gang/de-lab-studio.git
cd de-lab-studio
bash scripts/setup-macos.sh
./OPEN\ DE\ LAB.command
```

## Ollama
The app detects installed models via `http://127.0.0.1:11434/api/tags`. Choose the model in the UI. It does **not** install or change any model. If your local model already runs, no additional setup is required.

## Profiles
- `core`: PostgreSQL
- `analytics`: PostgreSQL + ClickHouse
- `batch` and `lakehouse`: MinIO
- `streaming`: PostgreSQL + Kafka

Profiles listed here are those currently implemented in the public repository. Spark, Flink, NiFi, Airflow, Hadoop, Trino and Iceberg remain planned and should not be assumed operational.

## Resource safety
Use **Exit & Stop** on the service card to stop that profile's exclusive services. Shared services remain running if used by another active profile. This mechanism tracks sessions in application memory; after restarting the dashboard, check Docker status before assuming previous profiles were released.

## Troubleshooting
```bash
docker compose config --quiet
docker compose ps
curl http://127.0.0.1:11434/api/tags
python3 -m unittest discover -s tests -v
```

## Security
The app listens on loopback only. Never expose port 8765 through a public reverse proxy or tunnel. This development dashboard is not a hardened multi-user service. Demo database passwords are only suitable for localhost and should be changed before any network exposure.
