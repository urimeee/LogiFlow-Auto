import streamlit as st
import pandas as pd
from datetime import datetime
import io
import chardet
import msoffcrypto
from difflib import SequenceMatcher

# 페이지 설정
st.set_page_config(
    page_title="물류 데이터 통합 시스템",
    page_icon="📦",
    layout="wide"
)

# 컬럼 매핑 규칙 정의
COLUMN_MAPPING = {
    '주문번호': ['주문번호', '쇼핑몰번호'],
    '수령인': ['받는분.이름', '수령인', '주문자', '수취인 명'],
    '연락처': ['받는분.전화번호', '핸드폰', '수령지전화', '사용자.전화번호', '수취인 핸드폰'],
    '우편번호': ['받는분.우편번호', '우편번호', '주문자우편번호'],
    '주소': ['받는분.통합주소', '주소', '받는분.주소', '주문자주소', '수취인 기본 주소'],
    '상품명': ['주문상품', '주문상품명', '상품명'],
    '수량': ['수량', '개수', '주문 수량'],
    '배송메세지': ['비고', '요청사항', '배송 메세지']
}

# 3PL 전용 컬럼 매핑 (카페24 전용)
CAFE24_TO_3PL_MAPPING = {
    '주문번호': '주문번호',
    '수취인 명': ['수령인', '받는사람', '주문자'],
    '수취인 핸드폰': ['핸드폰', '수령인휴대폰', '주문자핸드폰'],
    '수취인 기본 주소': ['주소', '배송주소', '주문자주소'],
    '쇼핑몰 상품 코드': None,  # 매칭 결과에서 가져옴
    '쇼핑몰 상품 이름': None,  # 매칭 결과에서 가져옴
    '쇼핑몰 옵션 이름': None,  # 매칭 결과에서 가져옴
    '주문 수량': '수량',
    '배송 메세지': ['비고', '배송메세지', '요청사항']
}


def detect_encoding(file_bytes):
    """파일의 인코딩을 자동으로 감지"""
    result = chardet.detect(file_bytes)
    return result['encoding']


def calculate_similarity(str1, str2):
    """두 문자열의 유사도 계산 (0~1)"""
    if pd.isna(str1) or pd.isna(str2):
        return 0.0
    return SequenceMatcher(None, str(str1), str(str2)).ratio()


def load_master_code_data(master_file):
    """물류_코드명 마스터 데이터 로드"""
    try:
        df = pd.read_excel(master_file)
        st.success(f"✅ 마스터 코드 데이터 로드 완료: {len(df)}개 항목")
        return df
    except Exception as e:
        st.error(f"❌ 마스터 코드 데이터 로드 실패: {str(e)}")
        return None


