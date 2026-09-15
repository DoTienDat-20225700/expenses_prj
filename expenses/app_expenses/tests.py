from datetime import timedelta

from django.contrib.auth import get_user_model
import json
from unittest.mock import patch

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from app_expenses.models import Expense, Income, RecurringIncome, RecurringExpense, SavingsGoal
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
