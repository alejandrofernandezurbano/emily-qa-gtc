#!/usr/bin/env bash
# Instala dependencias (primera vez) y ejecuta Emily QA.
set -e
cd "$(dirname "$0")"
[ -d .venv ] || python3 -m venv .venv
source .venv/bin/activate
pip install -q -r requirements.txt
python -m emily_qa "$@"
