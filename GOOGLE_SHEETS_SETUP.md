# 📋 Google Sheets 실시간 동기화 설정 가이드

Google Sheets (공개 링크 - 뷰어 접근 가능) → Streamlit 마스터 코드 실시간 자동 동기화

---

## 📋 개요

이 가이드는 Google Sheets와 Streamlit 앱을 실시간으로 연동하는 방법을 설명합니다.

**연동 방식**:
- **Sheets → Streamlit**: CSV Export URL (공개 링크, 인증 불필요)
- **Sheets 변경 감지**: Google Apps Script의 onEdit 트리거
- **실시간 업데이트**: Webhook POST 요청

**소요 시간**: 약 5분

---

## 🔧 Google Sheets 정보

### 시트 기본 정보

- **Sheets ID**: `1e7T7dANrJemFP1eouH02Wi4Ysoh08jmq77Rn_5pbzQs`
- **탭 이름**: `상품 코드 최종(마스터 코드)`
- **감지 대상 열**: B~F열 전체

### CSV Export URL

```
https://docs.google.com/spreadsheets/d/1e7T7dANrJemFP1eouH02Wi4Ysoh08jmq77Rn_5pbzQs/export?format=csv&sheet=상품 코드 최종(마스터 코드)
```

**⚠️ 주의**: 탭 이름에 한글/괄호가 포함되므로 URL 인코딩 필요  
→ `sheets_utils.py`에서 `urllib.parse.quote`로 자동 처리

---

## 📝 설정 단계

### Step 1: Google Apps Script 설정 (5분)

#### 1-1. Apps Script 편집기 열기

1. **Google Sheets 열기**
   - https://docs.google.com/spreadsheets/d/1e7T7dANrJemFP1eouH02Wi4Ysoh08jmq77Rn_5pbzQs/edit

2. **Apps Script 편집기 접속**
   - 상단 메뉴: Extensions → Apps Script

#### 1-2. 스크립트 코드 추가

1. **코드 복사**
   - `/home/user/webapp/google_apps_script.js` 파일 내용 복사

2. **붙여넣기**
   - Apps Script 편집기에 붙여넣기

3. **WEBHOOK_URL 확인**
   ```javascript
   const WEBHOOK_URL = 'https://5000-ip2l928h0vug305w91va9-d0b9e1e2.sandbox.novita.ai/webhook';
   ```

4. **TARGET_SHEET_NAME 확인**
   ```javascript
   const TARGET_SHEET_NAME = '상품 코드 최종(마스터 코드)';
   ```

5. **저장**
   - 프로젝트 이름: `Logistics Sheets Webhook` (예시)
   - 💾 저장 아이콘 클릭

#### 1-3. onEdit 트리거 설치

1. **setupTrigger() 실행**
   - Apps Script 편집기 상단 함수 드롭다운에서 `setupTrigger` 선택
   - ▶ "실행" 버튼 클릭
   - 권한 승인 (Google 계정 로그인 필요)
     * "이 앱은 확인되지 않았습니다" → "고급" → "프로젝트로 이동(안전하지 않음)"
     * "허용" 클릭

2. **트리거 확인**
   - 좌측 "트리거" (⏰ 시계 아이콘) 클릭
   - `onEdit` 트리거가 표시되어야 함

---

### Step 2: 연동 테스트 (2분)

#### 2-1. 설정 확인

1. **checkConfiguration() 실행**
   - 함수 드롭다운에서 `checkConfiguration` 선택 → 실행
   - "실행 로그" 탭에서 결과 확인:
     ```
     ✅ Target sheet "상품 코드 최종(마스터 코드)" exists
     ✅ onEdit trigger is installed
     ```

#### 2-2. 수동 웹훅 테스트

1. **testWebhook() 실행**
   - 함수 드롭다운에서 `testWebhook` 선택 → 실행
   - "실행 로그" 탭에서 결과 확인:
     ```
     ✅ Webhook sent successfully!
     ```

2. **Streamlit 앱 확인**
   - https://3000-ip2l928h0vug305w91va9-d0b9e1e2.sandbox.novita.ai/
   - "✅ 마스터 코드가 업데이트되었습니다" 알림 표시

#### 2-3. 실제 편집 테스트

1. **Google Sheets에서 B~F열 값 변경**
   - 아무 셀이나 선택하여 값 변경
   - Enter 키 입력

2. **Streamlit 앱 새로고침**
   - 변경된 값이 즉시 반영되어야 함
   - "✅ 마스터 코드가 업데이트되었습니다 (출처: webhook)" 알림 표시

