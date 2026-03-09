# HƯỚNG DẪN TRỢ LÝ ẢO (CHATBOT/VOICE ASSISTANT)

## 📝 Tổng quan

Tính năng Trợ lý ảo là một **widget cố định ở góc dưới màn hình**, xuất hiện trên mọi trang khi đã đăng nhập. Người dùng có thể nhập chi tiêu bằng:

- **Văn bản chat**: Gõ câu nói tự nhiên
- **Giọng nói**: Sử dụng microphone để nói

Hệ thống sẽ tự động phân tích và trích xuất:

- 💰 **Số tiền**: 50k, 100 nghìn, 1.5 triệu, etc.
- 📁 **Danh mục**: Ăn uống, Di chuyển, Mua sắm, etc.
- 📅 **Thời gian**: Hôm nay, hôm qua, vừa rồi, etc.

## 🎯 Cách sử dụng

### 1. Mở Trợ lý ảo

- Sau khi đăng nhập, bạn sẽ thấy **nút tròn màu tím** (🤖) ở góc dưới bên phải màn hình
- Click vào nút để **mở/đóng** cửa sổ chat
- Widget xuất hiện trên **TẤT CẢ các trang** của ứng dụng - bạn có thể nhập chi tiêu bất cứ lúc nào!

### 2. Nhập bằng Text

Gõ câu tự nhiên vào ô input, ví dụ:

- "Vừa ăn sáng hết 50k"
- "Chi 100 nghìn mua đồ ăn hôm qua"
- "Đổ xăng 200.000 đồng"
- "Mua cafe 45k sáng nay"

### 3. Nhập bằng Giọng nói

- Click vào nút 🎤 (microphone)
- Cho phép trình duyệt truy cập microphone
- Nói câu chi tiêu của bạn
- Hệ thống tự động nhận dạng và xử lý

**Lưu ý**: Tính năng nhận dạng giọng nói yêu cầu:

- Trình duyệt Chrome hoặc Edge (hỗ trợ Web Speech API)
- Kết nối internet
- Quyền truy cập microphone

### 4. Xác nhận và Lưu

- Hệ thống hiển thị preview thông tin đã trích xuất
- Kiểm tra lại thông tin (số tiền, danh mục, ngày)
- Có thể thay đổi danh mục nếu cần
- Click **"Lưu chi tiêu"** để hoàn tất

## 🔤 Cú pháp hỗ trợ

### Số tiền

Hỗ trợ nhiều định dạng số tiền tiếng Việt:

- **k**: 50k, 100k, 1.5k
- **nghìn/ngàn**: 50 nghìn, 100 ngàn
- **triệu**: 1 triệu, 1.5 triệu, 2,5 triệu
- **tỷ**: 1 tỷ, 2.5 tỷ
- **Số thuần**: 50000, 50.000

### Thời gian

Hỗ trợ các từ khóa thời gian:

- **Hiện tại**: vừa, vừa rồi, vừa mới, bây giờ, giờ
- **Hôm nay**: hôm nay, h nay, hnay
- **Hôm qua**: hôm qua, h qua, hqua, qua
- **Hôm kia**: hôm kia, h kia
- **Ngày mai**: ngày mai, mai
- **Ngày cụ thể**: 15/3, 15/03/2024, 15 tháng 3

### Danh mục (Tự động nhận dạng)

Hệ thống tự động gợi ý danh mục dựa trên từ khóa:

**Ăn uống**: ăn, uống, cơm, phở, bún, cafe, cà phê, trà, bánh, nhậu, ăn sáng, ăn trưa, ăn tối, nhà hàng, buffet

**Di chuyển**: xe, taxi, grab, gojek, be, xăng, xe bus, xe buýt, tàu, máy bay, vé, đi lại, xe ôm

**Mua sắm**: mua, shopping, quần áo, giày, dép, túi, áo, váy

**Giải trí**: xem phim, phim, game, karaoke, du lịch, bar, vui chơi, spa, massage

**Sức khỏe**: thuốc, bệnh viện, khám, doctor, bác sĩ, y tế, vaccine, tiêm

**Học tập**: sách, học, khóa học, course, học phí, trường

**Hóa đơn**: điện, nước, internet, wifi, điện thoại, tiền nhà, thuê nhà, phí, hóa đơn

## 💡 Ví dụ

### Ví dụ 1: Đơn giản

```
Input: "Ăn sáng 50k"
Output:
  - Số tiền: 50,000 đ
  - Danh mục: Ăn uống
  - Ngày: Hôm nay
  - Mô tả: Ăn sáng 50k
```

### Ví dụ 2: Có thời gian

```
Input: "Hôm qua mua đồ 200 nghìn"
Output:
  - Số tiền: 200,000 đ
  - Danh mục: Mua sắm
  - Ngày: Hôm qua
  - Mô tả: Hôm qua mua đồ 200 nghìn
```

### Ví dụ 3: Chi tiết

```
Input: "Vừa đổ xăng hết 500.000 đồng"
Output:
  - Số tiền: 500,000 đ
  - Danh mục: Di chuyển
  - Ngày: Hôm nay
  - Mô tả: Vừa đổ xăng hết 500.000 đồng
```

### Ví dụ 4: Ngày cụ thể

```
Input: "Chi 1.5 triệu mua điện thoại ngày 10/3"
Output:
  - Số tiền: 1,500,000 đ
  - Danh mục: Mua sắm
  - Ngày: 10/03/2024
  - Mô tả: Chi 1.5 triệu mua điện thoại ngày 10/3
```

## 🔧 Kỹ thuật Implementation

### Backend (Django)

#### 1. NLP Parser (`app_expenses/utils/nlp_parser.py`)

Module xử lý Natural Language Processing cho tiếng Việt:

- **Class `ExpenseNLPParser`**: Parser chính
- **Regex patterns**: Trích xuất số tiền với nhiều định dạng
- **Keyword matching**: Nhận dạng danh mục dựa trên từ khóa
- **Date parsing**: Xử lý các cách nói về thời gian

#### 2. API Endpoints (`app_expenses/views.py`)

**a) `parse_expense_api` (POST: `/api/parse-expense/`)**

- Nhận text input từ client
- Gọi NLP parser để trích xuất thông tin
- Trả về JSON với dữ liệu đã parse

**b) `save_expense_from_chat_api` (POST: `/api/save-expense-from-chat/`)**

- Nhận dữ liệu expense đã parse
- Validate và lưu vào database
- Kiểm tra budget warning
- Train ML model trong background

**c) `chat_assistant` (GET: `/chat-assistant/`)**

- Render giao diện chat
- Cung cấp context (categories, recent expenses)

**d) `chat_history_api` (GET: `/api/chat/history/`)**

- Lấy lịch sử chi tiêu gần đây
- Hỗ trợ pagination

### Frontend (HTML + JavaScript)

#### 1. Template (`templates/ep1/chat_assistant.html`)

- Chat interface với Bootstrap 5
- Responsive design
- Real-time message display

#### 2. Voice Input (Web Speech API)

```javascript
const SpeechRecognition =
  window.SpeechRecognition || window.webkitSpeechRecognition;
recognition = new SpeechRecognition();
recognition.lang = "vi-VN";
```

#### 3. Chat Flow

1. User input (text hoặc voice)
2. Send POST request to `/api/parse-expense/`
3. Display parsed data in confirmation modal
4. User confirms
5. Send POST request to `/api/save-expense-from-chat/`
6. Show success message
7. Reload page to update recent expenses

## 🎨 UI/UX Features

- **Floating Widget Design**: Widget cố định ở góc dưới màn hình, luôn sẵn sàng
- **Persistent Access**: Xuất hiện trên mọi trang, không cần chuyển trang
- **Smooth Animations**: Hiệu ứng mở/đóng mượt mà, professional
- **Responsive Design**: Tự động điều chỉnh kích thước trên mobile, tablet, desktop
- **Real-time Feedback**: Loading states, error messages, success notifications
- **Voice Visual Feedback**: Nút microphone đổi màu đỏ khi đang nghe
- **Confirmation Modal**: Preview chi tiết trước khi lưu
- **Auto-scroll**: Chat tự động scroll xuống bottom khi có tin nhắn mới
- **Dark Mode Support**: Tự động thích ứng với chế độ tối
- **Non-intrusive**: Không che khuất nội dung chính, dễ dàng đóng/mở

## 🔐 Security

- **CSRF Protection**: Tất cả POST requests có CSRF token
- **Authentication Required**: `@login_required` decorator
- **User Isolation**: Chỉ truy cập dữ liệu của user hiện tại
- **Input Validation**: Validate amount, date, category

## 🚀 Future Enhancements

Các tính năng có thể mở rộng:

1. **AI Learning**: Học từ lịch sử để cải thiện gợi ý danh mục
2. **Multi-language**: Hỗ trợ tiếng Anh và các ngôn ngữ khác
3. **Smart Suggestions**: Gợi ý chi tiêu dựa trên patterns
4. **Voice Feedback**: Text-to-speech để trả lời user
5. **Contextual Chat**: Theo dõi context của cuộc hội thoại
6. **OCR Integration**: Upload ảnh hóa đơn để tự động nhập
7. **Export Chat History**: Xuất lịch sử chat thành file

## 📱 Browser Compatibility

### Voice Input (Web Speech API)

- ✅ Chrome/Edge (Desktop & Mobile)
- ❌ Firefox (chưa hỗ trợ)
- ❌ Safari (hỗ trợ hạn chế)

### Text Input

- ✅ Tất cả trình duyệt hiện đại

## 🐛 Troubleshooting

### Vấn đề: Không nhận dạng được giọng nói

**Giải pháp**:

- Kiểm tra trình duyệt (chỉ Chrome/Edge)
- Cho phép quyền truy cập microphone
- Kiểm tra kết nối internet
- Thử reload trang

### Vấn đề: Danh mục không đúng

**Giải pháp**:

- Chọn lại danh mục trong modal xác nhận
- Cập nhật danh mục của user để phù hợp
- System sẽ học từ lịch sử để cải thiện

### Vấn đề: Số tiền không chính xác

**Giải pháp**:

- Sử dụng format rõ ràng: "50k", "100 nghìn"
- Tránh viết tắt quá phức tạp
- Có thể edit sau khi lưu

## 📊 Performance

- **Average parse time**: < 100ms
- **API response time**: < 200ms (không bao gồm ML training)
- **Voice recognition latency**: Phụ thuộc vào Google API

## 🔗 Related Files

```
app_expenses/
├── utils/
│   └── nlp_parser.py          # NLP Parser module
├── views.py                    # API endpoints và chat view
├── urls.py                     # URL routing
└── templates/
    └── ep1/
        ├── chat_assistant.html # Chat interface
        └── base.html           # Navigation menu (updated)
```

## 📝 Testing

### Manual Testing

1. Test các format số tiền khác nhau
2. Test các từ khóa thời gian
3. Test voice input trên các trình duyệt
4. Test với các danh mục khác nhau
5. Test validation và error handling

### Test Cases

- Input rỗng → Error message
- Số tiền âm → Error message
- Ngày không hợp lệ → Error message
- Category không tồn tại → Error message
- Voice không nhận dạng được → Error message

---

**Đã update**: 9 tháng 3, 2026
**Version**: 1.0.0
**Maintainer**: MoneyManager Team
