#!/bin/bash
set -e

# DB 초기화 (한 번만 실행)
python -c "from app import init_db; init_db()"

# gunicorn 실행
exec gunicorn --bind 0.0.0.0:5000 --workers 2 app:app
