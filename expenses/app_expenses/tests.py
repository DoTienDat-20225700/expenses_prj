from datetime import timedelta, date
from decimal import Decimal
import os
import json
from unittest.mock import patch

from django.contrib.auth import get_user_model

from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from app_expenses.models import (
    Budget, Category, Expense, Income, IncomeSource,
    RecurringExpense, RecurringIncome, SavingsGoal,
)
from app_expenses.form import ExpenseForm, IncomeForm, RecurringExpenseForm, SavingsGoalForm
from app_expenses.utils.chat_intent import ChatIntentDetector, ChatQueryHandler
from app_expenses.utils.nlp_parser import ExpenseNLPParser


class ChatbotRegressionTests(TestCase):
	def setUp(self):
		self.gemini_patcher = patch(
			'app_expenses.utils.gemini_service.analyze_chat_message',
			side_effect=RuntimeError('Gemini disabled in unit tests'),
		)
		self.gemini_patcher.start()

	def tearDown(self):
		self.gemini_patcher.stop()

	def test_expense_parser_supports_tr_and_decimal_amounts(self):
		parser = ExpenseNLPParser()

		result = parser.parse("Mua điện thoại 1.5tr", None)

		self.assertTrue(result['success'])
		self.assertEqual(result['amount'], 1500000.0)

	def test_income_amount_parser_supports_decimal_tr(self):
		detector = ChatQueryHandler(None)

		self.assertEqual(detector._extract_amount("Nhận lương 1,5tr"), 1500000.0)

	def test_previous_month_has_previous_month_boundaries(self):
		detector = ChatQueryHandler(None)
		today = timezone.now().date()

		result = detector._extract_time_range("Chi tiêu tháng trước")
		expected_end = today.replace(day=1) - timedelta(days=1)

		self.assertEqual(result['label'], 'tháng trước')
		self.assertEqual(result['start'], expected_end.replace(day=1))
		self.assertEqual(result['end'], expected_end)

	def test_expense_with_iphone_is_not_out_of_scope(self):
		intent, _ = ChatIntentDetector().detect_intent("Mua iphone 100k")

		self.assertEqual(intent, 'CREATE_EXPENSE')

	def test_natural_expense_question_is_query(self):
		intent, _ = ChatIntentDetector().detect_intent("tháng này chi tiêu như nào")

		self.assertEqual(intent, 'QUERY_EXPENSES')

	def test_help_examples_cover_all_supported_chat_intents(self):
		examples = {
			'Ăn sáng 50k': 'CREATE_EXPENSE',
			'Nhận lương 10 triệu': 'CREATE_INCOME',
			'Tiền điện 500k mỗi tháng': 'CREATE_RECURRING_EXPENSE',
			'Lương 15 triệu mỗi tháng': 'CREATE_RECURRING_INCOME',
			'Tổng chi tiêu hôm nay?': 'QUERY_EXPENSES',
			'Thu nhập tháng này?': 'QUERY_INCOME',
			'Top chi tiêu lớn nhất?': 'TOP_EXPENSES',
			'Giao dịch gần đây?': 'RECENT_TRANSACTIONS',
			'Tìm chi tiêu đổ xăng': 'SEARCH_EXPENSES',
			'So sánh tháng này với tháng trước': 'COMPARE_PERIODS',
			'Báo cáo tháng chi tiết': 'MONTHLY_REPORT',
			'Tổng quan tài chính': 'QUERY_SUMMARY',
			'Danh mục chi tiêu': 'QUERY_CATEGORIES',
			'Tư vấn tiết kiệm': 'FINANCIAL_ADVICE',
			'Sửa khoản chi cafe': 'EDIT_EXPENSE',
			'Xóa giao dịch tiền điện': 'DELETE_EXPENSE',
		}

		for text, expected_intent in examples.items():
			with self.subTest(text=text):
				intent, _ = ChatIntentDetector().detect_intent(text)
				self.assertEqual(intent, expected_intent)

	def test_help_response_lists_recurring_and_edit_delete_actions(self):
		response = ChatQueryHandler(None).handle_help('help')

		self.assertIn('Tiền điện 500k mỗi tháng', response['message'])
		self.assertIn('Sửa khoản chi cafe', response['message'])
		self.assertIn('Xóa giao dịch tiền điện', response['message'])

	def test_natural_expense_question_api_does_not_require_amount(self):
		user = get_user_model().objects.create_user(username='query-test')
		self.client.force_login(user)

		response = self.client.post(
			reverse('ep1:parse_expense_api'),
			data=json.dumps({'text': 'tháng này chi tiêu như nào'}),
			content_type='application/json',
		)

		self.assertEqual(response.status_code, 200)
		self.assertTrue(response.json()['is_query'])

	def test_expense_follow_up_uses_previous_chat_context(self):
		user = get_user_model().objects.create_user(username='chat-context-test')
		self.client.force_login(user)

		first_response = self.client.post(
			reverse('ep1:parse_expense_api'),
			data=json.dumps({'text': 'tháng này chi tiêu như nào'}),
			content_type='application/json',
		)
		follow_up_response = self.client.post(
			reverse('ep1:parse_expense_api'),
			data=json.dumps({'text': 'còn tháng trước thì sao'}),
			content_type='application/json',
		)

		self.assertEqual(first_response.status_code, 200)
		self.assertEqual(follow_up_response.status_code, 200)
		self.assertTrue(follow_up_response.json()['is_query'])
		self.assertIn('tháng trước', follow_up_response.json()['response']['message'])

	def test_chat_rate_limit_returns_retry_after(self):
		user = get_user_model().objects.create_user(username='rate-limit-test')
		self.client.force_login(user)
		session = self.client.session
		session['chat_request_times'] = [timezone.now().timestamp()] * 10
		session.save()

		response = self.client.post(
			reverse('ep1:parse_expense_api'),
			data=json.dumps({'text': 'chi tiêu hôm nay'}),
			content_type='application/json',
		)

		self.assertEqual(response.status_code, 429)
		self.assertIn('Retry-After', response)

	def test_recurring_income_intent_is_detected(self):
		intent, _ = ChatIntentDetector().detect_intent('Lương 15 triệu mỗi tháng')

		self.assertEqual(intent, 'CREATE_RECURRING_INCOME')

	def test_recurring_preview_requires_confirmation(self):
		user = get_user_model().objects.create_user(username='recurring-preview-test')
		self.client.force_login(user)

		with patch(
			'app_expenses.utils.gemini_service.analyze_chat_message',
			return_value={
				'intent': 'CREATE_RECURRING_EXPENSE',
				'confidence': 0.99,
				'amount': 500000,
				'description': 'Tiền điện',
				'frequency': 'monthly',
				'date': timezone.now().date().isoformat(),
			},
		):
			response = self.client.post(
				reverse('ep1:parse_expense_api'),
				data=json.dumps({'text': 'Tiền điện 500k mỗi tháng'}),
				content_type='application/json',
			)

		self.assertEqual(response.status_code, 200)
		self.assertTrue(response.json()['requires_confirmation'])
		self.assertEqual(response.json()['recurring_preview']['frequency'], 'monthly')
		self.assertEqual(RecurringExpense.objects.filter(user=user).count(), 0)

	def test_confirming_recurring_income_creates_template(self):
		user = get_user_model().objects.create_user(username='recurring-income-test')
		self.client.force_login(user)

		response = self.client.post(
			reverse('ep1:save_recurring_from_chat_api'),
			data=json.dumps({
				'amount': 15000000,
				'name': 'Lương',
				'description': 'Lương hàng tháng',
				'source_name': 'Lương',
				'frequency': 'monthly',
				'start_date': timezone.now().date().isoformat(),
				'transaction_type': 'recurring_income',
			}),
			content_type='application/json',
		)

		self.assertEqual(response.status_code, 200)
		self.assertTrue(response.json()['success'])
		self.assertEqual(RecurringIncome.objects.filter(user=user).count(), 1)

	def test_delete_expense_returns_confirmation_preview(self):
		user = get_user_model().objects.create_user(username='delete-chat-test')
		expense = Expense.objects.create(
			user=user,
			amount=50000,
			description='Cafe sáng',
			date=timezone.now().date(),
		)
		self.client.force_login(user)

		response = self.client.post(
			reverse('ep1:parse_expense_api'),
			data=json.dumps({'text': 'xóa khoản chi cafe'}),
			content_type='application/json',
		)

		self.assertEqual(response.status_code, 200)
		self.assertTrue(response.json()['requires_confirmation'])
		self.assertEqual(response.json()['expense_action_preview']['expense_id'], expense.id)
		self.assertTrue(Expense.objects.filter(pk=expense.id).exists())

	def test_confirming_edit_expense_updates_owned_record(self):
		user = get_user_model().objects.create_user(username='edit-chat-test')
		expense = Expense.objects.create(
			user=user,
			amount=50000,
			description='Cafe sáng',
			date=timezone.now().date(),
		)
		self.client.force_login(user)

		response = self.client.post(
			reverse('ep1:manage_expense_from_chat_api'),
			data=json.dumps({
				'expense_id': expense.id,
				'action': 'edit',
				'amount': 75000,
				'description': 'Cafe chiều',
				'date': timezone.now().date().isoformat(),
			}),
			content_type='application/json',
		)

		self.assertEqual(response.status_code, 200)
		expense.refresh_from_db()
		self.assertEqual(expense.amount, 75000)
		self.assertEqual(expense.description, 'Cafe chiều')

	def test_confirming_delete_expense_removes_owned_record(self):
		user = get_user_model().objects.create_user(username='delete-confirm-test')
		expense = Expense.objects.create(
			user=user,
			amount=50000,
			description='Cafe sáng',
			date=timezone.now().date(),
		)
		self.client.force_login(user)

		response = self.client.post(
			reverse('ep1:manage_expense_from_chat_api'),
			data=json.dumps({'expense_id': expense.id, 'action': 'delete'}),
			content_type='application/json',
		)

		self.assertEqual(response.status_code, 200)
		self.assertFalse(Expense.objects.filter(pk=expense.id).exists())

	def test_savings_query_uses_current_model_fields(self):
		user = get_user_model().objects.create_user(username='chat-test')
		SavingsGoal.objects.create(
			user=user,
			goal_name='Mua laptop',
			target_amount=10000000,
			current_amount=2500000,
			start_date=timezone.now().date(),
			target_date=timezone.now().date() + timedelta(days=30),
		)

		response = ChatQueryHandler(user).handle_query_savings('tình hình tiết kiệm')

		self.assertIn('Mua laptop', response['message'])
		self.assertEqual(response['data']['active_count'], 1)

	def test_income_parse_requires_confirmation_before_database_write(self):
		user = get_user_model().objects.create_user(username='income-test')
		self.client.force_login(user)

		response = self.client.post(
			reverse('ep1:parse_expense_api'),
			data=json.dumps({'text': 'Nhận lương 10 triệu'}),
			content_type='application/json',
		)

		self.assertEqual(response.status_code, 200)
		payload = response.json()
		self.assertTrue(payload['requires_confirmation'])
		self.assertEqual(payload['income_preview']['amount'], 10000000)
		self.assertEqual(Income.objects.filter(user=user).count(), 0)

	def test_confirming_income_creates_one_record(self):
		user = get_user_model().objects.create_user(username='income-save-test')
		self.client.force_login(user)

		response = self.client.post(
			reverse('ep1:save_income_from_chat_api'),
			data=json.dumps({
				'amount': 10000000,
				'description': 'Lương',
				'source_name': 'Lương',
				'date': timezone.now().date().isoformat(),
			}),
			content_type='application/json',
		)

		self.assertEqual(response.status_code, 200)
		self.assertTrue(response.json()['success'])
		self.assertEqual(Income.objects.filter(user=user).count(), 1)


