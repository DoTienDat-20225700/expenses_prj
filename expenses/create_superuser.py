import os
import django

# Thiết lập môi trường Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'expenses.config.settings')
django.setup()

from django.contrib.auth.models import User

def create_admin():
    username = 'admin'           # Tên đăng nhập bạn muốn
    email = 'admin@example.com'  # Email (không quan trọng)
    password = '123123'   # <--- ĐIỀN MẬT KHẨU BẠN MUỐN VÀO ĐÂY

    if not User.objects.filter(username=username).exists():
        print(f"Dang tao tai khoan Superuser: {username}...")
        User.objects.create_superuser(username, email, password)
        print("✅ Tao Superuser thanh cong!")
    else:
        print("Superuser da ton tai. Bo qua.")

if __name__ == '__main__':
    create_admin()