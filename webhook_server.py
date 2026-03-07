"""
Flask Webhook Server for Google Sheets Integration (Service Account 인증)
Google Sheets 변경사항을 받아서 DB에 저장하는 웹훅 서버
Secret token 검증 포함
"""
from flask import Flask, request, jsonify
import sqlite3
import logging
from datetime import datetime
import os
import json

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# DB 경로
DB_PATH = '/home/user/webapp/master_codes.db'

# Secret token (환경변수 또는 secrets.toml에서 로드)
WEBHOOK_SECRET = os.getenv('WEBHOOK_SECRET', None)

def init_db():
    """데이터베이스 초기화"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS master_codes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sheet_data TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            source TEXT DEFAULT 'google_sheets'
        )
    ''')
    conn.commit()
    conn.close()
    logger.info("Database initialized")

def load_secret_token():
    """
    Secret token을 로드 (Streamlit secrets 또는 환경변수)
    """
    global WEBHOOK_SECRET
    
    # 환경변수에서 먼저 확인
    if WEBHOOK_SECRET:
        logger.info("Using WEBHOOK_SECRET from environment variable")
        return WEBHOOK_SECRET
    
    # Streamlit secrets에서 로드 시도
    try:
        import streamlit as st
        if 'webhook_secret' in st.secrets:
            WEBHOOK_SECRET = st.secrets['webhook_secret']
            logger.info("Using WEBHOOK_SECRET from Streamlit secrets")
            return WEBHOOK_SECRET
    except Exception as e:
        logger.warning(f"Could not load secret from Streamlit secrets: {str(e)}")
    
    # .streamlit/secrets.toml 파일 직접 읽기
    try:
        import toml
        secrets_path = '/home/user/webapp/.streamlit/secrets.toml'
        if os.path.exists(secrets_path):
            with open(secrets_path, 'r') as f:
                secrets = toml.load(f)
                if 'webhook_secret' in secrets:
                    WEBHOOK_SECRET = secrets['webhook_secret']
                    logger.info("Using WEBHOOK_SECRET from secrets.toml file")
                    return WEBHOOK_SECRET
    except Exception as e:
        logger.warning(f"Could not load secret from secrets.toml: {str(e)}")
    
    logger.warning("⚠️ WEBHOOK_SECRET not found - webhook endpoint will be UNPROTECTED!")
    return None

def verify_token(request_data):
    """
    Webhook 요청의 token 검증
    Args:
        request_data: 요청 JSON 데이터
    Returns: True if valid, False otherwise
    """
    if not WEBHOOK_SECRET:
        logger.warning("WEBHOOK_SECRET not set - skipping token verification")
        return True  # Secret이 설정되지 않았으면 일단 통과 (개발용)
    
    request_token = request_data.get('token')
    
    if not request_token:
        logger.warning("No token provided in webhook request")
        return False
    
    if request_token != WEBHOOK_SECRET:
        logger.warning("Invalid token provided in webhook request")
        return False
    
    return True

def save_master_code(sheet_data, source='webhook'):
    """마스터 코드를 DB에 저장"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # 기존 데이터 삭제 (최신 1개만 유지)
    cursor.execute('DELETE FROM master_codes')
    
    # 새 데이터 저장
    updated_at = datetime.now().isoformat()
    
    # sheet_data가 문자열이 아니면 JSON으로 변환
    if isinstance(sheet_data, (list, dict)):
        sheet_data = json.dumps(sheet_data, ensure_ascii=False)
    
    cursor.execute(
        'INSERT INTO master_codes (sheet_data, updated_at, source) VALUES (?, ?, ?)',
        (sheet_data, updated_at, source)
    )
    
    conn.commit()
    conn.close()
    logger.info(f"Master code saved: {len(sheet_data)} bytes from {source}")
    return updated_at

@app.route('/webhook', methods=['POST'])
def webhook():
    """
    Google Apps Script에서 호출하는 웹훅 엔드포인트
    
    Expected JSON payload:
    {
        "sheet_data": [...],  // 전체 시트 데이터 (B~F열)
        "token": "secret_token",  // 인증 토큰
        "timestamp": "2026-03-07T10:00:00",  // 변경 시간 (선택사항)
        "sheet_name": "시트1"  // 시트 이름 (선택사항)
    }
    """
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'No JSON data provided'}), 400
        
        logger.info(f"Webhook received: {len(str(data))} bytes")
        
        # Token 검증
        if not verify_token(data):
            return jsonify({'error': 'Invalid or missing token'}), 401
        
        # sheet_data 확인
        if 'sheet_data' not in data:
            return jsonify({'error': 'Missing sheet_data'}), 400
        
        sheet_data = data['sheet_data']
        
        # DB에 저장
        updated_at = save_master_code(sheet_data, source='webhook')
        
        logger.info(f"✅ Master code updated via webhook at {updated_at}")
        
        return jsonify({
            'status': 'success',
            'message': 'Master code updated',
            'updated_at': updated_at
        }), 200
        
    except Exception as e:
        logger.error(f"Webhook error: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/health', methods=['GET'])
def health():
    """헬스체크 엔드포인트"""
    return jsonify({
        'status': 'ok',
        'service': 'webhook_server',
        'token_configured': WEBHOOK_SECRET is not None
    }), 200

def run_server(port=5000):
    """Flask 서버 실행"""
    init_db()
    load_secret_token()
    
    if not WEBHOOK_SECRET:
        logger.warning("⚠️⚠️⚠️ WEBHOOK_SECRET NOT SET - ENDPOINT IS UNPROTECTED! ⚠️⚠️⚠️")
    
    logger.info(f"Starting webhook server on port {port}")
    app.run(host='0.0.0.0', port=port, debug=False, use_reloader=False)

if __name__ == '__main__':
    run_server()
