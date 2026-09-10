"""
Chat Intent Detection và Query Handler
Phân tích câu hỏi/yêu cầu của user và xử lý
"""
import re
import logging
from datetime import datetime, timedelta
from django.utils import timezone
from django.db.models import Sum, Count, Avg
from decimal import Decimal

logger = logging.getLogger(__name__)


class ChatIntentDetector:
    """
    Detect intent từ user input
    Các intent:
    - CREATE_EXPENSE: Tạo chi tiêu mới
    - CREATE_INCOME: Tạo thu nhập nhanh
    - CREATE_RECURRING_EXPENSE: Tạo chi tiêu định kỳ
    - CREATE_RECURRING_INCOME: Tạo thu nhập định kỳ
    - EDIT_EXPENSE: Sửa chi tiêu
    - DELETE_EXPENSE: Xóa chi tiêu
    - QUERY_EXPENSES: Hỏi về chi tiêu
    - QUERY_INCOME: Hỏi về thu nhập
    - QUERY_SAVINGS: Hỏi về tiết kiệm
    - QUERY_BUDGET: Hỏi về ngân sách
    - QUERY_SUMMARY: Hỏi tổng quan
    - TOP_EXPENSES: Xem top chi tiêu lớn nhất
    - SEARCH_EXPENSES: Tìm kiếm chi tiêu
    - RECENT_TRANSACTIONS: Giao dịch gần đây
    - COMPARE_PERIODS: So sánh các khoảng thời gian
    - FINANCIAL_ADVICE: Lời khuyên tài chính
    - QUERY_CATEGORIES: Xem danh mục
    - MONTHLY_REPORT: Báo cáo tháng chi tiết
    - GREETING: Chào hỏi
    - HELP: Hỏi trợ giúp
    - OUT_OF_SCOPE: Câu hỏi ngoài lĩnh vực
    """
    
    # Từ khóa liên quan đến tài chính (in scope)
    FINANCE_KEYWORDS = [
        'chi', 'tiêu', 'chi tiêu', 'chi bao', 'chi tất',
        'tài chính', 'tiền', 'đồng',  # Removed 'đ' - too short, false positives
        'thu', 'thu nhập', 'lương', 'kiếm', 'được',
        'tiết kiệm', 'tiết', 'mục tiêu', 'goals',
        'ngân sách', 'budget', 'hạn mức', 'vượt',
        'giao dịch', 'transaction', 'tổng', 'số',
        'danh mục', 'category', 'ăn', 'uống', 'mua', 'shopping',
        'grab', 'taxi', 'xăng', 'cafe', 'gym', 'phone',
        'tháng', 'tuần', 'ngày', 'hôm', 'năm', 'định kỳ',
        'tư vấn', 'advice', 'khuyên', 'mẹo', 'tips',
        'báo cáo', 'report', 'phân tích', 'analyze',
        'so sánh', 'compare', 'top', 'lớn nhất',
        'tìm', 'search', 'gần đây', 'mới nhất', 'vừa',
        'bao nhiêu', 'tổng',  # Removed 'có', 'đã' - too generic
        'xem', 'help', 'giúp', 'hướng dẫn', 'chức năng',
        'chào', 'hello', 'xin chào', 'hế lô'  # Removed 'hi' - too short
    ]
    
    # Từ khóa ngoài lĩnh vực (out of scope)
    OUT_OF_SCOPE_KEYWORDS = [
        'thời tiết', 'trời', 'mưa', 'nắng',
        'tin tức', 'news', 'sự kiện', 'event',
        'phim', 'phát sóng', 'xem phim',
        'nhạc', 'bài hát', 'ca sĩ', 'concert',
        'thể thao', 'bóng', 'game', 'chơi',
        'công nghệ', 'tech', 'iphone', 'ipad', 'laptop', 'máy tính',
        'lịch sử', 'địa lý', 'khoa học',
        'công thức', 'cách nấu', 'nấu ăn',
        'hình ảnh', 'ảnh', 'hình',
        'đó là gì', 'cái gì', 'ai', 'ở đâu',
        'như thế nào', 'tại sao', 'vì sao',
        'những lý do', 'nguyên nhân',
        'tạm biệt', 'goodbye', 'bye',
        'tình cảm', 'tình yêu', 'yêu thương',
        'sức khỏe', 'bệnh', 'thuốc', 'bác sĩ',
        'thời gian', 'giờ', 'phút', 'giây',  # Nếu không có context tài chính
        'tên', 'họ', 'nhân vật', 'người',
        'chuyên gia', 'kỹ sư', 'bác', 'ông',
        'kinh doanh', 'đầu tư', 'cổ phiếu', 'forex', 'chứng khoán',  # Ngoài scope của app này
    ]
    
    # Từ khóa cho mỗi intent
    INTENT_KEYWORDS = {
        'EDIT_EXPENSE': {
            'keywords': ['sửa chi tiêu', 'sửa khoản chi', 'đổi khoản chi', 'cập nhật chi tiêu'],
            'patterns': [r'\bsửa\b', r'\bđổi\b', r'\bcập nhật\b'],
        },
        'DELETE_EXPENSE': {
            'keywords': ['xóa chi tiêu', 'xóa khoản chi', 'xóa giao dịch', 'bỏ khoản chi'],
            'patterns': [r'\bxóa\b', r'\bbỏ\b'],
        },
        'CREATE_INCOME': {
            'keywords': ['nhận lương', 'được trả', 'thu được', 'kiếm được', 'nhận được tiền',
                        'thêm thu nhập', 'tạo thu nhập', 'thu', 'nhận tiền', 'được',
                        'nhận thưởng', 'nhận'],
            'patterns': [r'(thu|nhận|kiếm).*(được).*\d+', r'lương.*\d+', r'nhận\s*(thưởng|lương)'],
        },
        'CREATE_RECURRING_INCOME': {
            'keywords': ['thu nhập định kỳ', 'lương hàng tháng', 'lương mỗi tháng',
                        'nhận lương mỗi', 'nhận lương hàng'],
            'patterns': [r'(lương|thu nhập).*(mỗi|hàng)\s+(ngày|tuần|tháng|năm)'],
        },
        'CREATE_EXPENSE': {
            'keywords': ['chi', 'mua', 'ăn', 'uống', 'đổ xăng', 'taxi', 'grab', 'hết', 
                        'trả tiền', 'thanh toán', 'vừa', 'mới', 'shopping'],
            'patterns': [r'\d+\s*[ktk]', r'\d+\s*triệu', r'\d+\s*nghìn', r'\d{3,}'],
        },
        'CREATE_RECURRING_EXPENSE': {
            'keywords': ['chi định kỳ', 'mỗi tháng', 'mỗi tuần', 'mỗi ngày', 'mỗi năm',
                        'hàng tháng', 'hàng tuần', 'hàng ngày', 'hàng năm', 'tiền nhà',
                        'tiền điện', 'tiền nước'],
            'patterns': [r'(mỗi|hàng)\s+(ngày|tuần|tháng|năm)'],
        },
        'QUERY_EXPENSES': {
            'keywords': ['bao nhiêu chi tiêu', 'tổng chi tiêu', 'chi bao nhiêu', 
                        'đã chi bao nhiêu', 'số chi tiêu', 'chi tiêu của tôi',
                        'chi tiêu hôm', 'chi tiêu tháng', 'chi tiêu tuần',
                        'các khoản chi', 'danh sách chi tiêu', 'xem chi tiêu'],
            'patterns': [r'tổng\s+chi', r'số\s+chi', r'bao\s+nhiêu\s+chi'],
        },
        'QUERY_INCOME': {
            'keywords': ['thu nhập', 'kiếm được', 'nhận được', 'lương', 'tiền thu',
                        'tổng thu', 'thu được bao nhiêu', 'có bao nhiêu thu'],
            'patterns': [r'tổng\s+thu', r'thu\s+nhập'],
        },
        'QUERY_SAVINGS': {
            'keywords': ['tiết kiệm', 'tiết kiệm được', 'còn tiết kiệm', 'mục tiêu tiết kiệm',
                        'saving', 'goals', 'đã tiết kiệm', 'đang tiết kiệm'],
            'patterns': [r'tiết\s+kiệm', r'ti[eế]t\s+ki[eệ]m'],
        },
        'QUERY_BUDGET': {
            'keywords': ['ngân sách', 'budget', 'còn lại', 'vượt ngân sách', 'trong ngân sách',
                        'hạn mức', 'giới hạn chi tiêu'],
            'patterns': [r'ngân\s+sách', r'còn\s+lại'],
        },
        'QUERY_SUMMARY': {
            'keywords': ['tổng quan', 'tóm tắt', 'summary', 'overview', 'tình hình',
                        'thống kê', 'báo cáo', 'tài chính của tôi'],
            'patterns': [r'tổng\s+quan', r'tóm\s+t[ắa]t'],
        },
        'TOP_EXPENSES': {
            'keywords': ['top chi tiêu', 'chi nhiều nhất', 'chi lớn nhất', 'khoản chi lớn',
                        'chi tiêu lớn', 'những khoản chi', 'top', 'nhiều nhất', 'lớn nhất'],
            'patterns': [r'top.*chi', r'(lớn|nhiều)\s*nhất'],
        },
        'SEARCH_EXPENSES': {
            'keywords': ['tìm chi tiêu', 'tìm kiếm', 'search', 'có khoản chi', 'chi nào',
                        'giao dịch nào', 'tìm giao dịch'],
            'patterns': [r'tìm', r'search'],
        },
        'RECENT_TRANSACTIONS': {
            'keywords': ['giao dịch gần đây', 'chi tiêu gần đây', 'vừa chi', 'mới chi',
                        'gần đây', 'recently', 'latest', 'giao dịch mới nhất'],
            'patterns': [r'(gần|mới)\s*đây', r'(vừa|mới)\s*(chi|mua)'],
        },
        'COMPARE_PERIODS': {
            'keywords': ['so sánh', 'compare', 'khác biệt', 'chênh lệch', 'tăng giảm',
                        'so với', 'hơn tháng trước', 'với tuần trước'],
            'patterns': [r'so\s*sánh', r'hơn.*trước', r'với.*trước'],
        },
        'FINANCIAL_ADVICE': {
            'keywords': ['lời khuyên', 'advice', 'nên', 'làm gì', 'cách tiết kiệm',
                        'giúp tiết kiệm', 'tips', 'mẹo', 'gợi ý', 'đề xuất', 'tư vấn'],
            'patterns': [r'nên.*gì', r'cách.*tiết\s*kiệm', r'tư\s*vấn'],
        },
        'QUERY_CATEGORIES': {
            'keywords': ['danh mục', 'categories', 'category', 'các danh mục', 'loại chi tiêu',
                        'xem danh mục', 'có những danh mục gì'],
            'patterns': [r'danh\s*mục'],
        },
        'MONTHLY_REPORT': {
            'keywords': ['báo cáo tháng', 'báo cáo chi tiết', 'monthly report', 
                        'chi tiết tháng', 'phân tích tháng', 'report'],
            'patterns': [r'báo\s*cáo.*tháng', r'chi\s*tiết.*tháng'],
        },
        'GREETING': {
            'keywords': ['xin chào', 'chào', 'hello', 'hi', 'hey', 'hế lô', 
                        'alo', 'chào bạn', 'chào bot'],
            'patterns': [],
        },
        'HELP': {
            'keywords': ['giúp', 'help', 'hướng dẫn', 'làm gì', 'có thể làm gì',
                        'chức năng', 'cách dùng', 'sử dụng'],
            'patterns': [],
        },
    }
    
    def is_in_scope(self, text):
        """
        Kiểm tra xem câu hỏi có liên quan đến tài chính không
        Returns: (is_in_scope: bool, reason: str)
        """
        text_lower = text.lower()
        
        # Nếu có greeting keywords, assume là in scope (hỏi/chào chatbot)
        if any(word in text_lower for word in ['chào', 'hello', 'xin chào', 'hế lô']):
            return True, "Greeting"
        
        # Nếu có finance keywords, return True
        for keyword in self.FINANCE_KEYWORDS:
            if keyword in text_lower:
                return True, "In scope"
        
        # Nếu có số tiền, assume là về chi tiêu
        if re.search(r'\d+\s*[ktk]|\d+\s*triệu|\d+\s*nghìn|\d{3,}', text):
            return True, "Detected amount"

        # Chỉ coi câu là ngoài phạm vi khi không có tín hiệu tài chính rõ ràng.
        for keyword in self.OUT_OF_SCOPE_KEYWORDS:
            if keyword in text_lower:
                return False, f"Out of scope: {keyword}"
        
        # Default: Out of scope
        return False, "No finance keywords detected"
    
    def detect_intent(self, text):
        """
        Phát hiện intent từ text
        Returns: (intent_type, confidence)
        """
        # Kiểm tra scope trước
        in_scope, reason = self.is_in_scope(text)
        if not in_scope:
            return 'OUT_OF_SCOPE', 0.9
        
        text = text.lower().strip()

        if re.search(r'(mỗi|hàng)\s+(ngày|tuần|tháng|năm)|định kỳ', text):
            if any(word in text for word in ['lương', 'thu nhập', 'nhận lương', 'tiền công']):
                return 'CREATE_RECURRING_INCOME', 0.95
            if re.search(r'\d+\s*(k|tr|triệu|nghìn|ngàn)|\d{3,}', text):
                return 'CREATE_RECURRING_EXPENSE', 0.95
        
        # Check cho mỗi intent
        scores = {}
        
        for intent, config in self.INTENT_KEYWORDS.items():
            score = 0
            
            # Check keywords với weighted scoring
            for keyword in config['keywords']:
                if keyword in text:
                    # Longer keywords get more weight
                    weight = 3 if len(keyword.split()) > 2 else 2
                    score += weight
            
            # Check patterns
            for pattern in config['patterns']:
                if re.search(pattern, text):
                    score += 2
            
            scores[intent] = score
        
        # Special rules để tránh false positives
        
        # Nếu có "tìm" hoặc "search" thì ưu tiên SEARCH_EXPENSES
        if any(word in text for word in ['tìm', 'search', 'tìm kiếm']):
            if 'SEARCH_EXPENSES' in scores:
                scores['SEARCH_EXPENSES'] += 5
        
        # Nếu có "so sánh" hoặc "hơn...trước" thì ưu tiên COMPARE_PERIODS
        if 'so sánh' in text or any(pattern in text for pattern in ['hơn', 'với', 'trước']):
            if 'COMPARE_PERIODS' in scores and scores.get('COMPARE_PERIODS', 0) > 0:
                scores['COMPARE_PERIODS'] += 3
        
        # Nếu có "gần đây" hoặc "mới nhất" hoặc "vừa" thì ưu tiên RECENT_TRANSACTIONS
        if any(word in text for word in ['gần đây', 'mới nhất', 'recently', 'latest', 'vừa']):
            if 'RECENT_TRANSACTIONS' in scores:
                scores['RECENT_TRANSACTIONS'] += 5
                # Giảm CREATE_EXPENSE khi có "vừa chi"
                if 'vừa' in text and 'CREATE_EXPENSE' in scores:
                    scores['CREATE_EXPENSE'] = max(0, scores['CREATE_EXPENSE'] - 3)
        
        # Câu hỏi về chi tiêu không được chuyển sang parser tạo giao dịch.
        query_words = [
            'bao nhiêu', 'tổng', 'có', 'đã', 'xem', 'list',
            'như nào', 'như thế nào', 'ra sao', 'tình hình',
        ]
        has_expense_query_context = (
            'chi tiêu' in text and (
                any(word in text for word in query_words)
                or any(word in text for word in ['hôm nay', 'tuần này', 'tháng này', 'năm nay'])
            )
        )
        if any(word in text for word in query_words) or has_expense_query_context:
            if 'QUERY_EXPENSES' in scores:
                scores['QUERY_EXPENSES'] = max(scores['QUERY_EXPENSES'] + 3, 6)
            # Giảm score của CREATE_EXPENSE khi có question words
            if 'CREATE_EXPENSE' in scores:
                scores['CREATE_EXPENSE'] = max(0, scores['CREATE_EXPENSE'] - 4)
        
        # Nếu có "lời khuyên", "nên", "advice", "tips", "mẹo", "tư vấn" thì ưu tiên FINANCIAL_ADVICE
        if any(word in text for word in ['lời khuyên', 'advice', 'tips', 'mẹo', 'nên', 'gợi ý', 'tư vấn']):
            if 'FINANCIAL_ADVICE' in scores:
                scores['FINANCIAL_ADVICE'] += 5
        
        # Nếu có "báo cáo" hoặc "report" thì ưu tiên MONTHLY_REPORT
        if any(word in text for word in ['báo cáo', 'report']):
            if 'MONTHLY_REPORT' in scores:
                scores['MONTHLY_REPORT'] += 5
        
        # Nếu có "top" thì ưu tiên TOP_EXPENSES (trừ khi có "danh mục")
        if 'top' in text:
            if 'TOP_EXPENSES' in scores:
                scores['TOP_EXPENSES'] += 5
        
        # Nếu có "danh mục" thì ưu tiên QUERY_CATEGORIES
        if 'danh mục' in text or 'categories' in text:
            if 'QUERY_CATEGORIES' in scores:
                scores['QUERY_CATEGORIES'] += 6  # Higher than TOP_EXPENSES
        
        # Nếu có "nhận" hoặc "được trả" hoặc "thu được" hoặc "thưởng" thì ưu tiên CREATE_INCOME
        if any(word in text for word in ['nhận', 'được trả', 'thu được', 'kiếm được', 'lương', 'thưởng']):
            if 'CREATE_INCOME' in scores and scores.get('CREATE_INCOME', 0) > 0:
                scores['CREATE_INCOME'] += 5
                # Nếu có "nhận thưởng" hoặc "nhận lương" thì giảm CREATE_EXPENSE
                if ('nhận' in text or 'thưởng' in text) and 'CREATE_EXPENSE' in scores:
                    scores['CREATE_EXPENSE'] = max(0, scores['CREATE_EXPENSE'] - 3)
        
        # Tìm intent có score cao nhất
        if not scores or max(scores.values()) == 0:
            # Nếu có số tiền thì assume là CREATE_EXPENSE
            if re.search(r'\d+', text):
                return 'CREATE_EXPENSE', 0.5
            # Nếu không in scope, return OUT_OF_SCOPE
            if not in_scope:
                return 'OUT_OF_SCOPE', 0.9
            return 'UNKNOWN', 0.0
        
        best_intent = max(scores, key=scores.get)
        max_score = scores[best_intent]
        
        # Confidence dựa trên score
        confidence = min(max_score / 5.0, 1.0)
        
        return best_intent, confidence


