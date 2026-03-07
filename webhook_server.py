"""
Flask Webhook Server for Google Sheets Integration
Google Sheets 변경사항을 받아서 DB에 저장하는 웹훅 서버
"""
from flask import Flask, request, jsonify
import sqlite3
import logging
from datetime import datetime
import os

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# DB 경로
DB_PATH = '/home/user/webapp/master_codes.db'

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

def save_master_code(sheet_data, source='google_sheets'):
    """마스터 코드를 DB에 저장"""
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
    logger.info(f"Master code saved: {len(sheet_data)} bytes from {source}")
    return updated_at

@app.route('/webhook', methods=['POST'])
def webhook():
    """Google Apps Script에서 호출하는 웹훅 엔드포인트"""
    try:
        data = request.get_json()
        logger.info(f"Webhook received: {data}")
        
        if not data or 'sheet_data' not in data:
            return jsonify({'error': 'Missing sheet_data'}), 400
        
        sheet_data = data['sheet_data']
        updated_at = save_master_code(sheet_data)
        
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
    return jsonify({'status': 'ok', 'service': 'webhook_server'}), 200

def run_server(port=5000):
    """Flask 서버 실행"""
    init_db()
    logger.info(f"Starting webhook server on port {port}")
    app.run(host='0.0.0.0', port=port, debug=False, use_reloader=False)

if __name__ == '__main__':
    run_server()
