import streamlit as st
import pandas as pd
from datetime import datetime
import io
import chardet
import msoffcrypto

# 페이지 설정
st.set_page_config(
    page_title="물류 데이터 통합 시스템",
    page_icon="📦",
    layout="wide"
)

# 컬럼 매핑 규칙 정의
COLUMN_MAPPING = {
    '주문번호': ['주문번호', '쇼핑몰번호'],
    '수령인': ['받는분.이름', '수령인', '주문자'],
    '연락처': ['받는분.전화번호', '핸드폰', '수령지전화', '사용자.전화번호'],
    '우편번호': ['받는분.우편번호', '우편번호', '주문자우편번호'],
    '주소': ['받는분.통합주소', '주소', '받는분.주소', '주문자주소'],
    '상품명': ['주문상품', '주문상품명', '상품명'],
    '수량': ['수량', '개수'],
    '배송메세지': ['비고', '요청사항']
}


def detect_encoding(file_bytes):
    """파일의 인코딩을 자동으로 감지"""
    result = chardet.detect(file_bytes)
    return result['encoding']


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
        
        # 헤더 스타일 적용
        for col_num, value in enumerate(df.columns.values):
            worksheet.write(0, col_num, value, header_format)
        
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
    
    # 사이드바 - 매핑 규칙 표시
    with st.sidebar:
        st.header("📋 컬럼 매핑 규칙")
        st.markdown("""
        각 파일의 다양한 컬럼명을 아래 표준 컬럼으로 통합합니다:
        """)
        
        for standard_col, variants in COLUMN_MAPPING.items():
            with st.expander(f"**{standard_col}**"):
                for variant in variants:
                    st.write(f"- {variant}")
        
        st.markdown("---")
        st.info("💡 **사용 방법**\n\n1. 여러 파일을 동시에 업로드\n2. 자동으로 컬럼명 통합\n3. 통합된 파일 다운로드")
    
    # 메인 영역
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.header("1️⃣ 파일 업로드")
        uploaded_files = st.file_uploader(
            "스마트스토어 발주서, 배송정보 CSV, DeliveryList, Orders 파일 등을 업로드하세요",
            type=['csv', 'xlsx', 'xls'],
            accept_multiple_files=True,
            help="여러 파일을 한 번에 선택할 수 있습니다"
        )
    
    with col2:
        st.header("📊 업로드 상태")
        if uploaded_files:
            st.metric("업로드된 파일", len(uploaded_files))
        else:
            st.info("파일을 업로드해주세요")
    
    if uploaded_files:
        st.markdown("---")
        st.header("2️⃣ 파일 처리")
        
        # 파일 읽기 및 표준화
        standardized_dfs = []
        file_info = []
        
        with st.spinner("파일을 처리하는 중..."):
            for uploaded_file in uploaded_files:
                # 파일 읽기
                df = read_file(uploaded_file)
                
                if df is not None:
                    # 컬럼 표준화
                    standardized_df, original_cols = standardize_columns(df)
                    standardized_dfs.append(standardized_df)
                    
                    file_info.append({
                        '파일명': uploaded_file.name,
                        '원본 행 수': len(df),
                        '원본 컬럼 수': len(original_cols),
                        '표준화 후 행 수': len(standardized_df)
                    })
        
        # 파일 정보 테이블 표시
        if file_info:
            st.subheader("📄 처리된 파일 정보")
            info_df = pd.DataFrame(file_info)
            st.dataframe(info_df, use_container_width=True)
        
        # 데이터 통합
        if standardized_dfs:
            st.markdown("---")
            st.header("3️⃣ 데이터 통합")
            
            merged_df = merge_dataframes(standardized_dfs)
            
            if merged_df is not None:
                # 통계 정보
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("총 행 수", len(merged_df))
                with col2:
                    st.metric("총 컬럼 수", len(merged_df.columns))
                with col3:
                    non_empty_rows = merged_df.dropna(how='all').shape[0]
                    st.metric("유효 행 수", non_empty_rows)
                
                # 미리보기
                st.subheader("📊 통합 데이터 미리보기")
                st.dataframe(merged_df.head(20), use_container_width=True)
                
                # 다운로드
                st.markdown("---")
                st.header("4️⃣ 파일 다운로드")
                
                # 오늘 날짜로 파일명 생성
                today = datetime.now().strftime("%Y%m%d")
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
            else:
                st.error("❌ 데이터 통합에 실패했습니다.")
        else:
            st.warning("⚠️ 처리된 파일이 없습니다.")
    
    # 푸터
    st.markdown("---")
    st.markdown("""
    <div style='text-align: center; color: gray;'>
        <small>물류 데이터 통합 시스템 v1.0 | Made with Streamlit</small>
    </div>
    """, unsafe_allow_html=True)


if __name__ == "__main__":
    main()
