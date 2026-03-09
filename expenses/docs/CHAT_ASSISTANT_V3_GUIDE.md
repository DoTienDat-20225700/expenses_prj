# Hướng Dẫn Sử Dụng Chat Assistant V3

## 📖 Tổng Quan

Chat Assistant V3 là trợ lý ảo thông minh giúp bạn quản lý tài chính cá nhân thông qua ngôn ngữ tự nhiên. Phiên bản 3.0 mở rộng từ 6 lên **14 loại tác vụ** với độ chính xác **100%**.

## 🎯 Các Tính Năng Chính

### 1. 💰 TẠO GIAO DỊCH

#### Tạo Chi Tiêu (CREATE_EXPENSE)

Nhập chi tiêu một cách tự nhiên:

```
✅ "Ăn sáng 50k"
✅ "Mua đồ 200 nghìn hôm qua"
✅ "Đổ xăng 300k"
✅ "Mua sách 150k danh mục học tập"
```

**Hỗ trợ:**

- Số tiền: k, nghìn, triệu, tr
- Thời gian: hôm nay, hôm qua, ngày DD/MM
- Danh mục tự động nhận diện

#### Tạo Thu Nhập (CREATE_INCOME) 🆕

Thêm thu nhập nhanh chóng:

```
✅ "Nhận lương 10 triệu"
✅ "Được trả 5 triệu"
✅ "Thu được 200k"
✅ "Nhận thưởng 3 triệu"
```

**Tự động:**

- Tạo income source nếu chưa có
- Nhận diện loại thu nhập (lương, thưởng)
- Gán ngày hiện tại

---

### 2. 🔍 TRA CỨU DỮ LIỆU

#### Xem Chi Tiêu (QUERY_EXPENSES)

Hỏi về chi tiêu của bạn:

```
✅ "Tổng chi tiêu hôm nay?"
✅ "Chi bao nhiêu trong tháng?"
✅ "Đã chi bao nhiêu tuần này?"
✅ "Chi tiêu của tôi năm nay?"
```

**Hiển thị:**

- 💰 Tổng chi tiêu
- 📝 Số giao dịch
- 📈 Trung bình/giao dịch
- 📊 Top 3 danh mục chi nhiều nhất

#### Xem Thu Nhập (QUERY_INCOME)

Kiểm tra thu nhập:

```
✅ "Thu nhập tháng này?"
✅ "Tổng thu được bao nhiêu?"
✅ "Kiếm được bao nhiêu tuần này?"
```

**Hiển thị:**

- 💵 Tổng thu nhập
- 📝 Số nguồn thu
- 💼 Chi tiết từng nguồn

#### Xem Tiết Kiệm (QUERY_SAVINGS)

Theo dõi mục tiêu tiết kiệm:

```
✅ "Tình hình tiết kiệm?"
✅ "Đã tiết kiệm bao nhiêu?"
✅ "Mục tiêu tiết kiệm?"
```

**Hiển thị:**

- 🐷 Tiến độ từng mục tiêu
- 💰 Số tiền đã tiết kiệm
- 📊 Phần trăm hoàn thành

#### Xem Ngân Sách (QUERY_BUDGET)

Kiểm tra ngân sách:

```
✅ "Ngân sách còn lại?"
✅ "Đã vượt ngân sách chưa?"
✅ "Tình trạng ngân sách?"
```

**Hiển thị:**

- 💰 Ngân sách tổng
- 💸 Đã sử dụng
- 📊 Phần trăm sử dụng
- Cảnh báo nếu > 80%

#### Tổng Quan (QUERY_SUMMARY)

Xem tổng quan tài chính:

```
✅ "Tổng quan tài chính"
✅ "Tóm tắt tài chính tháng này"
✅ "Tình hình tài chính"
```

**Hiển thị:**

- 💵 Thu nhập
- 💸 Chi tiêu
- 💰 Số dư
- 📊 Ngân sách
- 🐷 Tiết kiệm

#### Top Chi Tiêu (TOP_EXPENSES) 🆕

Xem các khoản chi lớn nhất:

```
✅ "Top chi tiêu tháng này"
✅ "Chi nhiều nhất"
✅ "Những khoản chi lớn nhất tuần này"
✅ "Xem top chi tiêu"
```

**Hiển thị:**

- Top 10 chi tiêu
- 🥇🥈🥉 Medals cho top 3
- Số tiền, mô tả, danh mục, ngày

#### Tìm Kiếm (SEARCH_EXPENSES) 🆕

