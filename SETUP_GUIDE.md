# 🔧 Google Sheets 실시간 동기화 설정 가이드 (Service Account)

Google Sheets (비공개) → Streamlit 마스터 코드 실시간 자동 동기화

---

## 📋 목차

1. [사전 준비](#1-사전-준비)
2. [Google Cloud 설정](#2-google-cloud-설정)
3. [Streamlit 앱 설정](#3-streamlit-앱-설정)
4. [Google Apps Script 설정](#4-google-apps-script-설정)
5. [연동 테스트](#5-연동-테스트)
6. [트러블슈팅](#6-트러블슈팅)

---

## 1. 사전 준비

### 필요한 정보

- **Google Sheets URL**: `https://docs.google.com/spreadsheets/d/1e7T7dANrJemFP1eouH02Wi4Ysoh08jmq77Rn_5pbzQs/edit?gid=1735735926`
- **Sheet ID**: `1e7T7dANrJemFP1eouH02Wi4Ysoh08jmq77Rn_5pbzQs`
- **gid**: `1735735926`
- **감지 대상 열**: B~F열
- **Streamlit 앱 URL**: `https://3000-ip2l928h0vug305w91va9-d0b9e1e2.sandbox.novita.ai/`
- **Webhook URL**: `https://5000-ip2l928h0vug305w91va9-d0b9e1e2.sandbox.novita.ai/webhook`

---

## 2. Google Cloud 설정

### 2-1. 프로젝트 생성 및 API 활성화

1. **Google Cloud Console 접속**
   - https://console.cloud.google.com/
   - Google 계정으로 로그인

2. **새 프로젝트 만들기**
   - 프로젝트 이름: `logistics-sheets-integration` (예시)
   - "만들기" 클릭

3. **Google Sheets API 활성화**
   - 좌측 메뉴 → "API 및 서비스" → "라이브러리"
   - "Google Sheets API" 검색 → "사용" 클릭

### 2-2. Service Account 생성

1. **Service Account 만들기**
   - 좌측 메뉴 → "API 및 서비스" → "사용자 인증 정보"
   - "사용자 인증 정보 만들기" → "서비스 계정"
   - 이름: `logistics-sheets-reader` (예시)
   - "만들기 및 계속하기" → "계속" → "완료"

2. **JSON 키 다운로드**
   - 생성된 서비스 계정 클릭
   - "키" 탭 → "키 추가" → "새 키 만들기"
   - "JSON" 선택 → "만들기"
   - **파일 다운로드됨**: 안전한 곳에 보관!

3. **Service Account 이메일 복사**
   - 예시: `logistics-sheets-reader@logistics-sheets-integration.iam.gserviceaccount.com`

### 2-3. ⭐ Google Sheets에 공유 (핵심!)

1. **대상 Sheets 열기**
   - https://docs.google.com/spreadsheets/d/1e7T7dANrJemFP1eouH02Wi4Ysoh08jmq77Rn_5pbzQs/edit

2. **공유 추가**
   - 우측 상단 "공유" 버튼
   - Service Account 이메일 입력
   - 권한: **"뷰어"** (읽기 전용)
   - "알림 보내기" 체크 해제
   - "공유" 클릭

---

## 3. Streamlit 앱 설정

### 3-1. 패키지 설치

```bash
cd /home/user/webapp
pip install -r requirements.txt
```

### 3-2. Secrets 파일 생성

1. **`.streamlit` 디렉토리 생성**
   ```bash
   mkdir -p /home/user/webapp/.streamlit
   ```

2. **`secrets.toml` 파일 생성**
   ```bash
   cp /home/user/webapp/.streamlit/secrets.toml.example /home/user/webapp/.streamlit/secrets.toml
   ```

3. **Service Account 정보 입력**
   - 다운로드한 JSON 키 파일을 텍스트 에디터로 열기
   - `/home/user/webapp/.streamlit/secrets.toml` 편집:

   ```toml
   [gcp_service_account]
   type = "service_account"
   project_id = "logistics-sheets-integration"
   private_key_id = "a1b2c3d4e5f6..."
   private_key = "-----BEGIN PRIVATE KEY-----\nMIIEvQIB...\n-----END PRIVATE KEY-----\n"
   client_email = "logistics-sheets-reader@logistics-sheets-integration.iam.gserviceaccount.com"
   client_id = "123456789012345678901"
   auth_uri = "https://accounts.google.com/o/oauth2/auth"
   token_uri = "https://oauth2.googleapis.com/token"
   auth_provider_x509_cert_url = "https://www.googleapis.com/oauth2/v1/certs"
   client_x509_cert_url = "https://www.googleapis.com/robot/v1/metadata/x509/..."
   universe_domain = "googleapis.com"
   ```

   **⚠️ 주의**: `private_key`는 `\n`을 그대로 유지!

### 3-3. Webhook Secret Token 생성

1. **랜덤 토큰 생성**
   ```bash
   openssl rand -hex 32
   ```
   출력 예시: `a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6q7r8s9t0u1v2w3x4y5z6`

2. **secrets.toml에 추가**
   ```toml
   webhook_secret = "a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6q7r8s9t0u1v2w3x4y5z6"
   ```

3. **토큰 복사** (Google Apps Script에서 사용)

### 3-4. .gitignore 확인

```bash
grep -q "secrets.toml" /home/user/webapp/.gitignore || echo ".streamlit/secrets.toml" >> /home/user/webapp/.gitignore
```

### 3-5. 앱 재시작

```bash
cd /home/user/webapp
fuser -k 3000/tcp 5000/tcp 2>/dev/null || true
pm2 delete all 2>/dev/null || true
pm2 start ecosystem.config.cjs
```

---

## 4. Google Apps Script 설정

### 4-1. 스크립트 추가

1. **Google Sheets 열기**
   - https://docs.google.com/spreadsheets/d/1e7T7dANrJemFP1eouH02Wi4Ysoh08jmq77Rn_5pbzQs/edit

2. **Apps Script 편집기 열기**
   - 상단 메뉴: Extensions → Apps Script

3. **코드 붙여넣기**
   - `/home/user/webapp/google_apps_script_service_account.js` 내용 복사
   - Apps Script 편집기에 붙여넣기

4. **WEBHOOK_URL 설정**
   - 코드 상단에서 `WEBHOOK_URL` 확인:
   ```javascript
   const WEBHOOK_URL = 'https://5000-ip2l928h0vug305w91va9-d0b9e1e2.sandbox.novita.ai/webhook';
   ```

5. **저장**
   - 프로젝트 이름: `Logistics Sheets Webhook` (예시)
   - "저장" 아이콘 클릭

### 4-2. Secret Token 설정

1. **스크립트 속성 열기**
   - 좌측 "프로젝트 설정" (톱니바퀴 아이콘) 클릭
   - "스크립트 속성" 섹션으로 스크롤

2. **속성 추가**
   - "스크립트 속성 추가" 클릭
   - 속성: `WEBHOOK_SECRET`
   - 값: (위에서 생성한 토큰 붙여넣기)
   - "스크립트 속성 저장" 클릭

### 4-3. onEdit 트리거 설정

1. **setupTrigger() 실행**
   - Apps Script 편집기 상단 함수 드롭다운에서 `setupTrigger` 선택
   - "실행" 버튼 (▶) 클릭
   - 권한 승인 (Google 계정 로그인 필요)

2. **트리거 확인**
   - 좌측 "트리거" (시계 아이콘) 클릭
   - `onEdit` 트리거가 표시되어야 함

---

## 5. 연동 테스트

### 5-1. 설정 확인

1. **Apps Script에서 `checkConfiguration()` 실행**
   - 함수 드롭다운에서 `checkConfiguration` 선택 → 실행
   - "실행 로그" 탭에서 결과 확인:
     - ✅ WEBHOOK_SECRET is set
     - ✅ onEdit trigger is installed

### 5-2. 수동 테스트

1. **Apps Script에서 `testWebhook()` 실행**
   - 함수 드롭다운에서 `testWebhook` 선택 → 실행
   - "실행 로그" 탭에서 결과 확인:
     - `✅ Webhook sent successfully!`

2. **Streamlit 앱 확인**
   - https://3000-ip2l928h0vug305w91va9-d0b9e1e2.sandbox.novita.ai/
   - "✅ 마스터 코드가 업데이트되었습니다" 알림 표시

### 5-3. 실제 편집 테스트

1. **Google Sheets에서 B~F열 값 변경**
   - 아무 셀이나 선택하여 값 변경
   - Enter 키 입력

2. **Streamlit 앱 새로고침**
   - 변경된 값이 즉시 반영되어야 함
   - "✅ 마스터 코드가 업데이트되었습니다 (출처: webhook)" 알림 표시

---

## 6. 트러블슈팅

### 문제 1: "Permission denied" 또는 "403 Forbidden"

**증상**: Streamlit 앱에서 Sheets 데이터를 읽을 수 없음

**해결**:
1. Service Account 이메일을 정확히 확인 (JSON의 `client_email`)
2. Google Sheets → 공유 → Service Account 이메일 추가 (뷰어 권한)
3. "알림 보내기" 체크 해제
4. 공유 대상 목록에 Service Account가 표시되는지 확인

### 문제 2: "Invalid token" 에러

**증상**: Webhook 요청이 401 Unauthorized로 실패

**해결**:
1. Streamlit `secrets.toml`의 `webhook_secret` 확인
2. Google Apps Script 스크립트 속성의 `WEBHOOK_SECRET` 확인
3. 두 값이 **정확히 일치**해야 함 (공백, 대소문자 주의)

### 문제 3: "Invalid private key"

**증상**: Service Account 인증 실패

**해결**:
- `private_key`의 `\n` 문자가 손상되지 않았는지 확인
- JSON 파일에서 그대로 복사 (수동 편집 금지)
- TOML 파일에서 큰따옴표 안에 `\n`이 문자열로 유지되어야 함

### 문제 4: Webhook이 호출되지 않음

**증상**: Google Sheets에서 값을 변경해도 Streamlit 앱에 반영 안 됨

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
   응답: `{"status":"ok","service":"webhook_server","token_configured":true}`

### 문제 5: PM2 프로세스가 죽음

**증상**: 앱이 접속되지 않음

**해결**:
```bash
pm2 list  # 프로세스 상태 확인
pm2 logs --nostream  # 에러 로그 확인
pm2 restart all  # 재시작
```

---

## 📌 보안 체크리스트

### ✅ 반드시 확인할 것

- [ ] `.streamlit/secrets.toml`이 `.gitignore`에 포함됨
- [ ] Service Account JSON 키 파일이 `.gitignore`에 포함됨
- [ ] Service Account에 최소 권한만 부여 (Sheets 뷰어)
- [ ] Webhook secret token이 32자 이상
- [ ] Secret token이 `st.secrets` 또는 스크립트 속성으로만 관리됨
- [ ] 코드에 인증 정보가 하드코딩되지 않음

### ❌ 절대 하지 말 것

- [ ] secrets.toml을 GitHub에 커밋
- [ ] Service Account JSON을 GitHub에 커밋
- [ ] Secret token을 코드에 하드코딩
- [ ] Service Account에 불필요한 권한 부여

---

## 📚 관련 문서

- **상세 설정 가이드**: `GOOGLE_SERVICE_ACCOUNT_SETUP.md`
- **Google Apps Script 코드**: `google_apps_script_service_account.js`
- **Secrets 템플릿**: `.streamlit/secrets.toml.example`

---

## 🎯 다음 단계

설정이 완료되면:

1. Google Sheets B~F열 값 변경
2. Streamlit 앱에 즉시 반영 확인
3. 정상 동작하면 실제 운영 시작!

문제가 발생하면 위 트러블슈팅 섹션 참조.
