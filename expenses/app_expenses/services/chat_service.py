import logging
import re
import threading
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Optional, Dict, Any, Tuple
from dateutil.relativedelta import relativedelta

from django.contrib.auth.models import User
from django.db.models import Q, Sum
from django.utils import timezone

from app_expenses.models import Expense, Category, Income, IncomeSource, RecurringExpense, RecurringIncome, Budget
from app_expenses.ml_utils import train_model

logger = logging.getLogger(__name__)


def build_recurring_chat_preview(
    text: str,
    structured: dict,
    user: User,
    intent: str,
) -> Optional[Dict[str, Any]]:
    """
    Construct a structured preview for creating recurring expenses or incomes from chat.
    """
    from app_expenses.utils.nlp_parser import ExpenseNLPParser

    amount = structured.get('amount')
    if not amount:
        amount = ExpenseNLPParser()._extract_amount(text.lower())
    if not amount:
        return None

    frequency = structured.get('frequency')
    if frequency not in {'daily', 'weekly', 'monthly', 'yearly'}:
        frequency_map = {
            'ngày': 'daily', 'hàng ngày': 'daily', 'mỗi ngày': 'daily',
            'tuần': 'weekly', 'hàng tuần': 'weekly', 'mỗi tuần': 'weekly',
            'tháng': 'monthly', 'hàng tháng': 'monthly', 'mỗi tháng': 'monthly',
            'năm': 'yearly', 'hàng năm': 'yearly', 'mỗi năm': 'yearly',
        }
        frequency = next((value for key, value in frequency_map.items() if key in text.lower()), 'monthly')

    date_value = structured.get('date')
    try:
        start_date = date.fromisoformat(date_value) if date_value else timezone.now().date()
    except (TypeError, ValueError):
        start_date = timezone.now().date()

    description = structured.get('description') or text.strip()
    category_hint = structured.get('category_hint')
    category = None
    if category_hint:
        category = Category.objects.filter(user=user, name__icontains=category_hint).first()

    return {
        'amount': amount,
        'description': description,
        'name': description[:200],
        'category_id': category.id if category else None,
        'category_name': category.name if category else category_hint,
        'source_name': structured.get('source_name') or description[:100],
        'frequency': frequency,
        'start_date': start_date.isoformat(),
        'end_date': structured.get('end_date'),
        '_type': 'recurring_income' if intent == 'CREATE_RECURRING_INCOME' else 'recurring_expense',
    }


def build_expense_action_preview(
    text: str,
    user: User,
    intent: str,
) -> Optional[Dict[str, Any]]:
    """
    Find one user-owned expense for explicit edit/delete confirmation from chat.
    """
    from app_expenses.utils.nlp_parser import ExpenseNLPParser

    expenses = Expense.objects.filter(user=user).select_related('category')
    amount = ExpenseNLPParser()._extract_amount(text.lower())
    if amount:
        expenses = expenses.filter(amount=amount)

    search_terms = re.sub(
        r'\b(sửa|sửa khoản chi|sửa chi tiêu|đổi|cập nhật|xóa|xóa khoản chi|'
        r'xóa chi tiêu|xóa giao dịch|bỏ|khoản|chi tiêu|giao dịch|giúp|tôi|cho tôi)\b',
        ' ', text.lower()
    )
    meaningful_terms = [term for term in search_terms.split() if len(term) > 2]
    if meaningful_terms:
        term_query = Q()
        for term in meaningful_terms:
            term_query |= Q(description__icontains=term) | Q(category__name__icontains=term)
        expenses = expenses.filter(term_query)

    expense = expenses.order_by('-date', '-id').first()
    if not expense:
        return None

    return {
        'expense_id': expense.id,
        'amount': float(expense.amount),
        'description': expense.description or '',
        'date': expense.date.isoformat(),
        'category_id': expense.category_id,
        'category_name': expense.category.name if expense.category else 'Khác',
        'action': 'delete' if intent == 'DELETE_EXPENSE' else 'edit',
        '_type': 'expense_action',
    }


def create_income_from_chat(user: User, data: dict) -> Tuple[bool, dict, int]:
    """
    Create a new Income record after user confirmation in chat.
    """
    try:
        amount = Decimal(str(data.get('amount', '')))
        description = str(data.get('description', '')).strip()[:500]
        source_name = str(data.get('source_name', 'Khác')).strip()[:100] or 'Khác'
        date_str = data.get('date')
        if amount <= 0 or not date_str:
            return False, {'success': False, 'error': 'Dữ liệu thu nhập không hợp lệ'}, 400
        income_date = datetime.strptime(date_str, '%Y-%m-%d').date()
    except (TypeError, ValueError, ArithmeticError):
        return False, {'success': False, 'error': 'Dữ liệu thu nhập không hợp lệ'}, 400

    income_source, _ = IncomeSource.objects.get_or_create(
        user=user,
        name=source_name,
    )
    income = Income.objects.create(
        user=user,
        source=income_source,
        amount=amount,
        description=description,
        date=income_date,
    )
    return True, {'success': True, 'income_id': income.id}, 200


