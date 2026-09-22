import logging
from datetime import date
from typing import Optional, Tuple
from django.contrib.auth.models import User
from django.db import transaction, IntegrityError
from django.utils import timezone

from app_expenses.models import Expense, Income, RecurringExpense, RecurringIncome

logger = logging.getLogger(__name__)


def generate_due_recurring_transactions(
    user: User,
    today: Optional[date] = None,
) -> Tuple[int, int, int]:
    """
    Generate actual Expense and Income records from due recurring templates.

    Ensures strict atomicity, concurrency protection via row locking (`select_for_update`),
    and database-level idempotency to prevent duplicate occurrences.

    Args:
        user: The authenticated User owning the recurring templates.
        today: The reference date for due checking (defaults to current local date).

    Returns:
        Tuple of (generated_expenses_count, generated_incomes_count, skipped_duplicates).
    """
    if today is None:
        today = timezone.now().date()

    generated_count = 0
    generated_income_count = 0
    skipped_duplicates = 0

    # ── Recurring Expenses ─────────────────────────────────────────────────────
    with transaction.atomic():
        due_recurrings = (
            RecurringExpense.objects
            .select_for_update()
            .filter(user=user, is_active=True, next_due_date__lte=today)
            .select_related('category')
        )

        for recurring in due_recurrings:
            if recurring.is_expired():
                recurring.is_active = False
                recurring.save(update_fields=['is_active'])
                continue

            occurrence_date = recurring.next_due_date

            try:
                with transaction.atomic():
                    Expense.objects.create(
                        user=user,
                        amount=recurring.amount,
                        description=f"[Định kỳ] {recurring.description or recurring.name}",
                        category=recurring.category,
                        date=occurrence_date,
                        recurring_template=recurring,
                        occurrence_date=occurrence_date,
                    )
                    recurring.advance_next_due_date()
                    recurring.save(update_fields=['next_due_date'])
                    generated_count += 1

            except IntegrityError:
                logger.warning(
                    "Duplicate recurring expense skipped: template=%s occurrence=%s",
                    recurring.pk,
                    occurrence_date,
                )
                skipped_duplicates += 1

    # ── Recurring Incomes ──────────────────────────────────────────────────────
    with transaction.atomic():
        due_incomes = (
            RecurringIncome.objects
            .select_for_update()
            .filter(user=user, is_active=True, next_due_date__lte=today)
            .select_related('source')
        )

        for recurring_income in due_incomes:
            if recurring_income.is_expired():
                recurring_income.is_active = False
                recurring_income.save(update_fields=['is_active'])
                continue

            occurrence_date = recurring_income.next_due_date

            try:
                with transaction.atomic():
                    Income.objects.create(
                        user=user,
                        source=recurring_income.source,
                        amount=recurring_income.amount,
                        description=f"[Định kỳ] {recurring_income.description or recurring_income.name}",
                        date=occurrence_date,
                        recurring_income_template=recurring_income,
                        occurrence_date=occurrence_date,
                    )
                    recurring_income.advance_next_due_date()
                    recurring_income.save(update_fields=['next_due_date'])
                    generated_income_count += 1

            except IntegrityError:
                logger.warning(
                    "Duplicate recurring income skipped: template=%s occurrence=%s",
                    recurring_income.pk,
                    occurrence_date,
                )
                skipped_duplicates += 1

    return generated_count, generated_income_count, skipped_duplicates


def toggle_recurring_active_status(recurring_id: int, user: User) -> Tuple[bool, str]:
    """
    Toggle the active/inactive state of a user's recurring expense template.

    Args:
        recurring_id: ID of the RecurringExpense instance.
        user: The owner User.

    Returns:
        Tuple of (new_is_active_status, template_name).
    """
    recurring = RecurringExpense.objects.get(pk=recurring_id, user=user)
    recurring.is_active = not recurring.is_active
    recurring.save(update_fields=['is_active'])
    return recurring.is_active, recurring.name
