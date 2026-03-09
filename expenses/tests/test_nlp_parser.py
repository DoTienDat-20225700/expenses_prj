"""
Test script cho NLP Parser
Chạy script này để test các pattern nhập chi tiêu

Usage:
    python test_nlp_parser.py
"""

import os
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from app_expenses.utils.nlp_parser import ExpenseNLPParser

def test_parser():
    parser = ExpenseNLPParser()
    
    # Test cases
    test_cases = [
        "Vừa ăn sáng hết 50k",
        "Chi 100 nghìn mua đồ ăn hôm qua",
        "Đổ xăng 200.000 đồng",
        "Mua cafe 45k sáng nay",
        "Hôm qua mua quần áo 500k",
        "Chi 1.5 triệu mua điện thoại",
        "Ăn trưa 75 ngàn",
        "Taxi về nhà 120k hôm qua",
        "Đi xem phim 150k",
        "Mua sách 200 nghìn ngày 10/3",
        "Chi tiền điện 1 triệu",
    ]
    
    print("=" * 80)
    print("TEST NLP PARSER - Trợ lý Chi Tiêu")
    print("=" * 80)
    print()
    
    for i, text in enumerate(test_cases, 1):
        print(f"Test {i}: \"{text}\"")
        print("-" * 80)
        
        # Parse (without user object, just for demo)
        result = parser.parse(text, user=None)
        
        if result['success']:
            print(f"✅ SUCCESS")
            print(f"   💰 Số tiền: {result['amount']:,.0f} đ")
            print(f"   📁 Danh mục gợi ý: {result['category_hint']}")
            if result.get('category_keywords'):
                print(f"   🔑 Keywords: {', '.join(result['category_keywords'])}")
            print(f"   📅 Ngày: {result['date']}")
            print(f"   📝 Mô tả: {result['description']}")
        else:
            print(f"❌ FAILED")
            print(f"   Error: {result['error']}")
        
        print()
    
    print("=" * 80)
    print("HOÀN TẤT TESTING")
    print("=" * 80)

if __name__ == '__main__':
    test_parser()
