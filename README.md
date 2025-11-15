# ISMS 자동화 도구 🚀

AWS 다중 계정에서 WorkSpaces, EC2, S3, RDS 리소스를 조회하여 Google Sheets로 직접 업데이트하는 도구입니다.

## ✨ 주요 기능

- 🏢 **다중 계정 지원**: 여러 AWS 계정에서 리소스를 동시에 조회
- 🌍 **다중 리전 지원**: 전체 AWS 리전에서 리소스 검색
- 🔐 **Role 기반 인증**: IAM Role Assume을 통한 안전한 접근
- 🗝️ **Secrets Manager 통합**: AWS Secrets Manager로 보안 설정 관리
- 📊 **Google Sheets 직접 업데이트**: 로컬 파일 없이 바로 Sheets로 업로드
- 🎨 **서비스별 워크시트 자동 생성**: ec2-20251114, s3-20251114 형식으로 구분
- 🔍 **일별 변경사항 비교**: 어제와 오늘 데이터를 비교하여 색상 하이라이팅
- ⚡ **병렬 처리**: 빠른 조회를 위한 멀티스레딩 지원
- 🎯 **선택적 서비스**: 필요한 AWS 서비스만 선택하여 조회

## 📦 지원 서비스

- **WorkSpaces**: 가상 데스크톱 인스턴스 정보
- **EC2**: 인스턴스, 볼륨, 네트워크 인터페이스 등
- **S3**: 버킷 및 객체 정보
- **RDS**: 데이터베이스 인스턴스 및 클러스터 정보

## 🛠️ 설치 및 설정

### 1. 가상환경 생성 및 활성화

```bash
python3 -m venv .venv
source .venv/bin/activate  # Linux/Mac
# 또는 
.venv\Scripts\activate  # Windows
```

### 2. 의존성 설치

```bash
pip install -r requirements.txt
```

### 3. 설정 방법

#### 🔐 AWS Secrets Manager 사용 (권장)

보안을 위해 AWS Secrets Manager에서 설정을 관리하는 방법입니다.

자세한 설정 방법은 [SECRETS_MANAGER_SETUP.md](SECRETS_MANAGER_SETUP.md)를 참조하세요.

```bash
# Secrets Manager 활성화
export ISMS_SECRET_NAME='dev/isms'
export ISMS_SECRET_REGION='ap-northeast-2'

# AWS 인증 (Secrets Manager 접근용)
# aws-vault 또는 IAM 자격 증명 사용
```

#### 필수 Secrets Manager 설정 항목