def match_product_code(row, master_df, cafe24_code_col, cafe24_name_col, cafe24_option_col):
    """
    카페24 주문 데이터와 마스터 코드 매칭
    
    매칭 우선순위:
    1. 판매 상품 코드 정확 매칭 (자체품목코드 == 판매 상품 코드)
    2. 상품명 + 옵션명 조합 매칭
    3. 유사도 기반 추천
    """
    cafe24_code = row.get(cafe24_code_col, None)
    cafe24_name = row.get(cafe24_name_col, None)
    cafe24_option = row.get(cafe24_option_col, None)
    
    # 1단계: 판매 상품 코드로 정확 매칭 (카페24 자체품목코드 == 마스터 판매 상품 코드)
    if pd.notna(cafe24_code):
        exact_match = master_df[master_df['판매 상품 코드'] == cafe24_code]
        if not exact_match.empty:
            matched = exact_match.iloc[0]
            return {
                '판매 상품 코드': matched['판매 상품 코드'],
                '쇼핑몰 상품 코드': matched['쇼핑몰 상품 코드'],
                '쇼핑몰 상품 이름': matched['쇼핑몰 상품 이름'],
                '쇼핑몰 옵션 이름': matched['쇼핑몰 옵션 이름'],
                '매칭 방법': '코드 정확 매칭',
                '확인 필요': False
            }
    
    # 2단계: 상품명 + 옵션명 조합 매칭
    if pd.notna(cafe24_name):
        name_matches = master_df[master_df['쇼핑몰 상품 이름'].str.contains(str(cafe24_name), case=False, na=False)]
        
        if pd.notna(cafe24_option) and not name_matches.empty:
            option_matches = name_matches[name_matches['쇼핑몰 옵션 이름'].str.contains(str(cafe24_option), case=False, na=False)]
            if not option_matches.empty:
                matched = option_matches.iloc[0]
                return {
                    '판매 상품 코드': matched['판매 상품 코드'],
                    '쇼핑몰 상품 코드': matched['쇼핑몰 상품 코드'],
                    '쇼핑몰 상품 이름': matched['쇼핑몰 상품 이름'],
                    '쇼핑몰 옵션 이름': matched['쇼핑몰 옵션 이름'],
                    '매칭 방법': '상품명+옵션명 매칭',
                    '확인 필요': False
                }
        
        # 상품명만으로 매칭 (옵션 없음)
        if not name_matches.empty:
            matched = name_matches.iloc[0]
            return {
                '판매 상품 코드': matched['판매 상품 코드'],
                '쇼핑몰 상품 코드': matched['쇼핑몰 상품 코드'],
                '쇼핑몰 상품 이름': matched['쇼핑몰 상품 이름'],
                '쇼핑몰 옵션 이름': matched['쇼핑몰 옵션 이름'],
                '매칭 방법': '상품명 부분 매칭',
                '확인 필요': True
            }
    
    # 3단계: 유사도 기반 추천
    if pd.notna(cafe24_name):
        similarities = []
        for idx, master_row in master_df.iterrows():
            name_sim = calculate_similarity(cafe24_name, master_row['쇼핑몰 상품 이름'])
            option_sim = 0
            if pd.notna(cafe24_option) and pd.notna(master_row['쇼핑몰 옵션 이름']):
                option_sim = calculate_similarity(cafe24_option, master_row['쇼핑몰 옵션 이름'])
            
            total_sim = (name_sim * 0.7) + (option_sim * 0.3)
            similarities.append((idx, total_sim))
        
        # 가장 유사한 항목 찾기
        if similarities:
            best_match_idx, best_sim = max(similarities, key=lambda x: x[1])
            if best_sim > 0.5:  # 유사도 50% 이상
                matched = master_df.iloc[best_match_idx]
                return {
                    '판매 상품 코드': matched['판매 상품 코드'],
                    '쇼핑몰 상품 코드': matched['쇼핑몰 상품 코드'],
                    '쇼핑몰 상품 이름': matched['쇼핑몰 상품 이름'],
                    '쇼핑몰 옵션 이름': matched['쇼핑몰 옵션 이름'],
                    '매칭 방법': f'유사도 매칭 ({best_sim:.1%})',
                    '확인 필요': True
                }
    
    # 매칭 실패
    return {
        '판매 상품 코드': None,
        '쇼핑몰 상품 코드': cafe24_code,
        '쇼핑몰 상품 이름': cafe24_name,
        '쇼핑몰 옵션 이름': cafe24_option,
        '매칭 방법': '매칭 실패',
        '확인 필요': True
    }


