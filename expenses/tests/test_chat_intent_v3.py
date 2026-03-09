"""
Test Chat Intent Detector V3 - Expanded Features
Test các tính năng mới của chatbot
"""

import os
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from app_expenses.utils.chat_intent import ChatIntentDetector

def test_intent_detection():
    """Test intent detection với các câu mẫu"""
    detector = ChatIntentDetector()
    
    test_cases = [
        # CREATE_INCOME - Mới
        ("Nhận lương 10 triệu", "CREATE_INCOME"),
        ("Được trả 5 triệu", "CREATE_INCOME"),
        ("Thu được 200k", "CREATE_INCOME"),
        ("Nhận thưởng 3 triệu", "CREATE_INCOME"),
        
        # CREATE_EXPENSE - Cũ
        ("Ăn sáng 50k", "CREATE_EXPENSE"),
        ("Mua đồ 200 nghìn", "CREATE_EXPENSE"),
        
        # TOP_EXPENSES - Mới
        ("Top chi tiêu tháng này", "TOP_EXPENSES"),
        ("Chi nhiều nhất", "TOP_EXPENSES"),
        ("Những khoản chi lớn nhất", "TOP_EXPENSES"),
        ("Xem top chi tiêu", "TOP_EXPENSES"),
        
        # SEARCH_EXPENSES - Mới
        ("Tìm chi tiêu đổ xăng", "SEARCH_EXPENSES"),
        ("Tìm kiếm giao dịch ăn uống", "SEARCH_EXPENSES"),
        ("Search chi tiêu grab", "SEARCH_EXPENSES"),
        
        # RECENT_TRANSACTIONS - Mới
        ("Giao dịch gần đây", "RECENT_TRANSACTIONS"),
        ("Chi tiêu mới nhất", "RECENT_TRANSACTIONS"),
        ("Vừa chi những gì", "RECENT_TRANSACTIONS"),
        
        # COMPARE_PERIODS - Mới
        ("So sánh tháng này với tháng trước", "COMPARE_PERIODS"),
        ("Chi tiêu hơn tuần trước", "COMPARE_PERIODS"),
        ("So với tháng trước thế nào", "COMPARE_PERIODS"),
        
        # FINANCIAL_ADVICE - Mới
        ("Tư vấn tiết kiệm", "FINANCIAL_ADVICE"),
        ("Nên làm gì để giảm chi tiêu", "FINANCIAL_ADVICE"),
        ("Lời khuyên tài chính", "FINANCIAL_ADVICE"),
        ("Mẹo tiết kiệm", "FINANCIAL_ADVICE"),
        
        # QUERY_CATEGORIES - Mới
        ("Xem danh mục chi tiêu", "QUERY_CATEGORIES"),
        ("Các danh mục chi tiêu", "QUERY_CATEGORIES"),
        ("Danh mục nào chi nhiều nhất", "QUERY_CATEGORIES"),
        
        # MONTHLY_REPORT - Mới
        ("Báo cáo tháng này", "MONTHLY_REPORT"),
        ("Chi tiết tháng", "MONTHLY_REPORT"),
        ("Báo cáo chi tiết tháng", "MONTHLY_REPORT"),
        
        # QUERY_EXPENSES - Cũ
        ("Tổng chi tiêu hôm nay", "QUERY_EXPENSES"),
        ("Chi bao nhiêu trong tháng", "QUERY_EXPENSES"),
        
        # QUERY_INCOME - Cũ
        ("Thu nhập tháng này", "QUERY_INCOME"),
        
        # QUERY_SUMMARY - Cũ
        ("Tổng quan tài chính", "QUERY_SUMMARY"),
        
        # GREETING - Cũ
        ("Xin chào", "GREETING"),
        ("Hi bot", "GREETING"),
        
        # HELP - Cũ
        ("Giúp tôi", "HELP"),
        ("Hướng dẫn sử dụng", "HELP"),
    ]
    
    print("=" * 80)
    print("TEST CHAT INTENT DETECTOR V3")
    print("=" * 80)
    print()
    
    correct = 0
    total = len(test_cases)
    
    # Group by intent
    by_intent = {}
    for text, expected in test_cases:
        if expected not in by_intent:
            by_intent[expected] = []
        by_intent[expected].append(text)
    
    print(f"📊 Tổng số test cases: {total}")
    print(f"📋 Số intent types: {len(by_intent)}")
    print()
    
    # Test từng intent
    for intent_type in sorted(by_intent.keys()):
        cases = by_intent[intent_type]
        print(f"\n{'='*80}")
        print(f"🎯 Testing Intent: {intent_type}")
        print(f"{'='*80}")
        
        intent_correct = 0
        for text in cases:
            detected_intent, confidence = detector.detect_intent(text)
            is_correct = detected_intent == intent_type
            
            if is_correct:
                correct += 1
                intent_correct += 1
                status = "✅"
            else:
                status = "❌"
            
            print(f"{status} Input: '{text}'")
            print(f"   Expected: {intent_type}")
            print(f"   Detected: {detected_intent} (confidence: {confidence:.2f})")
            
            if not is_correct:
                print(f"   ⚠️  MISMATCH!")
            print()
        
        accuracy = (intent_correct / len(cases) * 100) if len(cases) > 0 else 0
        print(f"Intent Accuracy: {intent_correct}/{len(cases)} = {accuracy:.1f}%")
    
    # Tổng kết
    print("\n" + "=" * 80)
    print("📊 KẾT QUẢ TỔNG")
    print("=" * 80)
    print(f"✅ Correct: {correct}/{total}")
    print(f"❌ Incorrect: {total - correct}/{total}")
    print(f"📈 Overall Accuracy: {correct/total*100:.1f}%")
    print()
    
    # Intent breakdown
    print("\n📋 INTENT BREAKDOWN:")
    print("-" * 80)
    for intent_type in sorted(by_intent.keys()):
        count = len(by_intent[intent_type])
        marker = "🆕" if intent_type in ['CREATE_INCOME', 'TOP_EXPENSES', 'SEARCH_EXPENSES', 
                                          'RECENT_TRANSACTIONS', 'COMPARE_PERIODS', 
                                          'FINANCIAL_ADVICE', 'QUERY_CATEGORIES', 
                                          'MONTHLY_REPORT'] else "📌"
        print(f"{marker} {intent_type}: {count} test cases")
    
    print("\n" + "=" * 80)
    
    # Đánh giá
    if correct == total:
        print("🎉 PERFECT! Tất cả test cases đều pass!")
    elif correct / total >= 0.9:
        print("✅ EXCELLENT! Accuracy > 90%")
    elif correct / total >= 0.8:
        print("👍 GOOD! Accuracy > 80%")
    else:
        print("⚠️  NEEDS IMPROVEMENT! Accuracy < 80%")
    
    print("=" * 80)

if __name__ == '__main__':
    test_intent_detection()
