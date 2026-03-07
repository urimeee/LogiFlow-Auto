# 📊 Google Sheets 실시간 연동 설정 가이드

## 🎯 목표

Google Sheets의 마스터 코드(B열~F열)를 Streamlit 앱과 실시간으로 동기화합니다.

- **앱 최초 실행 시**: Google Sheets에서 마스터 코드 자동 로드 → DB 저장
- **Sheets 변경 시**: B~F열 변경 즉시 → 웹훅 호출 → 앱 자동 갱신
- **Polling 없음**: 실시간 푸시 방식

---

## 📋 사전 준비사항

1. **Google Sheets 공개 설정**
   - Google Sheets를 열고
   - 우측 상단 "공유" 버튼 클릭
   - "링크가 있는 모든 사용자" 선택
   - "뷰어" 권한으로 설정
   
2. **Sheet ID 확인**
   - 현재 설정: `1e7T7dANrJemFP1eouH02Wi4Ysoh08jmq77Rn_5pbzQs`
   - gid: `1735735926`
   - URL 형식: `https://docs.google.com/spreadsheets/d/{SHEET_ID}/edit?gid={GID}`

3. **Streamlit 앱 URL 확인**
   - Streamlit 앱 URL: `https://3000-{SANDBOX_ID}.sandbox.novita.ai`
   - Webhook 서버 URL: `https://5000-{SANDBOX_ID}.sandbox.novita.ai`

---

## 🚀 Step 1: Streamlit 앱 설정 (이미 완료)

### 1-1. 서비스 시작

```bash
cd /home/user/webapp

# PM2로 두 서비스 동시 실행
pm2 start ecosystem.config.cjs

# 상태 확인
pm2 list

# 로그 확인
pm2 logs logistics-app --nostream
pm2 logs webhook-server --nostream
```

**실행되는 서비스**:
- `logistics-app`: Streamlit 앱 (포트 3000)
- `webhook-server`: Flask Webhook 서버 (포트 5000)

### 1-2. URL 확인

```bash
# Streamlit 앱
curl https://3000-{SANDBOX_ID}.sandbox.novita.ai

# Webhook 서버 헬스체크
curl https://5000-{SANDBOX_ID}.sandbox.novita.ai/health
```

---

## 🔧 Step 2: Google Apps Script 설정

### 2-1. Apps Script 편집기 열기

1. Google Sheets 열기
2. 메뉴: **확장 프로그램** > **Apps Script**
3. 새 프로젝트 생성 또는 기존 프로젝트 선택

### 2-2. 코드 붙여넣기

`google_apps_script.js` 파일의 전체 내용을 복사하여 Apps Script 편집기에 붙여넣습니다.

### 2-3. Webhook URL 수정

**중요**: WEBHOOK_URL을 실제 서비스 URL로 변경해야 합니다!

```javascript
// 수정 전
const WEBHOOK_URL = 'https://5000-SANDBOX_ID.sandbox.novita.ai/webhook';

// 수정 후 (실제 SANDBOX_ID로 교체)
const WEBHOOK_URL = 'https://5000-ip2l928h0vug305w91va9-d0b9e1e2.sandbox.novita.ai/webhook';
```

**SANDBOX_ID 확인 방법**:
1. Streamlit 앱 URL에서 복사: `https://3000-{이부분}-{나머지}.sandbox.novita.ai`
2. Webhook URL에 동일한 ID 사용: `https://5000-{같은ID}-{같은나머지}.sandbox.novita.ai/webhook`

### 2-4. 프로젝트 저장

- 프로젝트 이름: "Streamlit Webhook Integration" (원하는 이름)
- 저장 버튼 클릭 (Ctrl+S)

### 2-5. 트리거 설정

**방법 1: 자동 설정 (권장)**

1. Apps Script 편집기 상단 메뉴
2. **실행** > **함수 선택** > `setupTrigger`
3. **실행** 버튼 클릭
4. 권한 승인 (처음 한 번만)
5. "✅ 설정 완료" 알림 확인

**방법 2: 수동 설정**

1. 좌측 메뉴: **트리거** (시계 아이콘)
2. **+ 트리거 추가** 버튼
3. 설정:
   - 실행할 함수: `onEdit`
   - 이벤트 소스: `스프레드시트에서`
   - 이벤트 유형: `수정 시`
4. 저장

---

## 🧪 Step 3: 테스트

### 3-1. 수동 Webhook 테스트

Apps Script 편집기에서:

1. **실행** > **함수 선택** > `testWebhook`
2. **실행** 버튼 클릭
3. 로그 확인: **보기** > **로그** (Ctrl+Enter)

