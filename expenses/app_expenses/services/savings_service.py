from datetime import timedelta
from decimal import Decimal
from typing import Dict, Any

from django.contrib.auth.models import User
from django.db.models import Sum
from django.utils import timezone

from app_expenses.models import Expense, SavingsGoal


def sync_savings_goal_status(goal: SavingsGoal) -> bool:
    """
    Check if a SavingsGoal has been reached and persist the completed status if changed.

    Returns:
        True if the goal is completed, False otherwise.
    """
    if not goal.is_completed and goal.check_completion():
        goal.save(update_fields=['is_completed'])
        return True
    return goal.is_completed


def calculate_ai_savings_suggestions(user: User, goal: SavingsGoal) -> Dict[str, Any]:
    """
    Generate AI-driven savings suggestions and feasibility roadmap based on:
    - User's recent 30-day spending history
    - Target amount and remaining timeline
    - Selected reduction categories

    Uses single grouped aggregation for selected categories to avoid N+1 queries.
    """
    suggestions = {
        'daily_needed': goal.daily_savings_needed,
        'days_remaining': goal.days_remaining,
        'amount_remaining': goal.amount_remaining,
        'progress_percentage': goal.progress_percentage,
        'is_achievable': True,
        'category_analysis': [],
        'recommendations': [],
        'weekly_plan': {},
        'monthly_plan': {},
    }

    # Nếu đã hoàn thành hoặc quá hạn
    if goal.is_completed:
        suggestions['recommendations'].append({
            'type': 'success',
            'message': '🎉 Chúc mừng! Bạn đã hoàn thành mục tiêu này!',
        })
        return suggestions

    if goal.is_overdue:
        suggestions['recommendations'].append({
            'type': 'warning',
            'message': '⚠️ Mục tiêu đã quá hạn. Hãy cân nhắc gia hạn hoặc điều chỉnh mục tiêu.',
        })
        suggestions['is_achievable'] = False
        return suggestions

    # Phân tích chi tiêu trong 30 ngày gần đây
    thirty_days_ago = timezone.now().date() - timedelta(days=30)
    recent_expenses = Expense.objects.filter(
        user=user,
        date__gte=thirty_days_ago,
    )

    # Tổng chi tiêu 30 ngày
    total_spent_30days = recent_expenses.aggregate(Sum('amount'))['amount__sum'] or Decimal('0')
    daily_avg_spending = total_spent_30days / 30 if total_spent_30days > 0 else Decimal('0')

    # Phân tích từng danh mục được chọn để cắt giảm (gom thành 1 query duy nhất)
    categories_to_reduce = list(goal.categories_to_reduce.all())

    if categories_to_reduce:
        total_reducible = Decimal('0')
        cat_ids = [c.id for c in categories_to_reduce]

        cat_totals_query = recent_expenses.filter(category_id__in=cat_ids).values('category_id').annotate(
            cat_total=Sum('amount')
        )
        totals_by_cat_id = {item['category_id']: (item['cat_total'] or Decimal('0')) for item in cat_totals_query}

        for category in categories_to_reduce:
            cat_total = totals_by_cat_id.get(category.id, Decimal('0'))
            cat_daily_avg = cat_total / 30

            # Gợi ý cắt giảm 60%
            suggested_reduction_pct = 60
            suggested_daily_reduction = cat_daily_avg * Decimal(suggested_reduction_pct / 100)
            total_reducible += suggested_daily_reduction

            if cat_total > 0:
                suggestions['category_analysis'].append({
                    'category_name': category.name,
                    'total_30days': float(cat_total),
                    'daily_average': float(cat_daily_avg),
                    'suggested_reduction_pct': suggested_reduction_pct,
                    'suggested_daily_reduction': float(suggested_daily_reduction),
                    'monthly_savings': float(suggested_daily_reduction * 30),
                })

        # So sánh số tiền cần tiết kiệm với số tiền có thể cắt giảm
        if total_reducible >= goal.daily_savings_needed:
            suggestions['is_achievable'] = True
            suggestions['recommendations'].append({
                'type': 'success',
                'message': f'✅ Mục tiêu khả thi! Bạn có thể tiết kiệm {float(total_reducible):,.0f}đ/ngày bằng cách cắt giảm các danh mục đã chọn.',
            })
        else:
            gap = goal.daily_savings_needed - total_reducible
            suggestions['recommendations'].append({
                'type': 'warning',
                'message': f'⚠️ Cắt giảm các danh mục đã chọn chỉ đủ tiết kiệm {float(total_reducible):,.0f}đ/ngày. Bạn còn thiếu {float(gap):,.0f}đ/ngày. Hãy xem xét thêm các danh mục khác.',
            })
    else:
        # Nếu chưa chọn danh mục nào, phân tích top 5 danh mục chi tiêu nhiều nhất
        suggestions['recommendations'].append({
            'type': 'info',
            'message': '💡 Hãy chọn các danh mục bạn muốn cắt giảm để nhận gợi ý chi tiết hơn.',
        })

        top_categories = recent_expenses.values('category__name').annotate(
            total=Sum('amount')
        ).order_by('-total')[:5]

        for cat in top_categories:
            if cat['category__name']:
                cat_total = cat['total'] or Decimal('0')
                cat_daily = cat_total / 30
                suggestions['category_analysis'].append({
                    'category_name': cat['category__name'],
                    'total_30days': float(cat_total),
                    'daily_average': float(cat_daily),
                    'suggested_reduction_pct': 50,
                    'suggested_daily_reduction': float(cat_daily * Decimal('0.5')),
                    'monthly_savings': float(cat_daily * Decimal('0.5') * 30),
                })

    # Kế hoạch tuần/tháng
    days = goal.days_remaining
    if days > 0:
        suggestions['weekly_plan'] = {
            'amount': float(goal.daily_savings_needed * 7),
            'description': f'Tiết kiệm {float(goal.daily_savings_needed * 7):,.0f}đ mỗi tuần',
        }
        suggestions['monthly_plan'] = {
            'amount': float(goal.daily_savings_needed * 30),
            'description': f'Tiết kiệm {float(goal.daily_savings_needed * 30):,.0f}đ mỗi tháng',
        }

    # Thêm gợi ý tài chính thông minh
    if goal.daily_savings_needed > 0:
        daily_needed = float(goal.daily_savings_needed)
        if daily_needed < 50000:
            suggestions['recommendations'].append({
                'type': 'tip',
                'message': '💰 Mẹo: Bỏ 1 ly cafe/trà sữa mỗi ngày (40-50k) là đủ để đạt mục tiêu!',
            })
        elif daily_needed < 100000:
            suggestions['recommendations'].append({
                'type': 'tip',
                'message': '💰 Mẹo: Tự nấu ăn thay vì ăn ngoài, mang cơm trưa đi làm có thể tiết kiệm 50-100k/ngày.',
            })
        elif daily_needed < 200000:
            suggestions['recommendations'].append({
                'type': 'tip',
                'message': '💰 Mẹo: Cắt giảm shopping và giải trí không cần thiết, đi lại bằng phương tiện công cộng.',
            })
        else:
            suggestions['recommendations'].append({
                'type': 'tip',
                'message': f'💰 Số tiền cần tiết kiệm khá lớn ({daily_needed:,.0f}đ/ngày). Hãy xem xét tăng thu nhập hoặc kéo dài thời gian mục tiêu.',
            })

    return suggestions
