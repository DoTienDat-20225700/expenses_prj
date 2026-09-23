# MoneyManager — Django Personal Finance Management System

Ứng dụng web quản lý tài chính cá nhân toàn diện xây dựng trên nền tảng **Django 5.2**, tích hợp **Chatbot Trợ lý AI (Google Gemini & NLP)**, **Machine Learning dự đoán danh mục (scikit-learn)**, **Động cơ giao dịch định kỳ giao dịch nguyên tử (Atomic Recurring Engine)**, và **Quản lý mục tiêu tiết kiệm thông minh**.

---

## 📌 Tổng Quan Dự Án (Project Overview)

**MoneyManager** là hệ thống quản lý tài chính cá nhân bảo mật, đa người dùng (Multi-tenant data isolation) được tối ưu hóa theo mô hình kiến trúc phân lớp (Service-Oriented Django Monolith). Hệ thống cung cấp trải nghiệm quản lý dòng tiền trực quan, tự động hóa các khoản chi/thu định kỳ, phân tích xu hướng chi tiêu và hỗ trợ nhập liệu siêu tốc bằng hội thoại tự nhiên.

---

## ✨ Tính Năng Nổi Bật (Key Features)

### 1. Quản lý Chi Tiêu & Thu Nhập (Expense & Income Tracking)
- **Giao dịch thu chi**: Thêm, sửa, xóa, tìm kiếm, lọc theo khoảng thời gian, sắp xếp theo số tiền/ngày.
- **Danh mục & Nguồn thu**: Tùy biến danh mục chi tiêu và nguồn thu nhập riêng biệt cho từng người dùng.
- **Xuất dữ liệu**: Xuất báo cáo giao dịch chi tiêu ra file CSV với bộ lọc linh hoạt.
- **Machine Learning**: Tự động gợi ý danh mục chi tiêu dựa trên mô tả giao dịch bằng mô hình Naive Bayes riêng cho từng tài khoản.

### 2. Bảng Điều Khiển & Phân Tích Dữ Liệu (Dashboard & Visual Analytics)
- **Tổng quan thời gian thực**: Tổng chi tiêu, thu nhập, số dư khả dụng, ngân sách tháng và phần trăm đã sử dụng.
- **Biểu đồ trực quan (Chart.js)**:
  - Biểu đồ xu hướng chi tiêu 6 tháng gần nhất.
  - Biểu đồ so sánh tương quan Thu nhập vs Chi tiêu theo tháng.
  - Biểu đồ tỷ trọng phân bổ chi tiêu theo danh mục.
- **Tối ưu truy vấn**: 100% dữ liệu thống kê và biểu đồ dashboard được tổng hợp qua kỹ thuật Conditional Aggregation trong DB (giảm thiểu triệt để N+1 query).

### 3. Động Cơ Giao Dịch Định Kỳ (Recurring Transactions Engine)
- Thiết lập mẫu chi tiêu/thu nhập định kỳ theo chu kỳ: Hàng ngày (`daily`), Hàng tuần (`weekly`), Hàng tháng (`monthly`), Hàng năm (`yearly`).
- **Giao dịch nguyên tử (Atomic & Safe)**: Hỗ trợ sinh giao dịch tự động với khóa dòng (`select_for_update`), chống trùng lặp tại mức cơ sở dữ liệu (`unique_together` trên template và occurrence date), tự động hết hạn khi tới `end_date`.

### 4. Mục Tiêu Tiết Kiệm Thông Minh (Savings Goals & AI Recommendations)
- Đặt mục tiêu tài chính với số tiền đích và thời hạn hoàn thành.
- Cập nhật tiến độ tiết kiệm trực quan kèm thanh trạng thái.
- **Thuật toán gợi ý cắt giảm chi tiêu**: Phân tích lịch sử tiêu dùng 30 ngày gần nhất và tính toán lộ trình cắt giảm cụ thể (theo ngày/tuần/tháng) trên các danh mục người dùng lựa chọn để đảm bảo hoàn thành mục tiêu đúng hạn.

