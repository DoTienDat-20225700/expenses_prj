"""
Service layer modules for app_expenses.
Decouples domain business logic from Django HTTP view handlers.
"""

from .recurring_service import (
    generate_due_recurring_transactions,
    toggle_recurring_active_status,
)
from .dashboard_service import (
    get_dashboard_summary_metrics,
    get_monthly_trend_chart_data,
    get_expense_vs_income_chart_data,
    get_category_distribution_chart_data,
    get_dashboard_refresh_payload,
)
from .savings_service import (
    calculate_ai_savings_suggestions,
    sync_savings_goal_status,
)
from .chat_service import (
    build_recurring_chat_preview,
    build_expense_action_preview,
    create_income_from_chat,
    create_recurring_from_chat,
    manage_expense_from_chat,
    create_expense_from_chat,
)

__all__ = [
    'generate_due_recurring_transactions',
    'toggle_recurring_active_status',
    'get_dashboard_summary_metrics',
    'get_monthly_trend_chart_data',
    'get_expense_vs_income_chart_data',
    'get_category_distribution_chart_data',
    'get_dashboard_refresh_payload',
    'calculate_ai_savings_suggestions',
    'sync_savings_goal_status',
    'build_recurring_chat_preview',
    'build_expense_action_preview',
    'create_income_from_chat',
    'create_recurring_from_chat',
    'manage_expense_from_chat',
    'create_expense_from_chat',
]
