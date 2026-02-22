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


def detect_platform(df):
    """
    데이터프레임의 컬럼명을 보고 플랫폼 자동 감지
    """
    columns = set(df.columns)
    
    # 카페24 감지: '자체품목코드' 존재
    if '자체품목코드' in columns:
        return 'cafe24'
    
    # 앱 감지: '주문상품' + '받는분.이름' + '사용자.ID'
    if '주문상품' in columns and '받는분.이름' in columns and '사용자.ID' in columns:
        return 'app'
    
    # 쿠팡 감지: '노출상품ID' + '옵션ID'
    if '노출상품ID' in columns and '옵션ID' in columns:
        return 'coupang'
    
    # 네이버 감지: '상품번호' + '구매자명'
    if '상품번호' in columns and '구매자명' in columns:
        return 'naver'
    
    return 'unknown'


def parse_app_product(product_str):
    """
    앱 주문상품 파싱
    입력: [Zee] 1개 (페리윙클 PERIWINKLE 1개)
    출력: {'상품명': 'Zee', '수량': 1, '옵션': '페리윙클'}
    """
    import re
    
    if pd.isna(product_str):
        return {'상품명': None, '수량': 1, '옵션': None}
    
    product_match = re.search(r'\[(.*?)\]', product_str)
    quantity_match = re.search(r'\]\s*(\d+)개', product_str)
    option_match = re.search(r'\((.*?)\s+[A-Z\s]+\d+개\)', product_str)
    
    return {
        '상품명': product_match.group(1) if product_match else None,
        '수량': int(quantity_match.group(1)) if quantity_match else 1,
        '옵션': option_match.group(1) if option_match else None
    }


def load_master_code_data(master_file):
    """물류_코드명 마스터 데이터 로드"""
    try:
        df = pd.read_excel(master_file)
        st.success(f"✅ 마스터 코드 데이터 로드 완료: {len(df)}개 항목")
        return df
    except Exception as e:
        st.error(f"❌ 마스터 코드 데이터 로드 실패: {str(e)}")
        return None


