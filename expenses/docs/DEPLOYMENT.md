# Hướng dẫn Deploy ứng dụng Django lên Render

## Bước 1: Chuẩn bị Git Repository

1. Đảm bảo code của bạn đã được push lên GitHub/GitLab/Bitbucket:

```bash
git init
git add .
git commit -m "Initial commit for Render deployment"
git branch -M main
git remote add origin <your-git-repo-url>
git push -u origin main
```

## Bước 2: Tạo tài khoản Render

1. Truy cập [render.com](https://render.com)
2. Đăng ký tài khoản miễn phí
3. Kết nối với Git repository của bạn (GitHub/GitLab/Bitbucket)

## Bước 3: Deploy từ Dashboard

### Option A: Deploy tự động với render.yaml (Khuyến nghị)

1. Trong Render Dashboard, chọn **New** → **Blueprint**
2. Chọn repository của bạn
3. Render sẽ tự động phát hiện file `render.yaml` và tạo:
   - Web Service cho ứng dụng Django
   - PostgreSQL Database (Free tier)

### Option B: Deploy thủ công

1. **Tạo PostgreSQL Database:**

   - Chọn **New** → **PostgreSQL**
   - Name: `expenses-db`
   - Region: Singapore (hoặc gần nhất)
   - Plan: Free
   - Tạo database

2. **Tạo Web Service:**
   - Chọn **New** → **Web Service**
   - Chọn repository của bạn
   - Điền thông tin:
     - **Name**: `expenses-app`
     - **Region**: Singapore
     - **Branch**: `main`
     - **Runtime**: Python 3
     - **Build Command**: `./build.sh`
     - **Start Command**: `gunicorn config.wsgi:application -c gunicorn_config.py`
     - **Plan**: Free

## Bước 4: Cấu hình Environment Variables

Trong phần **Environment** của Web Service, thêm các biến sau:

### Bắt buộc:

```
DEBUG=False
SECRET_KEY=<Render sẽ tự động generate>
DATABASE_URL=<Chọn từ PostgreSQL database vừa tạo>
```

### Cloudinary (cho upload ảnh):

```
CLOUDINARY_URL=cloudinary://api_key:api_secret@cloud_name
CLOUDINARY_CLOUD_NAME=your_cloud_name
CLOUDINARY_API_KEY=your_api_key
CLOUDINARY_API_SECRET=your_api_secret
```

**Lấy thông tin Cloudinary:**

1. Đăng ký tài khoản tại [cloudinary.com](https://cloudinary.com)
2. Vào Dashboard, copy thông tin API

## Bước 5: Deploy

1. Click **Create Web Service** hoặc **Apply** (nếu dùng Blueprint)
2. Render sẽ tự động:
   - Clone repository
   - Chạy `build.sh` (install dependencies, collectstatic, migrate)
   - Start ứng dụng với Gunicorn
   - Deploy lên domain: `https://expenses-app.onrender.com`

## Bước 6: Tạo Superuser

Sau khi deploy thành công:

1. Vào **Shell** tab trong Render Dashboard
2. Chạy lệnh:

```bash
python create_superuser.py
```

Hoặc tạo thủ công:

```bash
python manage.py createsuperuser
```

## Kiểm tra Log

- Vào tab **Logs** để xem quá trình build và runtime logs
- Nếu có lỗi, check logs để debug

## Lưu ý quan trọng

### Free Tier Limitations:

- Web service sẽ tự động **sleep** sau 15 phút không hoạt động
- Lần truy cập đầu tiên sau khi sleep sẽ mất ~30 giây để wake up
- 750 giờ/tháng (miễn phí)
- 512MB RAM
- PostgreSQL: 1GB storage, expires sau 90 ngày (cần refresh)

### Cập nhật ứng dụng:

- Mỗi khi push code mới lên branch `main`, Render sẽ tự động deploy lại
- Hoặc click **Manual Deploy** trong Dashboard

### Custom Domain (Optional):

1. Vào **Settings** → **Custom Domain**
2. Add domain của bạn
3. Cấu hình DNS theo hướng dẫn

## Troubleshooting

### Lỗi "Application failed to start"

- Check logs trong tab **Logs**
- Đảm bảo `build.sh` có quyền execute: `chmod +x build.sh`
- Verify `requirements.txt` không có package conflict

### Lỗi Database Connection

- Kiểm tra `DATABASE_URL` đã được set đúng
- Đảm bảo PostgreSQL database đang running

### Lỗi Static Files không load

- Check `STATIC_ROOT` và `STATICFILES_STORAGE` trong settings.py
- Verify `python manage.py collectstatic` chạy thành công trong build

### Lỗi Cloudinary

- Verify API credentials
- Đảm bảo `CLOUDINARY_URL` format đúng: `cloudinary://api_key:api_secret@cloud_name`

## Monitoring

- **Health Check**: Render tự động ping ứng dụng
- **Metrics**: Xem CPU, Memory usage trong Dashboard
- **Alerts**: Setup email alerts khi service down

## Tài liệu tham khảo

- [Render Django Documentation](https://render.com/docs/deploy-django)
- [Render Free Tier Details](https://render.com/docs/free)
