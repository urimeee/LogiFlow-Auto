# ✅ Google Service Account 연동 완료 요약

---

## 🎯 구현 완료 내역

### 1. Google Service Account 인증 시스템

**구현된 기능**:
- ✅ gspread + google-auth 라이브러리로 비공개 Sheets 접근
- ✅ Service Account JSON 키를 `st.secrets`로 안전하게 관리
- ✅ B~F열 전체 데이터 읽기 (gid 기반)
- ✅ 앱 최초 실행 시 자동으로 Sheets에서 마스터 코드 로드

**파일**:
- `sheets_utils.py`: Service Account 인증 및 Sheets 데이터 읽기
- `requirements.txt`: gspread, google-auth 패키지 추가

---

### 2. Webhook Secret Token 검증

**구현된 기능**:
- ✅ Webhook 요청에 secret token 필수
- ✅ Token 불일치 시 401 Unauthorized 응답
- ✅ Token은 `st.secrets` 또는 환경변수로만 관리
- ✅ /health 엔드포인트에 token 설정 상태 표시

**파일**:
- `webhook_server.py`: Token 검증 로직 추가
- `.streamlit/secrets.toml.example`: Token 설정 템플릿

---

### 3. Google Apps Script

**구현된 기능**:
- ✅ B~F열 변경 감지 (onEdit 트리거)
- ✅ 변경 시 전체 시트 데이터를 Webhook으로 POST
- ✅ Secret token을 스크립트 속성으로 관리
- ✅ 설정 및 테스트 함수 제공

**파일**:
- `google_apps_script_service_account.js`

**주요 함수**:
- `onEdit()`: B~F열 변경 감지 및 웹훅 전송
- `setupTrigger()`: onEdit 트리거 자동 등록
- `testWebhook()`: 수동 테스트
- `checkConfiguration()`: 설정 상태 확인

---

### 4. 보안 설정

**구현된 보안 조치**:
- ✅ `.gitignore`에 secrets.toml, Service Account JSON 추가
- ✅ 인증 정보는 절대 코드에 하드코딩 안 됨
- ✅ Service Account는 최소 권한 (Sheets 뷰어)
- ✅ Webhook secret token은 32자 이상 무작위 문자열

---

### 5. 문서화

**생성된 가이드**:

1. **GOOGLE_SERVICE_ACCOUNT_SETUP.md** (6.2KB)
   - Service Account 발급 상세 가이드
   - Google Cloud Console 설정 방법
   - Sheets 공유 방법
   - 인증 정보 관리 방법
   - 트러블슈팅

2. **SETUP_GUIDE.md** (7.4KB)
   - 전체 설정 단계별 가이드
   - Google Cloud → Streamlit → Apps Script
   - 연동 테스트 방법
   - 보안 체크리스트
   - 트러블슈팅

3. **.streamlit/secrets.toml.example** (2.0KB)
   - Secrets 파일 템플릿
   - Service Account JSON 변환 방법
   - Webhook secret token 설정 방법

---

## 📋 사용자가 해야 할 작업 (체크리스트)

### Part 1: Google Cloud 설정

- [ ] Google Cloud Console 접속
- [ ] 프로젝트 생성: `logistics-sheets-integration` (예시)
- [ ] Google Sheets API 활성화
- [ ] Service Account 생성
- [ ] JSON 키 다운로드 (안전한 곳에 보관!)
- [ ] Service Account 이메일 복사

### Part 2: Google Sheets 공유

- [ ] 대상 Sheets 열기: https://docs.google.com/spreadsheets/d/1e7T7dANrJemFP1eouH02Wi4Ysoh08jmq77Rn_5pbzQs/edit
- [ ] "공유" 버튼 클릭
- [ ] Service Account 이메일 추가 (뷰어 권한)
- [ ] "알림 보내기" 체크 해제
- [ ] 공유 완료

### Part 3: Streamlit Secrets 설정

- [ ] `/home/user/webapp/.streamlit/secrets.toml` 파일 생성
- [ ] 다운로드한 JSON 키를 열어서 내용 복사
- [ ] TOML 형식으로 변환하여 붙여넣기
- [ ] Webhook secret token 생성: `openssl rand -hex 32`
- [ ] secrets.toml에 `webhook_secret` 추가
- [ ] 파일 저장

### Part 4: Google Apps Script 설정

