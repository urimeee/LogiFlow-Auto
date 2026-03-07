/**
 * Google Apps Script - Sheets B~F열 변경 감지 및 Webhook 전송
 * (공개 링크 버전 - 인증 불필요)
 * 
 * 설치 방법:
 * 1. Google Sheets 열기 → Extensions → Apps Script
 * 2. 이 코드를 붙여넣기
 * 3. WEBHOOK_URL 설정 (Streamlit 앱 URL)
 * 4. setupTrigger() 실행하여 onEdit 트리거 등록
 */

// ===== 설정 =====

// Streamlit 웹훅 URL (SANDBOX_ID를 실제 값으로 변경하세요!)
const WEBHOOK_URL = 'https://5000-ip2l928h0vug305w91va9-d0b9e1e2.sandbox.novita.ai/webhook';

// 감지할 열 범위 (B~F열)
const WATCH_COLUMN_START = 2;  // B열 = 2
const WATCH_COLUMN_END = 6;    // F열 = 6

// 대상 시트 이름 (선택사항 - 지정하지 않으면 모든 시트 감지)
const TARGET_SHEET_NAME = '상품 코드 최종(마스터 코드)';

// ===== 메인 함수 =====

/**
 * onEdit 트리거 함수
 * Sheets의 B~F열이 변경되면 자동 실행
 */
function onEdit(e) {
  try {
    // 이벤트 객체가 없으면 종료
    if (!e) {
      Logger.log('No edit event received');
      return;
    }
    
    const sheet = e.source.getActiveSheet();
    const range = e.range;
    const column = range.getColumn();
    const row = range.getRow();
    
    Logger.log(`Edit detected: Sheet="${sheet.getName()}", Row=${row}, Column=${column}`);
    
    // B~F열 범위 확인
    if (column < WATCH_COLUMN_START || column > WATCH_COLUMN_END) {
      Logger.log(`Column ${column} is outside watch range (${WATCH_COLUMN_START}-${WATCH_COLUMN_END})`);
      return;
    }
    
    // 대상 시트 이름 확인 (선택사항)
    if (TARGET_SHEET_NAME && sheet.getName() !== TARGET_SHEET_NAME) {
      Logger.log(`Sheet "${sheet.getName()}" does not match target "${TARGET_SHEET_NAME}"`);
      return;
    }
    
    Logger.log(`✅ Change detected in watched columns (${WATCH_COLUMN_START}-${WATCH_COLUMN_END})`);
    
    // 전체 시트 데이터를 웹훅으로 전송
    sendSheetDataToWebhook(sheet);
    
  } catch (error) {
    Logger.log(`Error in onEdit: ${error.message}`);
    Logger.log(error.stack);
  }
}

/**
 * 전체 시트 데이터를 Streamlit 웹훅으로 전송
 * @param {Sheet} sheet - 데이터를 읽을 시트
 */
function sendSheetDataToWebhook(sheet) {
  try {
    Logger.log('Reading sheet data...');
    
    // 전체 데이터 읽기 (헤더 포함)
    const dataRange = sheet.getDataRange();
    const values = dataRange.getValues();
    
    if (values.length === 0) {
      Logger.log('No data in sheet');
      return;
    }
    
    // 헤더와 데이터 분리
    const headers = values[0];
    const dataRows = values.slice(1);
    
    // JSON 배열로 변환 (헤더를 키로 사용)
    const sheetData = dataRows.map(row => {
      const rowObj = {};
      headers.forEach((header, index) => {
        rowObj[header] = row[index];
      });
      return rowObj;
    });
    
    Logger.log(`Prepared ${sheetData.length} rows for webhook`);
    
    // Webhook 페이로드 (인증 불필요)
    const payload = {
      sheet_data: sheetData,
      timestamp: new Date().toISOString(),
      sheet_name: sheet.getName()
    };
    
    // HTTP POST 요청
    const options = {
      method: 'post',
      contentType: 'application/json',
      payload: JSON.stringify(payload),
      muteHttpExceptions: true
    };
    
    Logger.log(`Sending webhook to ${WEBHOOK_URL}...`);
    const response = UrlFetchApp.fetch(WEBHOOK_URL, options);
    const responseCode = response.getResponseCode();
    const responseText = response.getContentText();
    
    if (responseCode === 200) {
      Logger.log(`✅ Webhook sent successfully! Response: ${responseText}`);
    } else {
      Logger.log(`❌ Webhook failed with status ${responseCode}: ${responseText}`);
    }
    
  } catch (error) {
    Logger.log(`❌ Error sending webhook: ${error.message}`);
    Logger.log(error.stack);
  }
}