**예상 로그**:
```
=== 수동 Webhook 테스트 시작 ===
Webhook 요청 시작: https://5000-...
전송 데이터 크기: 1234 bytes
✅ Webhook 성공: {"status":"success",...}
=== 테스트 완료 ===
```

### 3-2. 실제 편집 테스트

1. Google Sheets로 돌아가기
2. **B열~F열** 중 아무 셀이나 수정
   - 예: B2 셀의 값을 변경
3. Enter 키를 눌러 저장
4. Apps Script 로그 확인 (1~2초 후)
   - 메뉴: **확장 프로그램** > **Apps Script** > **보기** > **로그**

**예상 로그**:
```
편집 감지: 시트=시트1, 행=2, 열=2
✅ B열~F열 변경 감지! Webhook 호출 시작...
Webhook 요청 시작: https://5000-...
✅ Webhook 성공: {"status":"success",...}
```

### 3-3. Streamlit 앱 확인

1. Streamlit 앱 새로고침
2. 마스터 코드 업데이트 알림 확인:
   - "✅ {날짜} 마스터 코드가 업데이트되었습니다 (출처: Google Sheets)"

---

## 🔍 트러블슈팅

### ❌ "Webhook 실패: HTTP 401" 또는 "403"

**원인**: Webhook 서버가 실행 중이지 않거나 URL이 잘못됨

**해결**:
```bash
# 서비스 상태 확인
pm2 list

# webhook-server가 없으면 시작
pm2 start ecosystem.config.cjs

# URL 접근 테스트
curl https://5000-{SANDBOX_ID}.sandbox.novita.ai/health
```

### ❌ "Failed to fetch from Google Sheets: 401 Unauthorized"

**원인**: Google Sheets가 비공개 상태

**해결**:
1. Google Sheets 열기
2. 우측 상단 "공유" 버튼
3. "링크가 있는 모든 사용자" → "뷰어" 권한 설정
4. "완료" 클릭

### ❌ Apps Script에서 onEdit이 실행되지 않음

**원인**: 트리거가 설정되지 않음

**해결**:
1. Apps Script 편집기 > 좌측 메뉴 > **트리거** (시계 아이콘)
2. `onEdit` 트리거가 있는지 확인
3. 없으면 `setupTrigger` 함수 실행 또는 수동으로 트리거 추가

### ❌ "감지 대상 열이 아님: 열=1" (A열 변경)

**정상**: A열은 감지 대상이 아닙니다. B~F열만 감지합니다.

**확인**: B열~F열(2~6번 열) 중 하나를 수정하세요.

---

## 📊 데이터 흐름

```
┌─────────────────┐
│ Google Sheets   │
│ (B열~F열 변경)  │
└────────┬────────┘
         │
         ↓ onEdit 트리거
         │
┌────────┴────────┐
│ Apps Script     │
│ sendWebhook()   │
└────────┬────────┘
         │
         ↓ POST /webhook
         │
┌────────┴────────┐
│ Flask Server    │
│ (포트 5000)     │
└────────┬────────┘
         │
         ↓ SQLite DB 저장
         │
┌────────┴────────┐
│ master_codes DB │
│ (최신 데이터)   │
└────────┬────────┘
         │
         ↓ load_master_from_db()
         │
┌────────┴────────┐
│ Streamlit App   │
│ (포트 3000)     │
└─────────────────┘
```

---

## 🎯 핵심 포인트

1. **두 개의 서버 실행 필요**:
   - Streamlit (포트 3000): 사용자 인터페이스
   - Flask (포트 5000): Webhook 수신

2. **Polling 없음**:
   - Google Sheets 변경 → 즉시 푸시
   - 서버는 대기만 하고 주기적 확인 안 함

3. **B~F열만 감지**:
   - A열이나 G열 이상은 감지 안 함
   - 필요시 Apps Script의 `WATCH_COL_START`, `WATCH_COL_END` 수정

4. **DB 기반 저장**:
   - 최신 1개만 유지
   - 앱 재시작 시에도 데이터 유지

---

## 📝 관련 파일

- `webhook_server.py`: Flask Webhook 서버
- `sheets_utils.py`: Google Sheets 연동 유틸리티
- `google_apps_script.js`: Google Apps Script 코드
- `ecosystem.config.cjs`: PM2 설정 (두 서비스 포함)
- `master_codes.db`: SQLite 데이터베이스 (자동 생성)

---

## 🔄 서비스 관리 명령어

```bash
# 서비스 시작
pm2 start ecosystem.config.cjs

# 서비스 재시작
pm2 restart all

# 서비스 중지
pm2 stop all

# 로그 확인
pm2 logs logistics-app
pm2 logs webhook-server

# 서비스 삭제
pm2 delete all
```

---

**문의**: 설정 중 문제가 발생하면 `pm2 logs` 명령어로 로그를 확인하세요.
