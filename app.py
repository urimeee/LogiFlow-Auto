import streamlit as st
import pandas as pd
from datetime import datetime
import io
import chardet
import msoffcrypto
from difflib import SequenceMatcher
import os
from dotenv import load_dotenv

# 환경변수 로드 (.env 파일에서)
load_dotenv()

# 환경변수에서 설정값 가져오기
APP_NAME = os.getenv('APP_NAME', '물류 데이터 통합 시스템')
APP_VERSION = os.getenv('APP_VERSION', '3.12')
MAX_UPLOAD_SIZE = int(os.getenv('MAX_UPLOAD_SIZE', '200'))
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')

# 페이지 설정
st.set_page_config(
    page_title=APP_NAME,
    page_icon="📦",
    layout="wide"
)

# 플랫폼 이름 매핑 (영문 → 한글)
PLATFORM_NAME_MAP = {
    'cafe24': '카페24',
    'app': '앱',
    'coupang': '쿠팡',
    'naver': '네이버'
}

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


def split_app_products(product_str):
    """
    앱 주문상품을 쉼표 기준으로 분리
    입력: "[Zee] 1개 (페리윙클 PERIWINKLE 1개, 토이 전용 충전기 (5V 1A) 1개)"
    출력: ["[Zee] 1개 (페리윙클 PERIWINKLE 1개)", "토이 전용 충전기 (5V 1A) 1개)"]
    
    특별 케이스:
    "[(앱특가) 아크 극락 번들] 1개 (아이스 1개, 추가 극락젤 1set(10개입) (50% 할인) 2개)"
    → ["[(앱특가) 아크 극락 번들] 1개 (아이스 1개)", "추가 극락젤 1set(10개입) (50% 할인) 2개)"]
    """
    import re
    
    if pd.isna(product_str) or (isinstance(product_str, pd.DataFrame)):
        return [product_str]
    
    # 대괄호 [] 안의 상품명과 괄호 () 안의 옵션 찾기
    # 패턴: [상품명] N개 (옵션1, 옵션2, ...)
    match = re.match(r'(\[.*?\]\s*\d+개\s*\()(.*?)(\))', product_str)
    
    if not match:
        return [product_str]
    
    prefix = match.group(1)  # "[상품명] N개 ("
    options_str = match.group(2)  # "옵션1, 옵션2, ..."
    suffix = match.group(3)  # ")"
    
    # 괄호 안의 내용을 쉼표로 분리 (단, 괄호 안의 쉼표는 제외)
    options = []
    current = []
    paren_depth = 0
    
    for char in options_str:
        if char == '(':
            paren_depth += 1
            current.append(char)
        elif char == ')':
            paren_depth -= 1
            current.append(char)
        elif char == ',' and paren_depth == 0:
            options.append(''.join(current).strip())
            current = []
        else:
            current.append(char)
    
    if current:
        options.append(''.join(current).strip())
    
    # 옵션이 1개면 분리 안 함
    if len(options) <= 1:
        return [product_str]
    
    # 첫 번째 옵션은 원래 형식 유지
    results = [f"{prefix}{options[0]}{suffix}"]
    
    # 나머지 옵션들은 단독으로
    for opt in options[1:]:
        results.append(f"{opt}{suffix}")
    
    return results


