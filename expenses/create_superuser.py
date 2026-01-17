import os
import sys
import django
from pathlib import Path

# Lấy đường dẫn thư mục hiện tại (expenses)
current_dir = Path(__file__).resolve().parent
# Lấy thư mục cha (expenses_prj) để Python nhìn thấy được package 'expenses'
repo_root = current_dir.parent
sys.path.append(str(repo_root))
# -------------------------------

# Thiết lập môi trường Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

# Import SAU khi django.setup() để tránh lỗi "Apps aren't loaded yet"
from django.contrib.auth.models import User


def create_admin():
    username = 'admin'           # Tên đăng nhập
    email = 'admin@example.com'  # Email
    password = '123123'   # <--- ĐỔI MẬT KHẨU CỦA BẠN

    if not User.objects.filter(username=username).exists():
        print(f"Dang tao tai khoan Superuser: {username}...")
        User.objects.create_superuser(username, email, password)
        print("✅ Tao Superuser thanh cong!")
    else:
        print("Superuser da ton tai. Bo qua.")

if __name__ == '__main__':
    create_admin()