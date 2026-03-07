"""
Google Sheets Integration Utilities (Service Account 인증)
Google Sheets에서 마스터 코드를 가져오고 DB에 저장/조회하는 유틸리티
"""
import pandas as pd
import sqlite3
import json
from datetime import datetime
import logging
import streamlit as st
import gspread
from google.oauth2.service_account import Credentials

logger = logging.getLogger(__name__)

# Google Sheets 설정
SHEET_ID = '1e7T7dANrJemFP1eouH02Wi4Ysoh08jmq77Rn_5pbzQs'
GID = '1735735926'  # Sheet의 gid
SHEET_NAME = None  # gid로 접근하므로 이름은 불필요

DB_PATH = '/home/user/webapp/master_codes.db'

# Google Sheets API 스코프
SCOPES = [
    'https://www.googleapis.com/auth/spreadsheets.readonly',
    'https://www.googleapis.com/auth/drive.readonly'
]

def get_gspread_client():
    """
    Service Account 인증으로 gspread 클라이언트 생성
    Returns: gspread.Client 또는 None
    """
    try:
        # Streamlit secrets에서 Service Account 정보 가져오기
        if 'gcp_service_account' not in st.secrets:
            logger.error("Service Account credentials not found in st.secrets")
            return None
        
        # Service Account 인증 정보
        service_account_info = dict(st.secrets['gcp_service_account'])
        
        # Credentials 생성
        credentials = Credentials.from_service_account_info(
            service_account_info,
            scopes=SCOPES
        )
        
        # gspread 클라이언트 생성
        client = gspread.authorize(credentials)
        logger.info("Successfully created gspread client with Service Account")
        return client
        
    except Exception as e:
        logger.error(f"Failed to create gspread client: {str(e)}")
        return None

def fetch_master_from_sheets():
    """
    Google Sheets에서 마스터 코드 데이터를 가져옴 (Service Account 인증)
    B열~F열 전체 데이터를 읽음
    Returns: pandas DataFrame 또는 None
    """
    try:
        logger.info(f"Fetching master code from Google Sheets: {SHEET_ID}")
        
        # gspread 클라이언트 생성
        client = get_gspread_client()
        if client is None:
            logger.error("Failed to get gspread client")
            return None
        
        # Spreadsheet 열기
        spreadsheet = client.open_by_key(SHEET_ID)
        
        # gid로 워크시트 찾기
        worksheet = None
        for sheet in spreadsheet.worksheets():
            if str(sheet.id) == str(GID):
                worksheet = sheet
                break
        
        if worksheet is None:
            logger.error(f"Worksheet with gid {GID} not found")
            return None
        
        logger.info(f"Found worksheet: {worksheet.title} (gid: {GID})")
        
        # 모든 데이터 가져오기
        all_values = worksheet.get_all_values()
        
        if not all_values:
            logger.warning("No data found in worksheet")
            return None
        
        # DataFrame으로 변환 (첫 행을 헤더로 사용)
        df = pd.DataFrame(all_values[1:], columns=all_values[0])
        
        # B열~F열만 선택 (열 이름으로)
        # 실제 열 이름을 확인하여 필요한 열만 선택
        logger.info(f"Available columns: {df.columns.tolist()}")
        
        # B열~F열은 인덱스 1~5 (0부터 시작)
        # 또는 열 이름이 있다면 해당 이름으로 선택
        # 여기서는 모든 열을 가져온 후 필요한 처리를 app.py에서 수행
        
        logger.info(f"Successfully fetched {len(df)} rows from Google Sheets")
        return df
        
    except Exception as e:
        logger.error(f"Failed to fetch from Google Sheets: {str(e)}")
        return None

def save_master_to_db(df, source='google_sheets'):
    """
    마스터 코드 DataFrame을 DB에 저장
    Args:
        df: pandas DataFrame
        source: 데이터 출처 ('google_sheets', 'manual', 'file_upload', 'webhook')
    Returns: updated_at timestamp
    """
    try:
        # DataFrame을 JSON으로 변환
        sheet_data = df.to_json(orient='records', force_ascii=False)
        
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # 기존 데이터 삭제 (최신 1개만 유지)
        cursor.execute('DELETE FROM master_codes')
        
        # 새 데이터 저장
        updated_at = datetime.now().isoformat()
        cursor.execute(
            'INSERT INTO master_codes (sheet_data, updated_at, source) VALUES (?, ?, ?)',
            (sheet_data, updated_at, source)
        )
        
        conn.commit()
        conn.close()
        
        logger.info(f"Master code saved to DB: {len(df)} rows from {source}")
        return updated_at
        
    except Exception as e:
        logger.error(f"Failed to save master code to DB: {str(e)}")
        return None

def load_master_from_db():
    """
    DB에서 마스터 코드를 불러옴
    Returns: (DataFrame, updated_at, source) 또는 (None, None, None)
    """
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute('SELECT sheet_data, updated_at, source FROM master_codes ORDER BY id DESC LIMIT 1')
        row = cursor.fetchone()
        conn.close()
        
        if row:
            sheet_data, updated_at, source = row
            df = pd.read_json(sheet_data, orient='records')
            logger.info(f"Master code loaded from DB: {len(df)} rows, updated at {updated_at}")
            return df, updated_at, source
        else:
            logger.info("No master code found in DB")
            return None, None, None
            
    except Exception as e:
        logger.error(f"Failed to load master code from DB: {str(e)}")
        return None, None, None

def init_master_code():
    """
    앱 최초 실행 시 Google Sheets에서 마스터 코드를 가져와서 DB에 저장
    Returns: (DataFrame, updated_at, source) 또는 (None, None, None)
    """
    # 먼저 DB에 데이터가 있는지 확인
    df_db, updated_at, source = load_master_from_db()
    if df_db is not None:
        logger.info(f"Master code already exists in DB (source: {source}, updated: {updated_at})")
        return df_db, updated_at, source
    
    # DB에 없으면 Google Sheets에서 가져오기
    logger.info("No master code in DB, fetching from Google Sheets...")
    df_sheets = fetch_master_from_sheets()
    
    if df_sheets is not None:
        updated_at = save_master_to_db(df_sheets, source='google_sheets')
        if updated_at:
            return df_sheets, updated_at, 'google_sheets'
    
    return None, None, None

def refresh_master_code():
    """
    수동으로 Google Sheets에서 최신 데이터를 가져와 DB를 갱신
    Returns: (DataFrame, updated_at) 또는 (None, None)
    """
    df = fetch_master_from_sheets()
    if df is not None:
        updated_at = save_master_to_db(df, source='manual_refresh')
        return df, updated_at
    return None, None