def parse_app_product(product_str):
    """
    앱 주문상품 파싱
    입력: [Zee] 1개 (페리윙클 PERIWINKLE 1개)
    입력: [Dip] 1개 (딥 플럼 1개)
    입력: [(앱특가) 아크 극락 번들] 1개 (아이스 1개, ...)
    출력: {'상품명': 'Zee', '수량': 1, '옵션': '페리윙클', '옵션_원본': '페리윙클 PERIWINKLE 1개', 'IC/PL_키워드': None}
    """
    import re
    
    if pd.isna(product_str):
        return {'상품명': None, '수량': 1, '옵션': None, '옵션_원본': None, 'IC/PL_키워드': None}
    
    # 상품명 추출 (대괄호 안)
    product_match = re.search(r'\[(.*?)\]', product_str)
    product_name = product_match.group(1) if product_match else None
    
    # 수량 추출
    quantity_match = re.search(r'\]\s*(\d+)개', product_str)
    quantity = int(quantity_match.group(1)) if quantity_match else 1
    
    # 모든 괄호 내용 추출 (IC/PL 구분을 위해)
    all_parens = re.findall(r'\(([^)]+)\)', product_str)
    
    # IC/PL 키워드 찾기
    ic_pl_keyword = None
    for paren_text in all_parens:
        if '아이스' in paren_text or 'ICE' in paren_text.upper() or 'IC' in paren_text.upper():
            ic_pl_keyword = 'IC'
            break
        elif '플럼' in paren_text or 'PLUM' in paren_text.upper() or 'PL' in paren_text.upper():
            ic_pl_keyword = 'PL'
            break
        elif '페리윙클' in paren_text or 'PERIWINKLE' in paren_text.upper() or 'PW' in paren_text.upper():
            ic_pl_keyword = 'PW'
            break
    
    # 옵션 추출 (첫 번째 괄호 내용에서)
    option_name = None
    option_original = None
    if all_parens:
        option_original = all_parens[0]  # 원본 보존
        option_text = option_original
        
        # 정제: 숫자+개 제거하되, 띄어쓰기는 유지
        option_name = re.sub(r'\d+개', '', option_text)  # "딥 플럼 1개" → "딥 플럼 "
        option_name = option_name.strip()  # 앞뒤 공백만 제거
        
        # 영문 대문자 제거 (하지만 띄어쓰기는 유지)
        # "페리윙클 PERIWINKLE" → "페리윙클 "
        option_name = re.sub(r'\s+[A-Z]+\s*', ' ', option_name)  # 영문 단어 제거
        option_name = option_name.strip()
        
        if not option_name:
            option_name = None
    
    return {
        '상품명': product_name,
        '수량': quantity,
        '옵션': option_name,
        '옵션_원본': option_original,
        'IC/PL_키워드': ic_pl_keyword
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


def ensure_unique_order_numbers(df, order_col='쇼핑몰 주문번호'):
    """
    주문번호 중복 제거 함수
    
    동일한 주문번호가 여러 개 있을 경우, 두 번째부터 접미사 추가
    예시:
    - 20260225-83316T835
    - 20260225-83316T835  → 20260225-83316T835a
    - 20260225-83316T835  → 20260225-83316T835b
    """
    if order_col not in df.columns:
        return df
    
    # 주문번호별로 카운트
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
    
    # 새로운 주문번호로 교체
    df[order_col] = new_order_numbers
    
    return df


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
        # 영문 플랫폼 이름을 한글로 변환
        korean_platform_name = PLATFORM_NAME_MAP.get(platform, platform)
        platform_master = master_df[master_df['판매처'] == korean_platform_name].copy()
    else:
        korean_platform_name = platform
        platform_master = master_df
    
    # 마스터 데이터가 없으면 즉시 매칭 실패 반환
    if platform_master.empty:
        return {
            '플랫폼': korean_platform_name,  # 한글 이름 사용
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
        # 앱: 주문상품에서 상품명 추출
        product_str = row.get('주문상품', '')
        
        # 대괄호가 있는 경우 (예: [Zee] 1개 (...))
        parsed = parse_app_product(product_str)
        search_code = parsed['상품명']  # 예: 'Zee', 'Eva'
        product_name = parsed['상품명']
        option_name = parsed['옵션']
        option_original = parsed['옵션_원본']
        ic_pl_keyword = parsed['IC/PL_키워드']
        
        # 대괄호가 없는 경우 (분리된 상품: "토이 전용 충전기 (5V 1A)" 등)
        # 전체 문자열을 검색 키워드로 사용
        if search_code is None and product_str:
            # 괄호 앞부분만 추출 (예: "토이 전용 충전기(5V 1A)" → "토이 전용 충전기")
            import re
            # 한글/영문/숫자/공백만 추출
            clean_str = re.sub(r'\(.*?\)', '', product_str).strip()
            
            # 특수 키워드 매핑 (마스터 파일에 정확한 이름이 없는 경우)
            keyword_mapping = {
                '추가 극락젤': '극락젤',
                '추가 극락젤 1set': '극락젤',
            }
            
            # 키워드 변환 시도
            for key, value in keyword_mapping.items():
                if key in clean_str:
                    clean_str = value
                    break
            
            search_code = clean_str
            product_name = clean_str
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
                '플랫폼': korean_platform_name,  # 한글 이름 사용
                '판매 상품 코드': matched['판매 상품 코드'],
                '쇼핑몰 상품 코드': matched['쇼핑몰 상품 코드'],
                '쇼핑몰 상품 이름': matched['쇼핑몰 상품 이름'],
                '쇼핑몰 옵션 이름': matched['쇼핑몰 옵션 이름'],
                '매칭 방법': '코드 정확 매칭',
                '확인 필요': False
            }
        
        # 앱 플랫폼 특수 처리: 판매 상품 코드에서 상품명 부분 매칭
        if platform == 'app' and search_code:
            # 방법 1: 판매 상품 코드에서 [상품명] 패턴 검색
            # 괄호 () 때문에 정규식이 아닌 단순 문자열 검색 사용
            search_pattern = f'[{search_code}]'
            pattern_match = platform_master[platform_master['판매 상품 코드'].str.contains(search_pattern, case=False, na=False, regex=False)]
            
            if not pattern_match.empty:
                # Step 1: 원본 문자열(option_original)과 정확히 일치하는 항목 우선 검색
                # 예: "딥 페리윙클 1개" vs "딥 플럼 1개" 구분
                if option_original:
                    exact_option_match = pattern_match[pattern_match['판매 상품 코드'].str.contains(option_original, case=False, na=False, regex=False)]
                    if not exact_option_match.empty:
                        pattern_match = exact_option_match
                
                # Step 2: 옵션명(띄어쓰기 포함)으로 필터링
                # 예: "딥 페리윙클" (띄어쓰기 유지)
                if len(pattern_match) > 1 and option_name:
                    option_filtered = pattern_match[pattern_match['판매 상품 코드'].str.contains(str(option_name), case=False, na=False, regex=False)]
                    if not option_filtered.empty:
                        pattern_match = option_filtered
                
                # Step 3: IC/PL 키워드로 구분
                # 예: "아이스" → IC 버전, "플럼" → PL 버전
                if len(pattern_match) > 1 and ic_pl_keyword:
                    ic_pl_filtered = pattern_match[pattern_match['쇼핑몰 상품 이름'].str.contains(ic_pl_keyword, case=False, na=False)]
                    if not ic_pl_filtered.empty:
                        pattern_match = ic_pl_filtered
                
                # Step 4: 가장 짧은 것 선택 (가장 정확한 매칭)
                # 예: "[Dip] 1개 (딥 플럼 1개)" vs "딥 극락 번들..."
                pattern_match = pattern_match.copy()  # 경고 방지
                pattern_match['_len'] = pattern_match['판매 상품 코드'].str.len()
                matched = pattern_match.sort_values('_len').iloc[0]
                
                return {
                    '플랫폼': korean_platform_name,
                    '판매 상품 코드': matched['판매 상품 코드'],
                    '쇼핑몰 상품 코드': matched['쇼핑몰 상품 코드'],
                    '쇼핑몰 상품 이름': matched['쇼핑몰 상품 이름'],
                    '쇼핑몰 옵션 이름': matched['쇼핑몰 옵션 이름'],
                    '매칭 방법': '상품명 패턴 매칭',
                    '확인 필요': False
                }
            
            # 방법 2: 판매 상품 코드에서 키워드 포함 검색 (대괄호 없는 경우)
            # 예: "토이 전용 충전기" → "토이 전용 충전기(5V 1A)" 찾기
            keyword_match = platform_master[platform_master['판매 상품 코드'].str.contains(search_code, case=False, na=False, regex=False)]
            
            if not keyword_match.empty:
                # 여러 개가 매칭될 경우 가장 짧은 것 선택 (가장 정확한 매칭)
                # 예: "토이 전용 충전기(5V 1A)" vs "딥 극락 번들(..., 토이 전용 충전기...)"
                keyword_match = keyword_match.copy()  # 경고 방지
                keyword_match['_len'] = keyword_match['판매 상품 코드'].str.len()
                matched = keyword_match.sort_values('_len').iloc[0]
                
                return {
                    '플랫폼': korean_platform_name,
                    '판매 상품 코드': matched['판매 상품 코드'],
                    '쇼핑몰 상품 코드': matched['쇼핑몰 상품 코드'],
                    '쇼핑몰 상품 이름': matched['쇼핑몰 상품 이름'],
                    '쇼핑몰 옵션 이름': matched['쇼핑몰 옵션 이름'],
                    '매칭 방법': '키워드 매칭',
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
                    '플랫폼': korean_platform_name,  # 한글 이름 사용
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
                '플랫폼': korean_platform_name,  # 한글 이름 사용
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
                    '플랫폼': korean_platform_name,  # 한글 이름 사용
                    '판매 상품 코드': matched['판매 상품 코드'],
                    '쇼핑몰 상품 코드': matched['쇼핑몰 상품 코드'],
                    '쇼핑몰 상품 이름': matched['쇼핑몰 상품 이름'],
                    '쇼핑몰 옵션 이름': matched['쇼핑몰 옵션 이름'],
                    '매칭 방법': f'유사도 매칭 ({best_sim:.1%})',
                    '확인 필요': True
                }
    
    # 매칭 실패
    return {
        '플랫폼': korean_platform_name,  # 한글 이름 사용
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
    
    # 오늘 날짜
    today = datetime.now().strftime("%Y-%m-%d")
    
    # 데이터 행 수
    n_rows = len(result_df)
    
    # 3PL 표준 양식으로 재구성 (순서 중요!)
    output_df = pd.DataFrame()
    
    # 1. 쇼핑몰 코드
    output_df['쇼핑몰 코드'] = ['ONLINE1'] * n_rows
    
    # 2. 쇼핑몰 이름 (매칭 결과에서 가져옴 - 한글 이름)
    output_df['쇼핑몰 이름'] = match_df['플랫폼']
    
    # 3. 쇼핑몰 묶음 배송 번호 (주문번호와 동일)
    output_df['쇼핑몰 묶음 배송 번호'] = result_df['주문번호']
    
    # 4. 묶음배송유무
    output_df['묶음배송유무'] = ['유'] * n_rows
    
    # 5. 접수일시
    output_df['접수일시'] = [today] * n_rows
    
    # 6. 결제일시
    output_df['결제일시'] = [today] * n_rows
    
    # 7. 수취인 상세 주소
    output_df['수취인 상세 주소'] = ['.'] * n_rows
    
    # 8. 수취인 전화[안심 번호] (수취인 핸드폰과 동일)
    phone = None
    for col in ['핸드폰', '수령인휴대폰', '주문자핸드폰', '받는분.전화번호', '수취인전화번호']:
        if col in result_df.columns:
            phone = result_df[col]
            break
    output_df['수취인 전화[안심 번호]'] = phone
    
    # 9. 수취인 전화번호 (수취인 핸드폰과 동일)
    output_df['수취인 전화번호'] = phone
    
    # 10. 수취인 건물 관리번호 (공란)
    output_df['수취인 건물 관리번호'] = [''] * n_rows
    
    # 11. 주문자 명 (수취인 명과 동일)
    recipient_name = None
    for col in ['수령인', '받는사람', '주문자', '받는분.이름', '수취인이름']:
        if col in result_df.columns:
            recipient_name = result_df[col]
            break
    output_df['주문자 명'] = recipient_name
    
    # 12. 주문자 이메일
    output_df['주문자 이메일'] = ['AA@aa.com'] * n_rows
    
    # 13. 수취인 우편번호 (공란)
    output_df['수취인 우편번호'] = [''] * n_rows
    
    # 14. 수취인 주소 유형
    output_df['수취인 주소 유형'] = ['미확인'] * n_rows
    
    # 15. 주문자 전화[안심 번호] (수취인 핸드폰과 동일)
    output_df['주문자 전화[안심 번호]'] = phone
    
    # 16. 주문자 전화번호 (수취인 핸드폰과 동일)
    output_df['주문자 전화번호'] = phone
    
    # 17. 주문자 핸드폰 (수취인 핸드폰과 동일)
    output_df['주문자 핸드폰'] = phone
    
    # 18. 추가 상품 여부
    output_df['추가 상품 여부'] = ['추가상품'] * n_rows
    
    # 19. 택배 운임 지불 방식
    output_df['택배 운임 지불 방식'] = ['신용'] * n_rows
    
    # 20. 쇼핑몰 주문 라인번호 (1부터 시작하는 순번)
    output_df['쇼핑몰 주문 라인번호'] = list(range(1, n_rows + 1))
    
    # 21. 결제금액 (공란)
    output_df['결제금액'] = [''] * n_rows
    
    # 22. 고객 참조번호 (공란)
    output_df['고객 참조번호'] = [''] * n_rows
    
    # 23. 요청(희망)배송 일자 (오늘 날짜)
    output_df['요청(희망)배송 일자'] = [today] * n_rows
    
    # 24. 쇼핑몰 주문번호
    output_df['쇼핑몰 주문번호'] = result_df['주문번호']
    
    # 25. 수취인 명
    output_df['수취인 명'] = recipient_name
    
    # 26. 수취인 핸드폰
    output_df['수취인 핸드폰'] = phone
    
    # 27. 수취인 기본 주소
    address = None
    for col in ['주소', '배송주소', '주문자주소', '받는분.통합주소', '수취인 주소']:
        if col in result_df.columns:
            address = result_df[col]
            break
    output_df['수취인 기본 주소'] = address
    
    # 28. 쇼핑몰 상품 코드 (매칭 결과에서)
    output_df['쇼핑몰 상품 코드'] = match_df['쇼핑몰 상품 코드']
    
    # 29. 쇼핑몰 상품 이름 (매칭 결과에서)
    output_df['쇼핑몰 상품 이름'] = match_df['쇼핑몰 상품 이름']
    
    # 30. 쇼핑몰 옵션 이름 (매칭 결과에서)
    output_df['쇼핑몰 옵션 이름'] = match_df['쇼핑몰 옵션 이름']
    
    # 31. 주문 수량
    if platform == 'app':
        # 앱의 경우 항상 1
        output_df['주문 수량'] = [1] * n_rows
    else:
        quantity = None
        for col in ['수량', '구매수(수량)']:
            if col in result_df.columns:
                quantity = result_df[col]
                break
        output_df['주문 수량'] = quantity
    
    # 32. 배송 메세지
    if platform == 'app':
        # 앱의 경우 항상 '벨x, 문자'
        output_df['배송 메세지'] = ['벨x, 문자'] * n_rows
    else:
        message = None
        for col in ['비고', '배송메세지', '요청사항', '배송메세지']:
            if col in result_df.columns:
                message = result_df[col]
                break
        output_df['배송 메세지'] = message
    
    # 매칭 정보 추가 (디버깅용)
    output_df['매칭 방법'] = match_df['매칭 방법']
    output_df['확인 필요'] = match_df['확인 필요']
    
    # 주문번호 중복 제거 (접미사 자동 추가)
    output_df = ensure_unique_order_numbers(output_df, order_col='쇼핑몰 주문번호')
    
    # 쇼핑몰 묶음 배송 번호를 쇼핑몰 주문번호와 동일하게 업데이트
    output_df['쇼핑몰 묶음 배송 번호'] = output_df['쇼핑몰 주문번호']
    
    return output_df


def read_file(uploaded_file, password=None):
    """파일을 읽어서 DataFrame으로 반환 (CSV, Excel 지원)
    
    Args:
        uploaded_file: Streamlit UploadedFile 객체
        password: 엑셀 파일 암호 (선택사항)
    """
    try:
        file_extension = uploaded_file.name.lower().split('.')[-1]
        
        if file_extension == 'csv':
            # CSV 파일의 경우 인코딩 자동 감지
            file_bytes = uploaded_file.read()
            encoding = detect_encoding(file_bytes)
            
            # 앱 파일 특수 처리 (컬럼명 깨짐 방지 + 복수 상품 분리)
            if '앱' in uploaded_file.name:
                app_columns = ['주문번호', '상태', '주문상품', '입금액', '크레딧', '쿠폰', '구독상태',
                             '받는분.이름', '받는분.전화번호', '받는분.우편번호', '받는분.통합주소',
                             '받는분.주소', '받는분.상세주소', '사용자.ID', '사용자.닉네임',
                             '사용자.실명', '사용자.전화번호', '사용자.이메일']
                try:
                    # UTF-8로 디코딩 시도
                    try:
                        decoded = file_bytes.decode('utf-8')
                    except UnicodeDecodeError:
                        # UTF-8 실패 시 CP949 시도
                        decoded = file_bytes.decode('cp949', errors='replace')
                    
                    df = pd.read_csv(io.StringIO(decoded))
                    
                    # 컬럼명이 깨진 경우 수동 설정
                    if len(df.columns) == len(app_columns):
                        if not all(col in df.columns for col in ['주문번호', '주문상품', '받는분.이름']):
                            df.columns = app_columns
                    
                    # 복수 상품 주문 분리 (주문번호에 알파벳 접미사 추가)
                    expanded_rows = []
                    for idx, row in df.iterrows():
                        product_str = row['주문상품']
                        products = split_app_products(product_str)
                        
                        if len(products) == 1:
                            # 단일 상품 - 주문번호 그대로
                            expanded_rows.append(row)
                        else:
                            # 복수 상품 - 각각 별도 행으로 + 주문번호에 알파벳 접미사
                            original_order_no = row['주문번호']
                            for i, product in enumerate(products):
                                new_row = row.copy()
                                new_row['주문상품'] = product
                                # 모든 상품에 접미사 추가 (중복 방지)
                                # 첫 번째: 원본 유지, 두 번째: a, 세 번째: b...
                                if i > 0:
                                    suffix = chr(ord('a') + i - 1)  # a, b, c, d...
                                    new_row['주문번호'] = f"{original_order_no}{suffix}"
                                expanded_rows.append(new_row)
                    
                    df = pd.DataFrame(expanded_rows).reset_index(drop=True)
                    st.success(f"✅ {uploaded_file.name} - 앱 파일 처리 완료 (총 {len(df)}개 행)")
                    return df
                except Exception as e:
                    st.error(f"❌ 앱 파일 읽기 실패: {str(e)}")
                    return None
            
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
                        
                        # 방법 1: 사용자가 제공한 비밀번호
                        if password:
                            try:
                                office_file.load_key(password=password)
                                office_file.decrypt(decrypted)
                                decryption_success = True
                                st.success(f"🔓 제공된 암호로 파일 복호화 성공")
                            except Exception as pwd_err:
                                st.warning(f"⚠️ 제공된 암호로 복호화 실패: {str(pwd_err)}")
                        
                        # 방법 2: 빈 비밀번호
                        if not decryption_success:
                            try:
                                file_stream.seek(0)
                                office_file = msoffcrypto.OfficeFile(file_stream)
                                decrypted = io.BytesIO()
                                office_file.load_key(password='')
                                office_file.decrypt(decrypted)
                                decryption_success = True
                            except:
                                pass
                        
                        # 방법 3: VelvetSweatshop 알고리즘
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
                            error_msg = "복호화 실패: 올바른 비밀번호를 입력해주세요" if password else "복호화 실패: 비밀번호가 필요합니다"
                            raise Exception(error_msg)
                        
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
    st.title("📦 물류 데이터 통합 시스템 v3.1")
    st.markdown("**플랫폼별 파일 업로드**: 카페24, 앱, 쿠팡, 네이버를 명확히 구분!")
    st.markdown("---")
    
    # 사이드바 - 마스터 파일 업로드
    with st.sidebar:
        st.header("⚙️ 마스터 코드 업로드")
        
        master_file = st.file_uploader(
            "📁 물류_코드명.xlsx 파일 업로드",
            type=['xlsx', 'xls'],
            help="판매 상품 코드 매칭을 위한 마스터 데이터",
            key="master_file"
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
                    st.metric(platform, f"{count}개 상품")
        else:
            master_df = st.session_state.get('master_df', None)
        
        st.markdown("---")
        st.info("💡 **사용 방법**\n\n1. 마스터 코드 업로드\n2. 플랫폼별 파일 업로드\n3. 자동 매칭 확인\n4. 통합 파일 다운로드")
    
    # 메인 영역 - 플랫폼별 파일 업로더
    st.header("1️⃣ 플랫폼별 파일 업로드")
    
    # 플랫폼별 탭 생성
    tab1, tab2, tab3, tab4 = st.tabs(["📦 카페24", "📱 앱", "🛒 쿠팡", "🟢 네이버"])
    
    uploaded_files_map = {}
    
    with tab1:
        st.subheader("카페24 주문 파일")
        st.subheader("카페24 주문 파일")
        cafe24_files = st.file_uploader(
            "카페24 CSV 파일을 업로드하세요",
            type=['csv', 'xlsx', 'xls'],
            accept_multiple_files=True,
            key="cafe24_files"
        )
        if cafe24_files:
            uploaded_files_map['cafe24'] = cafe24_files
            st.success(f"✅ {len(cafe24_files)}개 파일 업로드됨")
    
    with tab2:
        st.subheader("앱 주문 파일")
        app_files = st.file_uploader(
            "앱 CSV 파일을 업로드하세요",
            type=['csv', 'xlsx', 'xls'],
            accept_multiple_files=True,
            key="app_files"
        )
        if app_files:
            uploaded_files_map['app'] = app_files
            st.success(f"✅ {len(app_files)}개 파일 업로드됨")
    
    with tab3:
        st.subheader("쿠팡 주문 파일")
        coupang_files = st.file_uploader(
            "쿠팡 XLSX/CSV 파일을 업로드하세요",
            type=['csv', 'xlsx', 'xls'],
            accept_multiple_files=True,
            key="coupang_files"
        )
        if coupang_files:
            uploaded_files_map['coupang'] = coupang_files
            st.success(f"✅ {len(coupang_files)}개 파일 업로드됨")
    
    with tab4:
        st.subheader("네이버 주문 파일")
        
        # 네이버 파일 암호 입력 필드
        naver_password = st.text_input(
            "🔐 파일 암호 (암호로 보호된 엑셀 파일인 경우)",
            type="password",
            key="naver_password_input",  # 위젯용 키
            help="암호로 보호된 엑셀 파일의 경우 암호를 입력하세요. 암호가 없으면 비워두세요."
        )
        
        naver_files = st.file_uploader(
            "네이버 CSV/XLSX 파일을 업로드하세요",
            type=['csv', 'xlsx', 'xls'],
            accept_multiple_files=True,
            key="naver_files"
        )
        if naver_files:
            uploaded_files_map['naver'] = naver_files
            # 네이버 파일 비밀번호를 다른 키로 저장 (위젯 키와 분리)
            st.session_state['naver_file_password'] = naver_password if naver_password else None
            st.success(f"✅ {len(naver_files)}개 파일 업로드됨")
            if naver_password:
                st.info(f"🔐 파일 암호가 설정되었습니다")
    
    # 업로드된 파일이 있는지 확인
    if not uploaded_files_map:
        st.info("👆 위 탭에서 플랫폼별 파일을 업로드해주세요")
        return
    
    # 마스터 파일 확인
    master_df = st.session_state.get('master_df', None)
    if master_df is None:
        st.error("❌ 사이드바에서 마스터 코드 파일을 먼저 업로드해주세요!")
        return
    
    # 파일 처리
    st.markdown("---")
    st.header("2️⃣ 파일 처리 및 매칭")
    
    processed_dfs = []
    file_info = []
    
    with st.spinner("모든 플랫폼 파일을 처리하는 중..."):
        for platform, files in uploaded_files_map.items():
            for uploaded_file in files:
                # 네이버 파일인 경우 비밀번호 전달
                if platform == 'naver':
                    naver_password = st.session_state.get('naver_file_password', None)
                    df = read_file(uploaded_file, password=naver_password)
                else:
                    df = read_file(uploaded_file)
                
                if df is not None:
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
        
        # 전체 통합 데이터에 대해 쇼핑몰 주문 라인번호 재할당 (1부터 시작, 중복 없음)
        merged_df['쇼핑몰 주문 라인번호'] = list(range(1, len(merged_df) + 1))
        
        # 모든 컬럼을 문자열로 변환 (Arrow 변환 오류 방지)
        for col in merged_df.columns:
            # 쇼핑몰 주문 라인번호는 정수형 유지
            if col == '쇼핑몰 주문 라인번호':
                continue
            
            # 먼저 문자열로 변환
            merged_df[col] = merged_df[col].astype(str)
            # 'nan' 문자열을 빈 문자열로 변환 (쇼핑몰 코드 등 고정값 제외)
            if col not in ['쇼핑몰 코드', '묶음배송유무', '수취인 상세 주소', '주문자 이메일', '수취인 주소 유형', '추가 상품 여부', '택배 운임 지불 방식']:
                merged_df[col] = merged_df[col].replace('nan', '')
            # 'None' 문자열을 빈 문자열로 변환
            merged_df[col] = merged_df[col].replace('None', '')
        
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
            platforms = merged_df['쇼핑몰 이름'].nunique()
            st.metric("처리 플랫폼", f"{platforms}개")
        
        # 플랫폼별 통계
        st.subheader("📊 플랫폼별 통계")
        platform_stats = merged_df.groupby('쇼핑몰 이름').agg({
            '쇼핑몰 주문번호': 'count',
            '확인 필요': 'sum'
        }).rename(columns={'쇼핑몰 주문번호': '주문 수', '확인 필요': '확인 필요 항목'})
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
            need_check = merged_df[merged_df['확인 필요'] == 'True']
            if not need_check.empty:
                st.warning(f"⚠️ {len(need_check)}개 항목 확인 필요")
                with st.expander("확인 필요 항목 보기"):
                    st.dataframe(need_check[['쇼핑몰 이름', '쇼핑몰 주문번호', '쇼핑몰 상품 이름', '매칭 방법']], use_container_width=True)
            else:
                st.success("✅ 모든 항목이 정확히 매칭되었습니다!")
        
        # 데이터 미리보기
        st.markdown("---")
        st.header("4️⃣ 데이터 미리보기")
        
        # 필터 옵션
        show_only_need_check = st.checkbox("확인 필요 항목만 보기")
        
        if show_only_need_check:
            display_df = merged_df[merged_df['확인 필요'] == 'True']
            st.info(f"📋 확인 필요 항목: {len(display_df)}건")
        else:
            display_df = merged_df
            st.info(f"📋 전체 데이터: {len(display_df)}건")
        
        st.dataframe(display_df, use_container_width=True)
        
        # 다운로드 버튼
        st.markdown("---")
        st.header("5️⃣ 파일 다운로드")
        
        today = datetime.now().strftime("%Y%m%d")
        filename = f"{today}_통합3PL배송업무.xlsx"
        
        excel_file = create_excel_file(merged_df)
        
        st.download_button(
            label="📥 통합 파일 다운로드",
            data=excel_file,
            file_name=filename,
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        
        st.success(f"✅ {filename} 파일이 준비되었습니다!")
        
        if need_confirm > 0:
            st.warning(f"⚠️ 다운로드한 파일에서 '확인 필요' 컬럼이 True인 {need_confirm}개 항목을 수동으로 확인해주세요.")
    
    else:
        st.error("❌ 처리된 데이터가 없습니다. 파일 형식을 확인해주세요.")
    
    # 푸터
    st.markdown("---")
    st.caption("물류 데이터 통합 시스템 v3.1 | 플랫폼별 명확한 파일 업로드")


if __name__ == "__main__":
    main()