### 5. Chatbot Trợ Lý Tài Chính Thông Minh (AI Chat Assistant)
- **Xử lý ngôn ngữ tự nhiên**: Nhận diện ý định (`CREATE_EXPENSE`, `CREATE_INCOME`, `CREATE_RECURRING`, `QUERY_EXPENSES`, `DELETE_EXPENSE`, `EDIT_EXPENSE`) qua mô hình Google Gemini 2.5 Flash kết hợp bộ phân tích NLP Heuristic dự phòng.
- **Luồng xác nhận an toàn (Preview & Confirmation Flow)**: Mọi thao tác ghi/sửa/xóa dữ liệu qua chat đều hiển thị bảng xem trước (preview) và chỉ thực thi khi người dùng bấm xác nhận.
- **Rate limiting & Bảo mật**: Giới hạn tần suất gọi chatbot, bảo vệ token, sanitize dữ liệu đầu vào và đầu ra.

### 6. Quản Lý Tài Khoản & Bảo Mật Hệ Thống (Auth & Security)
- Đăng ký, đăng nhập, đăng xuất, đổi mật khẩu và quy trình quên mật khẩu qua email token an toàn.
- Quản lý hồ sơ cá nhân, hỗ trợ lưu trữ ảnh đại diện qua **Cloudinary** hoặc bộ nhớ local.
- **Bảo mật đa tầng**: Cách ly dữ liệu 100% giữa các User, xác thực CSRF trên toàn bộ mutation endpoints, HTTP 405 cho sai method, bảo vệ chống Open Redirect, kiểm soát chặt chẽ giá trị tiền dương (`CheckConstraint` & `MinValueValidator`).
- Trang quản trị nội bộ dành cho Superuser: Quản lý người dùng, quản lý thông báo hệ thống toàn trang, giám sát mô hình AI.

---

## 🛠️ Công Nghệ Sử Dụng (Tech Stack)

| Thành phần | Công nghệ / Thư viện |
| :--- | :--- |
| **Backend Framework** | Python 3.10+, Django 5.2 |
| **Kiến trúc** | Django Monolith kết hợp Service Layer (`app_expenses/services/`) |
| **Database** | PostgreSQL (Production) / MySQL / SQLite |
| **Database Connector** | `psycopg2-binary`, `mysqlclient`, `dj-database-url` |
| **AI / NLP** | `google-genai==2.22.0` (Gemini API), Regex-based Rule Engine |
| **Machine Learning** | `scikit-learn`, `pandas`, `numpy`, `scipy`, `joblib` |
| **Media Storage** | `cloudinary`, `django-cloudinary-storage`, `Pillow` |
| **Web Server & Static** | `gunicorn`, `whitenoise` |
| **Frontend** | HTML5 Semantic, CSS3 (Custom Design System), JavaScript, Bootstrap 5, Font Awesome 6, Chart.js |

---

## 📂 Cấu Trúc Thư Mục (Project Structure)