def match_product_code(row, master_df, platform, code_col=None, name_col=None, option_col=None):
    """
    주문 데이터와 마스터 코드 매칭 (플랫폼별 처리)
    
    매칭 우선순위:
    1. 코드 정확 매칭
    2. 상품명 + 옵션명 조합 매칭
    3. 유사도 기반 추천
    """
    # 플랫폼별 마스터 데이터 필터링
    if platform in ['cafe24', 'coupang', 'naver', 'app']:
        platform_master = master_df[master_df['판매처'] == platform].copy()
    else:
        platform_master = master_df
    
    # 마스터 데이터가 없으면 즉시 매칭 실패 반환
    if platform_master.empty:
        return {
            '플랫폼': platform,
            '판매 상품 코드': None,
            '쇼핑몰 상품 코드': None,
            '쇼핑몰 상품 이름': None,
            '쇼핑몰 옵션 이름': None,
            '매칭 방법': f'매칭 실패 (마스터 데이터 없음)',
            '확인 필요': True
        }
    
    # 플랫폼별 코드 추출
    if platform == 'cafe24':
        search_code = row.get(code_col, None)
        product_name = row.get(name_col, None)
        option_name = row.get(option_col, None)
    elif platform == 'app':
        # 앱: 주문상품 파싱
        parsed = parse_app_product(row.get('주문상품', ''))
        search_code = parsed['상품명']
        product_name = parsed['상품명']
        option_name = parsed['옵션']
    elif platform == 'coupang':
        # 쿠팡: 옵션ID 사용
        search_code = str(row.get('옵션ID', ''))
        product_name = row.get('등록상품명', None)
        option_name = row.get('등록옵션명', None)
    elif platform == 'naver':
        # 네이버: 상품번호 사용
        search_code = row.get('상품번호', None)
        product_name = row.get('상품명', None)
        option_name = row.get('옵션정보', None)
    else:
        search_code = None
        product_name = None
        option_name = None
    
    # 1단계: 판매 상품 코드로 정확 매칭
    if pd.notna(search_code):
        exact_match = platform_master[platform_master['판매 상품 코드'].astype(str) == str(search_code)]
        if not exact_match.empty:
            matched = exact_match.iloc[0]
            return {
                '플랫폼': platform,
                '판매 상품 코드': matched['판매 상품 코드'],
                '쇼핑몰 상품 코드': matched['쇼핑몰 상품 코드'],
                '쇼핑몰 상품 이름': matched['쇼핑몰 상품 이름'],
                '쇼핑몰 옵션 이름': matched['쇼핑몰 옵션 이름'],
                '매칭 방법': '코드 정확 매칭',
                '확인 필요': False
            }
    
    # 2단계: 상품명 + 옵션명 조합 매칭
    if pd.notna(product_name):
        name_matches = platform_master[platform_master['쇼핑몰 상품 이름'].str.contains(str(product_name), case=False, na=False)]
        
        if pd.notna(option_name) and not name_matches.empty:
            option_matches = name_matches[name_matches['쇼핑몰 옵션 이름'].str.contains(str(option_name), case=False, na=False)]
            if not option_matches.empty:
                matched = option_matches.iloc[0]
                return {
                    '플랫폼': platform,
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
                '플랫폼': platform,
                '판매 상품 코드': matched['판매 상품 코드'],
                '쇼핑몰 상품 코드': matched['쇼핑몰 상품 코드'],
                '쇼핑몰 상품 이름': matched['쇼핑몰 상품 이름'],
                '쇼핑몰 옵션 이름': matched['쇼핑몰 옵션 이름'],
                '매칭 방법': '상품명 부분 매칭',
                '확인 필요': True
            }
    
    # 3단계: 유사도 기반 추천
    if pd.notna(product_name):
        similarities = []
        for idx, master_row in platform_master.iterrows():
            name_sim = calculate_similarity(product_name, master_row['쇼핑몰 상품 이름'])
            option_sim = 0
            if pd.notna(option_name) and pd.notna(master_row['쇼핑몰 옵션 이름']):
                option_sim = calculate_similarity(option_name, master_row['쇼핑몰 옵션 이름'])
            
            total_sim = (name_sim * 0.7) + (option_sim * 0.3)
            similarities.append((idx, total_sim))
        
        # 가장 유사한 항목 찾기
        if similarities:
            best_match_idx, best_sim = max(similarities, key=lambda x: x[1])
            if best_sim > 0.5:  # 유사도 50% 이상
                matched = platform_master.iloc[best_match_idx]
                return {
                    '플랫폼': platform,
                    '판매 상품 코드': matched['판매 상품 코드'],
                    '쇼핑몰 상품 코드': matched['쇼핑몰 상품 코드'],
                    '쇼핑몰 상품 이름': matched['쇼핑몰 상품 이름'],
                    '쇼핑몰 옵션 이름': matched['쇼핑몰 옵션 이름'],
                    '매칭 방법': f'유사도 매칭 ({best_sim:.1%})',
                    '확인 필요': True
                }
    
    # 매칭 실패
    return {
        '플랫폼': platform,
        '판매 상품 코드': None,
        '쇼핑몰 상품 코드': search_code,
        '쇼핑몰 상품 이름': product_name,
        '쇼핑몰 옵션 이름': option_name,
        '매칭 방법': '매칭 실패',
        '확인 필요': True
    }


def convert_to_3pl_format(df, master_df, platform):
    """
    플랫폼별 데이터를 3PL 배송 양식으로 변환
    """
    if master_df is None:
        st.error("❌ 마스터 코드 파일을 먼저 업로드해주세요!")
        return None
    
    # 플랫폼별 컬럼 감지
    if platform == 'cafe24':
        code_col = '자체품목코드'
        name_col = '주문상품명'
        option_col = '옵션'
    else:
        code_col = None
        name_col = None
        option_col = None
    
    st.info(f"🔍 {platform.upper()} 파일 처리 중...")
    
    # 각 행에 대해 코드 매칭 수행
    matching_results = []
    for idx, row in df.iterrows():
        result = match_product_code(row, master_df, platform, code_col, name_col, option_col)
        matching_results.append(result)
    
    # 매칭 결과를 데이터프레임에 추가
    match_df = pd.DataFrame(matching_results)
    
    # 원본 데이터와 병합
    result_df = pd.concat([df, match_df], axis=1)
    
    # 3PL 표준 양식으로 재구성
    output_df = pd.DataFrame()
    
    # 0. 플랫폼 (새로 추가)
    output_df['플랫폼'] = platform.upper()
    
    # 1. 주문번호
    output_df['주문번호'] = result_df['주문번호']
    
    # 2. 수취인 명
    for col in ['수령인', '받는사람', '주문자', '받는분.이름', '수취인이름']:
        if col in result_df.columns:
            output_df['수취인 명'] = result_df[col]
            break
    
    # 3. 수취인 핸드폰
    for col in ['핸드폰', '수령인휴대폰', '주문자핸드폰', '받는분.전화번호', '수취인전화번호']:
        if col in result_df.columns:
            output_df['수취인 핸드폰'] = result_df[col]
            break
    
    # 4. 수취인 기본 주소
    for col in ['주소', '배송주소', '주문자주소', '받는분.통합주소', '수취인 주소']:
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
    for col in ['수량', '구매수(수량)']:
        if col in result_df.columns:
            output_df['주문 수량'] = result_df[col]
            break
    
    # 9. 배송 메세지
    for col in ['비고', '배송메세지', '요청사항', '배송메세지']:
        if col in result_df.columns:
            output_df['배송 메세지'] = result_df[col]
            break
    
    # 매칭 정보 추가
    output_df['매칭 방법'] = match_df['매칭 방법']
    output_df['확인 필요'] = match_df['확인 필요']
    
    return output_df


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

