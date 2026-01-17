# 🔧 Railway Deployment Fix - Build Error

## ❌ Lỗi Gốc

**Error:** "Error creating build plan with Railpack"

**Nguyên nhân:**

- Railway deploy từ root directory (`expenses_prj/`)
- Nhưng `Procfile`, `runtime.txt`, `requirements.txt` nằm trong `expenses/` subdirectory
- Railway không tìm thấy các files này → không biết cách build

---

## ✅ Giải Pháp Đã Áp Dụng

### 1. Copy Files Lên Root Level

Đã copy các files cần thiết:

```
expenses_prj/
├── Procfile              ✅ NEW (from expenses/)
├── runtime.txt           ✅ NEW (from expenses/)
├── requirements.txt      ✅ NEW (from expenses/)
├── railway.json          ✅ NEW (config file)
└── expenses/
    ├── Procfile          (giữ lại)
    ├── runtime.txt       (giữ lại)
    ├── requirements.txt  (giữ lại)
    └── ...
```

### 2. Cập Nhật Procfile

**Old (không hoạt động ở root):**

```
release: python manage.py migrate
web: gunicorn config.wsgi --bind 0.0.0.0:$PORT
```

**New (cd vào expenses/ trước):**

```
release: cd expenses && python manage.py migrate
web: cd expenses && gunicorn config.wsgi --bind 0.0.0.0:$PORT
```

### 3. Tạo railway.json Config

Tạo file `railway.json` để Railway hiểu cấu trúc project:

```json
{
  "build": {
    "builder": "NIXPACKS",
    "buildCommand": "cd expenses && pip install -r requirements.txt"
  },
  "deploy": {
    "startCommand": "cd expenses && gunicorn config.wsgi --bind 0.0.0.0:$PORT",
    "healthcheckPath": "/"
  }
}
```

---

## 🚀 Deploy Lại

### Push lên GitHub:

```bash
git add Procfile runtime.txt requirements.txt railway.json
git commit -m "Fix Railway deployment - add files at root level"
git push
```

✅ **Đã push thành công!**

### Railway Auto-Deploy:

Railway sẽ tự động:

1. Detect git push mới
2. Tìm thấy `Procfile`, `runtime.txt`, `requirements.txt` ở root
3. Build lại project
4. Deploy thành công ✅

---

## 🎯 Next Steps

### 1. Check Railway Dashboard

Quay lại Railway dashboard, bạn sẽ thấy:

- 🔄 **Building...** - Railway đang build lại
- Logs sẽ hiện quá trình install dependencies
- ⏰ Đợi 2-3 phút

### 2. Verify Build Success

Khi thấy:

```
✅ Build successful
✅ Deployment successful
```

→ App đã deploy thành công!

### 3. Test Application

1. Vào service → **Settings** → **Generate Domain** (nếu chưa có)
2. Open URL: `https://your-app.up.railway.app`
3. Nếu thấy homepage → ✅ **SUCCESS!**

---

## 🔍 Troubleshooting

### Nếu vẫn lỗi build:

**Check logs:**

1. Railway Dashboard → Service → Deployments
2. Click deployment mới nhất
3. View **Build Logs**

**Common issues:**

- Missing dependencies: Check `requirements.txt`
- Python version: Verify `runtime.txt` has `python-3.10.14`
- Database issues: Ensure PostgreSQL service is running

### Nếu app crashes sau deploy:

**Check logs:**

```bash
railway logs -f
```

**Common issues:**

- Missing env vars: Add `SECRET_KEY`, `DEBUG`, `ALLOWED_HOSTS`
- Database not connected: Verify `DATABASE_URL` exists
- Port binding: Railway sets `$PORT` automatically

---

## ✅ Summary

**Problem:** Railway couldn't find build files
**Solution:** Moved Procfile, runtime.txt, requirements.txt to root + created railway.json
**Status:** Code pushed, Railway auto-deploying

**Expected result:** App live in 5 minutes! 🚀

---

Quay lại Railway dashboard để xem build progress!
