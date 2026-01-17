#!/usr/bin/env bash
# exit on error
set -o errexit

pip install -r requirements.txt

# Gom các file static (CSS, JS, Ảnh) vào 1 chỗ
python manage.py collectstatic --no-input --clear

# Chạy migrate database
python manage.py migrate

python create_superuser.py