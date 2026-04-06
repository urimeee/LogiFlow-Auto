#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
쿠팡 운송장 번호 입력 기능 테스트 스크립트
"""

import pandas as pd
from datetime import datetime

# 테스트 데이터
tracking_text = """256390456066   류지영
256390456070   이지영
256390456081   안민영
256390456092   서미리
256390456103   서지효"""

print("=" * 60)
print("쿠팡 운송장 번호 입력 기능 테스트")
print("=" * 60)

# DeliveryList 파일 읽기
delivery_file = '/home/user/uploaded_files/DeliveryList(2026-04-06)_(0) (1).xlsx'
df_delivery = pd.read_excel(delivery_file)

print(f"\n📦 DeliveryList 파일 정보:")
print(f"  - 총 주문 수: {len(df_delivery)}")
print(f"  - 컬럼 수: {len(df_delivery.columns)}")

# 운송장 번호 파싱
print(f"\n📝 운송장 번호 파싱:")
tracking_data = []
for line in tracking_text.strip().split('\n'):
    if line.strip():
        parts = line.strip().split()
        if len(parts) >= 2:
            tracking_num = parts[0].strip()
            recipient_name = ' '.join(parts[1:]).strip()
            tracking_data.append({
                '운송장번호': tracking_num,
                '수취인이름': recipient_name
            })
            print(f"  - {tracking_num} → {recipient_name}")

print(f"\n총 {len(tracking_data)}개 운송장 번호 파싱 완료")

# 수취인 이름으로 매칭
print(f"\n🔍 수취인 이름으로 매칭:")
matched_count = 0
unmatched_recipients = []

for tracking_info in tracking_data:
    recipient = tracking_info['수취인이름']
    tracking_num = tracking_info['운송장번호']
    
    # DeliveryList에서 수취인 이름으로 찾기
    mask = df_delivery['수취인이름'] == recipient
    matched_rows = df_delivery[mask]
    
    if len(matched_rows) > 0:
        # 운송장 번호 입력
        df_delivery.loc[mask, '운송장번호'] = int(tracking_num)
        # 분리배송 Y/N을 'N'으로 설정
        df_delivery.loc[mask, '분리배송 Y/N'] = 'N'
        matched_count += len(matched_rows)
        print(f"  ✅ {recipient}: {len(matched_rows)}개 주문 매칭")
    else:
        unmatched_recipients.append(recipient)
        print(f"  ❌ {recipient}: 매칭 실패")

# 결과 요약
print(f"\n" + "=" * 60)
print("매칭 결과 요약")
print("=" * 60)
print(f"입력된 운송장 수: {len(tracking_data)}")
print(f"매칭 성공: {matched_count}")
print(f"매칭 실패: {len(unmatched_recipients)}")

if unmatched_recipients:
    print(f"\n매칭되지 않은 수취인:")
    for name in unmatched_recipients:
        print(f"  - {name}")

# 번호 컬럼을 등차수열로 재설정
df_delivery['번호'] = range(1, len(df_delivery) + 1)

# 운송장 번호가 있는 행만 필터링
df_output = df_delivery[df_delivery['운송장번호'].notna()].copy()

print(f"\n출력 파일: {len(df_output)}개 주문 (운송장 번호 입력 완료)")

# 미리보기
print(f"\n" + "=" * 60)
print("출력 데이터 미리보기 (처음 10개)")
print("=" * 60)
preview_cols = ['번호', '묶음배송번호', '주문번호', '택배사', '운송장번호', '분리배송 Y/N', '수취인이름']
print(df_output[preview_cols].head(10).to_string(index=False))

# 필수 컬럼 검증
required_cols = ['번호', '주문번호', '택배사', '운송장번호', '분리배송 Y/N']
missing_cols = [col for col in required_cols if col not in df_output.columns]

print(f"\n" + "=" * 60)
print("필수 컬럼 검증")
print("=" * 60)
if missing_cols:
    print(f"❌ 필수 컬럼 누락: {', '.join(missing_cols)}")
else:
    print("✅ 모든 필수 컬럼 존재")
    for col in required_cols:
        print(f"  - {col}")

# 운송장 번호 형식 검증
print(f"\n" + "=" * 60)
print("운송장 번호 형식 검증")
print("=" * 60)
invalid_tracking = []
for idx, row in df_output.iterrows():
    tracking = str(row['운송장번호'])
    if not tracking.isdigit():
        invalid_tracking.append((row['수취인이름'], tracking))

if invalid_tracking:
    print(f"❌ 형식 오류 ({len(invalid_tracking)}개):")
    for name, tracking in invalid_tracking[:5]:
        print(f"  - {name}: {tracking}")
else:
    print("✅ 모든 운송장 번호가 숫자 형식")

print(f"\n✅ 테스트 완료!")
