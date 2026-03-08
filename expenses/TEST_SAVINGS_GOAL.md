# Test Tính năng Gợi ý lộ trình tiết kiệm

## Bước 1: Tạo dữ liệu mẫu (Tùy chọn)

Nếu muốn test nhanh với dữ liệu mẫu:

```bash
python3 manage.py shell < demo_savings_goals.py
```

Script sẽ tạo:
- Chi tiêu mẫu trong 30 ngày gần đây
- 3 mục tiêu tiết kiệm mẫu:
  * Mua Macbook M3 (30 triệu/6 tháng)
  * Du lịch Nhật Bản (50 triệu/1 năm)  
  * Mua xe máy SH (80 triệu, đã 75 triệu - gần hoàn thành)

## Bước 2: Khởi động server

```bash
python3 manage.py runserver
```

## Bước 3: Test các tính năng

### 3.1. Xem danh sách mục tiêu
- Truy cập: Menu → **Tiết Kiệm**
- Hoặc: http://localhost:8000/savings-goals/

**Kiểm tra:**
- ✅ Hiển thị danh sách mục tiêu dạng card
- ✅ Progress bar hiển thị đúng
- ✅ Badges status (Đang thực hiện/Hoàn thành/Quá hạn)
- ✅ Thông tin: hiện tại/mục tiêu/còn thiếu/còn lại
- ✅ Tính và hiển thị "Cần tiết kiệm: X đ/ngày"

### 3.2. Tạo mục tiêu mới
- Click **"Tạo mục tiêu mới"**

**Kiểm tra:**
- ✅ Form hiển thị đầy đủ các trường
- ✅ DatePicker hoạt động
- ✅ Checkbox danh mục cần cắt giảm
- ✅ Validation: ngày đích > ngày bắt đầu
- ✅ Validation: số tiền > 0

**Test case:**
- Tên: "Mua iPhone 16"
- Mục tiêu: 25,000,000đ
- Hiện tại: 0đ
- Thời gian: Từ hôm nay → 3 tháng sau
- Chọn danh mục: Ăn uống, Giải trí

### 3.3. Xem chi tiết & Gợi ý AI (⭐ QUAN TRỌNG)
- Click vào một mục tiêu → Click **"Chi tiết & Gợi ý AI"**

**Kiểm tra:**
- ✅ Hiển thị thông tin tổng quan (tiến độ, số tiền, ngày)
- ✅ Tính đúng "Cần tiết kiệm X đ/ngày"
- ✅ Hiển thị kế hoạch tuần/tháng
- ✅ **Phân tích chi tiêu 30 ngày** theo từng danh mục:
  * Tổng chi 30 ngày
  * Trung bình/ngày
  * % gợi ý cắt giảm (thường 60%)
  * Số tiền tiết kiệm được/ngày
  * Số tiền tiết kiệm được/tháng
- ✅ **Đánh giá mục tiêu**:
  * ✅ Khả thi → badge xanh
  * ⚠️ Khó đạt → badge vàng + gợi ý
- ✅ **Mẹo tiết kiệm** dựa trên số tiền cần:
  * < 50k: "Bỏ 1 ly cafe"
  * 50-100k: "Tự nấu ăn"
  * 100-200k: "Cắt shopping"
  * ≥ 200k: "Tăng thu nhập"

**Test các trường hợp:**
1. **Mục tiêu khả thi**: 
   - Chi tiêu 30 ngày: 5 triệu
   - Cần tiết kiệm: 150k/ngày
   - Có thể cắt: 150k/ngày → ✅ Khả thi

2. **Mục tiêu khó**:
   - Chi tiêu 30 ngày: 3 triệu
   - Cần tiết kiệm: 300k/ngày
   - Có thể cắt: 100k/ngày → ⚠️ Thiếu 200k/ngày

3. **Chưa chọn danh mục**:
   - Hiển thị top 5 danh mục chi nhiều nhất
   - Gợi ý chọn danh mục

### 3.4. Cập nhật tiến độ
- Trong trang chi tiết → Click **"Cập nhật tiến độ"**

**Kiểm tra:**
- ✅ Hiển thị progress bar hiện tại
- ✅ Form nhập số tiền mới
- ✅ Validation: không được âm
- ✅ Sau khi save: progress bar update
- ✅ **Nếu đạt 100%**: Hiển thị thông báo "🎉 Chúc mừng!"
- ✅ Status tự động chuyển "Hoàn thành"

**Test case:**
- Mục tiêu: 30 triệu
- Hiện tại: 20 triệu
- Cập nhật: 30 triệu → Hoàn thành!

### 3.5. Chỉnh sửa mục tiêu
- Click icon ✏️ hoặc button "Chỉnh sửa"

**Kiểm tra:**
- ✅ Form load đúng dữ liệu hiện tại
- ✅ Có thể thay đổi mục tiêu/ngày đích
- ✅ Thay đổi danh mục cần cắt giảm
- ✅ Sau khi save: gợi ý AI update theo thay đổi

### 3.6. Xóa mục tiêu
- Click icon 🗑️ hoặc button "Xóa"

**Kiểm tra:**
- ✅ Hiển thị trang xác nhận
- ✅ Hiển thị thông tin mục tiêu sẽ xóa
- ✅ Warning: "Không thể hoàn tác"
- ✅ Sau khi xác nhận: redirect về danh sách
- ✅ Hiển thị thông báo thành công

## Bước 4: Test Edge Cases

### 4.1. Mục tiêu quá hạn
- Tạo mục tiêu với ngày đích = hôm qua
- **Kỳ vọng**: 
  - Badge "Quá hạn" màu đỏ
  - Gợi ý: "Mục tiêu đã quá hạn. Hãy cân nhắc gia hạn"

### 4.2. Mục tiêu đã hoàn thành
- Cập nhật current_amount >= target_amount
- **Kỳ vọng**:
  - Badge "Hoàn thành" màu xanh
  - is_completed = True
  - Gợi ý: "🎉 Chúc mừng! Bạn đã hoàn thành mục tiêu"

### 4.3. Không có chi tiêu
- User mới, chưa có chi tiêu nào
- **Kỳ vọng**:
  - Vẫn tính được số tiền cần tiết kiệm/ngày
  - Thông báo: "Chưa có dữ liệu chi tiêu để phân tích"

### 4.4. Số ngày còn lại = 0
- Ngày đích = hôm nay
- **Kỳ vọng**:
  - days_remaining = 0
  - daily_savings_needed = 0
  - Không crash

## Bước 5: Test Django Admin

1. Truy cập: http://localhost:8000/admin/
2. Login với superuser
3. Vào **Savings Goals**

**Kiểm tra:**
- ✅ List view hiển thị: tên, user, số tiền, tiến độ%, ngày đích, status
- ✅ Filters: completed, active, user, date
- ✅ Search: tên mục tiêu, username
- ✅ Detail view: Fieldsets rõ ràng
- ✅ filter_horizontal cho categories_to_reduce
- ✅ readonly_fields: created_at, updated_at, progress_percentage

## Kết quả mong đợi

✅ Tất cả tính năng hoạt động đúng
✅ AI gợi ý chính xác dựa trên chi tiêu thực tế
✅ UX/UI mượt mà, responsive
✅ Không có lỗi 500 hoặc crash
✅ Messages hiển thị đúng (success/warning/info)

## Báo lỗi

Nếu gặp lỗi, kiểm tra:
1. Terminal console (Django errors)
2. Browser console (JS errors)
3. Database (python manage.py dbshell)

Tạo issue với:
- Bước tái hiện lỗi
- Screenshot
- Error message đầy đủ