Tìm chi tiêu theo từ khóa:

```
✅ "Tìm chi tiêu đổ xăng"
✅ "Tìm kiếm giao dịch ăn uống"
✅ "Search chi tiêu grab"
✅ "Có khoản chi nào về cafe không?"
```

**Tìm trong:**

- Description (mô tả)
- Category name (tên danh mục)
- Hiển thị top 10 kết quả

#### Giao Dịch Gần Đây (RECENT_TRANSACTIONS) 🆕

Xem giao dịch mới nhất:

```
✅ "Giao dịch gần đây"
✅ "Chi tiêu mới nhất"
✅ "Vừa chi những gì?"
✅ "Latest transactions"
```

**Hiển thị:**

- 10 giao dịch gần nhất
- Cả thu (💰) và chi (💸)
- Sắp xếp theo thời gian

---

### 3. 📊 PHÂN TÍCH DỮ LIỆU

#### So Sánh Thời Kỳ (COMPARE_PERIODS) 🆕

So sánh chi tiêu giữa các khoảng thời gian:

```
✅ "So sánh tháng này với tháng trước"
✅ "Chi tiêu hơn tuần trước như thế nào?"
✅ "So với tháng trước thế nào?"
```

**Phân tích:**

- Chi tiêu kỳ hiện tại
- Chi tiêu kỳ trước
- Chênh lệch (số tiền + %)
- 📈 Tăng hoặc 📉 Giảm
- Đánh giá

**Hỗ trợ:**

- Tuần này vs tuần trước
- Tháng này vs tháng trước (mặc định)

#### Danh Mục Chi Tiêu (QUERY_CATEGORIES) 🆕

Phân tích chi tiêu theo danh mục:

```
✅ "Xem danh mục chi tiêu"
✅ "Các danh mục chi tiêu tháng này"
✅ "Phân bố chi tiêu theo danh mục"
```

**Hiển thị:**

- Progress bar trực quan (█████░░░░░)
- Phần trăm từng danh mục
- Số tiền và số giao dịch
- Sắp xếp từ cao xuống thấp

#### Báo Cáo Tháng (MONTHLY_REPORT) 🆕

Báo cáo chi tiết toàn diện:

```
✅ "Báo cáo tháng này"
✅ "Chi tiết tháng"
✅ "Báo cáo chi tiết tháng"
✅ "Monthly report"
```

**Nội dung:**

**TỔNG QUAN:**

- 💵 Thu nhập
- 💸 Chi tiêu
- 💰 Số dư
- 📊 Ngân sách (% sử dụng)

**THỐNG KÊ:**

- 📝 Số giao dịch
- 📈 Trung bình/ngày
- 💳 Trung bình/giao dịch

**TOP CHI TIÊU:**

- 🥇🥈🥉 Top 3 khoản chi lớn

**TOP DANH MỤC:**

- Top 5 danh mục + %

**ĐÁNH GIÁ:**

- Cảnh báo vượt chi
- Tỷ lệ tiết kiệm
- Khuyến nghị

---

### 4. 💡 TƯ VẤN & HỖ TRỢ

#### Lời Khuyên Tài Chính (FINANCIAL_ADVICE) 🆕

Nhận tư vấn thông minh:

```
✅ "Tư vấn tiết kiệm"
✅ "Nên làm gì để giảm chi tiêu?"
✅ "Lời khuyên tài chính"
✅ "Mẹo tiết kiệm"
```

**Phân tích:**

**Ngân sách:**

- Tỷ lệ sử dụng
- Cảnh báo nếu > 90%
- Hướng dẫn cụ thể

**Thu - Chi:**

- Tính số dư
- Tỷ lệ tiết kiệm
- Khuyến nghị tiết kiệm ≥ 20%

**Danh mục:**

- Danh mục chi nhiều nhất
- Phần trăm so với tổng
- Gợi ý cân đối

**Mẹo chung:**

- Lập kế hoạch
- Ghi chép đầy đủ
- Đặt mục tiêu
- Review định kỳ

#### Trợ Giúp (HELP)

Xem hướng dẫn:

```
✅ "Giúp tôi"
✅ "Help"
✅ "Hướng dẫn sử dụng"
✅ "Có thể làm gì?"
```

---

## ⏰ Xử Lý Thời Gian

Bot hiểu các cụm từ thời gian:

### Ngày:

- **Hôm nay**: "Chi bao nhiêu hôm nay?"
- **Hôm qua**: "Chi tiêu hôm qua"
- **Ngày cụ thể**: "Mua đồ 100k ngày 15/01"

