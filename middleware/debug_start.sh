#!/usr/bin/env sh
set -eu

echo "=== Middleware debug start ==="
echo "PWD antes do cd: $(pwd)"
echo "Script path: $0"

cd "$(dirname "$0")"

echo "PWD depois do cd: $(pwd)"
echo "PORT: ${PORT:-<empty>}"
echo "SUBSCRIPTION_SERVICE_URL: ${SUBSCRIPTION_SERVICE_URL:-<empty>}"
echo "PHARMACY_URL: ${PHARMACY_URL:-<empty>}"
echo "Python: $(python --version 2>/dev/null || python3 --version 2>/dev/null || true)"
echo "Pip: $(pip --version 2>/dev/null || true)"
echo "Uvicorn: $(uvicorn --version 2>/dev/null || true)"
echo "Arquivos na pasta:"
ls -la

: "${PORT:=3000}"

echo "Iniciando Middleware em 0.0.0.0:$PORT"

exec uvicorn app:app --host 0.0.0.0 --port "$PORT"
