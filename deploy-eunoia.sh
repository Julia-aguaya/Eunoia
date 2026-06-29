#!/usr/bin/env bash
set -euo pipefail

cd ~/eunoia
git pull --ff-only
source .venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py collectstatic --noinput
sudo systemctl restart eunoia