class ChatQueryHandler:
    """
    Xử lý các query từ user
    """
    
    def __init__(self, user):
        self.user = user
    
    def handle_query_expenses(self, text):
        """Xử lý câu hỏi về chi tiêu"""
        from app_expenses.models import Expense
        
        # Xác định time range
        time_range = self._extract_time_range(text)
        
        # Query expenses
        expenses = Expense.objects.filter(user=self.user)
        
        if time_range:
            expenses = expenses.filter(date__gte=time_range['start'], date__lte=time_range['end'])
        
        # Tính toán
        total = expenses.aggregate(Sum('amount'))['amount__sum'] or 0
        count = expenses.count()
        
        # Top categories
        top_categories = expenses.values('category__name').annotate(
            total=Sum('amount')
        ).order_by('-total')[:3]
        
        # Format response
        response = f"📊 **Thông tin chi tiêu {time_range['label'] if time_range else 'tổng'}:**\n\n"
        response += f"💰 **Tổng chi tiêu:** {total:,.0f} đ\n"
        response += f"📝 **Số giao dịch:** {count}\n"
        
        if count > 0:
            avg = total / count
            response += f"📈 **Trung bình/giao dịch:** {avg:,.0f} đ\n"
        
        if top_categories:
            response += f"\n**Top danh mục:**\n"
            for i, cat in enumerate(top_categories, 1):
                cat_name = cat['category__name'] or 'Chưa phân loại'
                cat_total = cat['total']
                response += f"{i}. {cat_name}: {cat_total:,.0f} đ\n"
        
        return {
            'type': 'info',
            'message': response,
            'data': {
                'total': float(total),
                'count': count,
                'time_range': time_range
            }
        }
    
    def handle_query_income(self, text):
        """Xử lý câu hỏi về thu nhập"""
        from app_expenses.models import Income
        
        time_range = self._extract_time_range(text)
        
        incomes = Income.objects.filter(user=self.user)
        
        if time_range:
            incomes = incomes.filter(date__gte=time_range['start'], date__lte=time_range['end'])
        
        total = incomes.aggregate(Sum('amount'))['amount__sum'] or 0
        count = incomes.count()
        
        response = f"💵 **Thông tin thu nhập {time_range['label'] if time_range else 'tổng'}:**\n\n"
        response += f"💰 **Tổng thu nhập:** {total:,.0f} đ\n"
        response += f"📝 **Số giao dịch:** {count}\n"
        
        if count > 0:
            avg = total / count
            response += f"📈 **Trung bình/giao dịch:** {avg:,.0f} đ\n"
        
        return {
            'type': 'info',
            'message': response,
            'data': {
                'total': float(total),
                'count': count
            }
        }
    
    def handle_query_savings(self, text):
        """Xử lý câu hỏi về tiết kiệm"""
        from app_expenses.models import SavingsGoal
        
        savings_goals = SavingsGoal.objects.filter(user=self.user)
        
        active_goals = savings_goals.filter(is_active=True, is_completed=False)
        completed_goals = savings_goals.filter(is_completed=True)
        
        response = f"🐷 **Thông tin tiết kiệm:**\n\n"
        
        if not savings_goals.exists():
            response += "Bạn chưa có mục tiêu tiết kiệm nào.\n"
            response += "Tạo mục tiêu mới tại: /savings-goals/add/"
        else:
            response += f"📊 **Tổng quan:**\n"
            response += f"- Mục tiêu đang hoạt động: {active_goals.count()}\n"
            response += f"- Mục tiêu đã hoàn thành: {completed_goals.count()}\n\n"
            
            if active_goals.exists():
                response += "**📍 Mục tiêu đang theo dõi:**\n"
                for goal in active_goals[:3]:
                    progress_pct = (goal.current_amount / goal.target_amount * 100) if goal.target_amount > 0 else 0
                    response += f"\n• **{goal.goal_name}**\n"
                    response += f"  - Mục tiêu: {goal.target_amount:,.0f} đ\n"
                    response += f"  - Đã tiết kiệm: {goal.current_amount:,.0f} đ ({progress_pct:.1f}%)\n"
                    response += f"  - Còn thiếu: {goal.amount_remaining:,.0f} đ\n"
        
        return {
            'type': 'info',
            'message': response,
            'data': {
                'active_count': active_goals.count(),
                'completed_count': completed_goals.count()
            }
        }
    
    def handle_query_budget(self, text):
        """Xử lý câu hỏi về ngân sách"""
        from app_expenses.models import Budget, Expense
        
        try:
            budget = Budget.objects.get(user=self.user)
        except Budget.DoesNotExist:
            return {
                'type': 'info',
                'message': "💰 Bạn chưa thiết lập ngân sách.\nVui lòng vào Trang chủ để cài đặt ngân sách."
            }
        
        # Tính tổng chi tiêu (tháng này hoặc tất cả)
        time_range = self._extract_time_range(text)
        
        expenses = Expense.objects.filter(user=self.user)
        if time_range:
            expenses = expenses.filter(date__gte=time_range['start'], date__lte=time_range['end'])
        
        total_expenses = expenses.aggregate(Sum('amount'))['amount__sum'] or 0
        
        remaining = budget.total - total_expenses
        usage_pct = (total_expenses / budget.total * 100) if budget.total > 0 else 0
        
        response = f"💰 **Thông tin ngân sách:**\n\n"
        response += f"📊 **Ngân sách:** {budget.total:,.0f} đ\n"
        response += f"💸 **Đã chi:** {total_expenses:,.0f} đ ({usage_pct:.1f}%)\n"
        response += f"💵 **Còn lại:** {remaining:,.0f} đ\n\n"
        
        if usage_pct > 100:
            response += "⚠️ **Cảnh báo:** Bạn đã vượt ngân sách!\n"
            over = total_expenses - budget.total
            response += f"Vượt: {over:,.0f} đ ({usage_pct - 100:.1f}%)"
        elif usage_pct > 80:
            response += "⚠️ **Lưu ý:** Bạn đã sử dụng hơn 80% ngân sách."
        else:
            response += "✅ Bạn đang chi tiêu trong tầm kiểm soát."
        
        return {
            'type': 'info',
            'message': response,
            'data': {
                'budget': float(budget.total),
                'spent': float(total_expenses),
                'remaining': float(remaining),
                'usage_pct': usage_pct
            }
        }
    
    def handle_query_summary(self, text):
        """Xử lý câu hỏi tổng quan"""
        from app_expenses.models import Expense, Income, Budget, SavingsGoal
        
        time_range = self._extract_time_range(text)
        
        # Chi tiêu
        expenses = Expense.objects.filter(user=self.user)
        if time_range:
            expenses = expenses.filter(date__gte=time_range['start'], date__lte=time_range['end'])
        total_expenses = expenses.aggregate(Sum('amount'))['amount__sum'] or 0
        
        # Thu nhập
        incomes = Income.objects.filter(user=self.user)
        if time_range:
            incomes = incomes.filter(date__gte=time_range['start'], date__lte=time_range['end'])
        total_income = incomes.aggregate(Sum('amount'))['amount__sum'] or 0
        
        # Ngân sách
        try:
            budget = Budget.objects.get(user=self.user)
            budget_amount = budget.total
        except Budget.DoesNotExist:
            budget_amount = 0
        
        # Tiết kiệm
        active_savings = SavingsGoal.objects.filter(user=self.user, status='active').count()
        
        # Tính toán
        balance = total_income - total_expenses
        
        response = f"📊 **Tổng quan tài chính {time_range['label'] if time_range else ''}:**\n\n"
        response += f"💵 **Thu nhập:** {total_income:,.0f} đ\n"
        response += f"💸 **Chi tiêu:** {total_expenses:,.0f} đ\n"
        response += f"{'➖' if balance < 0 else '💰'} **Số dư:** {balance:,.0f} đ\n"
        
        if budget_amount > 0:
            response += f"\n💰 **Ngân sách:** {budget_amount:,.0f} đ\n"
            usage = (total_expenses / budget_amount * 100) if budget_amount > 0 else 0
            response += f"📊 **Sử dụng:** {usage:.1f}%\n"
        
        if active_savings > 0:
            response += f"\n🐷 **Mục tiêu tiết kiệm:** {active_savings} đang hoạt động\n"
        
        # Đánh giá
        response += "\n"
        if balance > 0:
            response += "✅ Bạn đang có khoản dư tích cực!"
        elif balance < 0:
            response += "⚠️ Chi tiêu vượt quá thu nhập. Cần cân đối lại!"
        else:
            response += "➖ Thu chi cân bằng."
        
        return {
            'type': 'info',
            'message': response,
            'data': {
                'income': float(total_income),
                'expenses': float(total_expenses),
                'balance': float(balance),
                'budget': float(budget_amount)
            }
        }
    
    def handle_out_of_scope(self, text):
        """Xử lý câu hỏi ngoài lĩnh vực"""
        response = """❌ Xin lỗi, tôi chỉ hỗ trợ các câu hỏi về **tài chính và chi tiêu** cá nhân.

Bạn có thể hỏi tôi về:
• 💰 Chi tiêu, thu nhập, tiết kiệm
• 📊 Phân tích tài chính, báo cáo tháng
• 💡 Tư vấn quản lý tiền
• 📈 Xu hướng chi tiêu, so sánh kỳ

Ví dụ: "Chi tiêu tháng này bao nhiêu?" hoặc "Gõ 'help' để xem hướng dẫn"
"""
        return {
            'type': 'info',
            'message': response
        }
    
    def handle_greeting(self, text):
        """Xử lý lời chào"""
        import random
        
        greetings = [
            "👋 Xin chào! Tôi có thể giúp gì cho bạn?",
            "🤖 Chào bạn! Bạn muốn biết thông tin gì về tài chính không?",
            "😊 Hi! Tôi sẵn sàng hỗ trợ bạn!",
        ]
        
        return {
            'type': 'info',
            'message': random.choice(greetings)
        }
    
    def handle_help(self, text):
        """Xử lý yêu cầu trợ giúp"""
        response = """🤖 **Tôi có thể giúp bạn:**

**1. Tạo giao dịch:**
   • "Ăn sáng 50k" - Chi tiêu
   • "Nhận lương 10 triệu" - Thu nhập
   • "Mua đồ 200 nghìn hôm qua"

**2. Tra cứu:**
   • "Tổng chi tiêu hôm nay?"
   • "Thu nhập tháng này?"
   • "Top chi tiêu lớn nhất?"
   • "Giao dịch gần đây?"
   • "Tìm chi tiêu đổ xăng"

**3. Phân tích:**
   • "So sánh tháng này với tháng trước"
   • "Báo cáo tháng chi tiết"
   • "Tổng quan tài chính"
   • "Danh mục chi tiêu"

**4. Lời khuyên:**
   • "Tư vấn tiết kiệm"
   • "Nên làm gì để giảm chi tiêu?"

**5. Thời gian:**
   • Hôm nay, hôm qua
   • Tuần/tháng/năm này

Hãy thử hỏi tôi! 😊"""
        
        return {
            'type': 'info',
            'message': response
        }
    
    def handle_create_income(self, text):
        """Xử lý tạo thu nhập nhanh"""
        # Extract amount
        amount = self._extract_amount(text)
        if not amount:
            return {
                'type': 'error',
                'message': '❌ Không tìm thấy số tiền. Vui lòng nhập theo dạng: "Nhận lương 10 triệu"'
            }
        
        # Extract description
        desc = "Thu nhập"
        if 'lương' in text.lower():
            desc = "Lương"
        elif 'bonus' in text.lower() or 'thưởng' in text.lower():
            desc = "Thưởng"

        return {
            'type': 'income_preview',
            'message': f'Xác nhận thêm thu nhập: **{desc}** - **{amount:,.0f} đ**',
            'amount': amount,
            'description': desc,
            'source_name': desc,
            'date': timezone.now().date().isoformat(),
            'requires_confirmation': True,
        }
    
    def handle_top_expenses(self, text):
        """Xử lý xem top chi tiêu"""
        from app_expenses.models import Expense
        
        # Extract time range
        time_range = self._extract_time_range(text)
        
        # Query
        expenses = Expense.objects.filter(user=self.user)
        if time_range:
            expenses = expenses.filter(date__gte=time_range['start'], date__lte=time_range['end'])
        
        # Get top 10
        top_expenses = expenses.order_by('-amount')[:10]
        
        if not top_expenses:
            return {
                'type': 'info',
                'message': f'📊 Không có chi tiêu nào {time_range["label"] if time_range else ""}.'
            }
        
        response = f"📊 **Top chi tiêu {time_range['label'] if time_range else 'tổng'}:**\n\n"
        
        for i, exp in enumerate(top_expenses, 1):
            emoji = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}."
            response += f"{emoji} **{exp.amount:,.0f} đ** - {exp.description} · {exp.category.name if exp.category else 'Khác'}\n"
            response += f"   __{exp.date.strftime('%d/%m/%Y')}__\n"
        
        total = sum(e.amount for e in top_expenses)
        response += f"\n💰 **Tổng top 10:** {total:,.0f} đ"
        
        return {
            'type': 'info',
            'message': response
        }
    
    def handle_search_expenses(self, text):
        """Xử lý tìm kiếm chi tiêu"""
        from app_expenses.models import Expense
        
        # Extract search term (remove common words)
        search_term = text.lower()
        for word in ['tìm', 'tìm kiếm', 'chi tiêu', 'giao dịch', 'search', 'có khoản', 'nào']:
            search_term = search_term.replace(word, '')
        search_term = search_term.strip()
        
        if not search_term:
            return {
                'type': 'error',
                'message': '❌ Vui lòng nhập từ khóa tìm kiếm. VD: "Tìm chi tiêu đổ xăng"'
            }
        
        # Search in description and category
        from django.db.models import Q
        expenses = Expense.objects.filter(
            user=self.user
        ).filter(
            Q(description__icontains=search_term) | 
            Q(category__name__icontains=search_term)
        ).order_by('-date')[:10]
        
        if not expenses:
            return {
                'type': 'info',
                'message': f'🔍 Không tìm thấy chi tiêu nào với từ khóa "**{search_term}**"'
            }
        
        response = f"🔍 **Tìm thấy {expenses.count()} kết quả cho '{search_term}':**\n\n"
        
        for exp in expenses:
            response += f"• **{exp.amount:,.0f} đ** - {exp.description}\n"
            response += f"  {exp.category.name if exp.category else 'Khác'} · {exp.date.strftime('%d/%m/%Y')}\n"
        
        return {
            'type': 'info',
            'message': response
        }
    
    def handle_recent_transactions(self, text):
        """Xử lý xem giao dịch gần đây"""
        from app_expenses.models import Expense, Income
        from datetime import datetime
        
        # Get recent expenses and incomes
        recent_expenses = Expense.objects.filter(user=self.user).order_by('-date', '-id')[:5]
        recent_incomes = Income.objects.filter(user=self.user).order_by('-date', '-id')[:5]
        
        response = "📝 **Giao dịch gần đây:**\n\n"
        
        # Combine and sort
        transactions = []
        for exp in recent_expenses:
            transactions.append({
                'type': 'expense',
                'date': exp.date,
                'amount': exp.amount,
                'description': exp.description,
                'category': exp.category.name if exp.category else 'Khác'
            })
        
        for inc in recent_incomes:
            transactions.append({
                'type': 'income',
                'date': inc.date,
                'amount': inc.amount,
                'description': inc.description,
                'category': inc.source.name if inc.source else 'Thu nhập'
            })
        
        # Sort by date
        transactions.sort(key=lambda x: x['date'], reverse=True)
        transactions = transactions[:10]
        
        if not transactions:
            return {
                'type': 'info',
                'message': '📝 Chưa có giao dịch nào.'
            }
        
        for trans in transactions:
            if trans['type'] == 'expense':
                response += f"💸 **-{trans['amount']:,.0f} đ** · {trans['description']}\n"
            else:
                response += f"💰 **+{trans['amount']:,.0f} đ** · {trans['description']}\n"
            response += f"   {trans['category']} · {trans['date'].strftime('%d/%m/%Y')}\n"
        
        return {
            'type': 'info',
            'message': response
        }
    
    def handle_compare_periods(self, text):
        """So sánh các khoảng thời gian"""
        from app_expenses.models import Expense
        from datetime import datetime, timedelta
        from django.db.models import Sum
        
        today = timezone.now().date()
        
        # Default: so sánh tháng này với tháng trước
        current_start = today.replace(day=1)
        current_end = today
        
        # Tháng trước
        last_month = current_start - timedelta(days=1)
        previous_start = last_month.replace(day=1)
        previous_end = last_month
        
        period_label = "tháng này"
        previous_label = "tháng trước"
        
        # Check if comparing weeks
        if 'tuần' in text.lower():
            current_start = today - timedelta(days=today.weekday())
            current_end = today
            previous_start = current_start - timedelta(days=7)
            previous_end = current_start - timedelta(days=1)
            period_label = "tuần này"
            previous_label = "tuần trước"
        
        # Query current period
        current_expenses = Expense.objects.filter(
            user=self.user,
            date__gte=current_start,
            date__lte=current_end
        )
        current_total = current_expenses.aggregate(Sum('amount'))['amount__sum'] or 0
        current_count = current_expenses.count()
        
        # Query previous period
        previous_expenses = Expense.objects.filter(
            user=self.user,
            date__gte=previous_start,
            date__lte=previous_end
        )
        previous_total = previous_expenses.aggregate(Sum('amount'))['amount__sum'] or 0
        previous_count = previous_expenses.count()
        
        # Calculate difference
        diff_amount = current_total - previous_total
        diff_percent = ((current_total - previous_total) / previous_total * 100) if previous_total > 0 else 0
        
        response = f"📊 **So sánh {period_label} vs {previous_label}:**\n\n"
        response += f"**{period_label.capitalize()}:**\n"
        response += f"💸 Chi tiêu: {current_total:,.0f} đ ({current_count} giao dịch)\n\n"
        response += f"**{previous_label.capitalize()}:**\n"
        response += f"💸 Chi tiêu: {previous_total:,.0f} đ ({previous_count} giao dịch)\n\n"
        response += f"**Chênh lệch:**\n"
        
        if diff_amount > 0:
            response += f"📈 Tăng {diff_amount:,.0f} đ ({diff_percent:+.1f}%)\n"
            response += "⚠️ Chi tiêu tăng so với kỳ trước"
        elif diff_amount < 0:
            response += f"📉 Giảm {abs(diff_amount):,.0f} đ ({diff_percent:.1f}%)\n"
            response += "✅ Tiết kiệm hơn kỳ trước!"
        else:
            response += "➖ Không có thay đổi"
        
        return {
            'type': 'info',
            'message': response
        }
    
    def handle_financial_advice(self, text):
        """Đưa ra lời khuyên tài chính"""
        from app_expenses.models import Expense, Income, Budget
        from django.db.models import Sum
        from datetime import datetime
        
        today = timezone.now().date()
        month_start = today.replace(day=1)
        
        # Analyze this month
        expenses = Expense.objects.filter(
            user=self.user,
            date__gte=month_start
        )
        total_expenses = expenses.aggregate(Sum('amount'))['amount__sum'] or 0
        
        incomes = Income.objects.filter(
            user=self.user,
            date__gte=month_start
        )
        total_income = incomes.aggregate(Sum('amount'))['amount__sum'] or 0
        
        # Get budget
        try:
            budget = Budget.objects.get(user=self.user)
            budget_amount = budget.total
        except Budget.DoesNotExist:
            budget_amount = 0
        
        # Top category
        top_category = expenses.values('category__name').annotate(
            total=Sum('amount')
        ).order_by('-total').first()
        
        response = "💡 **Phân tích và lời khuyên:**\n\n"
        
        # Budget analysis
        if budget_amount > 0:
            usage_percent = (total_expenses / budget_amount * 100)
            response += f"📊 **Ngân sách:** Đã dùng {usage_percent:.1f}%\n"
            
            if usage_percent > 90:
                response += "⚠️ Đã vượt ngưỡng 90% ngân sách!\n\n"
                response += "**Khuyến nghị:**\n"
                response += "• Hạn chế chi tiêu không cần thiết\n"
                response += "• Kiểm soát các khoản chi lớn\n"
                response += "• Tìm cách tăng thu nhập\n"
            elif usage_percent > 70:
                response += "⚡ Cần chú ý kiểm soát chi tiêu!\n\n"
                response += "**Khuyến nghị:**\n"
                response += "• Theo dõi chi tiêu hàng ngày\n"
                response += "• Ưu tiên chi tiêu thiết yếu\n"
            else:
                response += "✅ Kiểm soát tốt!\n\n"
        
        # Income vs Expense
        if total_income > 0:
            balance = total_income - total_expenses
            savings_rate = (balance / total_income * 100) if total_income > 0 else 0
            
            response += f"\n💰 **Thu - Chi:**\n"
            response += f"Số dư: {balance:,.0f} đ (Tiết kiệm {savings_rate:.1f}%)\n\n"
            
            if savings_rate < 10:
                response += "⚠️ **Tỷ lệ tiết kiệm thấp!**\n"
                response += "Khuyến nghị tiết kiệm ít nhất 20% thu nhập\n\n"
            elif savings_rate < 20:
                response += "📈 **Cố gắng tăng tỷ lệ tiết kiệm lên 20%**\n\n"
            else:
                response += "🌟 **Tuyệt vời! Duy trì thói quen này!**\n\n"
        
        # Top category advice
        if top_category:
            cat_name = top_category['category__name']
            cat_total = top_category['total']
            cat_percent = (cat_total / total_expenses * 100) if total_expenses > 0 else 0
            
            response += f"📊 **Danh mục chi nhiều nhất:**\n"
            response += f"{cat_name}: {cat_total:,.0f} đ ({cat_percent:.1f}%)\n\n"
            
            if cat_percent > 40:
                response += f"💡 Nên phân bổ chi tiêu cân đối hơn"
        
        # General tips
        response += "\n**💡 Mẹo tiết kiệm:**\n"
        response += "• Lập kế hoạch chi tiêu hàng tháng\n"
        response += "• Ghi chép đầy đủ các khoản chi\n"
        response += "• Đặt mục tiêu tiết kiệm cụ thể\n"
        response += "• Review chi tiêu định kỳ\n"
        
        return {
            'type': 'info',
            'message': response
        }
    
    def handle_query_categories(self, text):
        """Xem thống kê theo danh mục"""
        from app_expenses.models import Category, Expense
        from django.db.models import Sum, Count
        
        # Get time range
        time_range = self._extract_time_range(text)
        
        # Query expenses
        expenses = Expense.objects.filter(user=self.user)
        if time_range:
            expenses = expenses.filter(date__gte=time_range['start'], date__lte=time_range['end'])
        
        # Group by category
        category_stats = expenses.values('category__name').annotate(
            total=Sum('amount'),
            count=Count('id')
        ).order_by('-total')
        
        if not category_stats:
            return {
                'type': 'info',
                'message': f'📊 Không có chi tiêu nào {time_range["label"] if time_range else ""}.'
            }
        
        total_all = sum(item['total'] for item in category_stats)
        
        response = f"📊 **Chi tiêu theo danh mục {time_range['label'] if time_range else ''}:**\n\n"
        
        for stat in category_stats:
            cat_name = stat['category__name'] or 'Khác'
            cat_total = stat['total']
            cat_count = stat['count']
            percent = (cat_total / total_all * 100) if total_all > 0 else 0
            
            # Progress bar
            bar_length = int(percent / 5)
            bar = '█' * bar_length + '░' * (20 - bar_length)
            
            response += f"**{cat_name}**\n"
            response += f"{bar} {percent:.1f}%\n"
            response += f"💰 {cat_total:,.0f} đ · {cat_count} giao dịch\n\n"
        
        response += f"**Tổng:** {total_all:,.0f} đ"
        
        return {
            'type': 'info',
            'message': response
        }
    
    def handle_monthly_report(self, text):
        """Báo cáo tháng chi tiết"""
        from app_expenses.models import Expense, Income, Budget
        from django.db.models import Sum, Count, Avg
        from datetime import datetime
        
        today = timezone.now().date()
        month_start = today.replace(day=1)
        
        # Expenses
        expenses = Expense.objects.filter(
            user=self.user,
            date__gte=month_start
        )
        total_expenses = expenses.aggregate(Sum('amount'))['amount__sum'] or 0
        expense_count = expenses.count()
        avg_expense = expenses.aggregate(Avg('amount'))['amount__avg'] or 0
        
        # Income
        incomes = Income.objects.filter(
            user=self.user,
            date__gte=month_start
        )
        total_income = incomes.aggregate(Sum('amount'))['amount__sum'] or 0
        
        # Budget
        try:
            budget = Budget.objects.get(user=self.user)
            budget_amount = budget.total
        except Budget.DoesNotExist:
            budget_amount = 0
        
        # Top expenses
        top_expenses = expenses.order_by('-amount')[:3]
        
        # Categories
        top_categories = expenses.values('category__name').annotate(
            total=Sum('amount')
        ).order_by('-total')[:5]
        
        response = f"📊 **BÁO CÁO THÁNG {today.month}/{today.year}**\n\n"
        
        # Overview
        response += "**TỔNG QUAN:**\n"
        response += f"💵 Thu nhập: {total_income:,.0f} đ\n"
        response += f"💸 Chi tiêu: {total_expenses:,.0f} đ\n"
        balance = total_income - total_expenses
        response += f"{'💰' if balance >= 0 else '⚠️'} Số dư: {balance:,.0f} đ\n"
        
        if budget_amount > 0:
            usage = (total_expenses / budget_amount * 100)
            response += f"\n📊 Ngân sách: {budget_amount:,.0f} đ\n"
            response += f"Đã dùng: {usage:.1f}%\n"
        
        # Statistics
        response += f"\n**THỐNG KÊ:**\n"
        response += f"📝 Số giao dịch: {expense_count}\n"
        response += f"📈 Trung bình/ngày: {total_expenses/today.day:,.0f} đ\n"
        response += f"💳 Trung bình/giao dịch: {avg_expense:,.0f} đ\n"
        
        # Top expenses
        if top_expenses:
            response += f"\n**TOP CHI TIÊU:**\n"
            for i, exp in enumerate(top_expenses, 1):
                emoji = "🥇" if i == 1 else "🥈" if i == 2 else "🥉"
                response += f"{emoji} {exp.amount:,.0f} đ - {exp.description}\n"
        
        # Top categories
        if top_categories:
            response += f"\n**TOP DANH MỤC:**\n"
            for cat in top_categories:
                cat_name = cat['category__name'] or 'Khác'
                cat_total = cat['total']
                percent = (cat_total / total_expenses * 100) if total_expenses > 0 else 0
                response += f"• {cat_name}: {cat_total:,.0f} đ ({percent:.1f}%)\n"
        
        # Advice
        if balance < 0:
            response += "\n⚠️ **Cảnh báo:** Chi tiêu vượt thu nhập!"
        elif total_income > 0:
            savings_rate = (balance / total_income * 100)
            if savings_rate < 20:
                response += f"\n💡 Tỷ lệ tiết kiệm: {savings_rate:.1f}% - Nên tăng lên 20%"
            else:
                response += f"\n✅ Tỷ lệ tiết kiệm tốt: {savings_rate:.1f}%"
        
        return {
            'type': 'info',
            'message': response
        }
    
    def _extract_amount(self, text):
        """Extract amount from text"""
        import re
        
        # Pattern for amounts
        patterns = [
            (r'(\d+(?:[.,]\d+)?)\s*(?:triệu|tr)', 1000000),  # 10 triệu / 10tr
            (r'(\d+(?:[.,]\d+)?)\s*(?:nghìn|ngàn)', 1000),    # 50 nghìn / 50 ngàn
            (r'(\d+(?:[.,]\d+)?)\s*k(?!\w)', 1000),           # 50k
            r'(\d{4,})',                    # 50000
        ]
        
        for pattern_config in patterns:
            if isinstance(pattern_config, tuple):
                pattern, multiplier = pattern_config
            else:
                pattern, multiplier = pattern_config, 1
            match = re.search(pattern, text)
            if match:
                amount = float(match.group(1).replace(',', '.')) * multiplier
                if amount > 0:
                    return amount
        
        return None
    
    def _extract_time_range(self, text):
        """Trích xuất khoảng thời gian từ text"""
        text = text.lower()
        today = timezone.now().date()
        
        # Hôm nay
        if any(word in text for word in ['hôm nay', 'h nay', 'hnay', 'today']):
            return {
                'start': today,
                'end': today,
                'label': 'hôm nay'
            }
        
        # Hôm qua
        if any(word in text for word in ['hôm qua', 'h qua', 'hqua', 'yesterday']):
            yesterday = today - timedelta(days=1)
            return {
                'start': yesterday,
                'end': yesterday,
                'label': 'hôm qua'
            }
        
        # Tuần trước / tuần này
        if any(word in text for word in ['tuần trước', 'last week']):
            end_of_week = today - timedelta(days=today.weekday() + 1)
            start_of_week = end_of_week - timedelta(days=6)
            return {
                'start': start_of_week,
                'end': end_of_week,
                'label': 'tuần trước'
            }

        if any(word in text for word in ['tuần này', 'tuần', 'week']):
            start_of_week = today - timedelta(days=today.weekday())
            return {
                'start': start_of_week,
                'end': today,
                'label': 'tuần này'
            }
        
        # Tháng trước / tháng này
        if any(word in text for word in ['tháng trước', 'last month']):
            first_of_month = today.replace(day=1)
            end_of_month = first_of_month - timedelta(days=1)
            start_of_month = end_of_month.replace(day=1)
            return {
                'start': start_of_month,
                'end': end_of_month,
                'label': 'tháng trước'
            }

        if any(word in text for word in ['tháng này', 'tháng', 'month']):
            start_of_month = today.replace(day=1)
            return {
                'start': start_of_month,
                'end': today,
                'label': 'tháng này'
            }
        
        # Năm trước / năm nay
        if any(word in text for word in ['năm trước', 'last year']):
            start_of_year = today.replace(year=today.year - 1, month=1, day=1)
            end_of_year = today.replace(year=today.year - 1, month=12, day=31)
            return {
                'start': start_of_year,
                'end': end_of_year,
                'label': 'năm trước'
            }

        if any(word in text for word in ['năm nay', 'năm', 'year']):
            start_of_year = today.replace(month=1, day=1)
            return {
                'start': start_of_year,
                'end': today,
                'label': 'năm nay'
            }
        
        # Mặc định: tháng này
        if any(word in text for word in ['tổng', 'bao nhiêu', 'có']):
            start_of_month = today.replace(day=1)
            return {
                'start': start_of_month,
                'end': today,
                'label': 'tháng này'
            }
        
        return None


