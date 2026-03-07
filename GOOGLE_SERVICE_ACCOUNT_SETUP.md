# 📋 Google Service Account 설정 가이드

Google Sheets (비공개) → Streamlit 마스터 코드 실시간 자동 동기화

---

## Part 1. Google Service Account 발급 (단계별)

### 1-1. Google Cloud Console 프로젝트 생성

1. **Google Cloud Console 접속**
   - 브라우저에서 https://console.cloud.google.com/ 접속
   - Google 계정으로 로그인

2. **새 프로젝트 만들기**
   - 상단 프로젝트 선택 드롭다운 클릭
   - "새 프로젝트" 버튼 클릭
   - 프로젝트 이름 입력 (예: `logistics-sheets-integration`)
   - "만들기" 클릭

### 1-2. Google Sheets API 활성화

1. **API 및 서비스 → 라이브러리** 이동
   - 좌측 메뉴에서 "API 및 서비스" → "라이브러리" 클릭

2. **Google Sheets API 검색 및 활성화**
   - 검색창에 "Google Sheets API" 입력
   - "Google Sheets API" 선택
   - "사용" 버튼 클릭

3. **Google Drive API도 활성화 (선택사항, 권장)**
   - 같은 방법으로 "Google Drive API" 검색하여 활성화

### 1-3. Service Account 생성 및 JSON 키 다운로드

1. **Service Account 생성**
   - 좌측 메뉴에서 "API 및 서비스" → "사용자 인증 정보" 클릭
   - 상단 "사용자 인증 정보 만들기" → "서비스 계정" 선택
   - 서비스 계정 이름 입력 (예: `logistics-sheets-reader`)
   - 서비스 계정 ID 자동 생성됨 (예: `logistics-sheets-reader@logistics-sheets-integration.iam.gserviceaccount.com`)
   - "만들기 및 계속하기" 클릭

2. **역할 부여 (선택사항)**
   - "역할" 단계는 건너뛰어도 됨 (Sheets 공유로 권한 부여)
   - "계속" 클릭

3. **JSON 키 다운로드**
   - "서비스 계정" 목록에서 방금 만든 계정 클릭
   - "키" 탭 클릭
   - "키 추가" → "새 키 만들기" 선택
   - "JSON" 선택 → "만들기" 클릭
   - **중요**: JSON 파일이 자동 다운로드됨 (안전한 곳에 보관!)
   - 파일명 예시: `logistics-sheets-integration-a1b2c3d4e5f6.json`

### 1-4. ⭐ Service Account를 Google Sheets에 공유 (핵심 단계!)

1. **Service Account 이메일 복사**
   - JSON 키 파일을 열어 `client_email` 값 복사
   - 또는 Google Cloud Console → 서비스 계정 목록에서 이메일 복사
   - 예시: `logistics-sheets-reader@logistics-sheets-integration.iam.gserviceaccount.com`

2. **Google Sheets에 공유 추가**
   - 대상 Google Sheets 열기
     * URL: https://docs.google.com/spreadsheets/d/1e7T7dANrJemFP1eouH02Wi4Ysoh08jmq77Rn_5pbzQs/edit
   - 우측 상단 "공유" 버튼 클릭
   - Service Account 이메일 입력 (위에서 복사한 이메일)
   - 권한: **"뷰어"** 선택 (읽기 전용)
   - "알림 보내기" 체크 해제 (Service Account는 사람이 아님)
   - "공유" 클릭

3. **권한 확인**
   - Sheets의 "공유 대상" 목록에 Service Account 이메일이 표시되어야 함
   - 이제 Service Account가 해당 Sheets를 읽을 수 있음!

### 1-5. JSON 키 파일을 Streamlit 앱에 배치

#### 방법 A: Streamlit Secrets (권장)

1. **Streamlit 프로젝트에 `.streamlit` 디렉토리 생성**
   ```bash
   mkdir -p /home/user/webapp/.streamlit
   ```

2. **`secrets.toml` 파일 생성**
   ```bash
   touch /home/user/webapp/.streamlit/secrets.toml
   ```

3. **JSON 키 내용을 TOML 형식으로 변환**
   - 다운로드한 JSON 파일을 열고 내용을 복사
   - 아래 템플릿에 붙여넣기:

   ```toml
   # .streamlit/secrets.toml
   [gcp_service_account]
   type = "service_account"
   project_id = "logistics-sheets-integration"
   private_key_id = "a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6q7r8s9t0"
   private_key = "-----BEGIN PRIVATE KEY-----\nMIIEvQIBADANBg...(긴 문자열)...=\n-----END PRIVATE KEY-----\n"
   client_email = "logistics-sheets-reader@logistics-sheets-integration.iam.gserviceaccount.com"
   client_id = "123456789012345678901"
   auth_uri = "https://accounts.google.com/o/oauth2/auth"
   token_uri = "https://oauth2.googleapis.com/token"
   auth_provider_x509_cert_url = "https://www.googleapis.com/oauth2/v1/certs"
   client_x509_cert_url = "https://www.googleapis.com/robot/v1/metadata/x509/logistics-sheets-reader%40logistics-sheets-integration.iam.gserviceaccount.com"
   universe_domain = "googleapis.com"
   ```

   **⚠️ 주의사항**:
   - `private_key`는 줄바꿈 문자(`\n`)를 그대로 유지해야 함
   - TOML은 큰따옴표(`"`) 사용 필수
   - `.streamlit/secrets.toml`은 `.gitignore`에 추가되어야 함