def create_recurring_from_chat(user: User, data: dict) -> Tuple[bool, dict, int]:
    """
    Create a new RecurringExpense or RecurringIncome template from chat confirmation.
    """
    try:
        amount = Decimal(str(data.get('amount', '')))
        name = str(data.get('name') or data.get('description') or '').strip()[:200]
        frequency = data.get('frequency')
        start_date = datetime.strptime(data.get('start_date', ''), '%Y-%m-%d').date()
        end_date_value = data.get('end_date')
        end_date = datetime.strptime(end_date_value, '%Y-%m-%d').date() if end_date_value else None
        transaction_type = data.get('transaction_type')
        if amount <= 0 or not name or frequency not in {'daily', 'weekly', 'monthly', 'yearly'}:
            raise ValueError
        if end_date and end_date <= start_date:
            raise ValueError
    except (TypeError, ValueError, ArithmeticError):
        return False, {'success': False, 'error': 'Dữ liệu định kỳ không hợp lệ'}, 400

    next_due_date = start_date + {
        'daily': timedelta(days=1),
        'weekly': timedelta(weeks=1),
        'monthly': relativedelta(months=1),
        'yearly': relativedelta(years=1),
    }[frequency]

    if transaction_type == 'recurring_income':
        source_name = str(data.get('source_name') or name).strip()[:100]
        source, _ = IncomeSource.objects.get_or_create(user=user, name=source_name)
        recurring = RecurringIncome.objects.create(
            user=user,
            source=source,
            name=name,
            amount=amount,
            frequency=frequency,
            start_date=start_date,
            end_date=end_date,
            next_due_date=next_due_date,
            description=data.get('description', '')[:500],
        )
    else:
        category = None
        category_id = data.get('category_id')
        if category_id:
            category = Category.objects.filter(id=category_id, user=user).first()
        recurring = RecurringExpense.objects.create(
            user=user,
            name=name,
            amount=amount,
            category=category,
            frequency=frequency,
            start_date=start_date,
            end_date=end_date,
            next_due_date=next_due_date,
            description=data.get('description', '')[:500],
        )

    return True, {'success': True, 'recurring_id': recurring.id}, 200


def manage_expense_from_chat(user: User, data: dict) -> Tuple[bool, dict, int]:
    """
    Perform edit or delete on a user-owned expense from chat confirmation.
    """
    try:
        expense = Expense.objects.get(pk=data.get('expense_id'), user=user)
        action = data.get('action')
        if action not in {'edit', 'delete'}:
            raise ValueError
    except (TypeError, ValueError, Expense.DoesNotExist):
        return False, {'success': False, 'error': 'Giao dịch không hợp lệ'}, 400

    if action == 'delete':
        expense_id = expense.id
        expense.delete()
        logger.info('Chat expense deleted: user_id=%s expense_id=%s', user.id, expense_id)
        return True, {'success': True, 'action': 'delete'}, 200

    try:
        amount = Decimal(str(data.get('amount', expense.amount)))
        date_value = datetime.strptime(data.get('date', expense.date.isoformat()), '%Y-%m-%d').date()
        description = str(data.get('description', expense.description or '')).strip()[:500]
        if amount <= 0 or not description:
            raise ValueError
        category_id = data.get('category_id')
        category = Category.objects.filter(id=category_id, user=user).first() if category_id else None
        expense.amount = amount
        expense.date = date_value
        expense.description = description
        expense.category = category
        expense.save(update_fields=['amount', 'date', 'description', 'category'])
    except (TypeError, ValueError, ArithmeticError):
        return False, {'success': False, 'error': 'Dữ liệu cập nhật không hợp lệ'}, 400

    logger.info('Chat expense edited: user_id=%s expense_id=%s', user.id, expense.id)
    return True, {'success': True, 'action': 'edit', 'expense_id': expense.id}, 200


def create_expense_from_chat(user: User, data: dict) -> Tuple[bool, dict, int]:
    """
    Validate, create Expense from chat payload, check budget warning, and trigger background ML training.
    """
    amount_raw = data.get('amount')
    description = str(data.get('description', '')).strip()
    category_id = data.get('category_id')
    date_str = data.get('date')

    if not amount_raw:
        return False, {'success': False, 'error': 'Thiếu số tiền'}, 400

    if not date_str:
        return False, {'success': False, 'error': 'Thiếu ngày tháng'}, 400

    try:
        amount = Decimal(str(amount_raw))
        if amount <= 0:
            return False, {'success': False, 'error': 'Số tiền phải lớn hơn 0'}, 400
    except (TypeError, ValueError, ArithmeticError):
        return False, {'success': False, 'error': 'Số tiền không hợp lệ'}, 400

    try:
        if 'T' in date_str:
            expense_date = datetime.fromisoformat(date_str).date()
        else:
            expense_date = datetime.strptime(date_str, '%Y-%m-%d').date()
    except (ValueError, TypeError):
        return False, {'success': False, 'error': 'Ngày tháng không hợp lệ'}, 400

    category = None
    if category_id:
        try:
            category = Category.objects.get(id=category_id, user=user)
        except Category.DoesNotExist:
            return False, {'success': False, 'error': f'Danh mục không tồn tại (ID: {category_id})'}, 400

    expense = Expense.objects.create(
        user=user,
        amount=amount,
        description=description,
        category=category,
        date=expense_date,
    )

    # Kiểm tra cảnh báo vượt ngân sách
    warning_message = None
    try:
        budget = Budget.objects.get(user=user)
        current_total = Expense.objects.filter(user=user).aggregate(Sum('amount'))['amount__sum'] or Decimal('0')
        if current_total > budget.total:
            over_amount = current_total - budget.total
            warning_message = f'⚠️ Bạn đã vượt quá ngân sách {over_amount:,.0f} ₫!'
    except Budget.DoesNotExist:
        pass
    except Exception as e:
        logger.warning("Error checking budget warning: %s", e)

    # Train model trong background thread
    try:
        thread = threading.Thread(target=train_model, args=(user,))
        thread.start()
    except Exception as e:
        logger.warning("Error starting background ML train thread: %s", e)

    return True, {
        'success': True,
        'expense_id': expense.id,
        'warning': warning_message,
    }, 200