def process_chat_input(text, user, history=None):
    """
    Main function để xử lý chat input
    Returns: {
        'intent': str,
        'confidence': float,
        'response': dict hoặc None (nếu là CREATE_EXPENSE)
    }
    """
    detector = ChatIntentDetector()
    history = history or []
    normalized_text = text.lower().strip()
    if history and any(phrase in normalized_text for phrase in ['còn tháng trước', 'tháng trước thì sao', 'còn tuần trước', 'tuần trước thì sao']):
        previous_text = history[-1].lower()
        if 'chi tiêu' in previous_text or 'chi' in previous_text:
            period = 'tháng trước' if 'tháng' in normalized_text else 'tuần trước'
            text = f'chi tiêu {period}'
    structured = {}
    gemini_error = None
    try:
        from app_expenses.utils.gemini_service import analyze_chat_message
        structured = analyze_chat_message(text, history=history)
        intent = structured['intent']
        confidence = structured['confidence']
    except RuntimeError:
        intent, confidence = detector.detect_intent(text)
    except Exception as exc:
        intent, confidence = detector.detect_intent(text)
        gemini_error = str(exc)
        logger.warning('Gemini classification failed; using local fallback: %s', type(exc).__name__)

    # Preserve deterministic handling for clear financial queries even when
    # the external model returns an unrelated intent.
    local_intent, local_confidence = detector.detect_intent(text)
    if local_intent in {'QUERY_EXPENSES', 'CREATE_RECURRING_EXPENSE', 'CREATE_RECURRING_INCOME'} and intent != local_intent:
        intent, confidence = local_intent, local_confidence

    result_data = {
        'intent': intent,
        'confidence': confidence,
        'response': None,
        'structured': structured,
    }
    if gemini_error:
        result_data['gemini_error'] = 'Gemini tạm thời không khả dụng; đã dùng bộ phân tích dự phòng.'
    
    if intent in {'CREATE_EXPENSE', 'CREATE_RECURRING_EXPENSE', 'CREATE_RECURRING_INCOME', 'EDIT_EXPENSE', 'DELETE_EXPENSE'}:
        return result_data
    
    # Xử lý các intent khác
    handler = ChatQueryHandler(user)
    
    if intent == 'OUT_OF_SCOPE':
        response = handler.handle_out_of_scope(text)
    elif intent == 'CREATE_INCOME':
        response = handler.handle_create_income(text)
    elif intent == 'QUERY_EXPENSES':
        response = handler.handle_query_expenses(text)
    elif intent == 'QUERY_INCOME':
        response = handler.handle_query_income(text)
    elif intent == 'QUERY_SAVINGS':
        response = handler.handle_query_savings(text)
    elif intent == 'QUERY_BUDGET':
        response = handler.handle_query_budget(text)
    elif intent == 'QUERY_SUMMARY':
        response = handler.handle_query_summary(text)
    elif intent == 'TOP_EXPENSES':
        response = handler.handle_top_expenses(text)
    elif intent == 'SEARCH_EXPENSES':
        response = handler.handle_search_expenses(text)
    elif intent == 'RECENT_TRANSACTIONS':
        response = handler.handle_recent_transactions(text)
    elif intent == 'COMPARE_PERIODS':
        response = handler.handle_compare_periods(text)
    elif intent == 'FINANCIAL_ADVICE':
        response = handler.handle_financial_advice(text)
    elif intent == 'QUERY_CATEGORIES':
        response = handler.handle_query_categories(text)
    elif intent == 'MONTHLY_REPORT':
        response = handler.handle_monthly_report(text)
    elif intent == 'GREETING':
        response = handler.handle_greeting(text)
    elif intent == 'HELP':
        response = handler.handle_help(text)
    else:
        response = {
            'type': 'info',
            'message': "🤔 Xin lỗi, tôi chưa hiểu ý bạn.\n\nGõ **'help'** hoặc **'giúp'** để xem hướng dẫn."
        }
    
    result_data['response'] = response
    return result_data
