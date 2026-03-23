#!/bin/bash
# init_ollama.sh — Pull the qwen2.5:7b model into the running ollama container.
#
# Usage (after docker compose up -d):
#   bash scripts/init_ollama.sh
#
# On Linux/Mac you can also make it executable:
#   chmod +x scripts/init_ollama.sh && ./scripts/init_ollama.sh

set -e

OLLAMA_URL="http://localhost:11434"
MODEL="qwen2.5:7b"

echo "[init_ollama] Waiting for Ollama service to be ready..."
until curl -sf "${OLLAMA_URL}/api/tags" > /dev/null 2>&1; do
  echo "[init_ollama]   not ready yet, retrying in 3s..."
  sleep 3
done
echo "[init_ollama] Ollama is up."

echo "[init_ollama] Pulling model: ${MODEL}"
docker exec ollama ollama pull "${MODEL}"

echo "[init_ollama] Done! Model ${MODEL} is ready."
echo "[init_ollama] Open http://localhost:8501 to use the app."
