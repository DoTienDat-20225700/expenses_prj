# 🚂 Hướng Dẫn Deploy Django MoneyManager lên Railway

**Railway** = Nền tảng deployment đơn giản nhất, $5 free/tháng, PostgreSQL miễn phí

---

## 📋 Bước 1: Đẩy Code Lên GitHub (Nếu Chưa)

Railway deploy từ GitHub repository, nên cần push code lên GitHub trước.

### Nếu chưa có GitHub repo:

```bash
cd /Users/abanh/Library/CloudStorage/OneDrive-Personal/Documents/expenses_prj

# Initialize git (nếu chưa có)
git init

# Add remote
git remote add origin https://github.com/YOUR_USERNAME/expenses_prj.git

# Commit tất cả
git add .
git commit -m "Prepare for Railway deployment"

# Push
git push -u origin main
```

### Nếu đã có repo:

```bash
cd /Users/abanh/Library/CloudStorage/OneDrive-Personal/Documents/expenses_prj

# Commit changes mới nhất
git add .
git commit -m "Add Railway deployment files (Procfile, runtime.txt)"
git push
```

---

## 📋 Bước 2: Tạo Tài Khoản Railway

1. **Truy cập:** https://railway.app
2. Click **"Login"** hoặc **"Start a New Project"**
3. **Sign up với GitHub:**
   - Click "Login with GitHub"
   - Authorize Railway app
   - Railway sẽ có quyền đọc repos của bạn

✅ **Free tier:** $5 credit mỗi tháng (đủ cho side project)

---

## 📋 Bước 3: Tạo Project Mới

### 3.1 Vào Railway Dashboard

Sau khi login, bạn sẽ thấy Dashboard:

1. Click **"New Project"**
2. Chọn **"Deploy from GitHub repo"**

### 3.2 Connect GitHub Repository

1. Railway sẽ hiện danh sách repos
2. Tìm và click **"expenses_prj"** (hoặc tên repo của bạn)
3. Railway sẽ tự động:
   - Detect Python/Django
   - Clone repository
   - Bắt đầu build

### 3.3 Xem Build Process

Railway Dashboard sẽ hiện:

- 🔨 **Building...** - Đang cài dependencies
- Logs sẽ hiện quá trình cài đặt
- Đợi 2-3 phút

---

## 📋 Bước 4: Add PostgreSQL Database

Django cần database. Railway cung cấp PostgreSQL miễn phí!

### 4.1 Add Database Service

1. Trong project dashboard, click **"New"**
2. Chọn **"Database"**
3. Chọn **"Add PostgreSQL"**

Railway sẽ:

- ✅ Tạo PostgreSQL instance
- ✅ Tự động set biến `DATABASE_URL`
- ✅ Connect với Django app

### 4.2 Verify Database Connection

1. Click vào **PostgreSQL** service
2. Tab **"Variables"** - Bạn sẽ thấy `DATABASE_URL`
3. Tab **"Data"** - Có thể xem database sau này

---

## 📋 Bước 5: Configure Environment Variables

Django cần một số environment variables.

### 5.1 Vào Web Service Settings

1. Click vào **web service** (tên repo của bạn)
2. Tab **"Variables"**

### 5.2 Add Variables

Click **"New Variable"** và thêm:

```
SECRET_KEY
```

**Value:** Generate secret key mới

```bash
# Chạy local để generate:
python3 -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

Copy output và paste vào Railway

```
DEBUG
```

**Value:** `False`

```
ALLOWED_HOSTS
```

**Value:** `.railway.app`

```
DJANGO_SETTINGS_MODULE
```

**Value:** `config.settings`

### 5.3 Lưu Variables

Railway tự động save. Không cần click gì thêm.

---

## 📋 Bước 6: Deploy

### 6.1 Trigger Deploy

Sau khi add variables:

1. Railway sẽ tự động **redeploy**
2. Hoặc click **"Deploy"** nếu không tự động

### 6.2 Xem Deploy Logs

1. Tab **"Deployments"** - Xem lịch sử deploy
2. Click vào deployment mới nhất
3. Tab **"Build Logs"** - Xem quá trình build
4. Tab **"Deploy Logs"** - Xem app có chạy không

**Đợi 3-5 phút** cho đến khi thấy:

```
✅ Deployment successful
```

---

## 📋 Bước 7: Get Application URL

### 7.1 Generate Public URL

1. Vào web service
2. Tab **"Settings"**
3. Section **"Networking"**
4. Click **"Generate Domain"**

Railway sẽ tạo URL dạng:

```
https://your-app-name-production.up.railway.app
```

### 7.2 Test Application

1. Copy URL
2. Mở trong browser
3. Bạn sẽ thấy ứng dụng MoneyManager!

**Nếu thấy lỗi 502/503:**

- Đợi thêm 1-2 phút (app đang start)
- Check Deploy Logs xem có lỗi gì

---

## 📋 Bước 8: Run Migrations & Create Superuser

App đã deploy nhưng database chưa có tables. Cần chạy migrations.

### 8.1 Vào Railway CLI

Railway có built-in shell để run commands.

**Option A: Qua Web UI**

1. Web service → Tab **"Deployments"**
2. Click deployment đang chạy
3. **"View Logs"**
4. Không thể run commands trực tiếp qua UI

**Option B: Cài Railway CLI (KHUYẾN NGHỊ)**

```bash
# Cài Railway CLI
npm install -g @railway/cli

