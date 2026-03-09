"""
Test script cho Chat Intent Detection
Chạy script này để test các loại câu hỏi khác nhau

Usage:
    python test_chat_intent.py
"""

import os
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from app_expenses.utils.chat_intent import ChatIntentDetector, process_chat_input

def test_intent_detection():
    detector = ChatIntentDetector()
    
    # Test cases với expected intent
    test_cases = [
        # CREATE_EXPENSE
        ("Vừa ăn sáng hết 50k", "CREATE_EXPENSE"),
        ("Chi 100 nghìn mua đồ", "CREATE_EXPENSE"),
        ("Đổ xăng 200.000 đồng", "CREATE_EXPENSE"),
        
        # QUERY_EXPENSES
        ("Tổng chi tiêu hôm nay?", "QUERY_EXPENSES"),
        ("Chi bao nhiêu trong tháng?", "QUERY_EXPENSES"),
        ("Xem chi tiêu của tôi", "QUERY_EXPENSES"),
        ("Số chi tiêu tuần này", "QUERY_EXPENSES"),
        
        # QUERY_INCOME
        ("Thu nhập của tôi?", "QUERY_INCOME"),
        ("Tổng thu nhập tháng này", "QUERY_INCOME"),
        
        # QUERY_SAVINGS
        ("Tình hình tiết kiệm?", "QUERY_SAVINGS"),
        ("Mục tiêu tiết kiệm của tôi", "QUERY_SAVINGS"),
        ("Đã tiết kiệm được bao nhiêu?", "QUERY_SAVINGS"),
        
        # QUERY_BUDGET
        ("Ngân sách còn lại?", "QUERY_BUDGET"),
        ("Còn bao nhiêu trong ngân sách?", "QUERY_BUDGET"),
        
        # QUERY_SUMMARY
        ("Tổng quan tài chính", "QUERY_SUMMARY"),
        ("Tóm tắt tài chính tháng này", "QUERY_SUMMARY"),
        
        # GREETING
        ("Xin chào", "GREETING"),
        ("Hello", "GREETING"),
        ("Hi bot", "GREETING"),
        
        # HELP
        ("Giúp tôi", "HELP"),
        ("Help", "HELP"),
        ("Hướng dẫn sử dụng", "HELP"),
    ]
    
    print("=" * 80)
    print("TEST CHAT INTENT DETECTION")
    print("=" * 80)
    print()
    
    correct = 0
    total = len(test_cases)
    
    for i, (text, expected_intent) in enumerate(test_cases, 1):
        intent, confidence = detector.detect_intent(text)
        
        is_correct = intent == expected_intent
        if is_correct:
            correct += 1
            status = "✅"
        else:
            status = "❌"
        
        print(f"{status} Test {i}: \"{text}\"")
        print(f"   Expected: {expected_intent}")
        print(f"   Got: {intent} (confidence: {confidence:.2f})")
        
        if not is_correct:
            print(f"   ⚠️  MISMATCH!")
        
        print()
    
    print("=" * 80)
    print(f"RESULTS: {correct}/{total} correct ({correct/total*100:.1f}%)")
    print("=" * 80)

if __name__ == '__main__':
    test_intent_detection()
