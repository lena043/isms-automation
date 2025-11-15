# Google Drive 연동 설정 가이드

이 가이드는 AWS 인벤토리 Excel 파일을 자동으로 Google Sheets로 업로드하는 방법을 설명합니다.

## 📋 사전 준비사항

### 1. Python 라이브러리 설치

```bash
pip install google-api-python-client google-auth-httplib2 google-auth-oauthlib
```

### 2. Google Cloud Console 설정

#### 2.1 프로젝트 생성
1. [Google Cloud Console](https://console.cloud.google.com) 접속
2. 새 프로젝트 생성 또는 기존 프로젝트 선택

#### 2.2 API 활성화
1. **Google Drive API** 활성화
   - 탐색 메뉴 > API 및 서비스 > 라이브러리
   - "Google Drive API" 검색 후 활성화

2. **Google Sheets API** 활성화
   - "Google Sheets API" 검색 후 활성화

#### 2.3 OAuth 2.0 자격 증명 생성
1. 탐색 메뉴 > API 및 서비스 > 사용자 인증 정보
2. "+ 사용자 인증 정보 만들기" > OAuth 클라이언트 ID
3. 애플리케이션 유형: **데스크톱 애플리케이션**
4. 이름 입력 (예: "ISMS Automation")
5. **만들기** 클릭

#### 2.4 자격증명 파일 다운로드
1. 생성된 OAuth 클라이언트의 ⬇️ 다운로드 버튼 클릭
2. JSON 파일을 `credentials.json` 이름으로 저장
3. 프로젝트 루트 디렉토리에 배치

```
isms-automation/
├── credentials.json      ← 여기에 저장
├── main.py
├── services/
└── ...
```

## 🚀 사용법

### 1. 환경변수 설정

```bash
# Google Drive 업로드 활성화
export GOOGLE_DRIVE_UPLOAD=true

# 자격증명 파일 경로 (기본값: credentials.json)
export GOOGLE_CREDENTIALS_FILE=credentials.json

# 업로드할 폴더 ID (선택사항)
export GOOGLE_DRIVE_FOLDER_ID=your-folder-id
```

### 2. 폴더 ID 찾는 방법 (선택사항)

특정 Google Drive 폴더에 업로드하려면:

1. Google Drive에서 원하는 폴더 열기
2. URL에서 폴더 ID 복사
   ```
   https://drive.google.com/drive/folders/1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74mMJ6jT
                                        ↑ 이 부분이 폴더 ID
   ```

### 3. 실행

```bash
python main.py
```

## 🔄 최초 실행 시

1. 브라우저가 자동으로 열림
2. Google 계정 로그인
3. 앱 권한 승인
4. "token.json" 파일이 자동 생성됨 (다음부터는 자동 인증)

## 📊 결과

성공 시 다음과 같은 출력이 표시됩니다:

```
☁️  Google Drive 업로드 중...
📤 Google Sheets로 업로드 중: inventory_202511121430
✅ Google Sheets 업로드 완료!
📄 파일 ID: 1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74mMJ6jT
🔗 Google Sheets URL: https://docs.google.com/spreadsheets/d/1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74mMJ6jT/edit

🔗 Google Sheets 링크:
   https://docs.google.com/spreadsheets/d/1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74mMJ6jT/edit

📝 이제 Google Sheets에서 데이터를 확인하고 비교할 수 있습니다!
```

## 🎯 Google Sheets에서 데이터 비교

업로드된 Google Sheets에서:

1. **필터 기능**: 특정 계정이나 리전만 표시
2. **정렬**: 리소스 수량, 생성일 등으로 정렬
3. **조건부 서식**: 특정 조건에 해당하는 셀 강조
4. **차트**: 계정별, 리전별 리소스 분포 차트 생성
5. **공유**: 팀원들과 실시간 협업

## ❗ 문제 해결

### 자격증명 파일을 찾을 수 없습니다
```
❌ Google API 자격증명 파일을 찾을 수 없습니다: credentials.json
```
- `credentials.json` 파일이 올바른 위치에 있는지 확인
- 파일명이 정확한지 확인

### 라이브러리 설치 오류
```
⚠️  Google Drive 기능을 사용하려면 다음을 설치하세요:
   pip install google-api-python-client google-auth-httplib2 google-auth-oauthlib
```
- 가상환경이 활성화되어 있는지 확인
- 명령어를 정확히 실행

### 권한 오류
- Google Cloud Console에서 API가 활성화되었는지 확인
- OAuth 동의 화면 설정 확인
- 브라우저에서 쿠키/캐시 삭제 후 재시도

## 🔒 보안 고려사항

1. **자격증명 파일**: `credentials.json`과 `token.json`을 Git에 커밋하지 마세요
2. **폴더 권한**: 업로드할 Google Drive 폴더의 공유 설정 확인
3. **API 할당량**: Google Drive API 일일 사용량 제한 고려

## 📝 .gitignore 설정

프로젝트에 다음 내용을 `.gitignore`에 추가하세요:

```gitignore
# Google API 자격증명
credentials.json
token.json

# Excel 출력 파일
*.xlsx
```