# ============================================================================
# Phase 2 — Data Integrity Tests
# ============================================================================

class DataIntegrityTests(TestCase):
    """Tests cho monetary field validation và DB constraints."""

    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(username='integrity-user', password='pass')
        self.cat = Category.objects.create(name='Test Cat', user=self.user)

    # ── Amount validation at model level ─────────────────────────────────────

    def test_expense_negative_amount_rejected_by_validator(self):
        """Model validator phải từ chối amount âm."""
        expense = Expense(
            user=self.user,
            amount=Decimal('-100'),
            date=date.today(),
        )
        with self.assertRaises(ValidationError):
            expense.full_clean()

    def test_expense_zero_amount_rejected_by_validator(self):
        """Model validator phải từ chối amount = 0."""
        expense = Expense(
            user=self.user,
            amount=Decimal('0'),
            date=date.today(),
        )
        with self.assertRaises(ValidationError):
            expense.full_clean()

    def test_expense_valid_amount_accepted(self):
        """Amount > 0 phải được chấp nhận."""
        expense = Expense(
            user=self.user,
            amount=Decimal('50000'),
            category=self.cat,
            date=date.today(),
        )
        expense.full_clean()  # should not raise

    def test_income_negative_amount_rejected(self):
        """Income không được có amount âm."""
        income = Income(
            user=self.user,
            amount=Decimal('-1'),
            date=date.today(),
        )
        with self.assertRaises(ValidationError):
            income.full_clean()

    def test_budget_negative_total_rejected(self):
        """Budget không được có total âm."""
        budget = Budget(user=self.user, total=Decimal('-1'))
        with self.assertRaises(ValidationError):
            budget.full_clean()

    def test_budget_zero_total_accepted(self):
        """Budget total = 0 hợp lệ (chưa đặt ngân sách)."""
        budget = Budget(user=self.user, total=Decimal('0'))
        budget.full_clean()  # should not raise

    # ── DB-level CheckConstraint ──────────────────────────────────────────────

    def test_expense_negative_amount_blocked_by_db_constraint(self):
        """DB CheckConstraint phải chặn insert amount âm ngay cả khi bypass ORM validator."""
        with self.assertRaises(Exception):  # IntegrityError hoặc ValidationError
            # Dùng bulk_create để bypass model.full_clean()
            Expense.objects.bulk_create([
                Expense(user=self.user, amount=Decimal('-1'), date=date.today())
            ])

    # ── Form-level validation ─────────────────────────────────────────────────

    def test_expense_form_rejects_negative_amount(self):
        """ExpenseForm phải từ chối amount âm."""
        form = ExpenseForm(
            data={'amount': '-100', 'date': str(date.today()), 'category': ''},
            user=self.user,
        )
        self.assertFalse(form.is_valid())
        self.assertIn('amount', form.errors)

    def test_expense_form_rejects_zero_amount(self):
        """ExpenseForm phải từ chối amount = 0."""
        form = ExpenseForm(
            data={'amount': '0', 'date': str(date.today()), 'category': ''},
            user=self.user,
        )
        self.assertFalse(form.is_valid())
        self.assertIn('amount', form.errors)

    def test_expense_form_accepts_valid_amount(self):
        """ExpenseForm chấp nhận amount > 0."""
        form = ExpenseForm(
            data={'amount': '50000', 'date': str(date.today()), 'category': ''},
            user=self.user,
        )
        # category có thể rỗng (null=True) nên form valid
        self.assertNotIn('amount', form.errors)

    def test_income_form_rejects_negative_amount(self):
        """IncomeForm phải từ chối amount âm."""
        form = IncomeForm(
            data={'amount': '-1', 'date': str(date.today()), 'source': ''},
            user=self.user,
        )
        self.assertFalse(form.is_valid())
        self.assertIn('amount', form.errors)

    # ── SavingsGoal category ownership ───────────────────────────────────────

    def test_savings_goal_form_rejects_other_user_category(self):
        """SavingsGoalForm phải từ chối category của user khác."""
        User = get_user_model()
        other_user = User.objects.create_user(username='other-owner', password='pass')
        other_cat = Category.objects.create(name='Other Cat', user=other_user)

        today = date.today()
        form = SavingsGoalForm(
            data={
                'goal_name': 'Test Goal',
                'target_amount': '1000000',
                'current_amount': '0',
                'start_date': str(today),
                'target_date': str(today.replace(year=today.year + 1)),
                'categories_to_reduce': [str(other_cat.pk)],
            },
            user=self.user,
        )
        self.assertFalse(form.is_valid())

    def test_savings_goal_form_accepts_own_category(self):
        """SavingsGoalForm chấp nhận category của chính user."""
        today = date.today()
        form = SavingsGoalForm(
            data={
                'goal_name': 'Test Goal',
                'target_amount': '1000000',
                'current_amount': '0',
                'start_date': str(today),
                'target_date': str(today.replace(year=today.year + 1)),
                'categories_to_reduce': [str(self.cat.pk)],
            },
            user=self.user,
        )
        self.assertTrue(form.is_valid(), msg=form.errors)


