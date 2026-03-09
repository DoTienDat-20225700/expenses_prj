import os
import sys
import django
import random
from pathlib import Path
from datetime import datetime, timedelta

current_dir = Path(__file__).resolve().parent
sys.path.append(str(current_dir.parent))

# Cài đặt môi trường Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'expenses.config.settings')
django.setup()

from django.contrib.auth.models import User
from app_expenses.models import Category, Expense, Budget, Income, IncomeSource, RecurringExpense, Announcement, Profile
from app_expenses.ml_utils import train_model # Import hàm huấn luyện AI
from faker import Faker
import random

fake = Faker('vi_VN')

def create_smart_fake_data(num_expenses=50):
    print("🧹 Đang xóa dữ liệu cũ...")
    Expense.objects.all().delete()
    Income.objects.all().delete()
    RecurringExpense.objects.all().delete()
    Announcement.objects.all().delete()
    # Category.objects.all().delete() # Có thể giữ lại danh mục nếu muốn
    # IncomeSource.objects.all().delete()
    print("✅ Đã xóa sạch dữ liệu cũ.")

    username = "admin"
    try:
        user = User.objects.get(username=username)
    except User.DoesNotExist:
        print(f"❌ Không tìm thấy user '{username}'. Hãy tạo user trước.")
        return

    # --- CẬP NHẬT PROFILE ---
    print("👤 Đang cập nhật Profile...")
    profile, created = Profile.objects.get_or_create(user=user)
    profile.full_name = "Nguyễn Văn Admin"
    profile.date_of_birth = datetime(1995, 1, 1).date()
    profile.gender = 'M'
    profile.job = "Lập trình viên"
    profile.save()

    # --- TẠO NGÂN SÁCH ---
    Budget.objects.get_or_create(user=user, defaults={'total': 15000000})

    # --- TẠO DANH MỤC & CHI TIÊU ---
    # Key: Tên danh mục - Value: Các mô tả thường gặp
    DATA_MAPPING = {
        "Ăn uống": [
            "Ăn trưa văn phòng", "Mua rau củ", "Đi siêu thị", "Ăn phở bò", 
            "Cafe với bạn bè", "Trà sữa", "Mua gạo", "Ăn tối nhà hàng", "Nhậu cuối tuần"
        ],
        "Đi lại": [
            "Đổ xăng xe máy", "Gửi xe tháng", "Book Grab đi làm", 
            "Thay nhớt xe", "Sửa xe thủng săm", "Vé xe bus", "Phí cầu đường"
        ],
        "Nhà cửa": [
            "Tiền điện tháng này", "Tiền nước sinh hoạt", "Tiền mạng Internet", 
            "Mua xà phòng", "Sửa ống nước", "Mua bóng đèn mới", "Tiền thuê nhà"
        ],
        "Sức khỏe": [
            "Mua thuốc cảm", "Đi khám răng", "Mua vitamin", 
            "Khám sức khỏe định kỳ", "Mua khẩu trang", "Tập Gym"
        ],
        "Giải trí": [
            "Xem phim rạp", "Mua vé xem kịch", "Nạp thẻ game", 
            "Mua sách truyện", "Đăng ký Netflix", "Đi hát Karaoke"
        ],
        "Mua sắm": [
            "Mua quần áo mới", "Mua giày thể thao", "Săn sale Shopee", 
            "Mua mỹ phẩm", "Mua quà sinh nhật"
        ]
    }

    expenses_list = []
    
    print("🚀 Đang tạo dữ liệu Chi tiêu...")

    for cat_name, descriptions in DATA_MAPPING.items():
        # Tạo hoặc lấy danh mục
        category, _ = Category.objects.get_or_create(name=cat_name, user=user)
        
        # Tạo 5-10 giao dịch cho mỗi danh mục từ danh sách mô tả mẫu
        for _ in range(random.randint(5, 12)):
            desc = random.choice(descriptions)
            if random.random() > 0.5:
                desc += f" ({random.randint(1, 30)}/{random.randint(1, 12)})"
            
            amount = random.randint(20, 500) * 1000
            days_ago = random.randint(0, 60)
            date = datetime.now() - timedelta(days=days_ago)

            expenses_list.append(Expense(
                amount=amount, 
                description=desc, 
                category=category, 
                date=date, 
                user=user
            ))

    Expense.objects.bulk_create(expenses_list)
    print(f"   -> Đã tạo {len(expenses_list)} khoản chi tiêu.")

    # --- TẠO NGUỒN THU & THU NHẬP ---
    print("💰 Đang tạo dữ liệu Thu nhập...")
    INCOME_MAPPING = {
        "Lương": ["Lương tháng này", "Lương cứng", "Tạm ứng lương"],
        "Thưởng": ["Thưởng dự án", "Thưởng tết", "Thưởng nóng"],
        "Đầu tư": ["Lãi chứng khoán", "Lãi tiết kiệm", "Cổ tức"],
        "Freelance": ["Tiền job ngoài", "Thiết kế website", "Viết content"]
    }
    
    incomes_list = []
    
    for source_name, descriptions in INCOME_MAPPING.items():
        source, _ = IncomeSource.objects.get_or_create(name=source_name, user=user)
        
        # Tạo 2-5 khoản thu cho mỗi nguồn
        for _ in range(random.randint(2, 5)):
            desc = random.choice(descriptions)
            amount = random.randint(1000, 20000) * 1000
            days_ago = random.randint(0, 60)
            date = datetime.now() - timedelta(days=days_ago)

            incomes_list.append(Income(
                user=user,
                amount=amount,
                source=source,
                description=desc,
                date=date
            ))
            
    Income.objects.bulk_create(incomes_list)
    print(f"   -> Đã tạo {len(incomes_list)} khoản thu nhập.")

    # --- TẠO CHI TIÊU ĐỊNH KỲ ---
    print("🔄 Đang tạo Chi tiêu định kỳ...")
    recurring_data = [
        ("Tiền thuê nhà", 4500000, "monthly", "Nhà cửa"),
        ("Tiền Internet", 220000, "monthly", "Nhà cửa"),
        ("Netflix", 260000, "monthly", "Giải trí"),
        ("Spotify", 59000, "monthly", "Giải trí"),
        ("Học phí tiếng Anh", 1500000, "monthly", "Giáo dục"),
        ("Gửi xe", 150000, "monthly", "Đi lại"),
        ("Bảo hiểm xe máy", 66000, "yearly", "Đi lại"),
    ]

    for name, amount, freq, cat_name in recurring_data:
        cat, _ = Category.objects.get_or_create(name=cat_name, user=user)
        start_date = datetime.now() - timedelta(days=random.randint(1, 30))
        next_due = start_date + timedelta(days=30) # Giả sử tháng sau

        RecurringExpense.objects.create(
            user=user,
            name=name,
            amount=amount,
            category=cat,
            frequency=freq,
            start_date=start_date,
            next_due_date=next_due,
            is_active=True,
            description=f"Thanh toán {name} định kỳ"
        )
    print(f"   -> Đã tạo {len(recurring_data)} khoản chi tiêu định kỳ.")

    # --- TẠO THÔNG BÁO ---
    print("🔔 Đang tạo Thông báo...")
    announcements = [
        ("Chào mừng trở lại!", "Hệ thống đã cập nhật tính năng mới.", "success"),
        ("Nhắc nhở ngân sách", "Bạn đã tiêu quá 50% ngân sách ăn uống.", "warning"),
        ("Bảo trì hệ thống", "Hệ thống sẽ bảo trì vào 00:00 ngày mai.", "info"),
        ("Cảnh báo bảo mật", "Phát hiện đăng nhập lạ, hãy kiểm tra ngay.", "danger"),
    ]
    
    for title, content, priority in announcements:
        Announcement.objects.create(
            title=title,
            content=content,
            priority=priority,
            is_active=True
        )
    print(f"   -> Đã tạo {len(announcements)} thông báo.")

    # --- QUAN TRỌNG: HUẤN LUYỆN LẠI AI ---
    print("🧠 Đang huấn luyện lại AI từ dữ liệu mới...")
    try:
        # Xóa file model cũ nếu có để học lại từ đầu
        if os.path.exists('expense_model.pkl'):
            os.remove('expense_model.pkl')
        
        train_model(user)
        print("🤖 AI đã học xong! Sẵn sàng dự đoán.")
    except Exception as e:
        print(f"⚠️ Lỗi khi huấn luyện AI: {e}")

if __name__ == '__main__':
    create_smart_fake_data()