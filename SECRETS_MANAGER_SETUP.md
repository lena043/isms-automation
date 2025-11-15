# AWS Secrets Manager 설정 가이드

이 가이드는 환경변수 대신 AWS Secrets Manager에서 설정을 관리하는 방법을 설명합니다.

## 🔐 장점

1. **보안 강화**: 민감한 정보를 환경변수 대신 암호화된 Secrets Manager에 저장
2. **중앙 관리**: 여러 환경/서버에서 동일한 설정 사용
3. **버전 관리**: 설정 변경 이력 추적
4. **액세스 제어**: IAM으로 세밀한 권한 관리

## 📋 설정 방법

### 1. AWS CLI로 시크릿 생성

```bash
aws secretsmanager create-secret \
    --name dev/isms \
    --description "ISMS 자동화 도구 설정" \
    --secret-string '{
        "AWS_ACCOUNTS": [
            {
                "account_id": "123456789012",
                "role_arn": "arn:aws:iam::123456789012:role/Role1"
            },
            {
                "account_id": "987654321098",
                "role_arn": "arn:aws:iam::987654321098:role/Role2"
            }
        ],
        "AWS_DEFAULT_REGION": "ap-northeast-2",
        "AWS_SERVICES": "ec2,s3,rds",
        "AWS_SESSION_NAME": "isms-automation",
        "GOOGLE_CREDENTIALS": "{...service account json...}",
        "GOOGLE_SHEETS_ID": "1ABC...XYZ"
    }' \
    --region ap-northeast-2
```

### 2. AWS 콘솔에서 시크릿 생성

1. AWS 콘솔 > Secrets Manager 이동
2. "새 보안 암호 저장" 클릭
3. "다른 유형의 보안 암호" 선택
4. 키-값 쌍으로 입력:

| 키 | 값 | 설명 |
|---|---|---|
| AWS_ACCOUNTS | `[{"account_id":"123...","role_arn":"arn:..."}]` | 다중 계정 설정 (JSON 배열) |
| AWS_DEFAULT_REGION | `ap-northeast-2` | 기본 AWS 리전 |
| AWS_SERVICES | `ec2,s3,rds` | 조회할 서비스 목록 |
| AWS_SESSION_NAME | `isms-automation` | 세션 이름 |
| GOOGLE_CREDENTIALS | `{"type":"service_account",...}` | Google Service Account JSON |
| GOOGLE_SHEETS_ID | `1ABC...XYZ` | 대상 Google Sheets ID |

### 3. IAM 권한 설정

Secrets Manager 접근 권한이 필요합니다:

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "secretsmanager:GetSecretValue"
            ],
            "Resource": "arn:aws:secretsmanager:ap-northeast-2:123456789012:secret:isms-automation-config*"
        }
    ]
}
```

## 🚀 사용법

### 환경변수로 Secrets Manager 활성화

```bash
# Secrets Manager 활성화
export ISMS_SECRET_NAME='dev/isms'
export ISMS_SECRET_REGION='ap-northeast-2'  # 선택사항, 기본값: ap-northeast-2

# AWS 인증 (aws-vault 사용 권장)
aws-vault exec socar-sso-dev -- .venv/bin/python main.py
```

### 설정 우선순위

1. **Secrets Manager** (최우선)
2. **환경변수** (백업)
3. **기본값** (최종 백업)

## 📊 실행 결과

Secrets Manager 사용 시:

```
🚀 ISMS 자동화 도구 - 다중 계정 AWS 자원 조회
============================================================
🔐 Secrets Manager에서 설정 로드 중: dev/isms
✅ Secrets Manager에서 설정을 성공적으로 로드했습니다.
   AWS_ACCOUNTS: Secrets Manager에서 로드
   AWS_DEFAULT_REGION: Secrets Manager에서 로드
   AWS_SERVICES: Secrets Manager에서 로드
   GOOGLE_SHEETS_ID: Secrets Manager에서 로드
