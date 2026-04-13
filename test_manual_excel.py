#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
수기입력 엑셀 업로드 기능 테스트 스크립트
"""

import pandas as pd
from datetime import datetime

print("=" * 60)
print("수기입력 엑셀 업로드 기능 테스트")
print("=" * 60)

# 수기입력 서식 파일 읽기
excel_file = '/home/user/uploaded_files/수기입력_서식.xlsx'
df_excel = pd.read_excel(excel_file)

print(f"\n📄 엑셀 파일 정보:")
print(f"  - 총 주문 수: {len(df_excel)}")
print(f"  - 컬럼: {list(df_excel.columns)}")

# 컬럼명 정리
df_excel.columns = [col.replace('\n', '').replace('(교환 배송지 변경시 작성)', '').strip() 
                    for col in df_excel.columns]

print(f"\n정리된 컬럼: {list(df_excel.columns)}")

# 필수 컬럼 확인
required_cols = ['이름', '전화번호', '배송주소', '물품']
missing_cols = [col for col in required_cols if col not in df_excel.columns]

print(f"\n필수 컬럼 검증:")
if missing_cols:
    print(f"  ❌ 누락: {', '.join(missing_cols)}")
else:
    print(f"  ✅ 모든 필수 컬럼 존재")

# 카테고리 설정
excel_category = "Seed"
today = datetime.now().strftime("%Y%m%d")

print(f"\n📦 주문 생성:")
print(f"  - 카테고리: {excel_category}")
print(f"  - 날짜: {today}")

# 엑셀 데이터를 주문으로 변환
existing_count = 0  # 기존 주문 개수 (테스트에서는 0)
added_orders = []

for idx, row in df_excel.iterrows():
    # 고유번호 생성 (a, b, c, ...)
    unique_id = chr(ord('a') + existing_count + idx)
    
    # 주문번호 생성: {오늘날짜}_{카테고리}_{고유번호}
    order_number = f"{today}_{excel_category}_{unique_id}"
    
    # 쇼핑몰 상품 코드 생성: {오늘날짜}_{카테고리}_{고유번호}
    shop_product_code = f"{today}_{excel_category}_{unique_id}"
    
    # 물품명 (쇼핑몰 상품명/옵션명으로 사용)
    product_name = str(row['물품']).strip()
    
    # 주문 데이터 생성
    order = {
        '카테고리': excel_category,
        '주문번호': order_number,
        '쇼핑몰 상품 코드': shop_product_code,
        '수취인': str(row['이름']).strip(),
        '전화번호': str(row['전화번호']).strip(),
        '주소': str(row['배송주소']).strip(),
        '쇼핑몰 상품명': product_name,
        '쇼핑몰 옵션명': product_name,
        '수량': 1,  # 항상 1
        '배송 메시지': ''
    }
    
    added_orders.append(order)
    
    print(f"\n주문 #{idx + 1}:")
    print(f"  - 주문번호: {order_number}")
    print(f"  - 상품코드: {shop_product_code}")
    print(f"  - 수취인: {order['수취인']}")
    print(f"  - 전화번호: {order['전화번호']}")
    print(f"  - 주소: {order['주소'][:30]}...")
    print(f"  - 물품: {product_name}")
    print(f"  - 수량: {order['수량']}")

# 결과 요약
print(f"\n" + "=" * 60)
print("처리 결과 요약")
print("=" * 60)
print(f"총 처리된 주문 수: {len(added_orders)}")
print(f"카테고리: {excel_category}")
print(f"주문번호 범위: {added_orders[0]['주문번호']} ~ {added_orders[-1]['주문번호']}")

# 주문번호 고유성 검증
order_numbers = [o['주문번호'] for o in added_orders]
is_unique = len(order_numbers) == len(set(order_numbers))

print(f"\n주문번호 고유성: {'✅ 통과' if is_unique else '❌ 실패'}")

# 주문번호 형식 검증
print(f"\n주문번호 형식 검증:")
expected_format = f"{today}_{excel_category}_[a-z]"
print(f"  기대 형식: {expected_format}")

all_valid = True
for order_num in order_numbers:
    parts = order_num.split('_')
    if len(parts) == 3 and parts[0] == today and parts[1] == excel_category and len(parts[2]) == 1:
        print(f"  ✅ {order_num}")
    else:
        print(f"  ❌ {order_num}")
        all_valid = False

print(f"\n형식 검증: {'✅ 모두 통과' if all_valid else '❌ 일부 실패'}")

# 수량 검증
print(f"\n수량 검증 (모두 1이어야 함):")
quantities = [o['수량'] for o in added_orders]
all_one = all(q == 1 for q in quantities)
print(f"  {'✅ 모든 주문의 수량이 1' if all_one else '❌ 수량 오류 발생'}")

# 상품명/옵션명 동일성 검증
print(f"\n상품명/옵션명 동일성 검증:")
all_match = all(o['쇼핑몰 상품명'] == o['쇼핑몰 옵션명'] for o in added_orders)
print(f"  {'✅ 모든 주문의 상품명과 옵션명이 동일' if all_match else '❌ 불일치 발생'}")

print(f"\n✅ 테스트 완료!")