def convert_to_3pl_format(df, master_df, is_cafe24=False):
    """카페24 데이터를 3PL 배송 양식으로 변환"""
    
    if is_cafe24 and master_df is not None:
        # 카페24 컬럼 감지
        cafe24_code_col = None
        cafe24_name_col = None
        cafe24_option_col = None
        
        for col in df.columns:
            if '자체품목코드' in col or '품목코드' in col:
                cafe24_code_col = col
            elif '상품명' in col:
                cafe24_name_col = col
            elif '옵션' in col:
                cafe24_option_col = col
        
        st.info(f"🔍 카페24 컬럼 감지: 코드={cafe24_code_col}, 상품명={cafe24_name_col}, 옵션={cafe24_option_col}")
        
        # 각 행에 대해 코드 매칭 수행
        matching_results = []
        for idx, row in df.iterrows():
            result = match_product_code(row, master_df, cafe24_code_col, cafe24_name_col, cafe24_option_col)
            matching_results.append(result)
        
        # 매칭 결과를 데이터프레임에 추가
        match_df = pd.DataFrame(matching_results)
        
        # 원본 데이터와 병합
        result_df = pd.concat([df, match_df], axis=1)
        
        # 3PL 표준 양식으로 재구성
        output_df = pd.DataFrame()
        
        # 1. 주문번호
        output_df['주문번호'] = result_df['주문번호']
        
        # 2. 수취인 명
        for col in ['수령인', '받는사람', '주문자']:
            if col in result_df.columns:
                output_df['수취인 명'] = result_df[col]
                break
        
        # 3. 수취인 핸드폰
        for col in ['핸드폰', '수령인휴대폰', '주문자핸드폰']:
            if col in result_df.columns:
                output_df['수취인 핸드폰'] = result_df[col]
                break
        
        # 4. 수취인 기본 주소
        for col in ['주소', '배송주소', '주문자주소']:
            if col in result_df.columns:
                output_df['수취인 기본 주소'] = result_df[col]
                break
        
        # 5. 쇼핑몰 상품 코드 (매칭 결과에서)
        output_df['쇼핑몰 상품 코드'] = match_df['쇼핑몰 상품 코드']
        
        # 6. 쇼핑몰 상품 이름 (매칭 결과에서)
        output_df['쇼핑몰 상품 이름'] = match_df['쇼핑몰 상품 이름']
        
        # 7. 쇼핑몰 옵션 이름 (매칭 결과에서)
        output_df['쇼핑몰 옵션 이름'] = match_df['쇼핑몰 옵션 이름']
        
        # 8. 주문 수량
        output_df['주문 수량'] = result_df['수량']
        
        # 9. 배송 메세지
        for col in ['비고', '배송메세지', '요청사항']:
            if col in result_df.columns:
                output_df['배송 메세지'] = result_df[col]
                break
        
        # 매칭 정보 추가
        output_df['매칭 방법'] = match_df['매칭 방법']
        output_df['확인 필요'] = match_df['확인 필요']
        
        return output_df
    
    # 일반 통합 모드 (기존 로직)
    return df


def read_file(uploaded_file):
    """파일을 읽어서 DataFrame으로 반환 (CSV, Excel 지원)"""
    try:
        file_extension = uploaded_file.name.lower().split('.')[-1]
        
        if file_extension == 'csv':
            # CSV 파일의 경우 인코딩 자동 감지
            file_bytes = uploaded_file.read()
            encoding = detect_encoding(file_bytes)
            
            # 여러 인코딩 시도
            encodings = [encoding, 'utf-8-sig', 'cp949', 'euc-kr', 'utf-8']
            
            for enc in encodings:
                try:
                    df = pd.read_csv(io.BytesIO(file_bytes), encoding=enc)
                    st.success(f"✅ {uploaded_file.name} - 인코딩: {enc}")
                    return df
                except:
                    continue
            
            # 모든 인코딩 실패 시
            st.error(f"❌ {uploaded_file.name} 파일을 읽을 수 없습니다.")
            return None
            
        elif file_extension in ['xlsx', 'xls']:
            # 엑셀 파일 읽기 (암호화/보호 파일 처리 포함)
            file_bytes = uploaded_file.read()
            
            # 1단계: 일반 엑셀 파일로 읽기 시도 (openpyxl 엔진)
            try:
                df = pd.read_excel(io.BytesIO(file_bytes), engine='openpyxl')
                st.success(f"✅ {uploaded_file.name} 파일 읽기 완료 (XLSX)")
                return df
            except Exception as e1:
                # 2단계: XLS 형식으로 읽기 시도 (xlrd 엔진)
                try:
                    df = pd.read_excel(io.BytesIO(file_bytes), engine='xlrd')
                    st.success(f"✅ {uploaded_file.name} 파일 읽기 완료 (XLS)")
                    return df
                except Exception as e2:
                    # 3단계: 암호화된 파일 복호화 시도
                    try:
                        st.info(f"🔓 {uploaded_file.name} 암호 보호 해제 시도 중...")
                        
                        file_stream = io.BytesIO(file_bytes)
                        office_file = msoffcrypto.OfficeFile(file_stream)
                        
                        decrypted = io.BytesIO()
                        
                        # 여러 방법으로 복호화 시도
                        decryption_success = False
                        
                        # 방법 1: 빈 비밀번호
                        try:
                            office_file.load_key(password='')
                            office_file.decrypt(decrypted)
                            decryption_success = True
                        except:
                            pass
                        
                        # 방법 2: VelvetSweatshop 알고리즘
                        if not decryption_success:
                            try:
                                file_stream.seek(0)
                                office_file = msoffcrypto.OfficeFile(file_stream)
                                decrypted = io.BytesIO()
                                office_file.load_key()  # password 없이 호출
                                office_file.decrypt(decrypted)
                                decryption_success = True
                            except:
                                pass
                        
                        if not decryption_success:
                            raise Exception("복호화 실패: 비밀번호가 필요합니다")
                        
                        decrypted.seek(0)
                        
                        # 복호화된 파일 읽기
                        try:
                            df = pd.read_excel(decrypted, engine='openpyxl')
                            st.success(f"✅ {uploaded_file.name} 파일 읽기 완료 (암호 해제됨)")
                            return df
                        except:
                            df = pd.read_excel(decrypted, engine='xlrd')
                            st.success(f"✅ {uploaded_file.name} 파일 읽기 완료 (XLS, 암호 해제됨)")
                            return df
                            
                    except Exception as e3:
                        # 모든 방법 실패
                        st.error(f"❌ {uploaded_file.name} 파일을 읽을 수 없습니다.")
                        with st.expander("🔍 오류 상세 정보 및 해결 방법"):
                            st.markdown("""
                            ### 가능한 원인:
                            1. **파일이 암호로 보호됨**: 엑셀 파일에 비밀번호가 설정되어 있습니다
                            2. **파일 손상**: 파일이 손상되어 읽을 수 없습니다
                            3. **지원하지 않는 형식**: 특수한 엑셀 형식일 수 있습니다
                            
                            ### 해결 방법:
                            1. **엑셀에서 파일 열기** → **파일** → **다른 이름으로 저장**
                            2. 저장 시 **"도구"** 버튼 클릭 → **일반 옵션**
                            3. **"쓰기 암호"** 및 **"읽기 암호"** 제거
                            4. 저장 후 다시 업로드
                            
                            또는 CSV 형식으로 저장 후 업로드해주세요.
                            """)
                        return None
        else:
            st.error(f"❌ 지원하지 않는 파일 형식입니다: {uploaded_file.name}")
            return None
            
    except Exception as e:
        st.error(f"❌ {uploaded_file.name} 파일 읽기 오류: {str(e)}")
        return None