🔐 Secrets Manager에서 설정을 로드했습니다.
🌍 기본 리전: ap-northeast-2
🏢 조회할 계정 수: 2개
   1. 계정 123456789012 - arn:aws:iam::123456789012:role/Role1
   2. 계정 987654321098 - arn:aws:iam::987654321098:role/Role2
```

## 🔧 시크릿 업데이트

### AWS CLI로 업데이트

```bash
aws secretsmanager update-secret \
    --secret-id dev/isms \
    --secret-string '{
        "AWS_ACCOUNTS": [
            {
                "account_id": "999888777666",
                "role_arn": "arn:aws:iam::999888777666:role/NewRole"
            }
        ],
        "AWS_SERVICES": "ec2,rds",
        "AWS_DEFAULT_REGION": "ap-northeast-2",
        "GOOGLE_CREDENTIALS": "{...}",
        "GOOGLE_SHEETS_ID": "1ABC...XYZ"
    }' \
    --region ap-northeast-2
```

### 버전 관리

Secrets Manager는 자동으로 이전 버전을 보관합니다:

```bash
# 이전 버전으로 롤백
aws secretsmanager update-secret-version-stage \
    --secret-id dev/isms \
    --version-stage AWSCURRENT \
    --move-to-version-id previous-version-id
```

## 🛠️ 문제 해결

### 시크릿을 찾을 수 없습니다

```
❌ 시크릿을 찾을 수 없습니다: dev/isms
```

**해결 방법:**
- 시크릿 이름이 정확한지 확인
- 올바른 리전에 생성되었는지 확인
- IAM 권한이 있는지 확인

### 권한 부족

```
❌ Secrets Manager 오류 (AccessDenied): ...
```

**해결 방법:**
- IAM 정책에 `secretsmanager:GetSecretValue` 권한 추가
- 시크릿의 ARN이 정확한지 확인

### JSON 파싱 오류

**해결 방법:**
- 시크릿 값이 유효한 JSON 형식인지 확인
- 특수 문자는 이스케이프 처리

## 🔒 보안 모범 사례

1. **최소 권한 원칙**: 필요한 시크릿에만 접근 권한 부여
2. **리전 분리**: 환경별로 다른 리전에 시크릿 저장
3. **암호화**: 고객 관리 KMS 키 사용 고려
4. **액세스 로깅**: CloudTrail로 시크릿 접근 모니터링
5. **정기 로테이션**: 민감한 값들의 정기적 업데이트

## 📝 예시 설정 템플릿

### 전체 설정 예시

```json
{
  "AWS_ACCOUNTS": [
    {
      "account_id": "111222333444",
      "role_arn": "arn:aws:iam::111222333444:role/ProdRole"
    },
    {
      "account_id": "555666777888",
      "role_arn": "arn:aws:iam::555666777888:role/DevRole"
    }
  ],
  "AWS_DEFAULT_REGION": "ap-northeast-2",
  "AWS_SERVICES": "ec2,s3,rds",
  "AWS_SESSION_NAME": "isms-automation",
  "GOOGLE_CREDENTIALS": {
    "type": "service_account",
    "project_id": "your-project-id",
    "private_key_id": "key-id",
    "private_key": "-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----\n",
    "client_email": "isms-sheet-update@your-project.iam.gserviceaccount.com",
    "client_id": "123456789",
    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
    "token_uri": "https://oauth2.googleapis.com/token",
    "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
    "client_x509_cert_url": "https://www.googleapis.com/robot/v1/metadata/x509/..."
  },
  "GOOGLE_SHEETS_ID": "1ABC123XYZ456DEF789GHI"
}
```

### 최소 설정 예시

```json
{
  "AWS_ACCOUNTS": [
    {
      "account_id": "123456789012",
      "role_arn": "arn:aws:iam::123456789012:role/YourRole"
    }
  ],
  "AWS_DEFAULT_REGION": "ap-northeast-2",
  "AWS_SERVICES": "ec2,s3,rds",
  "GOOGLE_CREDENTIALS": "{...service account json...}",
  "GOOGLE_SHEETS_ID": "1ABC...XYZ"
}
```