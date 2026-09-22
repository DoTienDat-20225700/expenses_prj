# MoneyManager

Ứng dụng web Django quản lý tài chính cá nhân: theo dõi chi tiêu, thu nhập, ngân sách, giao dịch định kỳ và mục tiêu tiết kiệm.

## Overview

MoneyManager là Django monolith với app chính `app_expenses`. Người dùng đăng ký, đăng nhập và quản lý dữ liệu tài chính của mình qua Django templates. Ứng dụng có chatbot hỗ trợ truy vấn và xác nhận giao dịch, dự đoán danh mục bằng machine learning, cùng tùy chọn lưu ảnh đại diện qua Cloudinary.

## Features

- Đăng ký, đăng nhập, đăng xuất, đổi mật khẩu và khôi phục mật khẩu.
- Quản lý hồ sơ cá nhân và ảnh đại diện.
- CRUD chi tiêu, danh mục chi tiêu và xuất CSV.
- CRUD thu nhập và nguồn thu nhập.
- Dashboard với tổng hợp, ngân sách, giao dịch gần đây và biểu đồ.
- Chi tiêu định kỳ và thu nhập định kỳ.
- Mục tiêu tiết kiệm, cập nhật tiến độ và phân tích danh mục cần cắt giảm.
- Chat assistant cho truy vấn tài chính, preview và xác nhận tạo/sửa/xóa giao dịch.
- Dự đoán danh mục bằng scikit-learn theo user.
- Khu vực quản trị cho superuser và Django Admin.
- Quản lý thông báo hệ thống.

OCR, public REST API độc lập và mobile app chưa được triển khai trong source hiện tại.

## Tech Stack

- Python 3.10+ và Django 5.2.
- Django ORM, Django forms, function-based views và Django templates.
- MySQL hoặc PostgreSQL thông qua `DATABASE_URL` hoặc biến database riêng.
- Gunicorn và WhiteNoise.
- HTML/CSS/JavaScript; template hiện tại tham chiếu Bootstrap và Font Awesome.
- Cloudinary tùy chọn cho media.
- scikit-learn, pandas, NumPy, SciPy, joblib cho ML.
- Google Gemini tùy chọn thông qua `google-genai`.

## Project Structure

```text
expenses_prj/
├── README.md
├── Procfile
├── build.sh
├── runtime.txt
└── expenses/
    ├── manage.py
    ├── requirements.txt
    ├── build.sh
    ├── render.yaml
    ├── gunicorn_config.py
    ├── .env.example
    ├── config/              # settings, root URLs, ASGI, WSGI
    ├── app_expenses/        # models, views, forms, URLs, admin, tests
    │   ├── migrations/
    │   ├── templates/ep1/
    │   ├── static/ep1/
    │   └── utils/           # chatbot, NLP, Gemini, recurring logic
    ├── scripts/             # fake data, superuser, database utilities
    ├── media/               # local uploaded media
    └── staticfiles/         # collectstatic output
```

Không nên commit virtual environment, secrets hoặc generated artifacts.

## System Architecture

```text
Browser
  -> config.urls -> app_expenses.urls
  -> function-based views
  -> forms / chatbot utilities / ML utilities
  -> Django ORM -> configured database

Uploads -> local filesystem hoặc Cloudinary
Static files -> app static -> collectstatic -> WhiteNoise
```

Model chính gồm `Expense`, `Income`, `Category`, `IncomeSource`, `Budget`, `RecurringExpense`, `RecurringIncome`, `SavingsGoal`, `Profile` và `Announcement`. Giao dịch gắn với user; các form chính lọc category/source theo user hiện tại.

## Installation

Yêu cầu: Python 3.10+, pip và MySQL/PostgreSQL nếu không dùng database URL có sẵn.

Từ thư mục repository:

```bash
python3 -m venv expenses/venv
source expenses/venv/bin/activate
cd expenses
pip install -r requirements.txt
cp .env.example .env
```

Trên Windows, kích hoạt bằng `expenses\\venv\\Scripts\\activate`.

