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
from app_expenses.models import Category, Expense, Budget
from app_expenses.ml_utils import train_model # Import hàm huấn luyện AI
from faker import Faker

fake = Faker('vi_VN')

def create_smart_fake_data(num_expenses=50):
    print("🧹 Đang xóa dữ liệu cũ...")
    Expense.objects.all().delete()
    # Category.objects.all().delete() # Có thể giữ lại danh mục nếu muốn
    print("✅ Đã xóa sạch chi tiêu cũ.")

    username = "admin"
    try:
        user = User.objects.get(username=username)
    except User.DoesNotExist:
        print(f"❌ Không tìm thấy user '{username}'. Hãy tạo user trước.")
        return

    # Tạo ngân sách mẫu
    Budget.objects.get_or_create(user=user, defaults={'total': 10000000})

    # --- BỘ DỮ LIỆU MẪU (LOGIC THẬT) ---
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
    
    print("🚀 Đang tạo dữ liệu thông minh...")

    for cat_name, descriptions in DATA_MAPPING.items():
        # Tạo hoặc lấy danh mục
        category, _ = Category.objects.get_or_create(name=cat_name, user=user)
        
        # Tạo 5-10 giao dịch cho mỗi danh mục từ danh sách mô tả mẫu
        for _ in range(random.randint(5, 10)):
            desc = random.choice(descriptions)
            # Thêm chút ngẫu nhiên vào mô tả để đa dạng (Ví dụ: Ăn phở bò 1, Ăn phở bò...)
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
    print(f"🎉 Đã tạo {len(expenses_list)} bản ghi dữ liệu có ý nghĩa.")

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