# 🎯 Chuyển Sang Render - Hướng Dẫn Đầy Đủ

Render **DỄ HƠN** Railway và **100% MIỄN PHÍ** cho tier đầu!

---

## 📋 Bước 1: Xóa Railway Project (Nếu Muốn)

### Option A: Xóa Qua Web UI

1. Vào https://railway.app/dashboard
2. Click vào project **expenses_prj**
3. **Settings** → Scroll xuống cuối
4. **Danger Zone** → **Delete Project**
5. Confirm deletion

### Option B: Giữ Lại (Không Tính Tiền Nếu Không Chạy)

- Railway chỉ charge khi app đang chạy
- Pause hoặc delete deployment là đủ

---

## 📋 Bước 2: Chuẩn Bị Code cho Render

Đã tạo `build.sh` - Render sẽ dùng file này để build!

### Verify Files:

```bash
cd /Users/abanh/Library/CloudStorage/OneDrive-Personal/Documents/expenses_prj

# Check files cần thiết
ls -la | grep -E "(build.sh|Procfile|requirements.txt|runtime.txt)"
```

Cần có:

- ✅ `build.sh` - Build commands
- ✅ `Procfile` - Start command
- ✅ `requirements.txt` - Dependencies (no mysqlclient)
- ✅ `runtime.txt` - Python version

### Commit và Push:

```bash
git add build.sh
git commit -m "Add Render build script"
git push
```

---

## 📋 Bước 3: Tạo Tài Khoản Render

1. Vào https://render.com
2. Click **"Get Started for Free"**
3. **Sign up with GitHub**
4. Authorize Render to access repos

**Free Tier Includes:**

- ✅ 750 hours/month (đủ cho 1 app chạy 24/7)
- ✅ PostgreSQL 1GB miễn phí
- ✅ Unlimited bandwidth
- ⚠️ App sleep sau 15 phút không dùng (startup ~30s khi wake)

---

## 📋 Bước 4: Tạo PostgreSQL Database

1. Render Dashboard → **New** → **PostgreSQL**
2. **Name:** `expenses-db`
3. **Database:** `expenses_db`
4. **User:** `expenses_user`
5. **Region:** **Singapore** (gần Việt Nam nhất)
6. **Plan:** **Free**
7. Click **Create Database**

**⏰ Đợi 2-3 phút** cho database provisioning

### Lưu Database URL:

Sau khi tạo xong:

1. Click vào database `expenses-db`
2. **Connections** section
3. **Copy Internal Database URL**
4. Lưu lại để dùng cho web service

---

## 📋 Bước 5: Tạo Web Service

1. Render Dashboard → **New** → **Web Service**
2. **Connect Repository:**

   - Click **Connect account** (nếu chưa)
   - Select **GitHub**
   - Find và select `expenses_prj`

3. **Configure Service:**

**Basic Settings:**

- **Name:** `moneymanager`
- **Region:** **Singapore**
- **Branch:** `main`
- **Root Directory:** (leave empty)
- **Runtime:** **Python 3**

**Build & Deploy:**

- **Build Command:** `./build.sh`
- **Start Command:** `cd expenses && gunicorn config.wsgi --bind 0.0.0.0:$PORT`

**Plan:**

- **Instance Type:** **Free**

4. Click **Advanced** để set environment variables

---

## 📋 Bước 6: Set Environment Variables

Trong **Environment Variables** section, add:

### Variable 1: SECRET_KEY

```bash
# Generate trên máy local:
python3 -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

- **Key:** `SECRET_KEY`
- **Value:** (paste output từ command trên)

### Variable 2: DEBUG

- **Key:** `DEBUG`
- **Value:** `False`

### Variable 3: ALLOWED_HOSTS

- **Key:** `ALLOWED_HOSTS`
- **Value:** `.onrender.com`

### Variable 4: DATABASE_URL

- **Key:** `DATABASE_URL`
- **Value:** (paste Internal Database URL từ Bước 4)

### Variable 5: DJANGO_SETTINGS_MODULE

- **Key:** `DJANGO_SETTINGS_MODULE`
- **Value:** `config.settings`

### Variable 6: PYTHON_VERSION

- **Key:** `PYTHON_VERSION`
- **Value:** `3.10.14`

---

## 📋 Bước 7: Deploy!

1. Scroll xuống cuối
2. Click **Create Web Service**

Render sẽ:

- ✅ Clone GitHub repo
- ✅ Run `build.sh` (install packages, collectstatic, migrate)
- ✅ Start gunicorn
- ✅ Deploy app!

**⏰ Đợi 5-10 phút** cho lần deploy đầu

---

## 📋 Bước 8: Get URL và Test

Sau khi deploy thành công:

1. **Service dashboard** sẽ hiện URL:

   ```
   https://moneymanager.onrender.com
   ```

2. **Click vào URL** để test app

3. Nếu thấy app → ✅ **THÀNH CÔNG!**

---

## 🔧 Troubleshooting

### Nếu Build Fail:

**Check Build Logs:**

1. Service dashboard → **Logs** tab
2. Xem error message

**Common Issues:**

- Missing environment variables → Add trong Settings
- Database not connected → Check DATABASE_URL
- Static files error → Verify whitenoise in requirements.txt

### Nếu App Crashes:

**Check Runtime Logs:**

```
Service → Logs → Filter: "Live Logs"
```

**Common fixes:**

- SECRET_KEY missing → Add environment variable
- Database connection → Check DATABASE_URL format
- Module not found → Verify build.sh runs correctly

---

## 🎯 Sau Deploy

### Tạo Superuser:

**Option 1: Render Shell (Khuyến nghị)**

1. Service dashboard → **Shell** tab
2. Click **Launch Shell**
3. Chạy:

```bash
cd expenses
python manage.py createsuperuser
```

**Option 2: Local Script**
Nếu có `create_superuser.py`:

```bash
cd expenses
python manage.py shell < create_superuser.py
```

---

## 🔄 Update Code Sau Này

Mỗi khi có code mới:

```bash
git add .
git commit -m "Your changes"
git push
```

Render sẽ **auto-deploy** tự động!

---

## 💰 Chi Phí

**FREE TIER:**

- ✅ Web Service: 750h/month (31 days)
- ✅ PostgreSQL: 1GB storage
- ✅ $0/month!

**Limitations:**

- ⚠️ App sleep sau 15 phút idle
- ⚠️ Startup ~30 giây khi wake
- ⚠️ Build time giới hạn

**Upgrade ($7/month):**

- No sleep
- Always available
- Faster build

---

## 📊 So Sánh: Render vs Railway

| Feature         | Render Free       | Railway Free  |
| --------------- | ----------------- | ------------- |
| **Cost**        | $0                | $5 credit     |
| **Sleep**       | ✅ Yes (15 min)   | ❌ No         |
| **Database**    | ✅ 1GB PostgreSQL | ✅ PostgreSQL |
| **Ease**        | ⭐⭐⭐⭐⭐        | ⭐⭐⭐⭐      |
| **Auto-deploy** | ✅ Yes            | ✅ Yes        |

---

## ✅ Summary

**Đã làm:**

- ✅ Tạo `build.sh` cho Render
- ✅ Requirements đã không có mysqlclient
- ✅ Procfile sẵn sàng

**Làm tiếp:**

1. Xóa Railway project (optional)
2. Push `build.sh` lên GitHub
3. Tạo account Render
4. Tạo PostgreSQL database
5. Tạo Web Service
6. Set environment variables
7. Deploy!

**App sẽ live tại:** `https://moneymanager.onrender.com` 🚀

---

**Bắt đầu với Bước 2 (commit build.sh) ngay bây giờ!**