Mở `expenses/.env` và đổi `DJANGO_SECRET_KEY` thành `SECRET_KEY`, vì `config/settings.py` đọc biến `SECRET_KEY`.

## Environment Variables

### Django và database

```env
SECRET_KEY=replace-with-a-long-random-secret
DEBUG=True

# Có thể dùng DATABASE_URL thay cho các biến bên dưới.
DATABASE_URL=mysql://user:password@127.0.0.1:3306/expenses_db
# DATABASE_ENGINE=django.db.backends.mysql
# DATABASE_NAME=expenses_db
# DATABASE_USER=root
# DATABASE_PASSWORD=
# DATABASE_HOST=127.0.0.1
# DATABASE_PORT=3306
```

Khi không có `DATABASE_URL`, settings mặc định dùng MySQL tại `127.0.0.1:3306`. Production cần `DEBUG=False`, secret riêng và allowlist host phù hợp. Hiện settings vẫn đặt `ALLOWED_HOSTS = ['*']`; đây là known issue.

### Chat assistant

```env
GEMINI_API_KEY=
GEMINI_MODEL=gemini-2.5-flash
GEMINI_TIMEOUT_MS=10000
CHAT_RATE_LIMIT=10
CHAT_RATE_WINDOW_SECONDS=60
```

### Cloudinary

```env
CLOUDINARY_URL=cloudinary://api_key:api_secret@cloud_name
# Hoặc dùng CLOUDINARY_CLOUD_NAME, CLOUDINARY_API_KEY, CLOUDINARY_API_SECRET.
```

Không có `CLOUDINARY_CLOUD_NAME` thì app dùng local filesystem cho media.

### Email/password reset

Nếu không có `EMAIL_HOST`, development dùng console email backend. SMTP cần `EMAIL_HOST`, `EMAIL_PORT`, `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD`, `EMAIL_USE_TLS`, `EMAIL_USE_SSL` và `DEFAULT_FROM_EMAIL`.

## Database Setup

MySQL local:

```sql
CREATE DATABASE expenses_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

Hoặc tạo database PostgreSQL và cấu hình `DATABASE_URL`. Sau đó chạy từ thư mục `expenses`:

```bash
python manage.py migrate
python manage.py createsuperuser
```

> `expenses/scripts/create_superuser.py` tồn tại nhưng build scripts tham chiếu sai đường dẫn và script có credentials mặc định không an toàn. Không dùng script này cho production.

## Running The Project

```bash
cd expenses
python manage.py runserver
```

Mở [http://127.0.0.1:8000/](http://127.0.0.1:8000/). Django Admin ở [http://127.0.0.1:8000/admin/](http://127.0.0.1:8000/admin/).

Static files:

```bash
python manage.py collectstatic --no-input
```

Gunicorn trong môi trường đã cấu hình:

```bash
gunicorn config.wsgi:application
```

`Procfile`, `render.yaml`, `gunicorn_config.py` và hai build script hiện chưa thống nhất working directory, port và đường dẫn tạo superuser; cần rà soát trước khi deploy Render.

## Main Features / User Flow

1. User đăng ký/đăng nhập; signal tạo profile, category và income source mặc định.
2. User quản lý expense, income, category, source và budget của mình.
3. Dashboard tổng hợp dữ liệu, biểu đồ và giao dịch gần đây.
4. User tạo recurring expense/income và kích hoạt sinh giao dịch đến hạn.
5. User tạo savings goal, cập nhật tiến độ và xem gợi ý.
6. Chat assistant phân tích câu lệnh, trả preview và yêu cầu xác nhận trước khi ghi dữ liệu ở các flow hỗ trợ.
7. Superuser dùng `/admin/` hoặc manager pages để quản lý user, announcement và AI monitor.

## API / URLs

Các URL dưới đây nằm dưới root `/`; phần lớn yêu cầu đăng nhập:

| Nhóm               | URL tiêu biểu                                                                                                                                            |
| ------------------ | -------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Authentication     | `/login/`, `/logout/`, `/register/`                                                                                                                      |
| Dashboard          | `/`, `/dashboard/`                                                                                                                                       |
| Expenses           | `/expenses/`, `/expenses/add/`, `/expenses/export/`                                                                                                      |
| Categories         | `/categories/`                                                                                                                                           |
| Income             | `/income/`, `/income/sources/`                                                                                                                           |
| Recurring          | `/recurring/`, `/recurring/add/`, `/recurring/generate/`                                                                                                 |
| Savings goals      | `/savings-goals/`                                                                                                                                        |
| Profile            | `/profile/`, `/password_change/`, `/password_reset/`                                                                                                     |
| Admin              | `/admin/`, `/admin-dashboard/`, `/manager/users/`, `/manager/announcements/`                                                                             |
| Chat UI            | `/chat-assistant/`                                                                                                                                       |
| Chat APIs          | `/api/parse-expense/`, `/api/save-expense-from-chat/`, `/api/manage-expense-from-chat/`, `/api/save-income-from-chat/`, `/api/save-recurring-from-chat/` |
| Chart/refresh APIs | `/api/chart/category/`, `/api/chart/monthly/`, `/api/chart/income-expense/`, `/api/dashboard-refresh/`                                                   |

Đây là Django JSON endpoints nội bộ, không phải REST API có OpenAPI/DRF.

## Scripts

Các script nằm trong `expenses/scripts/`:

```bash
cd expenses
python scripts/fake_data.py
python scripts/debug_cloudinary.py
python scripts/manage_db.py
```

`fake_data.py` dành cho development/testing. `manage_db.py` có logic phụ thuộc MySQL/Homebrew và không phải công cụ database portable.

## Running Tests

```bash
cd expenses
python manage.py test
python manage.py check
python manage.py check --deploy
python manage.py makemigrations --check --dry-run
python manage.py showmigrations
```

Test hiện tập trung trong `app_expenses/tests.py`, chủ yếu cho chatbot, parsing, rate limit và một số flow xác nhận tạo/sửa/xóa. Chưa có bộ test đầy đủ cho authentication, authorization matrix, uploads, admin actions, recurring generation, migrations và deployment.

## Screenshots

Repository có asset giao diện tại `expenses/app_expenses/static/ep1/`, gồm logo, background và ảnh mặc định. Chưa có bộ screenshot sản phẩm được quản lý như tài liệu chính thức.

## Known Issues

- `SECRET_KEY` trong settings không khớp `DJANGO_SECRET_KEY` trong `.env.example`.
- Settings mặc định MySQL; SQLite không phải database mặc định.
- `ALLOWED_HOSTS` đang cho phép mọi host và production security headers/cookie settings chưa đầy đủ.
- Một số mutation endpoint cần được chuẩn hóa thành POST-only và bảo vệ CSRF.
- Sinh recurring transactions cần atomicity/idempotency khi có request đồng thời.
- Một số amount field chưa có database-level constraint chống giá trị âm.
- ML training bằng thread trong web process có thể gây tải CPU/memory khi scale.
- Render configuration và build scripts chưa thống nhất working directory, port và đường dẫn script.
- `google-genai` chưa được pin version trong `requirements.txt`.
- Không có demo credentials an toàn được xác nhận trong repository.

## Future Improvements

1. Chuẩn hóa secrets, `ALLOWED_HOSTS`, HTTPS/cookie settings và loại bỏ credentials hard-coded.
2. Chuyển mutation endpoints sang POST-only; tăng authorization tests và enforce ownership ở model/service layer.
3. Dùng transaction, locking và idempotency cho recurring generation.
4. Thêm constraints/indexes và tối ưu aggregate/query patterns dựa trên profiling.
5. Chuyển ML training sang task queue và quản lý model artifacts ngoài web filesystem.
6. Tách production/development dependencies và pin runtime dependencies.
7. Bổ sung test cho auth, permission, CRUD, uploads, migrations, admin, recurring và deployment smoke checks.
8. Thống nhất một cấu hình Render/deployment duy nhất.

## Contributing

Giữ thay đổi tập trung, cập nhật test/tài liệu liên quan và chạy `python manage.py test` cùng Django checks trước khi tạo pull request.