def standardize_columns(df):
    """데이터프레임의 컬럼명을 표준화"""
    standardized_df = pd.DataFrame()
    
    # 원본 컬럼명 저장 (디버깅용)
    original_columns = df.columns.tolist()
    
    # 각 표준 컬럼에 대해 매핑 수행
    for standard_col, variants in COLUMN_MAPPING.items():
        found = False
        for variant in variants:
            if variant in df.columns:
                standardized_df[standard_col] = df[variant]
                found = True
                break
        
        # 해당하는 컬럼이 없으면 빈 열 추가
        if not found:
            standardized_df[standard_col] = None
    
    return standardized_df, original_columns


def merge_dataframes(dfs):
    """여러 데이터프레임을 하나로 합치기"""
    if not dfs:
        return None
    
    # 모든 데이터프레임 세로로 연결
    merged_df = pd.concat(dfs, ignore_index=True)
    
    # 빈 행 제거
    merged_df = merged_df.dropna(how='all')
    
    return merged_df


def create_excel_file(df):
    """DataFrame을 엑셀 파일로 변환하여 바이트 스트림 반환"""
    output = io.BytesIO()
    
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='배송업무')
        
        # 워크북 및 워크시트 가져오기
        workbook = writer.book
        worksheet = writer.sheets['배송업무']
        
        # 헤더 포맷 설정
        header_format = workbook.add_format({
            'bold': True,
            'bg_color': '#4472C4',
            'font_color': 'white',
            'border': 1,
            'align': 'center',
            'valign': 'vcenter'
        })
        
        # 확인 필요 항목 강조 포맷
        warning_format = workbook.add_format({
            'bg_color': '#FFF3CD',
            'border': 1
        })
        
        # 헤더 스타일 적용
        for col_num, value in enumerate(df.columns.values):
            worksheet.write(0, col_num, value, header_format)
        
        # 확인 필요 행 강조
        if '확인 필요' in df.columns:
            confirm_col_idx = df.columns.get_loc('확인 필요')
            for row_num, value in enumerate(df['확인 필요'], start=1):
                if value == True:
                    for col_num in range(len(df.columns)):
                        cell_value = df.iloc[row_num-1, col_num]
                        worksheet.write(row_num, col_num, cell_value, warning_format)
        
        # 열 너비 자동 조정
        for i, col in enumerate(df.columns):
            column_width = max(df[col].astype(str).map(len).max(), len(col)) + 2
            worksheet.set_column(i, i, min(column_width, 50))
    
    output.seek(0)
    return output


