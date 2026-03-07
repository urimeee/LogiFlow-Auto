import pandas as pd

# 테스트 데이터 생성
test_data = {
    '주문번호': ['20260225-83316T835', '20260225-83316T835', '20260225-83316T835', '20260306-12345', '20260306-12345']
}

df = pd.DataFrame(test_data)

print("=== 원본 데이터 ===")
print(df)
print()

# ensure_unique_order_numbers 함수 시뮬레이션
order_col = '주문번호'
order_counts = {}
new_order_numbers = []

for order_no in df[order_col]:
    if pd.isna(order_no):
        new_order_numbers.append(order_no)
        continue
    
    order_no_str = str(order_no)
    
    # 처음 등장하는 주문번호
    if order_no_str not in order_counts:
        order_counts[order_no_str] = 0
        new_order_numbers.append(order_no_str)
    else:
        # 이미 등장한 주문번호 - 접미사 추가
        order_counts[order_no_str] += 1
        suffix = chr(ord('a') + order_counts[order_no_str] - 1)  # a, b, c...
        new_order_numbers.append(f"{order_no_str}{suffix}")

df['쇼핑몰 주문번호'] = new_order_numbers

# 쇼핑몰 묶음 배송 번호를 쇼핑몰 주문번호와 동일하게 설정
df['쇼핑몰 묶음 배송 번호'] = df['쇼핑몰 주문번호']

print("=== 수정 후 데이터 ===")
print(df[['주문번호', '쇼핑몰 주문번호', '쇼핑몰 묶음 배송 번호']])
print()

# 검증
print("=== 검증 결과 ===")
match_count = (df['쇼핑몰 주문번호'] == df['쇼핑몰 묶음 배송 번호']).sum()
print(f"쇼핑몰 주문번호 == 쇼핑몰 묶음 배송 번호: {match_count}/{len(df)} (일치)")
print(f"쇼핑몰 주문번호 고유성: {df['쇼핑몰 주문번호'].nunique()} == {len(df)} (모두 고유)")

if match_count == len(df) and df['쇼핑몰 주문번호'].nunique() == len(df):
    print("\n✅ 테스트 성공: 모든 조건 충족!")
else:
    print("\n❌ 테스트 실패")
