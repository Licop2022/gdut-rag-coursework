#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
test -x .tools/cloudflared || { printf 'Install official cloudflared at .tools/cloudflared first.\n'; exit 1; }
mkdir -p .public-private logs
chmod 700 .public-private
.venv/bin/python - <<'PY'
from pathlib import Path
import os,secrets
p=Path('.public-private/access.key')
if not p.exists():
    fd=os.open(p,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
    with os.fdopen(fd,'w') as f:f.write(secrets.token_urlsafe(32)+'\n')
os.chmod(p,0o600)
PY
if ! tmux has-session -t gdut9b-gateway 2>/dev/null; then
  tmux new-session -d -s gdut9b-gateway "cd '$PWD' && .venv/bin/python -u public_gateway.py >> logs/gateway.log 2>&1"
fi
if ! tmux has-session -t gdut9b-tunnel 2>/dev/null; then
  tmux new-session -d -s gdut9b-tunnel "cd '$PWD' && .tools/cloudflared tunnel --no-autoupdate --url http://127.0.0.1:8767 --protocol http2 >> logs/public-tunnel.log 2>&1"
fi
printf 'Public gateway starting. URL: logs/public-tunnel.log; private access key: .public-private/access.key\n'
