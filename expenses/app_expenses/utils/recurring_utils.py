"""
Utility functions cho tính năng Chi tiêu định kỳ (Recurring Expenses)

Module này chứa các hàm tính toán ngày đến hạn tiếp theo cho các chi tiêu định kỳ.
"""

from datetime import timedelta
from dateutil.relativedelta import relativedelta
from django.utils import timezone


def calculate_next_due_date(start_date, frequency, today=None):
    """
    Tính ngày đến hạn tiếp theo dựa trên start_date và frequency.
    
    Logic:
    1. Bắt đầu từ start_date
    2. Cộng dần theo frequency cho đến khi >= today
    3. Trả về ngày đầu tiên >= today
    
    Args:
        start_date (date): Ngày bắt đầu của mẫu định kỳ
        frequency (str): Tần suất ('daily', 'weekly', 'monthly', 'yearly')
        today (date, optional): Ngày hiện tại (mặc định = hôm nay)
    
    Returns:
        date: Ngày đến hạn tiếp theo (>= today)
    
    Examples:
        >>> from datetime import date
        >>> # Hôm nay là 13/01/2026, start_date là 10/01/2026
        >>> calculate_next_due_date(date(2026, 1, 10), 'monthly', date(2026, 1, 13))
        datetime.date(2026, 2, 10)  # Tháng sau vì 10/01 đã qua
        
        >>> # Hôm nay là 13/01/2026, start_date là 20/01/2026
        >>> calculate_next_due_date(date(2026, 1, 20), 'monthly', date(2026, 1, 13))
        datetime.date(2026, 1, 20)  # Chưa đến nên giữ nguyên
    """
    if today is None:
        today = timezone.now().date()
    
    next_due = start_date
    
    # Cộng dần cho đến khi next_due >= today
    # Vòng lặp này đảm bảo ngày đến hạn luôn trong tương lai
    while next_due < today:
        next_due = add_frequency_to_date(next_due, frequency)
    
    return next_due


def add_frequency_to_date(date, frequency):
    """
    Cộng 1 khoảng thời gian theo frequency vào date.
    
    Args:
        date (date): Ngày cần cộng
        frequency (str): Tần suất ('daily', 'weekly', 'monthly', 'yearly')
    
    Returns:
        date: Ngày sau khi cộng thêm 1 khoảng
    
    Examples:
        >>> from datetime import date
        >>> add_frequency_to_date(date(2026, 1, 15), 'daily')
        datetime.date(2026, 1, 16)
        
        >>> add_frequency_to_date(date(2026, 1, 15), 'monthly')
        datetime.date(2026, 2, 15)
    """
    if frequency == 'daily':
        return date + timedelta(days=1)
    elif frequency == 'weekly':
        return date + timedelta(weeks=1)
    elif frequency == 'monthly':
        return date + relativedelta(months=1)
    elif frequency == 'yearly':
        return date + relativedelta(years=1)
    else:
        # Mặc định trả về ngày gốc nếu frequency không hợp lệ
        return date


def get_frequency_description(frequency):
    """
    Lấy mô tả chi tiết cho tần suất.
    
    Args:
        frequency (str): Tần suất ('daily', 'weekly', 'monthly', 'yearly')
    
    Returns:
        str: Mô tả chi tiết
    """
    descriptions = {
        'daily': 'Tạo chi tiêu mỗi ngày',
        'weekly': 'Tạo chi tiêu mỗi tuần (cùng thứ trong tuần)',
        'monthly': 'Tạo chi tiêu mỗi tháng (cùng ngày trong tháng)',
        'yearly': 'Tạo chi tiêu mỗi năm (cùng ngày/tháng)',
    }
    return descriptions.get(frequency, 'Không xác định')
