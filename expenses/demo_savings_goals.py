"""
Script demo để tạo dữ liệu mẫu cho tính năng Savings Goals

Chạy: python3 manage.py shell < demo_savings_goals.py
"""

from django.contrib.auth.models import User
from app_expenses.models import SavingsGoal, Category, Expense
from datetime import date, timedelta
from decimal import Decimal

# Lấy user đầu tiên (hoặc tạo mới nếu chưa có)
try:
    user = User.objects.first()
    if not user:
        print("❌ Không tìm thấy user nào. Vui lòng tạo user trước.")
        exit()
    
    print(f"✅ Sử dụng user: {user.username}")
    
    # Lấy một số categories
    cafe_cat = Category.objects.filter(user=user, name__icontains='ăn').first()
    entertain_cat = Category.objects.filter(user=user, name__icontains='giải trí').first()
    
    if not cafe_cat:
        print("⚠️ Không tìm thấy category 'Ăn uống', tạo mới...")
        cafe_cat = Category.objects.create(user=user, name="Ăn uống")
    
    if not entertain_cat:
        print("⚠️ Không tìm thấy category 'Giải trí', tạo mới...")
        entertain_cat = Category.objects.create(user=user, name="Giải trí")
    
    # Tạo một số chi tiêu mẫu trong 30 ngày gần đây
    print("\n📊 Tạo chi tiêu mẫu...")
    today = date.today()
    
    # Chi tiêu cafe/ăn uống: 50k/ngày
    for i in range(30):
        expense_date = today - timedelta(days=i)
        Expense.objects.get_or_create(
            user=user,
            date=expense_date,
            category=cafe_cat,
            defaults={
                'amount': Decimal('50000'),
                'description': f'Cafe + sáng {expense_date.strftime("%d/%m")}'
            }
        )
    
    # Chi tiêu giải trí: 100k/ngày
    for i in range(30):
        expense_date = today - timedelta(days=i)
        Expense.objects.get_or_create(
            user=user,
            date=expense_date,
            category=entertain_cat,
            defaults={
                'amount': Decimal('100000'),
                'description': f'Xem phim/ăn tối {expense_date.strftime("%d/%m")}'
            }
        )
    
    print("✅ Đã tạo chi tiêu mẫu (30 ngày)")
    
    # Tạo mục tiêu tiết kiệm mẫu
    print("\n🎯 Tạo mục tiêu tiết kiệm mẫu...")
    
    # Mục tiêu 1: Mua Macbook
    goal1, created = SavingsGoal.objects.get_or_create(
        user=user,
        goal_name="Mua Macbook M3",
        defaults={
            'target_amount': Decimal('30000000'),
            'current_amount': Decimal('5000000'),
            'start_date': today,
            'target_date': today + timedelta(days=180),  # 6 tháng
            'notes': 'Tiết kiệm để mua Macbook M3 cho công việc'
        }
    )
    
    if created:
        goal1.categories_to_reduce.add(cafe_cat, entertain_cat)
        print("✅ Tạo mục tiêu: Mua Macbook M3 (30 triệu trong 6 tháng)")
    else:
        print("ℹ️ Mục tiêu 'Mua Macbook M3' đã tồn tại")
    
    # Mục tiêu 2: Du lịch
    goal2, created = SavingsGoal.objects.get_or_create(
        user=user,
        goal_name="Du lịch Nhật Bản",
        defaults={
            'target_amount': Decimal('50000000'),
            'current_amount': Decimal('10000000'),
            'start_date': today,
            'target_date': today + timedelta(days=365),  # 1 năm
            'notes': 'Chuyến du lịch Nhật Bản mơ ước'
        }
    )
    
    if created:
        goal2.categories_to_reduce.add(cafe_cat, entertain_cat)
        print("✅ Tạo mục tiêu: Du lịch Nhật Bản (50 triệu trong 1 năm)")
    else:
        print("ℹ️ Mục tiêu 'Du lịch Nhật Bản' đã tồn tại")
    
    # Mục tiêu 3: Mua xe máy (gần hoàn thành)
    goal3, created = SavingsGoal.objects.get_or_create(
        user=user,
        goal_name="Mua xe máy SH",
        defaults={
            'target_amount': Decimal('80000000'),
            'current_amount': Decimal('75000000'),
            'start_date': today - timedelta(days=180),
            'target_date': today + timedelta(days=60),  # 2 tháng nữa
            'notes': 'Gần đạt mục tiêu rồi!'
        }
    )
    
    if created:
        goal3.categories_to_reduce.add(cafe_cat)
        print("✅ Tạo mục tiêu: Mua xe máy SH (80 triệu, đã 75 triệu - 93.75%)")
    else:
        print("ℹ️ Mục tiêu 'Mua xe máy SH' đã tồn tại")
    
    print("\n" + "="*50)
    print("✨ HOÀN THÀNH! Dữ liệu mẫu đã được tạo.")
    print("="*50)
    print(f"\n👤 User: {user.username}")
    print(f"📁 Categories: {Category.objects.filter(user=user).count()}")
    print(f"💰 Expenses (30 ngày): {Expense.objects.filter(user=user, date__gte=today-timedelta(days=30)).count()}")
    print(f"🎯 Savings Goals: {SavingsGoal.objects.filter(user=user).count()}")
    
    print("\n🚀 Bây giờ bạn có thể:")
    print("   1. Truy cập: http://localhost:8000/savings-goals/")
    print("   2. Xem chi tiết mục tiêu để thấy gợi ý AI")
    print("   3. Cập nhật tiến độ tiết kiệm")
    
    print("\n💡 Gợi ý AI sẽ dựa trên:")
    print(f"   - Chi tiêu '{cafe_cat.name}': ~50,000đ/ngày")
    print(f"   - Chi tiêu '{entertain_cat.name}': ~100,000đ/ngày")
    print(f"   - Tổng: ~150,000đ/ngày có thể cắt giảm")
    
except Exception as e:
    print(f"❌ Lỗi: {e}")
    import traceback
    traceback.print_exc()
