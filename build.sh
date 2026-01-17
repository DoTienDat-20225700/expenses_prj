#!/usr/bin/env bash
# exit on error
set -o errexit

cd expenses

# Tạo requirements.txt tạm thời, bỏ qua mysqlclient (chỉ cần cho local)
echo "📦 Filtering requirements for Render..."
grep -v "mysqlclient" requirements.txt > requirements-render.txt

# Install packages từ file đã filter
pip install -r requirements-render.txt

# Cleanup
rm requirements-render.txt

# Django commands
python manage.py collectstatic --no-input
python manage.py migrate

# Tạo superuser tự động
echo "👤 Creating superuser..."
python create_superuser.py
