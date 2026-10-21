#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
GPU="${GDUT_GPU:-2}"
case "$GPU" in [0-7]) ;; *) printf 'GDUT_GPU must be a single physical GPU index 0-7\n'; exit 2;; esac
if .venv/bin/python - <<'PY'
import json,urllib.request
from pathlib import Path
try:
    endpoint=json.loads(Path('cache/demo_endpoint.json').read_text())
    response=json.load(urllib.request.urlopen(f"http://127.0.0.1:{int(endpoint['port'])}/health",timeout=3))
    if response.get('project')!='gdut-scholarship-9b-20261021' or not response.get('ready'): raise ValueError()
    print('Demo already ready on server port',endpoint['port'])
except Exception:
    raise SystemExit(1)
PY
then exit 0; fi
mkdir -p logs
if tmux has-session -t gdut9b-demo 2>/dev/null; then
  printf 'Demo startup session exists; inspect logs/demo.log\n'
  exit 0
fi
tmux new-session -d -s gdut9b-demo "cd '$PWD' && CUDA_VISIBLE_DEVICES='$GPU' .venv/bin/python -u web_demo.py --adapter adapters/lora_pilot --port 8766 >> logs/demo.log 2>&1"
printf 'Demo starting; inspect logs/demo.log for DEMO_READY\n'
