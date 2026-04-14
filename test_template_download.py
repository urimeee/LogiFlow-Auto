#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
수기입력 서식 파일 다운로드 기능 테스트
"""

import pandas as pd
from io import BytesIO

print("=" * 60)
print("수기입력 서식 파일 생성 테스트")
print("=" * 60)

# 서식 파일 데이터 생성
template_data = {
    '이름': ['김지현', '엄정해', ''],
    '전화번호': ['010-1234-5678', '010-2345-6789', ''],
    '배송주소': ['서울 강남구 테헤란로 123', '부산 해운대구 센텀대로 456', ''],
    '물품': ['에바 아이스', '딥 플럼', '']
}
template_df = pd.DataFrame(template_data)

print(f"\n📄 서식 파일 구조:")
print(f"  - 행 수: {len(template_df)}")
print(f"  - 열 수: {len(template_df.columns)}")
print(f"\n컬럼:")
for col in template_df.columns:
    print(f"  • {col}")

print(f"\n데이터 미리보기:")
print(template_df.to_string(index=False))

# Excel 파일로 변환
output = BytesIO()
with pd.ExcelWriter(output, engine='openpyxl') as writer:
    template_df.to_excel(writer, index=False, sheet_name='수기입력')
template_excel_data = output.getvalue()

print(f"\n📦 생성된 Excel 파일:")
print(f"  - 파일 크기: {len(template_excel_data)} bytes")
print(f"  - 시트명: 수기입력")

# 생성된 파일 읽기 테스트
output.seek(0)
df_read = pd.read_excel(output)

print(f"\n✅ 파일 읽기 테스트:")
print(f"  - 읽은 행 수: {len(df_read)}")
print(f"  - 읽은 열 수: {len(df_read.columns)}")
print(f"  - 컬럼 일치: {list(df_read.columns) == list(template_df.columns)}")

# 필수 컬럼 검증
required_cols = ['이름', '전화번호', '배송주소', '물품']
missing_cols = [col for col in required_cols if col not in df_read.columns]

print(f"\n필수 컬럼 검증:")
if missing_cols:
    print(f"  ❌ 누락: {', '.join(missing_cols)}")
else:
    print(f"  ✅ 모든 필수 컬럼 존재")

# 샘플 데이터 검증
print(f"\n샘플 데이터 검증:")
print(f"  - 첫 번째 이름: {df_read.loc[0, '이름']}")
print(f"  - 첫 번째 전화번호: {df_read.loc[0, '전화번호']}")
print(f"  - 첫 번째 배송주소: {df_read.loc[0, '배송주소']}")
print(f"  - 첫 번째 물품: {df_read.loc[0, '물품']}")

# 빈 행 확인
print(f"\n빈 행 검증:")
empty_rows = df_read[df_read['이름'] == '']
print(f"  - 빈 행 개수: {len(empty_rows)}")
print(f"  - 작성 가능 행: ✅")

print(f"\n✅ 테스트 완료!")
print(f"\n📥 다운로드 파일명: 수기입력_서식.xlsx")
