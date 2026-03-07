"""
Google Sheets Integration Utilities (CSV Export 방식)
Google Sheets에서 마스터 코드를 가져오고 DB에 저장/조회하는 유틸리티
"""
import pandas as pd
import requests
import sqlite3
import json
from datetime import datetime
import logging
from urllib.parse import quote

logger = logging.getLogger(__name__)

# Google Sheets 설정 (공개 링크 - 뷰어 접근 가능)
SHEET_ID = '1e7T7dANrJemFP1eouH02Wi4Ysoh08jmq77Rn_5pbzQs'
SHEET_NAME = '상품 코드 최종(마스터 코드)'  # 한글/괄호 포함 - URL 인코딩 필요

# CSV Export URL 생성 (sheet 파라미터 사용)
SHEET_NAME_ENCODED = quote(SHEET_NAME)
CSV_EXPORT_URL = f'https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&sheet={SHEET_NAME_ENCODED}'

DB_PATH = '/home/user/webapp/master_codes.db'

def fetch_master_from_sheets():
    """
    Google Sheets에서 마스터 코드 데이터를 가져옴 (CSV Export 방식)
    공개 링크 - 뷰어 접근 가능, 인증 불필요
    
    Returns: pandas DataFrame 또는 None
    """
    try:
        logger.info(f"Fetching master code from Google Sheets: {CSV_EXPORT_URL}")
        
        # CSV로 다운로드 (인증 불필요)
        response = requests.get(CSV_EXPORT_URL, timeout=10)
        response.raise_for_status()
        
        # DataFrame으로 변환
        from io import StringIO
        df = pd.read_csv(StringIO(response.text))
        
        logger.info(f"Successfully fetched {len(df)} rows from Google Sheets")
        logger.info(f"Columns: {df.columns.tolist()}")
        
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