### Tuần:

- **Tuần này**: "Chi tiêu tuần này?"
- **Tuần trước**: "So với tuần trước"

### Tháng:

- **Tháng này**: "Tổng chi tháng này?"
- **Tháng trước**: "Chi tháng trước"

### Năm:

- **Năm này**: "Thu nhập năm nay?"
- **Năm trước**: "So với năm trước"

---

## 🎨 Định Dạng Văn Bản

Bot sử dụng emoji và markdown để dễ đọc:

### Emoji:

- 💰 💵 💸 - Tiền
- 📊 📈 📉 - Thống kê
- ✅ ❌ ⚠️ - Trạng thái
- 🥇🥈🥉 - Top 3
- 🐷 💼 🎯 - Mục tiêu

### Markdown:

- **Bold** cho con số quan trọng
- _Italic_ cho ghi chú
- Line breaks cho dễ đọc

---

## 📱 Cách Sử Dụng

### 1. Mở Chat Widget

- Widget ở góc dưới bên phải màn hình
- Click vào icon 💬 để mở/đóng
- Luôn sẵn sàng trên mọi trang

### 2. Nhập/Nói

- **Gõ**: Nhập câu tự nhiên
- **Giọng nói**: Click 🎤 và nói (tiếng Việt)

### 3. Xem Kết Quả

- Bot trả lời ngay lập tức
- Thông tin được format đẹp
- Có thể cuộn xem lịch sử

---

## 💪 Tips Sử Dụng

### 1. Nói Tự Nhiên

Không cần cú pháp chính xác. Bot hiểu ngôn ngữ tự nhiên:

```
✅ "Hôm nay tôi chi bao nhiêu?"
✅ "Chi bao nhiêu hôm nay?"
✅ "Chi hôm nay tổng là bao nhiêu thế?"
```

### 2. Kết Hợp Thông Tin

Một câu có thể chứa nhiều thông tin:

```
✅ "Ăn sáng 50k hôm qua"
    → Nhận diện: số tiền, thời gian, danh mục
```

### 3. Dùng Từ Khóa

Các từ sau giúp bot hiểu rõ hơn:

- **Hỏi**: bao nhiêu, tổng, có, đã
- **Tạo**: chi, mua, ăn, nhận
- **Phân tích**: so sánh, top, tìm kiếm
- **Tư vấn**: nên, lời khuyên, mẹo

### 4. Thử Giọng Nói

Voice input rất tiện lợi:

- Click 🎤
- Nói câu của bạn
- Bot tự động nhận diện

---

## ❓ FAQ

**Q: Bot có hiểu tiếng lóng không?**  
A: Có! "50k", "100 nghìn", "2 triệu" đều được hiểu.

**Q: Có thể sửa giao dịch qua chat không?**  
A: Chưa hỗ trợ. Cần sửa trên giao diện chính.

**Q: Bot có nhớ context không?**  
A: Mỗi câu được xử lý độc lập. Chưa có context memory.

**Q: Độ chính xác là bao nhiêu?**  
A: 100% trên 37 test cases đa dạng.

**Q: Có hỗ trợ offline không?**  
A: Không. Cần kết nối internet.

**Q: Bot có lưu lịch sử chat không?**  
A: Có, trong session hiện tại. Clear khi reload page.

---

## 🔧 Troubleshooting

### Bot không hiểu câu của tôi?

- Thử đơn giản hóa câu
- Dùng từ khóa rõ ràng hơn
- Gõ "help" để xem ví dụ

### Voice input không hoạt động?

- Check microphone permissions
- Chỉ hỗ trợ Chrome/Edge
- Cần HTTPS connection

### Kết quả không đúng?

- Kiểm tra dữ liệu đã nhập
- Refresh page và thử lại
- Báo lỗi cho admin

---

## 📊 Accuracy

**Test Coverage**: 37 test cases  
**Success Rate**: 100% (37/37)  
**Intent Types**: 14  
**Languages**: Vietnamese, English (mixed)

---

## 🚀 Version History

- **V1.0**: Basic expense creation
- **V2.0**: Multi-intent queries
- **V3.0**: Expanded to 14 intents (100% accuracy)

---

**Cần hỗ trợ?** Gõ **"help"** hoặc **"giúp"** để xem hướng dẫn nhanh!

**Góp ý?** Liên hệ admin để đề xuất tính năng mới! 💡
