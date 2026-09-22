from datetime import date
from decimal import Decimal
from typing import Optional, Dict, Any, List
from dateutil.relativedelta import relativedelta

from django.contrib.auth.models import User
from django.db.models import Sum, Q
from django.template.loader import render_to_string
from django.utils import timezone

from app_expenses.models import Expense, Income, Budget, RecurringExpense, Announcement


def get_dashboard_summary_metrics(
    user: User,
    today: Optional[date] = None,
) -> Dict[str, Any]:
    """
    Calculate and aggregate summary statistics and metrics for user dashboard.

    Uses single conditional aggregations to avoid multiple queries.
    """
    if today is None:
        today = timezone.now().date()

    first_day_this_month = today.replace(day=1)
    first_day_next_month = first_day_this_month + relativedelta(months=1)
    first_day_last_month = first_day_this_month - relativedelta(months=1)

    # Thống kê chi tiêu (gộp total, tháng này, tháng trước)
    expense_stats = Expense.objects.filter(user=user).aggregate(
        total=Sum('amount'),
        this_month=Sum('amount', filter=Q(date__gte=first_day_this_month, date__lt=first_day_next_month)),
        last_month=Sum('amount', filter=Q(date__gte=first_day_last_month, date__lt=first_day_this_month)),
    )
    total_expenses = expense_stats['total'] or Decimal('0')
    this_month_expenses = expense_stats['this_month'] or Decimal('0')
    last_month_expenses = expense_stats['last_month'] or Decimal('0')

    # Thống kê thu nhập (gộp total, tháng này)
    income_stats = Income.objects.filter(user=user).aggregate(
        total=Sum('amount'),
        this_month=Sum('amount', filter=Q(date__gte=first_day_this_month, date__lt=first_day_next_month)),
    )
    total_income = income_stats['total'] or Decimal('0')
    this_month_income = income_stats['this_month'] or Decimal('0')

    balance = total_income - total_expenses

    budget_obj, _ = Budget.objects.get_or_create(user=user)
    budget_remaining = budget_obj.total - this_month_expenses
    budget_percentage = (this_month_expenses / budget_obj.total * 100) if budget_obj.total > 0 else 0

    top_categories = Expense.objects.filter(user=user).values('category__name').annotate(
        total=Sum('amount')
    ).order_by('-total')[:5]

    recent_expenses = Expense.objects.filter(user=user).select_related('category').order_by('-date')[:3]
    recent_income = Income.objects.filter(user=user).select_related('source').order_by('-date')[:3]

    upcoming_recurring = RecurringExpense.objects.filter(
        user=user,
        is_active=True,
        next_due_date__gte=today,
    ).select_related('category').order_by('next_due_date')[:5]

    active_announcements = Announcement.objects.filter(is_active=True).order_by('-created_at')

    return {
        'total_expenses': total_expenses,
        'this_month_expenses': this_month_expenses,
        'last_month_expenses': last_month_expenses,
        'total_income': total_income,
        'this_month_income': this_month_income,
        'balance': balance,
        'budget': budget_obj,
        'budget_remaining': budget_remaining,
        'budget_percentage': budget_percentage,
        'top_categories': top_categories,
        'recent_expenses': recent_expenses,
        'recent_income': recent_income,
        'upcoming_recurring': upcoming_recurring,
        'active_announcements': active_announcements,
    }


def get_monthly_trend_chart_data(
    user: User,
    months_count: int = 6,
    today: Optional[date] = None,
) -> Dict[str, List]:
    """
    Retrieve monthly expense trend over recent N months in a single query.
    """
    if today is None:
        today = timezone.now().date()

    month_ranges = []
    agg_kwargs = {}
    for i in range(months_count - 1, -1, -1):
        month_start = today.replace(day=1) - relativedelta(months=i)
        month_end = month_start + relativedelta(months=1)
        label = month_start.strftime('%m/%Y')
        key = f'm_{i}'
        month_ranges.append((label, key))
        agg_kwargs[key] = Sum('amount', filter=Q(date__gte=month_start, date__lt=month_end))

    oldest_start = today.replace(day=1) - relativedelta(months=months_count - 1)
    newest_end = today.replace(day=1) + relativedelta(months=1)

    expense_agg = Expense.objects.filter(
        user=user,
        date__gte=oldest_start,
        date__lt=newest_end,
    ).aggregate(**agg_kwargs)

    labels = [label for label, key in month_ranges]
    data = [float(expense_agg.get(key) or 0) for label, key in month_ranges]

    return {
        'labels': labels,
        'data': data,
    }