---

## 🔧 데이터 흐름

### 앱 최초 실행 시

```
Streamlit 앱 시작
    ↓
sheets_utils.py
(CSV Export URL 호출)
    ↓
Google Sheets
(공개 링크 - 인증 불필요)
    ↓
마스터 코드 로드
    ↓
master_codes.db 저장
    ↓
앱에서 사용
```

### Sheets 변경 시 실시간 업데이트

```
B~F열 값 변경
    ↓
onEdit 트리거 발동
    ↓
Google Apps Script
(전체 데이터 읽기)
    ↓
POST /webhook
    ↓
webhook_server.py
(Flask, port 5000)
    ↓
master_codes.db 업데이트
    ↓
Streamlit 앱 즉시 반영
```

---

## 📂 관련 파일

### 백엔드 파일
- `sheets_utils.py` - CSV Export URL로 Sheets 데이터 읽기
- `webhook_server.py` - Webhook 서버 (Flask)
- `master_codes.db` - SQLite 데이터베이스

### 프론트엔드 파일
- `app.py` - Streamlit 메인 앱
- `google_apps_script.js` - Apps Script 코드

### 설정 파일
- `requirements.txt` - Python 패키지 의존성
- `ecosystem.config.cjs` - PM2 설정

---

## ❓ 트러블슈팅

### 문제 1: "401 Unauthorized" 또는 "403 Forbidden"

**증상**: CSV Export URL 호출 시 에러

**원인**: Sheets가 비공개로 설정됨

**해결**:
1. Google Sheets 열기
2. 우측 상단 "공유" 버튼 클릭
3. "링크가 있는 모든 사용자" → "뷰어" 권한 설정
4. "링크 복사" 클릭하여 공개 링크 확인

### 문제 2: Webhook이 호출되지 않음

**증상**: Sheets에서 값을 변경해도 Streamlit 앱에 반영 안 됨

**해결**:
1. **트리거 확인**:
   - Apps Script → 좌측 "트리거" 클릭
   - `onEdit` 트리거가 있는지 확인
   - 없으면 `setupTrigger()` 재실행

2. **WEBHOOK_URL 확인**:
   - Apps Script 코드의 `WEBHOOK_URL`이 올바른지 확인
   - 현재: `https://5000-ip2l928h0vug305w91va9-d0b9e1e2.sandbox.novita.ai/webhook`

3. **Apps Script 로그 확인**:
   - Apps Script → 좌측 "실행" 클릭
   - 최근 실행 기록에서 에러 확인

4. **Webhook 서버 상태 확인**:
   ```bash
   curl https://5000-ip2l928h0vug305w91va9-d0b9e1e2.sandbox.novita.ai/health
   ```
   응답: `{"status":"ok","service":"webhook_server"}`

### 문제 3: 탭 이름이 다름

**증상**: `checkConfiguration()`에서 "Target sheet NOT found"

**해결**:
1. Google Sheets에서 탭 이름 확인
2. Apps Script 코드의 `TARGET_SHEET_NAME` 수정
3. 저장 후 트리거 재설치

### 문제 4: PM2 프로세스가 죽음

**증상**: 앱이 접속되지 않음

**해결**:
```bash
pm2 list  # 프로세스 상태 확인
pm2 logs --nostream  # 에러 로그 확인
pm2 restart all  # 재시작
```

---

## ✅ 설정 완료 체크리스트

### Google Apps Script
- [ ] `google_apps_script.js` 코드 붙여넣기 완료
- [ ] `WEBHOOK_URL` 확인 완료
- [ ] `TARGET_SHEET_NAME` 확인 완료
- [ ] 프로젝트 저장 완료
- [ ] `setupTrigger()` 실행 완료
- [ ] 트리거 탭에서 `onEdit` 확인 완료

### 테스트
- [ ] `checkConfiguration()` 실행 → 모두 ✅
- [ ] `testWebhook()` 실행 → "Webhook sent successfully"
- [ ] Sheets B~F열 값 변경 → Streamlit 앱 즉시 반영
- [ ] Webhook 서버 health check → `{"status":"ok"}`

---

## 🎯 다음 단계

설정이 완료되면:

1. Google Sheets B~F열 값 변경
2. Streamlit 앱에 즉시 반영 확인
3. 정상 동작하면 실제 운영 시작!

문제가 발생하면 위 트러블슈팅 섹션 참조.

---

**업데이트**: 2026-03-07  
**버전**: v3.18 (공개 링크 버전)