# Hoặc dùng brew
brew install railway

# Login
railway login

# Link project
cd /Users/abanh/Library/CloudStorage/OneDrive-Personal/Documents/expenses_prj/expenses
railway link
```

Chọn project và service từ danh sách.

### 8.2 Run Migrations

```bash
# Migrate database
railway run python manage.py migrate

# Create superuser
railway run python create_superuser.py
```

Hoặc tự động chạy mỗi deploy:

**Cách tốt hơn:** Migrations đã được run tự động qua `Procfile`:

```
release: python manage.py migrate
```

Chỉ cần run `create_superuser.py`:

```bash
railway run python create_superuser.py
```

---

## 📋 Bước 9: Update Code (Sau Này)

Khi có code mới:

```bash
cd /Users/abanh/Library/CloudStorage/OneDrive-Personal/Documents/expenses_prj

# Make changes...

# Commit
git add .
git commit -m "Add new feature"

# Push
git push
```

**Railway tự động:**

- Detect git push
- Build lại app
- Deploy phiên bản mới
- Zero downtime!

---

## ✅ Checklist Deploy Hoàn Chỉnh

- [ ] Push code lên GitHub
- [ ] Tạo Railway account (GitHub login)
- [ ] New Project → Deploy from GitHub
- [ ] Add PostgreSQL database
- [ ] Set environment variables (SECRET_KEY, DEBUG, ALLOWED_HOSTS)
- [ ] Generate domain
- [ ] Test app tại URL
- [ ] Run migrations (tự động qua Procfile)
- [ ] Create superuser (railway run)
- [ ] Login và test tất cả features

---

## 🎯 Tổng Kết

**Railway URLs:**

- Dashboard: https://railway.app/dashboard
- Your app: `https://your-app.up.railway.app`
- Database: Xem trong PostgreSQL service

**Commands Hay Dùng:**

```bash
# Link local project
railway link

# Run command on Railway
railway run <command>

# View logs
railway logs

# Open in browser
railway open
```

---

## 💡 Tips & Tricks

### Xem Logs Real-time

```bash
railway logs -f
```

### SSH vào Container (Debug)

```bash
railway shell
```

### Check Environment Variables

Railway Dashboard → Service → Variables tab

### Database Management

1. Railway Dashboard → PostgreSQL → Connect
2. Copy connection string
3. Dùng tool như pgAdmin hoặc TablePlus

---

## 🚨 Troubleshooting

### Lỗi: Application failed to respond

- Check Deploy Logs
- Verify `Procfile` đúng
- Ensure `gunicorn` trong requirements.txt

### Lỗi: 502 Bad Gateway

- App đang start (đợi 1-2 phút)
- Check logs: `railway logs`

### Lỗi: Database connection refused

- Verify PostgreSQL service đang chạy
- Check `DATABASE_URL` variable exists

### Static files không load

- Run: `railway run python manage.py collectstatic --noinput`
- Verify `whitenoise` trong requirements.txt

---

## 💰 Chi Phí

**Free Tier:**

- $5 credit/tháng
- PostgreSQL database miễn phí
- 500 hours execution
- 100GB bandwidth

**Estimated usage cho MoneyManager:**

- ~$3-4/tháng (nằm trong $5 free credit!)

**Nếu vượt free tier:**

- $0.000463/minute execution time
- ~$20/tháng cho production app với traffic trung bình

---

**🎉 Chúc mừng! App của bạn đã live trên Railway!**

Vào URL để xem thành quả: `https://your-app.up.railway.app` 🚀
