#!/usr/bin/env sh
set -eu

echo "=== Hospital debug start ==="
echo "PWD antes do cd: $(pwd)"
echo "Script path: $0"

cd "$(dirname "$0")"

echo "PWD depois do cd: $(pwd)"
echo "PORT: ${PORT:-<empty>}"
echo "Python: $(python --version 2>/dev/null || python3 --version 2>/dev/null || true)"
echo "Pip: $(pip --version 2>/dev/null || true)"
echo "Streamlit: $(streamlit --version 2>/dev/null || true)"
echo "Arquivos na pasta:"
ls -la

: "${PORT:=8501}"

echo "Iniciando Streamlit em 0.0.0.0:$PORT"

exec streamlit run app.py \
  --server.address=0.0.0.0 \
  --server.port="$PORT" \
  --server.headless=true \
  --browser.gatherUsageStats=false