// ===== 설정 및 테스트 함수 =====

/**
 * onEdit 트리거를 자동으로 설정
 * 실행: Apps Script 편집기 상단에서 "setupTrigger" 선택 후 실행
 */
function setupTrigger() {
  try {
    // 기존 트리거 삭제
    const triggers = ScriptApp.getProjectTriggers();
    triggers.forEach(trigger => {
      if (trigger.getHandlerFunction() === 'onEdit') {
        ScriptApp.deleteTrigger(trigger);
        Logger.log('Deleted existing onEdit trigger');
      }
    });
    
    // 새 트리거 생성
    ScriptApp.newTrigger('onEdit')
      .forSpreadsheet(SpreadsheetApp.getActive())
      .onEdit()
      .create();
    
    Logger.log('✅ onEdit trigger created successfully!');
    Logger.log('Now any edit in columns B-F will trigger the webhook.');
    
  } catch (error) {
    Logger.log(`❌ Error creating trigger: ${error.message}`);
  }
}

/**
 * 웹훅 연동 테스트 (수동 실행용)
 * 실행: Apps Script 편집기 상단에서 "testWebhook" 선택 후 실행
 */
function testWebhook() {
  try {
    Logger.log('=== Testing Webhook ===');
    
    const sheet = SpreadsheetApp.getActiveSpreadsheet().getSheetByName(TARGET_SHEET_NAME);
    if (!sheet) {
      Logger.log(`❌ Sheet "${TARGET_SHEET_NAME}" not found!`);
      return;
    }
    
    Logger.log(`Testing with sheet: ${sheet.getName()}`);
    
    sendSheetDataToWebhook(sheet);
    
    Logger.log('=== Test Complete ===');
    Logger.log('Check the Logs tab to see the result.');
    
  } catch (error) {
    Logger.log(`❌ Test failed: ${error.message}`);
    Logger.log(error.stack);
  }
}

/**
 * 스크립트 설정 확인
 * 실행: Apps Script 편집기 상단에서 "checkConfiguration" 선택 후 실행
 */
function checkConfiguration() {
  Logger.log('=== Configuration Check ===');
  Logger.log(`Webhook URL: ${WEBHOOK_URL}`);
  Logger.log(`Watch columns: ${WATCH_COLUMN_START} to ${WATCH_COLUMN_END} (B-F)`);
  Logger.log(`Target sheet: ${TARGET_SHEET_NAME || 'All sheets'}`);
  
  // 시트 존재 확인
  const sheet = SpreadsheetApp.getActiveSpreadsheet().getSheetByName(TARGET_SHEET_NAME);
  if (sheet) {
    Logger.log(`✅ Target sheet "${TARGET_SHEET_NAME}" exists`);
  } else {
    Logger.log(`❌ Target sheet "${TARGET_SHEET_NAME}" NOT found!`);
  }
  
  // 트리거 확인
  const triggers = ScriptApp.getProjectTriggers();
  const onEditTriggers = triggers.filter(t => t.getHandlerFunction() === 'onEdit');
  
  if (onEditTriggers.length > 0) {
    Logger.log(`✅ onEdit trigger is installed (${onEditTriggers.length} trigger(s))`);
  } else {
    Logger.log('❌ onEdit trigger is NOT installed!');
    Logger.log('Run setupTrigger() to install it.');
  }
  
  Logger.log('=== Check Complete ===');
}

/**
 * 현재 시트의 B~F열 데이터 미리보기
 * 실행: Apps Script 편집기 상단에서 "previewData" 선택 후 실행
 */
function previewData() {
  const sheet = SpreadsheetApp.getActiveSpreadsheet().getSheetByName(TARGET_SHEET_NAME);
  
  if (!sheet) {
    Logger.log(`❌ Sheet "${TARGET_SHEET_NAME}" not found!`);
    return;
  }
  
  const dataRange = sheet.getDataRange();
  const values = dataRange.getValues();
  
  Logger.log('=== Sheet Data Preview ===');
  Logger.log(`Sheet: ${sheet.getName()}`);
  Logger.log(`Total rows: ${values.length}`);
  
  if (values.length > 0) {
    Logger.log('Headers:');
    Logger.log(JSON.stringify(values[0]));
    
    if (values.length > 1) {
      Logger.log('First data row:');
      Logger.log(JSON.stringify(values[1]));
    }
  }
  
  Logger.log('=== Preview Complete ===');
}
