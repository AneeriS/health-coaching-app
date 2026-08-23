#!/bin/sh
set -eu
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
export HC_ADMIN_PASSWORD="${HC_ADMIN_PASSWORD:-ChangeThisPassword123!}"
export HC_SECRET_KEY="${HC_SECRET_KEY:-$(python3 -c 'import secrets; print(secrets.token_hex(32))')}"
python app.py
