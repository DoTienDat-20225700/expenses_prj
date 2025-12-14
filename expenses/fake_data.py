import os
import django
import random
from datetime import datetime, timedelta

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'expenses.settings')
django.setup()

from django.contrib.auth.models import User
from app_expenses.models import Category, Expense, Budget
from faker import Faker

fake = Faker('vi_VN')

def create_fake_data(num_expenses=20):
    print("🧹 Đang xóa dữ liệu cũ...")
    # Lệnh này sẽ xóa sạch chi tiêu cũ để tránh bị trùng lặp
    Expense.objects.all().delete()
    print("✅ Đã xóa sạch chi tiêu cũ.")

    print(f"🚀 Đang bắt đầu tạo {num_expenses} dữ liệu giả mới...")
    
    # --- TẠO USER & CATEGORY (Giữ nguyên logic cũ) ---
    username = "admin" 
    try:
        user = User.objects.get(username=username)
    except User.DoesNotExist:
        user = User.objects.create_user(username=username, email='admin@example.com', password='1')

    Budget.objects.get_or_create(user=user, defaults={'total': 5000000})

    categories_list = ["Ăn uống", "Đi lại", "Tiền nhà", "Hẹn hò", "Mua sắm", "Học tập", "Sức khỏe", "Du lịch"]
    db_categories = []
    for cat_name in categories_list:
        cat, _ = Category.objects.get_or_create(name=cat_name, user=user)
        db_categories.append(cat)

    # --- TẠO CHI TIÊU MỚI ---
    expenses = []
    for _ in range(num_expenses):
        random_days = random.randint(0, 30)
        expense_date = datetime.now() - timedelta(days=random_days)
        amount = random.randint(20, 500) * 1000 
        category = random.choice(db_categories)
        description = fake.sentence(nb_words=6)

        expenses.append(Expense(
            amount=amount, description=description, category=category, 
            date=expense_date, user=user
        ))

    Expense.objects.bulk_create(expenses)
    print(f"🎉 XONG! Hiện tại trong database chỉ có đúng {num_expenses} khoản chi tiêu.")

if __name__ == '__main__':
    # Chạy tạo 20 bản ghi
    create_fake_data(20)