4. **`.gitignore` 확인**
   ```bash
   echo ".streamlit/secrets.toml" >> /home/user/webapp/.gitignore
   ```

#### 방법 B: 환경변수 (대안)

1. **JSON 파일을 프로젝트 디렉토리에 복사**
   ```bash
   cp ~/Downloads/logistics-sheets-integration-*.json /home/user/webapp/service_account.json
   ```

2. **환경변수 설정**
   ```bash
   export GOOGLE_APPLICATION_CREDENTIALS="/home/user/webapp/service_account.json"
   ```

3. **`.gitignore`에 추가**
   ```bash
   echo "service_account.json" >> /home/user/webapp/.gitignore
   ```

---

## Part 2. Webhook Secret Token 설정

### 2-1. Secret Token 생성

- 무작위 문자열 생성 (32자 이상 권장):
  ```bash
  openssl rand -hex 32
  ```
  또는 온라인 도구 사용: https://www.random.org/strings/

- 예시: `a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6q7r8s9t0u1v2w3x4y5z6`

### 2-2. Streamlit Secrets에 추가

`/home/user/webapp/.streamlit/secrets.toml`에 추가:

```toml
# Webhook secret token
webhook_secret = "a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6q7r8s9t0u1v2w3x4y5z6"
```

### 2-3. Google Apps Script에 Secret 저장

1. **Google Sheets 열기** → Extensions → Apps Script
2. **스크립트 에디터**에서:
   - 좌측 "프로젝트 설정" (톱니바퀴 아이콘) 클릭
   - "스크립트 속성" 섹션으로 이동
   - "스크립트 속성 추가" 클릭
   - 속성: `WEBHOOK_SECRET`
   - 값: `a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6q7r8s9t0u1v2w3x4y5z6` (위에서 생성한 토큰)
   - "스크립트 속성 저장" 클릭

---

## Part 3. 설정 확인 체크리스트

### ✅ Google Cloud Console
- [ ] 프로젝트 생성 완료
- [ ] Google Sheets API 활성화 완료
- [ ] Service Account 생성 완료
- [ ] JSON 키 다운로드 완료

### ✅ Google Sheets
- [ ] Service Account 이메일을 Sheets에 공유 (뷰어 권한)
- [ ] 공유 대상 목록에 Service Account 표시됨

### ✅ Streamlit 앱
- [ ] `.streamlit/secrets.toml` 파일 생성
- [ ] Service Account JSON 내용을 TOML로 변환하여 입력
- [ ] `webhook_secret` 추가
- [ ] `.gitignore`에 `secrets.toml` 추가

### ✅ Google Apps Script
- [ ] 스크립트 속성에 `WEBHOOK_SECRET` 추가

---

## 트러블슈팅

### 문제 1: "Permission denied" 또는 "403 Forbidden"

**원인**: Service Account가 Sheets에 공유되지 않음

**해결**:
1. Service Account 이메일을 정확히 복사 (JSON의 `client_email`)
2. Google Sheets → 공유 → Service Account 이메일 추가 (뷰어)
3. 알림 보내기 체크 해제

### 문제 2: "Invalid private key"

**원인**: `private_key`의 줄바꿈 문자가 손상됨

**해결**:
- JSON 파일에서 `private_key` 값을 그대로 복사
- `\n`을 실제 줄바꿈으로 변환하지 말 것
- TOML 파일에서는 큰따옴표(`"`) 안에 `\n`이 문자열로 유지되어야 함

### 문제 3: "API has not been used"

**원인**: Google Sheets API가 활성화되지 않음

**해결**:
1. Google Cloud Console → API 및 서비스 → 라이브러리
2. "Google Sheets API" 검색 → 사용 클릭

### 문제 4: Webhook 요청이 실패함

**원인**: Secret token 불일치

**해결**:
1. Streamlit `secrets.toml`의 `webhook_secret` 확인
2. Google Apps Script의 스크립트 속성 `WEBHOOK_SECRET` 확인
3. 두 값이 정확히 일치해야 함

---

## 보안 권장 사항

### 🔒 절대 하지 말아야 할 것

- ❌ JSON 키 파일을 GitHub에 커밋
- ❌ `secrets.toml`을 GitHub에 커밋
- ❌ 코드에 Service Account 정보 하드코딩
- ❌ Secret token을 코드에 하드코딩

### ✅ 반드시 해야 할 것

- ✅ `.gitignore`에 `secrets.toml`, `service_account.json` 추가
- ✅ Service Account에 최소 권한만 부여 (Sheets 뷰어)
- ✅ Secret token은 `st.secrets` 또는 스크립트 속성으로만 관리
- ✅ JSON 키 파일은 안전한 곳에 백업

---

## 다음 단계

설정이 완료되면:

1. **패키지 설치**: `pip install -r requirements.txt`
2. **앱 실행**: `pm2 restart logistics-app`
3. **테스트**: Google Sheets B~F열 값 변경 → Streamlit 앱 즉시 반영 확인

자세한 내용은 `README.md` 참조.