def get_expense_vs_income_chart_data(
    user: User,
    months_count: int = 6,
    today: Optional[date] = None,
) -> Dict[str, List]:
    """
    Retrieve monthly expense vs income comparison over recent N months in 2 queries.
    """
    if today is None:
        today = timezone.now().date()

    month_ranges = []
    exp_agg_kwargs = {}
    inc_agg_kwargs = {}
    for i in range(months_count - 1, -1, -1):
        month_start = today.replace(day=1) - relativedelta(months=i)
        month_end = month_start + relativedelta(months=1)
        label = month_start.strftime('%m/%Y')
        key = f'm_{i}'
        month_ranges.append((label, key))
        exp_agg_kwargs[key] = Sum('amount', filter=Q(date__gte=month_start, date__lt=month_end))
        inc_agg_kwargs[key] = Sum('amount', filter=Q(date__gte=month_start, date__lt=month_end))

    oldest_start = today.replace(day=1) - relativedelta(months=months_count - 1)
    newest_end = today.replace(day=1) + relativedelta(months=1)

    expense_agg = Expense.objects.filter(
        user=user,
        date__gte=oldest_start,
        date__lt=newest_end,
    ).aggregate(**exp_agg_kwargs)

    income_agg = Income.objects.filter(
        user=user,
        date__gte=oldest_start,
        date__lt=newest_end,
    ).aggregate(**inc_agg_kwargs)

    labels = [label for label, key in month_ranges]
    expense_data = [float(expense_agg.get(key) or 0) for label, key in month_ranges]
    income_data = [float(income_agg.get(key) or 0) for label, key in month_ranges]

    return {
        'labels': labels,
        'expenses': expense_data,
        'income': income_data,
    }


def get_category_distribution_chart_data(
    user: User,
    limit: int = 10,
) -> Dict[str, List]:
    """
    Retrieve top spending categories for chart rendering.
    """
    category_data = Expense.objects.filter(user=user).values('category__name').annotate(
        total=Sum('amount')
    ).order_by('-total')[:limit]

    labels = [item['category__name'] or 'Không xác định' for item in category_data]
    data = [float(item['total']) for item in category_data]

    return {
        'labels': labels,
        'data': data,
    }


def get_dashboard_refresh_payload(
    user: User,
    request=None,
    today: Optional[date] = None,
) -> Dict[str, Any]:
    """
    Construct complete refresh payload for AJAX dashboard updates.
    """
    if today is None:
        today = timezone.now().date()

    first_day_this_month = today.replace(day=1)
    first_day_next_month = first_day_this_month + relativedelta(months=1)

    exp_agg_kwargs = {
        'total': Sum('amount'),
        'this_month': Sum('amount', filter=Q(date__gte=first_day_this_month, date__lt=first_day_next_month)),
    }
    inc_agg_kwargs = {
        'total': Sum('amount'),
        'this_month': Sum('amount', filter=Q(date__gte=first_day_this_month, date__lt=first_day_next_month)),
    }
    month_ranges = []
    for i in range(5, -1, -1):
        m_start = first_day_this_month - relativedelta(months=i)
        m_end = m_start + relativedelta(months=1)
        label = m_start.strftime('%m/%Y')
        key = f'm_{i}'
        month_ranges.append((label, key))
        exp_agg_kwargs[key] = Sum('amount', filter=Q(date__gte=m_start, date__lt=m_end))
        inc_agg_kwargs[key] = Sum('amount', filter=Q(date__gte=m_start, date__lt=m_end))

    expense_agg = Expense.objects.filter(user=user).aggregate(**exp_agg_kwargs)
    income_agg = Income.objects.filter(user=user).aggregate(**inc_agg_kwargs)

    total_expenses = expense_agg['total'] or Decimal('0')
    this_month_expenses = expense_agg['this_month'] or Decimal('0')

    total_income = income_agg['total'] or Decimal('0')
    this_month_income = income_agg['this_month'] or Decimal('0')

    balance = total_income - total_expenses

    budget_obj, _ = Budget.objects.get_or_create(user=user)
    budget_remaining = budget_obj.total - this_month_expenses
    budget_percentage = (this_month_expenses / budget_obj.total * 100) if budget_obj.total > 0 else 0

    top_categories = Expense.objects.filter(user=user).values('category__name').annotate(
        total=Sum('amount')
    ).order_by('-total')[:5]

    recent_expenses = Expense.objects.filter(user=user).select_related('category').order_by('-date')[:3]
    recent_income = Income.objects.filter(user=user).select_related('source').order_by('-date')[:3]

    cat_chart = get_category_distribution_chart_data(user, limit=10)

    income_labels = [label for label, key in month_ranges]
    income_values = [float(income_agg.get(key) or 0) for label, key in month_ranges]
    expense_values = [float(expense_agg.get(key) or 0) for label, key in month_ranges]

    top_categories_html = render_to_string(
        'ep1/partials/dashboard_top_categories.html',
        {'top_categories': top_categories},
        request=request,
    )

    recent_transactions_html = render_to_string(
        'ep1/partials/dashboard_recent_transactions.html',
        {
            'recent_expenses': recent_expenses,
            'recent_income': recent_income,
        },
        request=request,
    )

    return {
        'success': True,
        'summary': {
            'this_month_expenses': float(this_month_expenses),
            'total_expenses': float(total_expenses),
            'this_month_income': float(this_month_income),
            'total_income': float(total_income),
            'balance': float(balance),
            'budget_total': float(budget_obj.total),
            'budget_remaining': float(budget_remaining),
            'budget_percentage': float(budget_percentage),
        },
        'top_categories_html': top_categories_html,
        'recent_transactions_html': recent_transactions_html,
        'charts_category': {
            'labels': cat_chart['labels'],
            'data': cat_chart['data'],
        },
        'charts_income_expense': {
            'labels': income_labels,
            'income': income_values,
            'expenses': expense_values,
        },
    }
