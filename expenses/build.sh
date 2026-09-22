#!/usr/bin/env bash
# exit on error
set -o errexit

pip install -r requirements.txt

# Remove old static files to ensure clean build
echo "Cleaning staticfiles directory..."
rm -rf staticfiles
mkdir -p staticfiles

# Gom các file static (CSS, JS, Ảnh) vào 1 chỗ
echo "Collecting static files..."
python manage.py collectstatic --no-input

# Verify collection succeeded
echo "Files collected:"
ls -la staticfiles/ | head -20

# Chạy migrate database
python manage.py migrate

# Tạo superuser từ env vars (không crash nếu đã tồn tại)
# Yêu cầu: DJANGO_SUPERUSER_USERNAME, DJANGO_SUPERUSER_EMAIL, DJANGO_SUPERUSER_PASSWORD
echo "👤 Creating superuser (if DJANGO_SUPERUSER_* env vars are set)..."
python manage.py createsuperuser --no-input || true