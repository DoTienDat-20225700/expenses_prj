# 🚀 Hướng Dẫn Deploy - Nền Tảng Thay Thế AWS

AWS account của bạn có limitations (không tạo được Load Balancer). Dưới đây là các nền tảng deployment tốt hơn, đơn giản hơn và **MIỄN PHÍ** hoặc giá rẻ.

---

## 🎯 So Sánh Nền Tảng

| Platform           | Giá         | Độ Dễ           | Database            | Thời Gian Deploy | Khuyến Nghị             |
| ------------------ | ----------- | --------------- | ------------------- | ---------------- | ----------------------- |
| **Railway**        | $5-10/tháng | ⭐️⭐️⭐️⭐️⭐️ | PostgreSQL miễn phí | 5 phút           | ✅ **KHUYẾN NGHỊ NHẤT** |
| **Render**         | Free tier   | ⭐️⭐️⭐️⭐️    | PostgreSQL free     | 10 phút          | ✅ Rất tốt              |
| **Heroku**         | $7/tháng    | ⭐️⭐️⭐️⭐️⭐️ | Add-on $5/tháng     | 10 phút          | ✅ Phổ biến nhất        |
| **PythonAnywhere** | $5/tháng    | ⭐️⭐️⭐️⭐️    | MySQL miễn phí      | 20 phút          | ✅ Dễ dùng              |
| **DigitalOcean**   | $5/tháng    | ⭐️⭐️⭐️       | Add-on $15/tháng    | 15 phút          | ⭐ Trung bình           |

---

## 🥇 KHUYẾN NGHỊ: RAILWAY (DỄ NHẤT + RẺ NHẤT)

**Tại sao Railway?**

- ✅ **$5 free credit** hàng tháng (đủ dùng cho side project)
- ✅ PostgreSQL database **miễn phí**
- ✅ Deploy bằng Git (zero config)
- ✅ Tự động HTTPS
- ✅ Deploy trong **5 phút**!

### 📋 Deploy lên Railway - Chi Tiết

#### Bước 1: Tạo Tài Khoản

1. Vào https://railway.app
2. Sign up với GitHub account
3. Verify email

#### Bước 2: Chuẩn Bị Project

```bash
cd /Users/abanh/Library/CloudStorage/OneDrive-Personal/Documents/expenses_prj/expenses

# Tạo Procfile
cat > Procfile << 'EOF'
release: python manage.py migrate
web: gunicorn config.wsgi --bind 0.0.0.0:$PORT
EOF

# Tạo runtime.txt
echo "python-3.10.14" > runtime.txt

# Đảm bảo requirements.txt có gunicorn
grep -q "gunicorn" requirements.txt || echo "gunicorn==21.2.0" >> requirements.txt

# Update settings.py để dùng DATABASE_URL
# (Railway tự động set DATABASE_URL)
```

Thêm vào `config/settings.py`:

```python
# Railway database configuration
import dj_database_url

DATABASES = {
    'default': dj_database_url.config(
        default='sqlite:///db.sqlite3',
        conn_max_age=600,
        conn_health_checks=True,
    )
}
```

```bash
# Git commit
git add .
git commit -m "Prepare for Railway deployment"
```

#### Bước 3: Deploy

1. **Vào Railway Dashboard** → **New Project**
2. **Deploy from GitHub repo**
3. **Connect GitHub** → Authorize Railway
4. **Select repository:** `expenses_prj`
5. Railway sẽ tự động:
   - Detect Django
   - Install dependencies
   - Run migrations
   - Deploy app

#### Bước 4: Add PostgreSQL Database

1. Trong project → **New** → **Database** → **PostgreSQL**
2. Railway tự động:
   - Tạo database
   - Set `DATABASE_URL` environment variable
   - Connect Django với database

#### Bước 5: Set Environment Variables

Click **Variables** tab, thêm:

```
SECRET_KEY = <your-secret-key>
DEBUG = False
ALLOWED_HOSTS = .railway.app
DJANGO_SETTINGS_MODULE = config.settings
```

#### Bước 6: Redeploy

Sau khi set variables → **Deploy** lại
Hoặc push commit mới: Railway tự động redeploy

