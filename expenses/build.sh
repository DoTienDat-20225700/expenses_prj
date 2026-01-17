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

python create_superuser.py