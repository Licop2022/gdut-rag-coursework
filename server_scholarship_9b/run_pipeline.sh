#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
export CUDA_VISIBLE_DEVICES="${GDUT_GPU:-2}"
export HF_HUB_OFFLINE=1
export TOKENIZERS_PARALLELISM=false
export PYTHONUNBUFFERED=1
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
mkdir -p logs runs
test -f models/DOWNLOAD_COMPLETE
while tmux has-session -t gdut9b-kernels 2>/dev/null; do sleep 10; done
.venv/bin/python -m pip check
if ! test -f runs/retrieval/run_manifest.json; then
  .venv/bin/python run_experiment.py retrieve --output runs/retrieval
fi
if ! test -f runs/base/run_manifest.json; then
  .venv/bin/python run_experiment.py generate --output runs/base
fi
if ! test -f adapters/lora_pilot/training_manifest.json; then
  .venv/bin/python train_lora.py --output adapters/lora_pilot
fi
if ! test -f runs/lora/run_manifest.json; then
  .venv/bin/python run_experiment.py generate --output runs/lora --adapter adapters/lora_pilot
fi
printf 'PIPELINE_COMPLETED\n'
