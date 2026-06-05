#!/usr/bin/env sh
set -eu

cd "$(dirname "$0")"

: "${PORT:=8501}"

exec streamlit run app.py \
  --server.address=0.0.0.0 \
  --server.port="$PORT" \
  --server.headless=true
