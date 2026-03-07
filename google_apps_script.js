/**
 * Google Apps Script - Streamlit Webhook Integration
 * 
 * 설치 방법:
 * 1. Google Sheets 열기
 * 2. 확장 프로그램 > Apps Script
 * 3. 아래 코드 붙여넣기
 * 4. WEBHOOK_URL 수정 (실제 Streamlit 앱 URL + /webhook)
 * 5. 저장 후 onEdit 트리거 설정
 */

// ===== 설정 =====
// Streamlit 앱의 Webhook URL (포트 5000)
// 예: https://your-streamlit-app-url.com:5000/webhook
const WEBHOOK_URL = 'https://5000-SANDBOX_ID.sandbox.novita.ai/webhook';

// 감지할 열 범위 (B열~F열 = 2~6)
const WATCH_COL_START = 2; // B열
const WATCH_COL_END = 6;   // F열

// 대상 시트 이름 (비워두면 모든 시트)
const TARGET_SHEET_NAME = '';

/**
 * onEdit 트리거 함수
 * B열~F열에 변경이 생기면 자동으로 실행됨
 */
function onEdit(e) {
  try {
    // 변경 정보 가져오기
    const range = e.range;
    const sheet = range.getSheet();
    const col = range.getColumn();
    const row = range.getRow();
    
    // 로그 출력
    Logger.log('편집 감지: 시트=' + sheet.getName() + ', 행=' + row + ', 열=' + col);
    
    // 대상 시트가 지정되어 있고, 다른 시트면 무시
    if (TARGET_SHEET_NAME && sheet.getName() !== TARGET_SHEET_NAME) {
      Logger.log('대상 시트가 아님: ' + sheet.getName());
      return;
    }
    
    // B열~F열 범위 확인
    if (col < WATCH_COL_START || col > WATCH_COL_END) {
      Logger.log('감지 대상 열이 아님: 열=' + col);
      return;
    }
    
    Logger.log('✅ B열~F열 변경 감지! Webhook 호출 시작...');
    
    // 전체 시트 데이터를 가져와서 전송
    sendSheetDataToWebhook(sheet);
    
  } catch (error) {
    Logger.log('❌ onEdit 오류: ' + error.toString());
  }
}

/**
 * 시트 데이터를 Webhook으로 전송
 */
function sendSheetDataToWebhook(sheet) {
  try {
    // 전체 데이터 가져오기
    const dataRange = sheet.getDataRange();
    const values = dataRange.getValues();
    
    // 헤더와 데이터 분리
    const headers = values[0];
    const rows = values.slice(1);
    
    // JSON 배열로 변환
    const jsonData = rows.map(row => {
      const obj = {};
      headers.forEach((header, index) => {
        obj[header] = row[index];
      });
      return obj;
    });
    
    // JSON 문자열로 변환
    const sheetData = JSON.stringify(jsonData);
    
    // Webhook 요청 보내기
    const options = {
      method: 'post',
      contentType: 'application/json',
      payload: JSON.stringify({
        sheet_data: sheetData,
        sheet_name: sheet.getName(),
        timestamp: new Date().toISOString()
      }),
      muteHttpExceptions: true
    };
    
    Logger.log('Webhook 요청 시작: ' + WEBHOOK_URL);
    Logger.log('전송 데이터 크기: ' + sheetData.length + ' bytes');
    
    const response = UrlFetchApp.fetch(WEBHOOK_URL, options);
    const responseCode = response.getResponseCode();
    const responseBody = response.getContentText();
    
    if (responseCode === 200) {
      Logger.log('✅ Webhook 성공: ' + responseBody);
      
      // 성공 알림 (선택사항)
      // SpreadsheetApp.getActiveSpreadsheet().toast(
      //   '마스터 코드가 업데이트되었습니다',
      //   '✅ 성공',
      //   3
      // );
    } else {
      Logger.log('❌ Webhook 실패: HTTP ' + responseCode);
      Logger.log('응답: ' + responseBody);
    }
    
  } catch (error) {
    Logger.log('❌ Webhook 전송 오류: ' + error.toString());
    
    // 오류 알림 (선택사항)
    // SpreadsheetApp.getActiveSpreadsheet().toast(
    //   '마스터 코드 업데이트 실패: ' + error.toString(),
    //   '❌ 오류',
    //   5
    // );
  }
}

/**
 * 수동 테스트 함수
 * Apps Script 편집기에서 실행 > testWebhook 선택하여 수동 테스트 가능
 */
function testWebhook() {
  Logger.log('=== 수동 Webhook 테스트 시작 ===');
  
  const sheet = SpreadsheetApp.getActiveSheet();
  sendSheetDataToWebhook(sheet);
  
  Logger.log('=== 테스트 완료 ===');
  Logger.log('로그를 확인하세요: 보기 > 로그');
}

/**
 * 트리거 설정 함수
 * 처음 한 번만 실행하여 onEdit 트리거 자동 설정
 */
function setupTrigger() {
  // 기존 트리거 삭제
  const triggers = ScriptApp.getProjectTriggers();
  triggers.forEach(trigger => {
    if (trigger.getHandlerFunction() === 'onEdit') {
      ScriptApp.deleteTrigger(trigger);
    }
  });
  
  // 새 트리거 생성
  ScriptApp.newTrigger('onEdit')
    .forSpreadsheet(SpreadsheetApp.getActive())
    .onEdit()
    .create();
  
  Logger.log('✅ onEdit 트리거가 설정되었습니다');
  SpreadsheetApp.getActiveSpreadsheet().toast(
    'B열~F열 변경 감지 트리거가 활성화되었습니다',
    '✅ 설정 완료',
    3
  );
}
