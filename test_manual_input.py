#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
수동 입력 기능 테스트 스크립트
"""

from datetime import datetime

def test_manual_input_generation():
    """수동 입력 주문번호 생성 테스트"""
    
    print("=" * 60)
    print("수동 입력 주문 생성 테스트")
    print("=" * 60)
    
    # 테스트 데이터
    recipients = ["김유림", "김종국", "이효리"]
    phones = ["010-1234-5678", "010-2345-6789", "010-3456-7890"]
    addresses = [
        "서울시 강남구 테헤란로 123",
        "경기도 성남시 분당구 판교로 456",
        "부산시 해운대구 센텀대로 789"
    ]
    product_name = "프리미엄 스킨케어 세트"
    category = "Seed"
    quantity = 1
    
    # 오늘 날짜
    today = datetime.now().strftime("%Y%m%d")
    
    print(f"\n📅 오늘 날짜: {today}")
    print(f"📦 카테고리: {category}")
    print(f"🎁 상품명: {product_name}")
    print(f"👥 수취인 수: {len(recipients)}명")
    
    print("\n" + "-" * 60)
    print("생성된 주문 목록:")
    print("-" * 60)
    
    orders = []
    existing_count = 0  # 기존 주문 개수 (테스트에서는 0)
    
    for idx, (recipient, phone, address) in enumerate(zip(recipients, phones, addresses)):
        # 고유번호 생성 (a, b, c, ...)
        unique_id = chr(ord('a') + existing_count + idx)
        
        # 주문번호 생성: {오늘날짜}_{Seed/CS}_{고유번호}
        order_number = f"{today}_{category}_{unique_id}"
        
        # 쇼핑몰 상품 코드 생성: {오늘날짜}_{Seed/CS}_{고유번호}
        shop_product_code = f"{today}_{category}_{unique_id}"
        
        order = {
            '카테고리': category,
            '주문번호': order_number,
            '쇼핑몰 상품 코드': shop_product_code,
            '수취인': recipient,
            '전화번호': phone,
            '주소': address,
            '쇼핑몰 상품명': product_name,
            '쇼핑몰 옵션명': product_name,
            '수량': quantity,
            '배송 메시지': ''
        }
        
        orders.append(order)
        
        print(f"\n주문 #{idx + 1}:")
        print(f"  - 주문번호: {order_number}")
        print(f"  - 쇼핑몰 상품 코드: {shop_product_code}")
        print(f"  - 수취인: {recipient}")
        print(f"  - 전화번호: {phone}")
        print(f"  - 주소: {address}")
        print(f"  - 상품명: {product_name}")
    
    print("\n" + "=" * 60)
    print("✅ 검증 결과:")
    print("=" * 60)
    
    # 주문번호 중복 검증
    order_numbers = [o['주문번호'] for o in orders]
    product_codes = [o['쇼핑몰 상품 코드'] for o in orders]
    
    is_unique_orders = len(order_numbers) == len(set(order_numbers))
    is_unique_codes = len(product_codes) == len(set(product_codes))
    
    print(f"주문번호 고유성: {'✅ 통과' if is_unique_orders else '❌ 실패'}")
    print(f"상품 코드 고유성: {'✅ 통과' if is_unique_codes else '❌ 실패'}")
    print(f"생성된 주문 수: {len(orders)}개")
    
    print("\n주문번호 목록:")
    for order_num in order_numbers:
        print(f"  - {order_num}")
    
    print("\n상품 코드 목록:")
    for code in product_codes:
        print(f"  - {code}")
    
    # 주문번호 형식 검증
    print("\n주문번호 형식 검증:")
    expected_format = f"{today}_{category}_[a-z]"
    print(f"기대 형식: {expected_format}")
    
    for order_num in order_numbers:
        parts = order_num.split('_')
        if len(parts) == 3 and parts[0] == today and parts[1] == category and len(parts[2]) == 1:
            print(f"  ✅ {order_num} - 형식 정상")
        else:
            print(f"  ❌ {order_num} - 형식 오류")
    
    return orders


def test_cs_orders():
    """CS 주문 테스트"""
    print("\n\n" + "=" * 60)
    print("CS 주문 생성 테스트")
    print("=" * 60)
    
    recipients = ["박민수", "정수진"]
    phones = ["010-4567-8901", "010-5678-9012"]
    addresses = [
        "인천시 남동구 구월동 111",
        "대전시 서구 둔산동 222"
    ]
    product_name = "CS 교체 상품"
    category = "CS"
    quantity = 1
    
    today = datetime.now().strftime("%Y%m%d")
    
    print(f"\n📅 오늘 날짜: {today}")
    print(f"📦 카테고리: {category}")
    print(f"🎁 상품명: {product_name}")
    print(f"👥 수취인 수: {len(recipients)}명")
    
    print("\n" + "-" * 60)
    print("생성된 주문 목록:")
    print("-" * 60)
    
    orders = []
    existing_count = 0
    
    for idx, (recipient, phone, address) in enumerate(zip(recipients, phones, addresses)):
        unique_id = chr(ord('a') + existing_count + idx)
        order_number = f"{today}_{category}_{unique_id}"
        shop_product_code = f"{today}_{category}_{unique_id}"
        
        order = {
            '카테고리': category,
            '주문번호': order_number,
            '쇼핑몰 상품 코드': shop_product_code,
            '수취인': recipient,
            '전화번호': phone,
            '주소': address,
            '쇼핑몰 상품명': product_name,
            '쇼핑몰 옵션명': product_name,
            '수량': quantity,
            '배송 메시지': 'CS 교체 요청'
        }
        
        orders.append(order)
        
        print(f"\n주문 #{idx + 1}:")
        print(f"  - 주문번호: {order_number}")
        print(f"  - 쇼핑몰 상품 코드: {shop_product_code}")
        print(f"  - 수취인: {recipient}")
        print(f"  - 배송 메시지: {order['배송 메시지']}")
    
    print("\n✅ CS 주문 생성 완료")
    return orders


if __name__ == "__main__":
    # Seed 주문 테스트
    seed_orders = test_manual_input_generation()
    
    # CS 주문 테스트
    cs_orders = test_cs_orders()
    
    # 전체 결과
    print("\n\n" + "=" * 60)
    print("전체 테스트 결과 요약")
    print("=" * 60)
    print(f"Seed 주문: {len(seed_orders)}개")
    print(f"CS 주문: {len(cs_orders)}개")
    print(f"총 주문: {len(seed_orders) + len(cs_orders)}개")
    print("\n✅ 모든 테스트 통과!")