```json
{
  "AWS_ACCOUNTS": [
    {
      "account_id": "123456789012",
      "role_arn": "arn:aws:iam::123456789012:role/YourRole"
    }
  ],
  "AWS_DEFAULT_REGION": "ap-northeast-2",
  "AWS_SESSION_NAME": "isms-automation",
  "AWS_SERVICES": "ec2,s3,rds",
  "GOOGLE_CREDENTIALS": "{...service account json...}",
  "GOOGLE_SHEETS_ID": "1ABC...XYZ"
}

## 🚀 사용법

### 기본 실행 (AWS 데이터 수집 + Sheets 업데이트)

```bash
export ISMS_SECRET_NAME="dev/isms"
aws-vault exec socar-sso-dev -- .venv/bin/python main.py
```

### 특정 서비스만 조회

Secrets Manager의 `AWS_SERVICES` 값을 수정하거나 환경변수로 오버라이드:

```bash
# EC2와 RDS만 조회
export AWS_SERVICES="ec2,rds"
export ISMS_SECRET_NAME="dev/isms"
aws-vault exec socar-sso-dev -- .venv/bin/python main.py
```

## 🔍 비교 기능 (별도 스크립트)

### 간단 비교 - EC2 서버 비교

```bash
# 쏘카_자산현황_Automation vs AWS 수집 시트
export TARGET_SHEET_ID="AWS_수집_시트_ID"
export TARGET_WORKSHEET="ec2-20251114"
export ISMS_SECRET_NAME="dev/isms"
aws-vault exec socar-sso-dev -- .venv/bin/python compare_ec2_simple.py
```

**출력 예시:**
- ✅ 양쪽 모두 존재하는 서버
- � 쏘카 문서에만 있는 서버 (AWS에 없음)
- 🆕 AWS에만 있는 서버 (쏘카 문서에 없음)

### 고급 비교 - 워크시트 직접 지정

```bash
# 특정 워크시트 비교 및 색상 표시
export SOURCE_SHEET_ID="1Ek32..."  # 쏘카_자산현황_Automation
export SOURCE_WORKSHEET="1.서버(Linux,Window)"
export TARGET_SHEET_ID="1uD91..."  # AWS 수집 시트
export TARGET_WORKSHEET="ec2-20251114"
export ISMS_SECRET_NAME="dev/isms"
aws-vault exec socar-sso-dev -- .venv/bin/python compare_sheets.py
```

**색상 코드:**
- 🟢 **초록색**: 타겟에만 있는 항목 (신규/추가)
- 🔴 **빨간색**: 소스에만 있는 항목 (삭제/누락)

## 📊 Google Sheets 출력 형식

### 워크시트 구조

자동으로 생성되는 워크시트 (날짜별):

```
📄 Google Sheets 문서
├─ ec2-20251114      (오늘 EC2 데이터)
├─ ec2-20251113      (어제 EC2 데이터)
├─ s3-20251114       (오늘 S3 데이터)
├─ s3-20251113       (어제 S3 데이터)
├─ rds-20251114      (오늘 RDS 데이터)
└─ rds-20251113      (어제 RDS 데이터)
```

### 워크시트별 컬럼

**EC2 워크시트:**
- InstanceId, InstanceName, InstanceType, State
- Platform, PrivateIpAddress, PublicIpAddress
- LaunchTime, Region, AccountID

**S3 워크시트:**
- BucketName, CreationDate, Region, AccountID

**RDS 워크시트:**
- DBInstanceIdentifier, DBInstanceClass, Engine
- EngineVersion, DBInstanceStatus, Endpoint
- AllocatedStorage, MultiAZ, Region, AccountID

## 🏗️ 프로젝트 구조

```
isms-automation/
├── config/                     # 설정 관리 모듈
│   ├── __init__.py
│   ├── config.py              # 주요 설정 클래스
│   ├── aws_auth.py            # AWS 인증 관리
│   ├── aws_regions.py         # AWS 리전 정보
│   └── secrets_manager.py     # Secrets Manager 통합
├── services/                   # AWS 서비스별 조회 모듈
│   ├── __init__.py
│   ├── base.py               # 공통 서비스 기본 클래스
│   ├── workspaces_service.py # WorkSpaces 조회
│   ├── ec2_service.py        # EC2 조회
│   ├── s3_service.py         # S3 조회
│   └── rds_service.py        # RDS 조회
├── exporters/                  # 내보내기 모듈
│   ├── __init__.py
│   ├── sheets_updater.py     # Google Sheets 직접 업데이트
│   └── sheets_comparator.py  # 일별 시트 비교 및 색상 표시
├── tests/                     # 테스트 파일
│   ├── check_config.py       # 설정 검증
│   └── test_sheets.py        # Sheets 업데이트 테스트
├── main.py                    # 메인 실행 파일 (데이터 수집 + Sheets 업데이트)
├── compare_sheets.py          # 고급 비교 도구 (색상 표시)
├── compare_ec2_simple.py      # 간단 EC2 비교 도구
├── requirements.txt           # Python 의존성
├── README.md                  # 프로젝트 문서
└── SECRETS_MANAGER_SETUP.md   # Secrets Manager 설정 가이드
```

## ⚠️ 권한 요구사항

### AWS IAM 권한

실행하려는 Role에는 다음 권한이 필요합니다:

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "workspaces:Describe*",
                "ec2:Describe*",
                "s3:ListAllMyBuckets",
                "s3:GetBucketLocation",
                "s3:ListBucket",
                "rds:Describe*",
                "secretsmanager:GetSecretValue"
            ],
            "Resource": "*"
        }
    ]
}
```

