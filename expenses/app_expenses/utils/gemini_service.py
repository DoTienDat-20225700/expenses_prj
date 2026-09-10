import json
import logging

from decouple import config

logger = logging.getLogger(__name__)


SUPPORTED_INTENTS = {
    'CREATE_EXPENSE',
    'CREATE_INCOME',
    'CREATE_RECURRING_EXPENSE',
    'CREATE_RECURRING_INCOME',
    'EDIT_EXPENSE',
    'DELETE_EXPENSE',
    'QUERY_EXPENSES',
    'QUERY_INCOME',
    'QUERY_SAVINGS',
    'QUERY_BUDGET',
    'QUERY_SUMMARY',
    'TOP_EXPENSES',
    'SEARCH_EXPENSES',
    'RECENT_TRANSACTIONS',
    'COMPARE_PERIODS',
    'FINANCIAL_ADVICE',
    'QUERY_CATEGORIES',
    'MONTHLY_REPORT',
    'GREETING',
    'HELP',
    'OUT_OF_SCOPE',
}


def analyze_chat_message(text, history=None):
    """Classify a chat message with Gemini and return a validated JSON object."""
    api_key = config('GEMINI_API_KEY', default='').strip()
    if not api_key:
        raise RuntimeError('GEMINI_API_KEY is not configured')

    from google import genai
    from google.genai import types

    timeout_ms = config('GEMINI_TIMEOUT_MS', default='10000', cast=int)
    client = genai.Client(
        api_key=api_key,
        http_options=types.HttpOptions(timeout=timeout_ms),
    )
    history_text = ''
    if history:
        history_text = 'Ngữ cảnh các lượt trước:\n' + '\n'.join(
            f'- Người dùng: {item}' for item in history[-4:]
        ) + '\n'

    response = client.models.generate_content(
        model=config('GEMINI_MODEL', default='gemini-2.5-flash'),
        contents=(
            'Bạn là bộ phân loại intent cho ứng dụng quản lý tài chính cá nhân. '
            'Chỉ trả về JSON hợp lệ, không markdown. '
            'Intent hợp lệ: '
            f'{", ".join(sorted(SUPPORTED_INTENTS))}. '
            'Chọn CREATE_EXPENSE cho câu tạo chi tiêu, CREATE_INCOME cho câu tạo thu nhập. '
            'Chọn CREATE_RECURRING_EXPENSE hoặc CREATE_RECURRING_INCOME khi có tần suất '
            'như mỗi ngày, mỗi tuần, mỗi tháng hoặc mỗi năm. '
            'Chọn OUT_OF_SCOPE nếu câu hỏi không liên quan đến tài chính. '
            'JSON phải có dạng: {"intent":"...", "confidence":0.0, '
            '"amount":null, "description":null, "category_hint":null, '
            '"source_name":null, "frequency":null, "date":"YYYY-MM-DD"}. '
            f'{history_text}Câu người dùng hiện tại: {text}'
        ),
        config={
            'temperature': 0,
            'response_mime_type': 'application/json',
        },
    )

    result = json.loads(response.text)
    intent = result.get('intent')
    if intent not in SUPPORTED_INTENTS:
        raise ValueError(f'Gemini returned unsupported intent: {intent}')

    confidence = float(result.get('confidence', 0.0))
    result['intent'] = intent
    result['confidence'] = max(0.0, min(confidence, 1.0))
    return result