```text
expenses_prj/
├── Procfile                    # Cấu hình process cho hosting (Render/Heroku)
├── README.md                   # Tài liệu hướng dẫn chính thức của dự án
├── RENDER_DEPLOYMENT.md        # Hướng dẫn chi tiết triển khai lên Render
├── build.sh                    # Build script cho deployment môi trường root
├── runtime.txt                 # Định nghĩa phiên bản Python (python-3.10.14)
└── expenses/                   # Thư mục gốc chứa mã nguồn Django
    ├── manage.py
    ├── requirements.txt        # Danh sách Python dependencies đã được pin version
    ├── build.sh                # Build script chi tiết cho Render Web Service
    ├── render.yaml             # Infrastructure-as-code cho Render (Web + Postgres)
    ├── gunicorn_config.py      # Cấu hình worker và timeout cho Gunicorn
    ├── .env.example            # Bản mẫu cấu hình các biến môi trường
    ├── config/                 # Module cấu hình chính của Django
    │   ├── settings.py         # Cài đặt ứng dụng, bảo mật, database, logging
    │   ├── urls.py             # Root URL routing
    │   ├── wsgi.py             # WSGI entrypoint cho web server
    │   └── asgi.py             # ASGI entrypoint
    ├── app_expenses/           # Ứng dụng chính quản lý thu chi
    │   ├── models.py           # Data models với CheckConstraints & Indexes
    │   ├── views.py            # HTTP View controllers
    │   ├── form.py             # Django forms với validation chặt chẽ
    │   ├── urls.py             # URL patterns của app
    │   ├── admin.py            # Đăng ký Django Admin
    │   ├── ml_utils.py         # Quản lý huấn luyện và dự đoán danh mục ML
    │   ├── services/           # Tầng nghiệp vụ (Domain Business Logic)
    │   │   ├── recurring_service.py  # Xử lý tạo giao dịch định kỳ nguyên tử
    │   │   ├── savings_service.py    # Phân tích và tính toán mục tiêu tiết kiệm
    │   │   ├── dashboard_service.py  # Tổng hợp số liệu và biểu đồ Dashboard
    │   │   └── chat_service.py       # Xử lý nghiệp vụ xác nhận hành động từ Chat
    │   ├── utils/              # Tiện ích bổ trợ (Gemini API, NLP Parser, Security)
    │   ├── templates/ep1/      # Giao diện người dùng (Bootstrap 5 + Semantic HTML)
    │   │   └── partials/       # UI partials (Biểu đồ, bảng giao dịch, danh mục)
    │   ├── static/ep1/         # CSS, JS, hình ảnh hệ thống
    │   └── tests.py            # Bộ 91 unit & integration tests toàn diện
    ├── scripts/                # Scripts tiện ích phát triển và kiểm thử
    │   ├── create_superuser.py # Tạo superuser an toàn từ biến môi trường
    │   ├── fake_data.py        # Tạo bộ dữ liệu mẫu thông minh cho kiểm thử
    │   ├── demo_savings_goals.py
    │   ├── debug_cloudinary.py
    │   └── manage_db.py
    └── media/                  # Thư mục lưu trữ media cục bộ
```

---

## ⚙️ Hướng Dẫn Cài Đặt (Installation & Setup)

### 1. Yêu cầu hệ thống
- Python 3.10 trở lên
- Git
- MySQL hoặc PostgreSQL (tùy chọn; mặc định hỗ trợ biến môi trường `DATABASE_URL`)

### 2. Cài đặt môi trường ảo và dependencies

```bash
# 1. Clone repository
git clone <repository-url>
cd expenses_prj

# 2. Tạo và kích hoạt môi trường ảo Python
python3 -m venv expenses/venv
source expenses/venv/bin/activate       # Trên macOS / Linux
# expenses\venv\Scripts\activate        # Trên Windows

# 3. Cài đặt dependencies
cd expenses
pip install -r requirements.txt
```

### 3. Cấu hình biến môi trường (`.env`)

Tạo file `.env` từ file mẫu `.env.example`:

```bash
cp .env.example .env
```

Điền các thông số cơ bản vào file `expenses/.env`:

```env
# Core Django
SECRET_KEY=your-long-random-secret-key-here
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1

# Database (Sử dụng DATABASE_URL hoặc cấu hình riêng lẻ)
DATABASE_URL=mysql://root:password@127.0.0.1:3306/expenses_db
# Hoặc PostgreSQL: postgresql://expenses_user:password@localhost:5432/expenses_db

# Gemini AI (Tùy chọn - để sử dụng Chatbot AI)
GEMINI_API_KEY=your_gemini_api_key_here
GEMINI_MODEL=gemini-2.5-flash
GEMINI_TIMEOUT_MS=10000
CHAT_RATE_LIMIT=10
CHAT_RATE_WINDOW_SECONDS=60

# Cloudinary (Tùy chọn - nếu không set sẽ lưu avatar vào local media/)
CLOUDINARY_CLOUD_NAME=
CLOUDINARY_API_KEY=
CLOUDINARY_API_SECRET=
```

### 4. Khởi tạo Cơ sở dữ liệu và Superuser

```bash
# Chạy migration tạo các bảng và constraints
python manage.py migrate

# Tạo tài khoản quản trị (Superuser)
python manage.py createsuperuser
```

### 5. (Tùy chọn) Nạp dữ liệu mẫu để thử nghiệm

```bash
# Tạo dữ liệu chi tiêu, thu nhập, định kỳ và huấn luyện AI mẫu
python scripts/fake_data.py
```