### Cross Account 접근

다른 계정에 접근하려면 신뢰 정책이 필요합니다:

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Principal": {
                "AWS": "arn:aws:iam::YOUR-ACCOUNT:user/your-user"
            },
            "Action": "sts:AssumeRole",
            "Condition": {
                "StringEquals": {
                    "sts:ExternalId": "your-external-id"
                }
            }
        }
    ]
}
```

## 🔧 문제 해결

### 자주 발생하는 오류

#### 1. 권한 오류
```
botocore.exceptions.ClientError: ... AccessDenied
```
**해결책**: IAM 권한을 확인하고 필요한 정책을 추가하세요.

#### 2. Role Assume 실패
```
Unable to assume role: An error occurred (AccessDenied) when calling the AssumeRole operation
```
**해결책**: 
- Role의 신뢰 정책 확인
- `AWS_EXTERNAL_ID` 설정 확인
- 계정 ID와 Role ARN이 정확한지 확인

#### 3. Google Sheets 접근 실패
```
HttpError 400: This operation is not supported for this document
```
**해결책**:
- Service Account 이메일을 Google Sheets에 추가 (편집자 권한)
- Sheet ID가 올바른지 확인
- Google Sheets API가 활성화되었는지 확인

#### 4. Secrets Manager 접근 오류
```
❌ 시크릿을 찾을 수 없습니다
```
**해결책**:
- `ISMS_SECRET_NAME`과 `ISMS_SECRET_REGION` 설정 확인
- IAM에서 `secretsmanager:GetSecretValue` 권한 확인
- 시크릿이 올바른 리전에 생성되었는지 확인

## 📝 Google Sheets API 설정

### 1. Google Cloud Console 설정

1. [Google Cloud Console](https://console.cloud.google.com/) 접속
2. 새 프로젝트 생성 또는 기존 프로젝트 선택
3. API 및 서비스 → 라이브러리 → "Google Sheets API" 검색 및 활성화

### 2. Service Account 생성

1. IAM 및 관리자 → 서비스 계정
2. "서비스 계정 만들기" 클릭
3. 이름: `isms-sheet-update` (또는 원하는 이름)
4. 역할: 프로젝트 편집자 (또는 최소 권한)
5. "키 만들기" → JSON 형식 선택 → 다운로드

### 3. Secrets Manager에 저장

다운로드한 JSON 파일 내용을 Secrets Manager의 `GOOGLE_CREDENTIALS`에 저장:

```bash
# JSON 파일 내용을 한 줄로 변환하여 저장
cat service-account-key.json | jq -c . > credentials-oneline.json
```

### 4. Google Sheets 공유

1. 대상 Google Sheets 문서 열기
2. 오른쪽 상단 "공유" 클릭
3. Service Account 이메일 추가 (예: `isms-sheet-update@project-id.iam.gserviceaccount.com`)
4. 권한: **편집자** 선택
5. 완료

### 5. Sheet ID 확인

Google Sheets URL에서 ID 추출:
```
https://docs.google.com/spreadsheets/d/1ABC123XYZ/edit
                                        ↑ 이 부분이 Sheet ID
```

Secrets Manager의 `GOOGLE_SHEETS_ID`에 저장:
```json
{
  "GOOGLE_SHEETS_ID": "1ABC123XYZ"
}
```

## 🤝 기여하기

버그 리포트, 기능 제안, 풀 리퀘스트를 환영합니다!

## 📄 라이센스

이 프로젝트는 MIT 라이센스 하에 배포됩니다.
