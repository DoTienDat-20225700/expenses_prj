import os
import sys
import django
from pathlib import Path

# Lấy đường dẫn thư mục hiện tại (scripts/)
current_dir = Path(__file__).resolve().parent.parent  # → expenses/
repo_root = current_dir.parent                         # → expenses_prj/
sys.path.append(str(repo_root))

# Thiết lập môi trường Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

# Import SAU khi django.setup() để tránh lỗi "Apps aren't loaded yet"
from django.contrib.auth.models import User


def create_admin():
    """Tạo superuser từ environment variables.

    Yêu cầu các biến môi trường:
        DJANGO_SUPERUSER_USERNAME
        DJANGO_SUPERUSER_EMAIL
        DJANGO_SUPERUSER_PASSWORD

    Nếu thiếu bất kỳ biến nào → bỏ qua, không crash build.
    """
    username = os.environ.get('DJANGO_SUPERUSER_USERNAME', '').strip()
    email = os.environ.get('DJANGO_SUPERUSER_EMAIL', '').strip()
    password = os.environ.get('DJANGO_SUPERUSER_PASSWORD', '').strip()

    if not username or not password:
        print(
            "⚠️  Bỏ qua tạo superuser: thiếu DJANGO_SUPERUSER_USERNAME "
            "hoặc DJANGO_SUPERUSER_PASSWORD."
        )
        return

    if User.objects.filter(username=username).exists():
        print(f"ℹ️  Superuser '{username}' đã tồn tại. Bỏ qua.")
        return

    print(f"👤 Đang tạo superuser: {username} ...")
    User.objects.create_superuser(username=username, email=email, password=password)
    print(f"✅ Tạo superuser '{username}' thành công!")


if __name__ == '__main__':
    create_admin()