# Streamlit UI
def main():
    st.title("📦 물류 데이터 통합 시스템 v3.0")
    st.markdown("**모든 플랫폼 동시 처리**: 카페24, 앱, 쿠팡, 네이버를 한 번에!")
    st.markdown("---")
    
    # 사이드바 - 마스터 파일 업로드
    with st.sidebar:
        st.header("⚙️ 마스터 코드 업로드")
        
        master_file = st.file_uploader(
            "📁 물류_코드명.xlsx 파일 업로드",
            type=['xlsx', 'xls'],
            help="판매 상품 코드 매칭을 위한 마스터 데이터"
        )
        
        if master_file:
            master_df = load_master_code_data(master_file)
            st.session_state['master_df'] = master_df
            
            # 플랫폼별 통계
            if master_df is not None:
                st.markdown("---")
                st.header("📊 마스터 데이터 현황")
                platform_counts = master_df['판매처'].value_counts()
                for platform, count in platform_counts.items():
                    st.metric(f"{platform.upper()}", f"{count}개 상품")
        else:
            master_df = st.session_state.get('master_df', None)
        
        st.markdown("---")
        st.info("💡 **사용 방법**\n\n1. 마스터 코드 업로드\n2. 모든 플랫폼 파일 업로드\n3. 자동 처리 확인\n4. 통합 파일 다운로드")
    
    # 메인 영역
    st.header("1️⃣ 파일 업로드 (모든 플랫폼)")
    
    uploaded_files = st.file_uploader(
        "📁 카페24, 앱, 쿠팡, 네이버 파일을 모두 선택하세요",
        type=['csv', 'xlsx', 'xls'],
        accept_multiple_files=True,
        help="여러 플랫폼의 파일을 한 번에 업로드할 수 있습니다"
    )
    
    if uploaded_files:
        st.success(f"✅ {len(uploaded_files)}개 파일 업로드됨")
        
        # 플랫폼별 파일 자동 분류
        platform_files = {
            'cafe24': [],
            'app': [],
            'coupang': [],
            'naver': [],
            'unknown': []
        }
        
        file_platform_map = {}
        
        for f in uploaded_files:
            df_temp = read_file(f)
            if df_temp is not None:
                platform = detect_platform(df_temp)
                platform_files[platform].append(f.name)
                file_platform_map[f.name] = platform
        
        # 분류 결과 표시
        st.markdown("---")
        st.header("📱 플랫폼별 파일 분류")
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("📱 카페24", len(platform_files['cafe24']))
            for fname in platform_files['cafe24']:
                st.caption(f"✓ {fname}")
        
        with col2:
            st.metric("📱 앱", len(platform_files['app']))
            for fname in platform_files['app']:
                st.caption(f"✓ {fname}")
        
        with col3:
            st.metric("🛒 쿠팡", len(platform_files['coupang']))
            for fname in platform_files['coupang']:
                st.caption(f"✓ {fname}")
        
        with col4:
            st.metric("🛍️ 네이버", len(platform_files['naver']))
            for fname in platform_files['naver']:
                st.caption(f"✓ {fname}")
        
        if platform_files['unknown']:
            st.warning(f"⚠️ 알 수 없는 파일 {len(platform_files['unknown'])}개: {', '.join(platform_files['unknown'])}")
        
        # 파일 처리
        st.markdown("---")
        st.header("2️⃣ 파일 처리 및 매칭")
        
        master_df = st.session_state.get('master_df', None)
        if master_df is None:
            st.error("❌ 마스터 코드 파일을 먼저 업로드해주세요!")
            return
        
        processed_dfs = []
        file_info = []
        
        with st.spinner("모든 플랫폼 파일을 처리하는 중..."):
            for uploaded_file in uploaded_files:
                df = read_file(uploaded_file)
                
                if df is not None:
                    platform = file_platform_map.get(uploaded_file.name, 'unknown')
                    
                    if platform in ['cafe24', 'app', 'coupang', 'naver']:
                        converted_df = convert_to_3pl_format(df, master_df, platform)
                        if converted_df is not None:
                            processed_dfs.append(converted_df)
                            
                            matched = (converted_df['매칭 방법'] != '매칭 실패').sum()
                            need_check = converted_df['확인 필요'].sum()
                            
                            file_info.append({
                                '플랫폼': platform.upper(),
                                '파일명': uploaded_file.name,
                                '원본 행 수': len(df),
                                '매칭 성공': f"{matched}/{len(converted_df)}",
                                '확인 필요': need_check
                            })
                    else:
                        st.warning(f"⚠️ {uploaded_file.name}: 알 수 없는 플랫폼")
        
        # 파일 정보 테이블 표시
        if file_info:
            st.subheader("📄 처리된 파일 정보")
            info_df = pd.DataFrame(file_info)
            st.dataframe(info_df, use_container_width=True)
        
        # 데이터 통합
        if processed_dfs:
            st.markdown("---")
            st.header("3️⃣ 데이터 통합 결과")
            
            merged_df = pd.concat(processed_dfs, ignore_index=True)
            
            # 모든 컬럼을 문자열로 변환 (Arrow 변환 오류 방지)
            for col in merged_df.columns:
                merged_df[col] = merged_df[col].astype(str).replace('nan', '')
                merged_df[col] = merged_df[col].replace('None', '')
                merged_df[col] = merged_df[col].replace('<NA>', '')
            
            # 통계 정보
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("총 주문 수", len(merged_df))
            with col2:
                matched = (merged_df['매칭 방법'] != '매칭 실패').sum()
                st.metric("매칭 성공", f"{matched}/{len(merged_df)}")
            with col3:
                need_confirm = merged_df['확인 필요'].sum()
                st.metric("확인 필요", need_confirm)
            with col4:
                platforms = merged_df['플랫폼'].nunique()
                st.metric("처리 플랫폼", f"{platforms}개")
            
            # 플랫폼별 통계
            st.subheader("📊 플랫폼별 통계")
            platform_stats = merged_df.groupby('플랫폼').agg({
                '주문번호': 'count',
                '확인 필요': 'sum'
            }).rename(columns={'주문번호': '주문 수', '확인 필요': '확인 필요 항목'})
            st.dataframe(platform_stats, use_container_width=True)
            
            # 매칭 방법별 통계
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
                        st.dataframe(need_check[['플랫폼', '주문번호', '쇼핑몰 상품 이름', '매칭 방법']], use_container_width=True)
                else:
                    st.success("✅ 모든 항목이 정확히 매칭되었습니다!")
            
            # 미리보기
            st.subheader("📊 통합 데이터 미리보기")
            
            # 확인 필요 항목 필터
            show_filter = st.checkbox("⚠️ 확인 필요 항목만 보기")
            if show_filter:
                display_df = merged_df[merged_df['확인 필요'] == True]
            else:
                display_df = merged_df
            
            st.dataframe(display_df.head(50), use_container_width=True)
            
            # 다운로드
            st.markdown("---")
            st.header("4️⃣ 파일 다운로드")
            
            # 오늘 날짜로 파일명 생성
            today = datetime.now().strftime("%Y%m%d")
            filename = f"{today}_통합3PL배송업무.xlsx"
            
            # 엑셀 파일 생성
            excel_file = create_excel_file(merged_df)
            
            # 다운로드 버튼
            st.download_button(
                label="📥 통합 3PL 배송 파일 다운로드",
                data=excel_file,
                file_name=filename,
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                type="primary",
                use_container_width=True
            )
            
            st.success(f"✅ **{filename}** 파일이 준비되었습니다!")
            
            if merged_df['확인 필요'].sum() > 0:
                st.warning("⚠️ 다운로드한 파일에서 노란색으로 표시된 항목을 확인해주세요!")
        else:
            st.warning("⚠️ 처리된 파일이 없습니다.")
    
    # 푸터
    st.markdown("---")
    st.markdown("""
    <div style='text-align: center; color: gray;'>
        <small>물류 데이터 통합 시스템 v3.0 | 모든 플랫폼 동시 처리 지원</small>
    </div>
    """, unsafe_allow_html=True)


if __name__ == "__main__":
    main()