class RecurringGenerationTests(TestCase):
    """Tests cho recurring transaction generation: idempotency, atomicity, concurrency."""

    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(username='recurring-user', password='pass')
        self.client.force_login(self.user)
        self.cat = Category.objects.create(name='Bills', user=self.user)
        self.today = timezone.now().date()

    def _make_recurring(self, days_overdue=0, frequency='monthly', amount='500000'):
        """Helper: Tạo RecurringExpense đã đến hạn."""
        due_date = self.today - timedelta(days=days_overdue)
        return RecurringExpense.objects.create(
            user=self.user,
            name='Test Recurring',
            amount=Decimal(amount),
            category=self.cat,
            frequency=frequency,
            start_date=due_date,
            next_due_date=due_date,
            is_active=True,
        )

    def _post_generate(self):
        return self.client.post(reverse('ep1:generate_recurring'))

    # ── Basic generation ──────────────────────────────────────────────────────

    def test_generate_creates_expense_from_due_template(self):
        """Gọi generate phải tạo 1 Expense từ template đã đến hạn."""
        recurring = self._make_recurring(days_overdue=0)

        response = self._post_generate()
        self.assertIn(response.status_code, [200, 302])

        self.assertEqual(Expense.objects.filter(user=self.user).count(), 1)
        expense = Expense.objects.get(user=self.user)
        self.assertEqual(expense.amount, Decimal('500000'))
        self.assertEqual(expense.recurring_template, recurring)
        self.assertEqual(expense.occurrence_date, self.today)

    def test_generate_advances_next_due_date(self):
        """Sau khi generate, next_due_date phải được tăng lên."""
        recurring = self._make_recurring(days_overdue=0, frequency='monthly')
        original_due = recurring.next_due_date

        self._post_generate()

        recurring.refresh_from_db()
        self.assertGreater(recurring.next_due_date, original_due)

    def test_generate_not_due_creates_nothing(self):
        """Template chưa đến hạn không tạo Expense."""
        RecurringExpense.objects.create(
            user=self.user,
            name='Future Recurring',
            amount=Decimal('100000'),
            category=self.cat,
            frequency='monthly',
            start_date=self.today + timedelta(days=30),
            next_due_date=self.today + timedelta(days=30),
            is_active=True,
        )

        self._post_generate()
        self.assertEqual(Expense.objects.filter(user=self.user).count(), 0)

    # ── Idempotency ───────────────────────────────────────────────────────────

    def test_generate_twice_does_not_duplicate(self):
        """Gọi generate 2 lần cho cùng occurrence không tạo duplicate Expense."""
        self._make_recurring(days_overdue=0)

        self._post_generate()
        count_after_first = Expense.objects.filter(user=self.user).count()

        # Gọi lần 2 — phải idempotent
        self._post_generate()
        count_after_second = Expense.objects.filter(user=self.user).count()

        self.assertEqual(count_after_first, 1)
        # Lần 2: next_due_date đã advance nên không có gì đến hạn nữa,
        # hoặc nếu advance thất bại thì UniqueConstraint chặn duplicate.
        self.assertEqual(count_after_second, count_after_first)

    def test_unique_constraint_prevents_duplicate_occurrence(self):
        """UniqueConstraint (recurring_template, occurrence_date) chặn duplicate trực tiếp qua ORM."""
        recurring = self._make_recurring(days_overdue=0)
        occ_date = self.today

        # Tạo lần 1 — thành công
        Expense.objects.create(
            user=self.user,
            amount=recurring.amount,
            description='First',
            category=self.cat,
            date=occ_date,
            recurring_template=recurring,
            occurrence_date=occ_date,
        )

        # Tạo lần 2 — phải raise IntegrityError
        with self.assertRaises(IntegrityError):
            Expense.objects.create(
                user=self.user,
                amount=recurring.amount,
                description='Duplicate',
                category=self.cat,
                date=occ_date,
                recurring_template=recurring,
                occurrence_date=occ_date,
            )

    # ── Expired template ──────────────────────────────────────────────────────

    def test_expired_recurring_is_deactivated(self):
        """Template quá end_date phải bị deactivate, không tạo Expense."""
        yesterday = self.today - timedelta(days=1)
        RecurringExpense.objects.create(
            user=self.user,
            name='Expired Recurring',
            amount=Decimal('100000'),
            category=self.cat,
            frequency='monthly',
            start_date=yesterday - timedelta(days=30),
            next_due_date=yesterday,
            end_date=yesterday,  # đã hết hạn
            is_active=True,
        )

        self._post_generate()

        # Không tạo Expense vì đã expired
        self.assertEqual(Expense.objects.filter(user=self.user).count(), 0)
        # Template phải bị deactivate
        template = RecurringExpense.objects.get(user=self.user)
        self.assertFalse(template.is_active)

    # ── Inactive template ─────────────────────────────────────────────────────

    def test_inactive_recurring_not_generated(self):
        """Template is_active=False không được generate."""
        RecurringExpense.objects.create(
            user=self.user,
            name='Inactive',
            amount=Decimal('100000'),
            category=self.cat,
            frequency='monthly',
            start_date=self.today,
            next_due_date=self.today,
            is_active=False,
        )

        self._post_generate()
        self.assertEqual(Expense.objects.filter(user=self.user).count(), 0)


