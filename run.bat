@echo off
python -m venv .venv
call .venv\Scripts\activate
pip install -r requirements.txt
set HC_ADMIN_PASSWORD=ChangeThisPassword123!
python app.py
pause
