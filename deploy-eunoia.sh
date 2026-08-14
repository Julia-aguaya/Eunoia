#!/usr/bin/env bash
set -euo pipefail

cd ~/eunoia
git pull --ff-only
venv_python="$HOME/eunoia/.venv/bin/python"

test -x "$venv_python"
"$venv_python" -m pip install -r requirements.txt
"$venv_python" -m pip check
"$venv_python" manage.py migrate
"$venv_python" manage.py collectstatic --noinput
"$venv_python" manage.py check
sudo systemctl restart eunoia
