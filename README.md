# 💰 MoneyManager - Ứng Dụng Quản Lý Chi Tiêu

<div align="center">

![Django](https://img.shields.io/badge/Django-5.2-092E20?style=for-the-badge&logo=django&logoColor=white)
![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=for-the-badge&logo=python&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-green?style=for-the-badge)

**Ứng dụng web quản lý tài chính cá nhân hiện đại, giúp bạn theo dõi chi tiêu, thu nhập và ngân sách một cách dễ dàng.**

[Tính Năng](#-tính-năng) •
[Cài Đặt](#-cài-đặt) •
[Sử Dụng](#-sử-dụng) •
[Công Nghệ](#-công-nghệ-sử-dụng)

</div>

---

## ✨ Tính Năng

### 🔐 Xác Thực & Bảo Mật

- ✅ Đăng ký và đăng nhhập người dùng
- ✅ Quản lý hồ sơ cá nhân với ảnh đại diện
- ✅ Bảo mật session và xác thực

### 📊 Quản Lý Tài Chính

- ✅ **Dashboard tổng quan** - Hiển thị thống kê tài chính theo tháng
- ✅ **Theo dõi chi tiêu** - Ghi chép và phân loại các khoản chi tiêu
- ✅ **Quản lý thu nhập** - Theo dõi các nguồn thu nhập
- ✅ **Ngân sách** - Đặt và theo dõi ngân sách hàng tháng
- ✅ **Danh mục chi tiêu** - Phân loại chi tiêu theo danh mục tùy chỉnh
- ✅ **Thống kê & Báo cáo** - Biểu đồ và phân tích chi tiết

### 🎨 Giao Diện & Trải Nghiệm

- ✅ **Dark Mode** - Chế độ tối/sáng
- ✅ **Responsive Design** - Tối ưu cho mọi thiết bị
- ✅ **UI/UX hiện đại** - Thiết kế đẹp mắt với hiệu ứng glassmorphism
- ✅ **Thông báo thông minh** - Cảnh báo và thông báo người dùng
- ✅ **Animations mượt mà** - Trải nghiệm người dùng tốt nhất

### 🤖 Tính Năng Nâng Cao

- ✅ **Machine Learning** - Dự đoán danh mục chi tiêu tự động
- ✅ **OCR Integration** - Quét hóa đơn tự động (sẵn sàng tích hợp)
- ✅ **Fake Data Generator** - Tạo dữ liệu mẫu để test

---

## 🚀 Cài Đặt

### Yêu Cầu Hệ Thống

- Python 3.10 hoặc cao hơn
- PostgreSQL hoặc MySQL (khuyến nghị) hoặc SQLite (development)
- pip (Python package manager)

### Các Bước Cài Đặt

#### 1. Clone Repository

```bash
git clone https://github.com/your-username/expenses_prj.git
cd expenses_prj/expenses
```

#### 2. Tạo Virtual Environment

```bash
# Tạo virtual environment
python3 -m venv venv

# Kích hoạt virtual environment
# Trên macOS/Linux:
source venv/bin/activate
# Trên Windows:
# venv\Scripts\activate
```

#### 3. Cài Đặt Dependencies

```bash
pip install -r requirements.txt
```

#### 4. Cấu Hình Environment Variables

Tạo file `.env` từ file mẫu:

```bash
cp .env.example .env
```

Chỉnh sửa file `.env` với thông tin của bạn:

```env
DJANGO_SECRET_KEY=your-secret-key-here
DEBUG=True
DATABASE_NAME=expenses_db
DATABASE_USER=your_db_user
DATABASE_PASSWORD=your_db_password
DATABASE_HOST=localhost
DATABASE_PORT=5432
```

> **Lưu ý:** Để tạo SECRET_KEY mới, bạn có thể chạy:
>
> ```bash
> python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
> ```

#### 5. Cấu Hình Database

**Option A: PostgreSQL (Khuyến nghị cho production)**

```bash
# Tạo database trong PostgreSQL
createdb expenses_db
```

**Option B: MySQL**

```sql
CREATE DATABASE expenses_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

**Option C: SQLite (Chỉ dành cho development)**

Không cần cấu hình gì thêm, Django sẽ tự tạo file db.sqlite3

#### 6. Chạy Migrations

```bash
python manage.py migrate
```

#### 7. Tạo Superuser (Admin)

**Cách 1: Tự động (sử dụng script)**

```bash
python create_superuser.py
```

**Cách 2: Thủ công**

```bash
python manage.py createsuperuser
```

#### 8. Tạo Dữ Liệu Mẫu (Tùy chọn)

```bash
python fake_data.py
```

Script này sẽ tạo:

- Người dùng mẫu
- Danh mục chi tiêu
- Nguồn thu nhập
- Chi tiêu và thu nhập mẫu

#### 9. Chạy Development Server

```bash
python manage.py runserver
```

Truy cập ứng dụng tại: **http://127.0.0.1:8000**

---

## 📖 Sử Dụng

### Đăng Nhập

1. Truy cập trang đăng nhập: `http://127.0.0.1:8000/login`
2. Sử dụng tài khoản đã tạo hoặc đăng ký tài khoản mới
3. Sau khi đăng nhập, bạn sẽ được chuyển đến Dashboard

### Dashboard

Dashboard hiển thị tổng quan tài chính của bạn:

- **Tổng Thu Nhập** - Thu nhập trong tháng hiện tại
- **Tổng Chi Tiêu** - Chi tiêu trong tháng hiện tại
- **Ngân Sách Còn Lại** - Số tiền còn lại sau khi trừ chi tiêu
- **Chi Tiêu Gần Đây** - 5 khoản chi tiêu mới nhất
- **Thanh Toán Sắp Tới** - Các khoản cần thanh toán

### Quản Lý Chi Tiêu

1. Vào menu **Expenses** > **Add Expense**
2. Nhập thông tin:
   - Tên chi tiêu
   - Số tiền
   - Danh mục
   - Ngày chi tiêu
   - Ghi chú (tùy chọn)
3. Upload hóa đơn/ảnh (tùy chọn)

### Quản Lý Thu Nhập

1. Vào menu **Income** > **Add Income**
2. Nhập thông tin thu nhập
3. Chọn nguồn thu nhập

### Quản Lý Ngân Sách

1. Vào **Budget** để xem và chỉnh sửa ngân sách
2. Đặt ngân sách cho từng danh mục chi tiêu
3. Theo dõi tiến độ sử dụng ngân sách

### Admin Panel

Truy cập admin panel tại: `http://127.0.0.1:8000/admin`

Admin có thể:

- Quản lý người dùng
- Quản lý danh mục
- Xem tất cả giao dịch
- Quản lý cấu hình hệ thống

---

## 🛠 Công Nghệ Sử Dụng

### Backend

- **Django 5.2** - Web framework chính
- **Python 3.10+** - Ngôn ngữ lập trình
- **PostgreSQL/MySQL** - Database
- **Gunicorn** - WSGI HTTP Server (production)
- **WhiteNoise** - Static file serving

### Frontend

- **HTML5/CSS3** - Markup & Styling
- **JavaScript** - Client-side logic
- **Bootstrap 5** - UI Framework
- **Font Awesome** - Icons

### Machine Learning

- **scikit-learn** - ML algorithms
- **pandas** - Data manipulation
- **numpy** - Numerical computing
- **joblib** - Model persistence

### Utilities

- **Pillow** - Image processing
- **python-decouple** - Environment management
- **django-widget-tweaks** - Form rendering
- **django-cleanup** - Automatic file cleanup
- **Faker** - Fake data generation

---

## 📁 Cấu Trúc Dự Án

```
expenses_prj/
├── expenses/                      # Thư mục chính của project
│   ├── app_expenses/             # Django app chính
│   │   ├── migrations/          # Database migrations
│   │   ├── static/              # Static files (CSS, JS, images)
│   │   ├── templates/           # HTML templates
│   │   │   ├── ep1/            # App templates
│   │   │   └── users/          # User authentication templates
│   │   ├── admin.py            # Admin configuration
│   │   ├── models.py           # Database models
│   │   ├── views.py            # View functions
│   │   ├── urls.py             # URL routing
│   │   ├── form.py             # Django forms
│   │   ├── validators.py       # Custom validators
│   │   └── ml_utils.py         # Machine learning utilities
│   ├── config/                   # Project configuration
│   │   ├── settings.py         # Main settings
│   │   ├── urls.py             # Main URL configuration
│   │   └── wsgi.py             # WSGI configuration
│   ├── media/                    # User uploaded files
│   ├── venv/                     # Virtual environment
│   ├── manage.py                 # Django management script
│   ├── requirements.txt          # Python dependencies
│   ├── .env                      # Environment variables (không commit)
│   ├── .env.example             # Environment variables template
│   ├── fake_data.py             # Fake data generator
│   ├── create_superuser.py      # Auto create superuser
│   ├── manage_db.py             # Database utilities
│   ├── build.sh                 # Build script (production)
│   └── expense_model_1.pkl      # Trained ML model
└── README.md                     # Documentation này
```

---

## 🔧 Utility Scripts

### 1. Fake Data Generator (`fake_data.py`)

Tạo dữ liệu mẫu cho development và testing:

```bash
python fake_data.py
```

### 2. Create Superuser (`create_superuser.py`)

Tự động tạo superuser:

```bash
python create_superuser.py
```

### 3. Database Management (`manage_db.py`)

Quản lý database utilities:

```bash
python manage_db.py
```

### 4. Build Script (`build.sh`)

Script deployment cho production:

```bash
chmod +x build.sh
./build.sh
```

---

## 🧪 Testing

### Chạy Tests

```bash
python manage.py test
```

### Test Coverage

```bash
coverage run --source='.' manage.py test
coverage report
```

---

## 🤝 Contributing

Nếu bạn muốn đóng góp cho dự án:

1. Fork repository
2. Tạo branch mới (`git checkout -b feature/AmazingFeature`)
3. Commit changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to branch (`git push origin feature/AmazingFeature`)
5. Tạo Pull Request

---

## 📝 License

Dự án này được phân phối dưới giấy phép MIT. Xem file `LICENSE` để biết thêm chi tiết.

---

## 👨‍💻 Author

**Do Tien Dat - 20225700**

- GitHub: [@DoTienDat-20225700](https://github.com/DoTienDat-20225700)

---

## 🙏 Acknowledgments

- Django Documentation
- Bootstrap Team
- Font Awesome
- Community contributors

---

## 📞 Support

Nếu bạn gặp vấn đề hoặc có câu hỏi:

1. Kiểm tra [Issues](https://github.com/your-username/expenses_prj/issues) đã tồn tại
2. Tạo issue mới nếu chưa có
3. Liên hệ qua email: your-email@example.com

---

<div align="center">

**⭐ Nếu dự án hữu ích, đừng quên cho một star nhé! ⭐**

Made with ❤️ by Do Tien Dat

</div>