# Streamlit UI
def main():
    st.title("📦 물류 데이터 통합 시스템")
    st.markdown("---")
    
    # 사이드바 - 모드 선택
    with st.sidebar:
        st.header("⚙️ 시스템 모드 선택")
        
        mode = st.radio(
            "작업 모드를 선택하세요:",
            ["일반 통합 모드", "3PL 변환 모드 (카페24)"]
        )
        
        st.markdown("---")
        
        if mode == "3PL 변환 모드 (카페24)":
            st.header("📋 마스터 코드 업로드")
            master_file = st.file_uploader(
                "물류_코드명.xlsx 파일 업로드",
                type=['xlsx', 'xls'],
                help="판매 상품 코드 매칭을 위한 마스터 데이터"
            )
            
            if master_file:
                master_df = load_master_code_data(master_file)
                st.session_state['master_df'] = master_df
            else:
                master_df = st.session_state.get('master_df', None)
        else:
            st.header("📋 컬럼 매핑 규칙")
            st.markdown("""
            각 파일의 다양한 컬럼명을 아래 표준 컬럼으로 통합합니다:
            """)
            
            for standard_col, variants in COLUMN_MAPPING.items():
                with st.expander(f"**{standard_col}**"):
                    for variant in variants:
                        st.write(f"- {variant}")
        
        st.markdown("---")
        st.info("💡 **사용 방법**\n\n1. 모드 선택\n2. 파일 업로드\n3. 자동 처리 확인\n4. 결과 다운로드")
    
    # 메인 영역
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.header("1️⃣ 파일 업로드")
        
        if mode == "3PL 변환 모드 (카페24)":
            st.info("📌 카페24 주문 CSV 파일을 업로드하세요")
        
        uploaded_files = st.file_uploader(
            "엑셀/CSV 파일을 업로드하세요",
            type=['csv', 'xlsx', 'xls'],
            accept_multiple_files=True,
            help="여러 파일을 한 번에 선택할 수 있습니다"
        )
    
    with col2:
        st.header("📊 업로드 상태")
        if uploaded_files:
            st.metric("업로드된 파일", len(uploaded_files))
            
            if mode == "3PL 변환 모드 (카페24)":
                if st.session_state.get('master_df') is not None:
                    st.success("✅ 마스터 코드 로드됨")
                else:
                    st.warning("⚠️ 마스터 코드 필요")
        else:
            st.info("파일을 업로드해주세요")
    
    if uploaded_files:
        st.markdown("---")
        st.header("2️⃣ 파일 처리")
        
        # 파일 읽기 및 표준화
        processed_dfs = []
        file_info = []
        
        with st.spinner("파일을 처리하는 중..."):
            for uploaded_file in uploaded_files:
                # 파일 읽기
                df = read_file(uploaded_file)
                
                if df is not None:
                    if mode == "3PL 변환 모드 (카페24)":
                        # 3PL 변환
                        master_df = st.session_state.get('master_df', None)
                        if master_df is not None:
                            converted_df = convert_to_3pl_format(df, master_df, is_cafe24=True)
                            processed_dfs.append(converted_df)
                        else:
                            st.error("❌ 마스터 코드 파일을 먼저 업로드해주세요!")
                            continue
                    else:
                        # 일반 통합 모드
                        standardized_df, original_cols = standardize_columns(df)
                        processed_dfs.append(standardized_df)
                    
                    file_info.append({
                        '파일명': uploaded_file.name,
                        '원본 행 수': len(df),
                        '원본 컬럼 수': len(df.columns),
                        '처리 후 행 수': len(processed_dfs[-1]) if processed_dfs else 0
                    })
        
        # 파일 정보 테이블 표시
        if file_info:
            st.subheader("📄 처리된 파일 정보")
            info_df = pd.DataFrame(file_info)
            st.dataframe(info_df, use_container_width=True)
        
        # 데이터 통합
        if processed_dfs:
            st.markdown("---")
            st.header("3️⃣ 데이터 통합")
            
            if mode == "일반 통합 모드":
                merged_df = merge_dataframes(processed_dfs)
            else:
                # 3PL 모드는 파일별로 처리
                merged_df = pd.concat(processed_dfs, ignore_index=True)
            
            if merged_df is not None:
                # 통계 정보
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.metric("총 행 수", len(merged_df))
                with col2:
                    st.metric("총 컬럼 수", len(merged_df.columns))
                with col3:
                    if '확인 필요' in merged_df.columns:
                        need_confirm = merged_df['확인 필요'].sum()
                        st.metric("확인 필요", need_confirm, delta="항목")
                    else:
                        non_empty_rows = merged_df.dropna(how='all').shape[0]
                        st.metric("유효 행 수", non_empty_rows)
                with col4:
                    if '매칭 방법' in merged_df.columns:
                        matched = (merged_df['매칭 방법'] != '매칭 실패').sum()
                        st.metric("매칭 성공", f"{matched}/{len(merged_df)}")
                
                # 매칭 결과 요약 (3PL 모드)
                if mode == "3PL 변환 모드 (카페24)" and '매칭 방법' in merged_df.columns:
                    st.subheader("🔍 매칭 결과 분석")
                    
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.markdown("**매칭 방법별 통계:**")
                        method_counts = merged_df['매칭 방법'].value_counts()
                        st.dataframe(method_counts, use_container_width=True)
                    
                    with col2:
                        st.markdown("**확인 필요 항목:**")
                        need_check = merged_df[merged_df['확인 필요'] == True]
                        if not need_check.empty:
                            st.warning(f"⚠️ {len(need_check)}개 항목 확인 필요")
                            with st.expander("확인 필요 항목 보기"):
                                st.dataframe(need_check[['주문번호', '쇼핑몰 상품 이름', '매칭 방법']], use_container_width=True)
                        else:
                            st.success("✅ 모든 항목이 정확히 매칭되었습니다!")
                
                # 미리보기
                st.subheader("📊 통합 데이터 미리보기")
                
                # 확인 필요 항목 필터
                if '확인 필요' in merged_df.columns:
                    show_filter = st.checkbox("⚠️ 확인 필요 항목만 보기")
                    if show_filter:
                        display_df = merged_df[merged_df['확인 필요'] == True]
                    else:
                        display_df = merged_df
                else:
                    display_df = merged_df
                
                st.dataframe(display_df.head(50), use_container_width=True)
                
                # 다운로드
                st.markdown("---")
                st.header("4️⃣ 파일 다운로드")
                
                # 오늘 날짜로 파일명 생성
                today = datetime.now().strftime("%Y%m%d")
                
                if mode == "3PL 변환 모드 (카페24)":
                    filename = f"{today}_3PL배송업무.xlsx"
                else:
                    filename = f"{today}_배송업무.xlsx"
                
                # 엑셀 파일 생성
                excel_file = create_excel_file(merged_df)
                
                # 다운로드 버튼
                st.download_button(
                    label="📥 통합 파일 다운로드",
                    data=excel_file,
                    file_name=filename,
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    type="primary",
                    use_container_width=True
                )
                
                st.success(f"✅ **{filename}** 파일이 준비되었습니다!")
                
                if mode == "3PL 변환 모드 (카페24)" and '확인 필요' in merged_df.columns:
                    if merged_df['확인 필요'].sum() > 0:
                        st.warning("⚠️ 다운로드한 파일에서 노란색으로 표시된 항목을 확인해주세요!")
            else:
                st.error("❌ 데이터 통합에 실패했습니다.")
        else:
            st.warning("⚠️ 처리된 파일이 없습니다.")
    
    # 푸터
    st.markdown("---")
    st.markdown("""
    <div style='text-align: center; color: gray;'>
        <small>물류 데이터 통합 시스템 v2.0 | Made with Streamlit</small>
    </div>
    """, unsafe_allow_html=True)


if __name__ == "__main__":
    main()