- [ ] Google Sheets → Extensions → Apps Script
- [ ] `google_apps_script_service_account.js` 코드 붙여넣기
- [ ] `WEBHOOK_URL` 확인 (현재: https://5000-ip2l928h0vug305w91va9-d0b9e1e2.sandbox.novita.ai/webhook)
- [ ] 저장
- [ ] 프로젝트 설정 → 스크립트 속성
- [ ] `WEBHOOK_SECRET` 추가 (위에서 생성한 token)
- [ ] `setupTrigger()` 실행 (권한 승인)
- [ ] 트리거 탭에서 onEdit 확인

### Part 5: 테스트

- [ ] Apps Script에서 `checkConfiguration()` 실행 → 모두 ✅ 확인
- [ ] Apps Script에서 `testWebhook()` 실행 → "Webhook sent successfully" 확인
- [ ] Google Sheets B~F열 값 변경
- [ ] Streamlit 앱 새로고침 → 변경된 값 즉시 반영 확인

---

## 🔧 기술 구조

### 데이터 흐름

```
┌─────────────────────┐
│  Google Sheets      │
│  (비공개)           │
│  B~F열 데이터       │
└──────────┬──────────┘
           │
           │ 1. Service Account 인증
           │    (앱 최초 실행 시)
           ↓
┌─────────────────────┐
│  sheets_utils.py    │
│  - gspread client   │
│  - fetch_master()   │
└──────────┬──────────┘
           │
           │ 2. DataFrame 저장
           ↓
┌─────────────────────┐
│  master_codes.db    │
│  (SQLite)           │
└──────────┬──────────┘
           │
           │ 3. 앱에서 사용
           ↓
┌─────────────────────┐
│  Streamlit App      │
│  (port 3000)        │
└─────────────────────┘
```

### 실시간 업데이트 흐름

```
┌─────────────────────┐
│  Google Sheets      │
│  B~F열 값 변경      │
└──────────┬──────────┘
           │
           │ 1. onEdit 트리거 발동
           ↓
┌─────────────────────┐
│  Google Apps Script │
│  - 전체 데이터 읽기 │
│  - JSON 변환        │
└──────────┬──────────┘
           │
           │ 2. POST /webhook
           │    + secret token
           ↓
┌─────────────────────┐
│  webhook_server.py  │
│  (port 5000)        │
│  - Token 검증       │
│  - DB 저장          │
└──────────┬──────────┘
           │
           │ 3. DB 업데이트
           ↓
┌─────────────────────┐
│  master_codes.db    │
│  (최신 데이터)      │
└──────────┬──────────┘
           │
           │ 4. 앱에서 읽기
           ↓
┌─────────────────────┐
│  Streamlit App      │
│  (즉시 반영)        │
└─────────────────────┘
```

---

## 🔐 보안 아키텍처

### 인증 계층

1. **Sheets → Streamlit**:
   - Service Account JSON 키 (st.secrets)
   - OAuth 2.0 토큰 자동 생성
   - 읽기 전용 권한

2. **Apps Script → Webhook**:
   - Secret token 검증
   - 401 Unauthorized (실패 시)
   - Token은 스크립트 속성에 저장

3. **파일 시스템**:
   - secrets.toml: .gitignore로 보호
   - Service Account JSON: .gitignore로 보호
   - DB 파일: .gitignore로 보호

---

## 📂 프로젝트 구조

```
webapp/
├── app.py                                   # Streamlit 메인 앱
├── sheets_utils.py                          # ✨ Service Account 인증
├── webhook_server.py                        # ✨ Token 검증 웹훅
├── requirements.txt                         # ✨ gspread, google-auth 추가
├── ecosystem.config.cjs                     # PM2 설정
├── master_codes.db                          # SQLite DB
├── .streamlit/
│   ├── secrets.toml                         # ✨ 인증 정보 (git 제외)
│   └── secrets.toml.example                 # ✨ 템플릿
├── google_apps_script_service_account.js    # ✨ Apps Script 코드
├── GOOGLE_SERVICE_ACCOUNT_SETUP.md          # ✨ Service Account 가이드
├── SETUP_GUIDE.md                           # ✨ 전체 설정 가이드
└── .gitignore                               # ✨ 보안 파일 제외
```

---

## 🚀 배포 상태

- **Git Commit**: `68c4c0c`
- **GitHub Push**: ✅ 완료
- **버전**: v3.17
- **Repository**: https://github.com/urimeee/LogiFlow-Auto

---

## 📚 다음 단계

### 사용자가 직접 해야 할 작업:

1. **Google Cloud 설정 (10분)**
   - Service Account 생성
   - JSON 키 다운로드
   - Sheets 공유

2. **Secrets 파일 설정 (5분)**
   - secrets.toml 생성
   - JSON 키 내용 붙여넣기
   - Webhook secret token 추가

3. **Apps Script 설정 (5분)**
   - 코드 붙여넣기
   - Secret token 설정
   - 트리거 설치

4. **테스트 (2분)**
   - Sheets 값 변경
   - 앱에서 즉시 반영 확인

**예상 소요 시간**: 약 20~25분

---

## 🎉 기대 효과

### Before (기존 방식)

- ❌ 공개 CSV export URL만 사용 가능
- ❌ 비공개 Sheets는 접근 불가
- ❌ 401 Unauthorized 에러

### After (Service Account 인증)

- ✅ 비공개 Sheets 접근 가능
- ✅ 앱 최초 실행 시 자동 로드
- ✅ Sheets 변경 시 즉시 반영 (webhook)
- ✅ Polling 없이 실시간 동기화
- ✅ Secret token으로 보안 강화
- ✅ 모든 인증 정보는 st.secrets로 안전하게 관리

---

## 📞 문제 발생 시

1. **SETUP_GUIDE.md** → 트러블슈팅 섹션 참조
2. **GOOGLE_SERVICE_ACCOUNT_SETUP.md** → 상세 설정 방법 참조
3. Apps Script → `checkConfiguration()` 실행하여 설정 상태 확인
4. PM2 로그: `pm2 logs --nostream`

---

**완료 시간**: 2026-03-07  
**구현자**: AI Assistant (Claude)  
**버전**: v3.17
