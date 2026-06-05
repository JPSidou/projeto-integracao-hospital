#!/usr/bin/env sh
set -eu

echo "=== Farmacia debug start ==="
echo "PWD antes do cd: $(pwd)"
echo "Script path: $0"

cd "$(dirname "$0")"

echo "PWD depois do cd: $(pwd)"
echo "PORT: ${PORT:-<empty>}"
echo "Python: $(python --version 2>/dev/null || python3 --version 2>/dev/null || true)"
echo "Pip: $(pip --version 2>/dev/null || true)"
echo "Uvicorn: $(uvicorn --version 2>/dev/null || true)"
echo "Arquivos na pasta:"
ls -la

: "${PORT:=3001}"

echo "Iniciando Farmacia em 0.0.0.0:$PORT"

exec uvicorn app:app --host 0.0.0.0 --port "$PORT"
