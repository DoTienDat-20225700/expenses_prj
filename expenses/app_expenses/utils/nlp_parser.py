"""
Module NLP Parser cho tiếng Việt
Xử lý natural language input để trích xuất thông tin chi tiêu
"""
import re
from datetime import datetime, timedelta
from django.utils import timezone


class ExpenseNLPParser:
    """
    Parser để phân tích câu nói/text tiếng Việt và trích xuất thông tin chi tiêu
    Ví dụ: "Vừa ăn sáng hết 50k" -> amount: 50000, category_hint: "ăn uống", time: now
    """
    
    # Từ khóa danh mục chi tiêu phổ biến
    CATEGORY_KEYWORDS = {
        'ăn uống': ['ăn', 'uống', 'cơm', 'phở', 'bún', 'cafe', 'cà phê', 'trà', 'sữa', 
                    'bánh', 'nhậu', 'đồ ăn', 'thức ăn', 'ăn sáng', 'ăn trưa', 'ăn tối',
                    'bữa sáng', 'bữa trưa', 'bữa tối', 'quán', 'nhà hàng', 'buffet'],
        'di chuyển': ['xe', 'taxi', 'grab', 'gojek', 'be', 'xăng', 'xe bus', 'xe buýt', 
                      'tàu', 'máy bay', 'vé', 'đi lại', 'di chuyển', 'xe ôm', 'moto'],
        'mua sắm': ['mua', 'shopping', 'quần áo', 'giày', 'dép', 'túi', 'áo', 
                    'váy', 'đồ', 'sắm', 'phụ kiện'],
        'giải trí': ['xem phim', 'phim', 'game', 'karaoke', 'du lịch', 'bar', 
                     'vui chơi', 'giải trí', 'spa', 'massage'],
        'sức khỏe': ['thuốc', 'bệnh viện', 'khám', 'doctor', 'bác sĩ', 'y tế', 
                     'vaccine', 'tiêm', 'sức khỏe'],
        'học tập': ['sách', 'học', 'khóa học', 'course', 'học phí', 'trường'],
        'hóa đơn': ['điện', 'nước', 'internet', 'wifi', 'điện thoại', 'mobile', 
                    'tiền nhà', 'thuê nhà', 'phí', 'hóa đơn', 'bill'],
        'khác': ['khác', 'other', 'mua'],
    }
    
    # Từ khóa thời gian
    TIME_KEYWORDS = {
        'now': ['vừa', 'vừa mới', 'vừa rồi', 'mới', 'mới đây', 'bây giờ', 'giờ', 'lúc này'],
        'today': ['hôm nay', 'h nay', 'hnay', 'ngày hôm nay'],
        'yesterday': ['hôm qua', 'h qua', 'hqua', 'qua'],
        'day_before_yesterday': ['hôm kia', 'h kia'],
        'tomorrow': ['ngày mai', 'mai'],
    }
    
    # Pattern cho số tiền tiếng Việt
    AMOUNT_PATTERNS = [
        # 50k, 50K, 50.5k
        (r'(\d+(?:[.,]\d+)?)\s*k(?!\w)', lambda x: float(x.replace(',', '.')) * 1000),
        # 5 triệu, 1.5 triệu, 2,5 triệu
        (r'(\d+(?:[.,]\d+)?)\s*tri[eệ]u', lambda x: float(x.replace(',', '.')) * 1000000),
        # 50 nghìn, 100 ngàn
        (r'(\d+(?:[.,]\d+)?)\s*(?:nghìn|ngàn|ngh[iì]n)', lambda x: float(x.replace(',', '.')) * 1000),
        # 1 tỷ
        (r'(\d+(?:[.,]\d+)?)\s*t[yỷ]', lambda x: float(x.replace(',', '.')) * 1000000000),
        # 50.000, 50000 (số thuần)
        (r'(\d{1,3}(?:[.,]\d{3})+)(?!\s*k)', lambda x: float(x.replace(',', '').replace('.', ''))),
        # Số đơn giản: 50, 100, 1000 (phải > 100 để tránh nhầm)
        (r'\b(\d{3,})(?!\s*[ktm])\b', lambda x: float(x)),
    ]
    
    def parse(self, text, user):
        """
        Parse text input và trả về dict với thông tin chi tiêu
        
        Args:
            text: Chuỗi input từ người dùng
            user: Django User object để tìm category
            
        Returns:
            dict: {
                'amount': Decimal,
                'category_hint': str (tên gợi ý danh mục),
                'category_id': int hoặc None,
                'description': str,
                'date': date object,
                'success': bool,
                'error': str (nếu có lỗi)
            }
        """
        text = text.lower().strip()
        
        if not text:
            return {'success': False, 'error': 'Vui lòng nhập nội dung'}
        
        # 1. Trích xuất số tiền
        amount = self._extract_amount(text)
        if not amount:
            return {
                'success': False, 
                'error': 'Không tìm thấy số tiền. Ví dụ: "50k", "50.000", "1 triệu"'
            }
        
        # 2. Trích xuất thời gian
        date = self._extract_date(text)
        
        # 3. Trích xuất gợi ý danh mục
        category_hint, category_keywords = self._extract_category_hint(text)
        
        # 4. Tìm category_id từ database dựa vào category_hint
        category_id = self._find_category_id(category_hint, user)
        
        # 5. Tạo description (giữ nguyên text gốc hoặc làm sạch)
        description = self._clean_description(text)
        
        return {
            'success': True,
            'amount': amount,
            'category_hint': category_hint,
            'category_keywords': category_keywords,
            'category_id': category_id,
            'description': description,
            'date': date,
            'original_text': text
        }
    
    def _extract_amount(self, text):
        """Trích xuất số tiền từ text"""
        for pattern, converter in self.AMOUNT_PATTERNS:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                try:
                    number_str = match.group(1)
                    amount = converter(number_str)
                    if amount > 0:
                        return round(amount, 2)
                except (ValueError, IndexError):
                    continue
        return None
    
    def _extract_date(self, text):
        """Trích xuất ngày tháng từ text"""
        today = timezone.now().date()
        
        # Kiểm tra các từ khóa thời gian
        for time_key, keywords in self.TIME_KEYWORDS.items():
            for keyword in keywords:
                if keyword in text:
                    if time_key == 'now' or time_key == 'today':
                        return today
                    elif time_key == 'yesterday':
                        return today - timedelta(days=1)
                    elif time_key == 'day_before_yesterday':
                        return today - timedelta(days=2)
                    elif time_key == 'tomorrow':
                        return today + timedelta(days=1)
        
        # Kiểm tra pattern ngày cụ thể: 15/3, 15-3, 15/03/2024
        date_patterns = [
            r'(?:ngày\s+)?(\d{1,2})[/-](\d{1,2})(?:[/-](\d{2,4}))?',  # 15/3, 15/3/2024
            r'(?:ngày\s+)?(\d{1,2})\s+tháng\s+(\d{1,2})',  # 15 tháng 3
        ]
        
        for pattern in date_patterns:
            match = re.search(pattern, text)
            if match:
                try:
                    day = int(match.group(1))
                    month = int(match.group(2))
                    year = int(match.group(3)) if match.lastindex >= 3 and match.group(3) else today.year
                    
                    # Xử lý năm 2 chữ số
                    if year < 100:
                        year += 2000
                    
                    return datetime(year, month, day).date()
                except (ValueError, AttributeError):
                    pass
        
        # Mặc định là hôm nay
        return today
    
    def _extract_category_hint(self, text):
        """Trích xuất gợi ý danh mục từ text"""
        # Tìm danh mục có nhiều keyword match nhất
        best_match_category = 'khác'
        best_match_count = 0
        matched_keywords = []
        
        for category, keywords in self.CATEGORY_KEYWORDS.items():
            match_count = 0
            temp_keywords = []
            for keyword in keywords:
                if keyword in text:
                    match_count += 1
                    temp_keywords.append(keyword)
            
            if match_count > best_match_count:
                best_match_count = match_count
                best_match_category = category
                matched_keywords = temp_keywords
        
        return best_match_category, matched_keywords
    
    def _find_category_id(self, category_hint, user):
        """
        Tìm category_id từ database dựa vào category_hint
        Tìm category của user có tên giống hoặc tương tự category_hint
        """
        from app_expenses.models import Category
        
        # Tìm exact match
        category = Category.objects.filter(
            user=user, 
            name__iexact=category_hint
        ).first()
        
        if category:
            return category.id
        
        # Tìm similar match (chứa từ khóa)
        category = Category.objects.filter(
            user=user,
            name__icontains=category_hint.split()[0]  # Lấy từ đầu tiên
        ).first()
        
        if category:
            return category.id
        
        return None
    
    def _clean_description(self, text):
        """Làm sạch text để làm description"""
        # Giữ nguyên text gốc, có thể customize sau
        return text.strip()


# Helper functions để sử dụng từ views
def parse_expense_text(text, user):
    """
    Helper function để parse text input
    """
    parser = ExpenseNLPParser()
    return parser.parse(text, user)