#### Bước 7: Get URL

Railway Dashboard → **Settings** → **Domains**
URL dạng: `https://your-app.up.railway.app`

**✅ XONG! App đã live!**

---

## 🥈 CÁCH 2: RENDER (MIỄN PHÍ 100%)

**Free tier includes:**

- ✅ PostgreSQL 1GB miễn phí
- ✅ 750 giờ/tháng compute
- ⚠️ App sleep sau 15 phút không dùng (startup chậm)

### Deploy lên Render:

#### Bước 1: Tạo `build.sh`

```bash
cat > build.sh << 'EOF'
#!/usr/bin/env bash
set -o errexit

pip install -r requirements.txt
python manage.py collectstatic --no-input
python manage.py migrate
EOF

chmod +x build.sh
```

#### Bước 2: Cập nhật `settings.py`

Thêm vào `config/settings.py`:

```python
import dj_database_url

DATABASES = {
    'default': dj_database_url.config(
        default='sqlite:///db.sqlite3',
        conn_max_age=600
    )
}

# Render.com static files
if not DEBUG:
    STATIC_ROOT = BASE_DIR / 'staticfiles'
    STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'
```

#### Bước 3: Git Push

```bash
git add .
git commit -m "Prepare for Render deployment"
git push
```

#### Bước 4: Deploy trên Render

1. Vào https://render.com → Sign up với GitHub
2. **New** → **Web Service**
3. Connect GitHub repo: `expenses_prj`
4. **Settings:**
   - Name: `moneymanager`
   - Root Directory: `expenses`
   - Build Command: `./build.sh`
   - Start Command: `gunicorn config.wsgi:application`
5. **Environment:**
   - Python 3.10
6. **Add Environment Variables:**
   ```
   SECRET_KEY = your-secret-key
   DEBUG = False
   ALLOWED_HOSTS = .onrender.com
   ```
7. **Create PostgreSQL Database:**

   - New → PostgreSQL
   - Free tier
   - Copy "Internal Database URL"
   - Add to web service: `DATABASE_URL = <internal-url>`

8. Click **Create Web Service**

⏰ **Đợi 5-10 phút** → App live tại: `https://moneymanager.onrender.com`

---

## 🥉 CÁCH 3: HEROKU (Phổ Biến Nhất)

**Chi phí:** $7/tháng (Eco Dyno) + $5/tháng (PostgreSQL)

### Deploy lên Heroku:

```bash
# Cài Heroku CLI
brew tap heroku/brew && brew install heroku

# Login
heroku login

# Create app
cd /Users/abanh/Library/CloudStorage/OneDrive-Personal/Documents/expenses_prj/expenses
heroku create moneymanager-django

# Add PostgreSQL
heroku addons:create heroku-postgresql:mini

# Set env vars
heroku config:set SECRET_KEY="your-secret-key"
heroku config:set DEBUG=False
heroku config:set DJANGO_SETTINGS_MODULE=config.settings

# Deploy
git push heroku main

# Run migrations
heroku run python manage.py migrate

# Create superuser
heroku run python create_superuser.py

# Open app
heroku open
```

---

## 🎯 KHUYẾN NGHỊ CUỐI CÙNG

**Chọn Railway vì:**

1. ✅ **Dễ nhất** - Zero config, tự động detect Django
2. ✅ **Rẻ nhất** - $5 free credit/tháng (đủ dùng)
3. ✅ **Nhanh nhất** - Deploy trong 5 phút
4. ✅ **PostgreSQL miễn phí** - Không phải trả thêm
5. ✅ **Tự động HTTPS** - Secure by default
6. ✅ **Git-based deployment** - Push code là deploy

---

## 📝 Next Steps

**Tôi khuyên bạn làm theo thứ tự:**

1. **Clean up EB application thủ công** (nếu chưa xóa):

   ```bash
   eb terminate --all --force
   ```

2. **Chọn platform:** **Railway** (khuyến nghị)

3. **Follow hướng dẫn** ở trên

4. **App sẽ live sau 10 phút!**

---

**Bạn muốn deploy lên platform nào?** Tôi sẽ hướng dẫn chi tiết! 🚀