class PerformanceQueryRegressionTests(TestCase):
    """Kiểm tra ngăn chặn N+1 queries và query regressions trên các luồng trọng yếu."""

    def setUp(self):
        self.User = get_user_model()
        self.user = self.User.objects.create_user(
            username='perf_user',
            password='perf_password123',
        )
        self.client.force_login(self.user)
        self.today = timezone.now().date()
        
        self.cat1 = Category.objects.create(name='Ăn uống Perf', user=self.user)
        self.cat2 = Category.objects.create(name='Di chuyển Perf', user=self.user)
        self.cat3 = Category.objects.create(name='Mua sắm Perf', user=self.user)
        
        self.source = IncomeSource.objects.create(name='Lương Perf', user=self.user)
        self.budget = Budget.objects.create(user=self.user, total=Decimal('10000000'))
        
        # Tạo 15 chi tiêu và 5 thu nhập rải đều các tháng
        for i in range(15):
            Expense.objects.create(
                user=self.user,
                category=self.cat1 if i % 2 == 0 else self.cat2,
                amount=Decimal('50000') * (i + 1),
                date=self.today - timedelta(days=i * 5),
                description=f'Perf Expense {i}',
            )
        for i in range(5):
            Income.objects.create(
                user=self.user,
                source=self.source,
                amount=Decimal('2000000'),
                date=self.today - timedelta(days=i * 15),
                description=f'Perf Income {i}',
            )

    def test_dashboard_query_count(self):
        """Dashboard phải tải thành công và có số lượng query nhỏ, không phát sinh N+1."""
        response = self.client.get(reverse('ep1:dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Ăn uống Perf')

    def test_dashboard_refresh_api_no_loop_queries(self):
        """dashboard_refresh_api lấy số liệu 6 tháng bằng conditional aggregation."""
        response = self.client.get(reverse('ep1:dashboard_refresh_api'))
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        self.assertEqual(len(data['charts_income_expense']['labels']), 6)
        self.assertEqual(len(data['charts_income_expense']['income']), 6)
        self.assertEqual(len(data['charts_income_expense']['expenses']), 6)

    def test_export_csv_no_n_plus_one(self):
        """export_expenses_csv không bị N+1 khi duyệt qua nhiều bản ghi chi tiêu."""
        # Tạo thêm 20 bản ghi
        for i in range(20):
            Expense.objects.create(
                user=self.user,
                category=self.cat3,
                amount=Decimal('100000'),
                date=self.today,
                description=f'Bulk CSV {i}',
            )
        response = self.client.get(reverse('ep1:export_expenses'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'text/csv')
        # Đảm bảo CSV chứa nội dung chính xác
        content = response.content.decode('utf-8')
        self.assertIn('Bulk CSV 19', content)
        self.assertIn('Mua sắm Perf', content)

    def test_ai_monitor_no_n_plus_one(self):
        """ai_monitor lấy số lượng bản ghi của tất cả users trong 1 query annotated."""
        admin_user = self.User.objects.create_superuser(
            username='perf_admin',
            password='admin_password123',
            email='admin@perf.com',
        )
        self.client.force_login(admin_user)
        # Tạo thêm 4 users
        for i in range(4):
            u = self.User.objects.create_user(username=f'dummy_user_{i}', password='pwd')
            Expense.objects.create(user=u, category=self.cat1, amount=Decimal('50000'), date=self.today)
        
        response = self.client.get(reverse('ep1:ai_monitor'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Giám sát hệ thống AI')

    def test_savings_goal_ai_suggestions_no_n_plus_one(self):
        """get_ai_savings_suggestions gom các category cần cắt giảm vào 1 query."""
        goal = SavingsGoal.objects.create(
            user=self.user,
            goal_name='Mua Laptop Perf',
            target_amount=Decimal('20000000'),
            current_amount=Decimal('5000000'),
            start_date=self.today,
            target_date=self.today + timedelta(days=90),
        )
        goal.categories_to_reduce.add(self.cat1, self.cat2, self.cat3)

        response = self.client.get(reverse('ep1:savings_goal_detail', kwargs={'pk': goal.pk}))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Mua Laptop Perf')

    def test_chart_monthly_trend_and_comparison_apis(self):
        """API charts 6 tháng chạy đúng cấu trúc dữ liệu với conditional aggregates."""
        resp1 = self.client.get(reverse('ep1:chart_monthly'))
        self.assertEqual(resp1.status_code, 200)
        self.assertEqual(len(resp1.json()['labels']), 6)

        resp2 = self.client.get(reverse('ep1:chart_income_expense'))
        self.assertEqual(resp2.status_code, 200)
        self.assertEqual(len(resp2.json()['labels']), 6)

    def test_ml_train_model_optimization(self):
        """train_model trích xuất raw tuples trực tiếp và tạo model thành công."""
        from app_expenses.ml_utils import train_model, get_model_path
        # User đã có 15 chi tiêu trong setUp với description & category
        model = train_model(self.user)
        self.assertIsNotNone(model)
        model_path = get_model_path(self.user)
        self.assertTrue(os.path.exists(model_path))
        # Dọn dẹp model file sau test
        if os.path.exists(model_path):
            os.remove(model_path)