### 6. Khởi chạy Development Server

```bash
python manage.py runserver
```

Truy cập ứng dụng tại: [http://127.0.0.1:8000/](http://127.0.0.1:8000/)
Truy cập Django Admin tại: [http://127.0.0.1:8000/admin/](http://127.0.0.1:8000/admin/)

---

## 🧪 Chạy Kiểm Thử (Automated Tests & Quality Checks)

Dự án sở hữu bộ **91 bài kiểm thử tự động (Automated Test Suite)** bao phủ các luồng nghiệp vụ cốt lõi, bảo mật và tính toán:

```bash
cd expenses

# 1. Chạy toàn bộ 91 tests
python manage.py test app_expenses

# 2. Kiểm tra tính toàn vẹn hệ thống Django
python manage.py check

# 3. Kiểm tra bảo mật triển khai (Deployment Security Check)
python manage.py check --deploy

# 4. Kiểm tra migrations không bị thiếu hoặc lệch schema
python manage.py makemigrations --check --dry-run

# 5. Kiểm tra cú pháp toàn bộ file Python
python -m compileall -q config app_expenses scripts
```

### Danh mục phạm vi kiểm thử (Test Coverage Areas):
1. **Authentication Flow**: Đăng ký, đăng nhập sai/đúng, đăng xuất, chuyển hướng người dùng ẩn danh.
2. **Multi-Tenant Data Isolation Matrix**: Kiểm thử cách ly User A / User B tuyệt đối trên Chi tiêu, Thu nhập, Danh mục, Ngân sách, Định kỳ và Mục tiêu tiết kiệm.
3. **Money Validation & Constraints**: Chặn số tiền âm, số tiền bằng 0, kiểm tra giới hạn giá trị lớn và độ chính xác phần thập phân.
4. **CRUD Lifecycle**: Luồng Tạo - Đọc - Sửa - Xóa trọn vẹn trên tất cả domain models.
5. **Recurring Advanced Engine**: Kiểm thử chu kỳ ngày/tuần/tháng/năm, tính toán ngày hết hạn, tính lũy đẳng (idempotency) khi chạy đồng thời, rollback an toàn khi xảy ra lỗi.
6. **Chatbot Intent & Security**: Mock Gemini API, heuristic fallback, xác nhận tạo/sửa/xóa qua chat, rate limit và validation tham số.
7. **Avatar Upload & Cloudinary**: Cập nhật hồ sơ, mock upload và xóa avatar cũ trên Cloudinary.
8. **CSV Export**: Xuất dữ liệu đúng định dạng, đúng header, đúng bộ lọc và bảo toàn cách ly user.
9. **Security Hardening**: Chống Open Redirect, chặn request mutation qua method GET (HTTP 405), kiểm tra an toàn SQL injection.

---

## 🚀 Hướng Dẫn Triển Khai (Deployment on Render)

Dự án đã được đóng gói sẵn sàng triển khai trên **Render** (Web Service + Managed PostgreSQL Database).

Chi tiết từng bước cấu hình xem tại: [`RENDER_DEPLOYMENT.md`](file:///Users/abanh/Library/CloudStorage/OneDrive-Personal/Documents/expenses_prj/RENDER_DEPLOYMENT.md).

### Tóm tắt cấu hình Render:
- **Build Command**: `./build.sh` (hoặc `expenses/build.sh` nếu root directory là `expenses`)
- **Start Command**: `gunicorn config.wsgi:application -c gunicorn_config.py` (hoặc `cd expenses && gunicorn config.wsgi --bind 0.0.0.0:$PORT`)
- **Environment Variables**:
  - `SECRET_KEY`: Khóa bảo mật ngẫu nhiên
  - `DEBUG`: `False`
  - `ALLOWED_HOSTS`: `.onrender.com` (hoặc custom domain của bạn)
  - `DATABASE_URL`: Connection string PostgreSQL do Render cung cấp
  - `PYTHON_VERSION`: `3.10.14`
  - `DJANGO_SUPERUSER_USERNAME`, `DJANGO_SUPERUSER_EMAIL`, `DJANGO_SUPERUSER_PASSWORD`: Tự động khởi tạo superuser khi build lần đầu mà không làm crash ứng dụng.

---

## 📋 Danh Sách Endpoint URL Tiêu Biểu

| Nhóm chức năng | Đường dẫn (URL Pattern) | Phương thức | Mô tả |
| :--- | :--- | :--- | :--- |
| **Authentication** | `/login/`, `/logout/`, `/register/` | `GET, POST` | Đăng nhập, đăng xuất, đăng ký tài khoản |
| **Dashboard** | `/`, `/dashboard/` | `GET` | Trang tổng quan tài chính cá nhân |
| **Expenses** | `/expenses/`, `/expenses/add/`, `/expenses/edit/<id>/`, `/expenses/delete/<id>/` | `GET, POST` | Quản lý danh sách và chi tiết các khoản chi |
| **Export** | `/expenses/export/` | `GET` | Xuất danh sách chi tiêu ra file CSV |
| **Income** | `/income/`, `/income/add/`, `/income/edit/<id>/`, `/income/delete/<id>/` | `GET, POST` | Quản lý thu nhập |
| **Income Sources** | `/income/sources/`, `/income/sources/edit/<id>/`, `/income/sources/delete/<id>/` | `GET, POST` | Quản lý danh mục nguồn thu nhập |
| **Categories** | `/categories/`, `/categories/add/`, `/categories/edit/<id>/`, `/categories/delete/<id>/` | `GET, POST` | Quản lý danh mục chi tiêu |
| **Recurring** | `/recurring/`, `/recurring/add/`, `/recurring/edit/<id>/`, `/recurring/delete/<id>/` | `GET, POST` | Quản lý mẫu giao dịch định kỳ |
| **Recurring Action**| `/recurring/generate/`, `/recurring/toggle/<id>/` | `POST` | Kích hoạt sinh giao dịch và bật/tắt mẫu định kỳ |
| **Savings Goals** | `/savings-goals/`, `/savings-goals/add/`, `/savings-goals/<id>/` | `GET, POST` | Quản lý mục tiêu tiết kiệm và gợi ý AI |
| **Chat Assistant** | `/chat-assistant/` | `GET` | Giao diện trò chuyện cùng trợ lý AI |
| **Chat API** | `/api/parse-expense/` | `POST` | Parse câu thoại tự nhiên và trích xuất ý định |
| **Chat Actions** | `/api/save-expense-from-chat/`, `/api/manage-expense-from-chat/`, `/api/save-income-from-chat/`, `/api/save-recurring-from-chat/` | `POST` | Thực thi ghi nhận giao dịch sau khi user xác nhận |
| **Chart APIs** | `/api/chart/category/`, `/api/chart/monthly/`, `/api/chart/income-expense/`, `/api/dashboard-refresh/` | `GET` | Cung cấp dữ liệu JSON cho biểu đồ Dashboard |
| **Profile & Pass** | `/profile/`, `/password_change/`, `/password_reset/` | `GET, POST` | Hồ sơ cá nhân, đổi mật khẩu, quên mật khẩu |
| **Management** | `/admin/`, `/admin-dashboard/`, `/manager/users/`, `/manager/announcements/`, `/manager/ai-monitor/` | `GET, POST` | Quản trị hệ thống dành riêng cho Superuser |

---

## 🔮 Nợ Kỹ Thuật & Cải Tiến Tương Lai (Technical Debt & Future Roadmap)

Các hạng mục tối ưu hóa nâng cao cho giai đoạn mở rộng quy mô lớn (Scale-up Phase):
1. **Asynchronous Background Task Queue**: Chuyển việc huấn luyện lại mô hình ML cá nhân từ in-process Python Thread sang hàng đợi phân tán (như Celery / Redis) để không chiếm dụng worker thread của web server khi có hàng ngàn user hoạt động đồng thời.
2. **Centralized Caching**: Tích hợp Redis Cache cho các bảng tham chiếu ít biến động (như danh sách danh mục mặc định, thông báo hệ thống toàn trang).
3. **Dedicated REST API with OpenAPI/Swagger**: Xây dựng bộ RESTful API chuẩn hóa (Django REST Framework) nếu cần mở rộng phát triển ứng dụng di động (Mobile App iOS/Android).
