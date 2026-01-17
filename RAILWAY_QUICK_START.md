# 🚂 Railway Deployment - Quick Start

## ⚡ TÓM TẮT 5 PHÚT

### 1️⃣ Push Code to GitHub

```bash
cd /Users/abanh/Library/CloudStorage/OneDrive-Personal/Documents/expenses_prj
git add .
git commit -m "Ready for Railway"
git push
```

### 2️⃣ Deploy on Railway (Web UI)

1. Vào: https://railway.app
2. Login with GitHub
3. **New Project** → **Deploy from GitHub repo**
4. Select: `expenses_prj`

### 3️⃣ Add Database

1. Click **New** → **Database** → **PostgreSQL**
2. Railway tự động connect với app

### 4️⃣ Set Environment Variables

Click service → **Variables** → Add:

```
SECRET_KEY = <run command dưới để generate>
DEBUG = False
ALLOWED_HOSTS = .railway.app
```

**Generate SECRET_KEY:**

```bash
python3 -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

### 5️⃣ Get URL & Test

1. **Settings** → **Networking** → **Generate Domain**
2. Open URL: `https://your-app.up.railway.app`
3. ✅ Done!

---

## 🔧 Optional: Railway CLI

```bash
# Install
npm install -g @railway/cli

# Login & link
railway login
railway link

# Run migrations (nếu cần)
railway run python manage.py migrate

# Create superuser
railway run python create_superuser.py

# View logs
railway logs -f
```

---

## 📚 Chi Tiết Đầy Đủ

Xem: [RAILWAY_DEPLOYMENT_GUIDE.md](file:///Users/abanh/Library/CloudStorage/OneDrive-Personal/Documents/expenses_prj/RAILWAY_DEPLOYMENT_GUIDE.md)

---

**🎯 Tổng thời gian: 10-15 phút từ đầu đến khi app live!** 🚀
