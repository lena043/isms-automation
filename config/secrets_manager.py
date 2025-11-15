"""
AWS Secrets Manager 연동 모듈
설정 정보를 Secrets Manager에서 로드합니다.
"""

import json
import os
from typing import Dict, Optional, Any
from dataclasses import dataclass
import boto3
from botocore.exceptions import ClientError


@dataclass
class SecretsManagerConfig:
    """Secrets Manager 연동 설정"""
    secret_name: str
    region: str = 'ap-northeast-2'
    aws_access_key_id: Optional[str] = None
    aws_secret_access_key: Optional[str] = None
    aws_session_token: Optional[str] = None
    
    @classmethod
    def from_environment(cls) -> 'SecretsManagerConfig':
        """환경변수에서 Secrets Manager 설정을 로드합니다."""
        return cls(
            secret_name=os.getenv('ISMS_SECRET_NAME', 'isms-automation-config'),
            region=os.getenv('ISMS_SECRET_REGION', 'ap-northeast-2'),
            aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
            aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY'),
            aws_session_token=os.getenv('AWS_SESSION_TOKEN')
        )


def get_secret_client(config: SecretsManagerConfig):
    """Secrets Manager 클라이언트를 생성합니다."""
    client_kwargs = {
        'service_name': 'secretsmanager',
        'region_name': config.region
    }
    
    # AWS 인증 정보가 있으면 사용
    if config.aws_access_key_id and config.aws_secret_access_key:
        client_kwargs.update({
            'aws_access_key_id': config.aws_access_key_id,
            'aws_secret_access_key': config.aws_secret_access_key
        })
        
        if config.aws_session_token:
            client_kwargs['aws_session_token'] = config.aws_session_token
    
    return boto3.client(**client_kwargs)


def get_secret_value(secret_name: str, region: str = 'ap-northeast-2') -> Optional[Dict[str, Any]]:
    """
    Secrets Manager에서 시크릿 값을 가져옵니다.
    
    Args:
        secret_name: 시크릿 이름
        region: AWS 리전
        
    Returns:
        시크릿 값 (JSON 파싱된 dict) 또는 None
    """
    try:
        config = SecretsManagerConfig(secret_name=secret_name, region=region)
        client = get_secret_client(config)
        
        response = client.get_secret_value(SecretId=secret_name)
        secret_string = response['SecretString']
        
        # JSON 파싱 시도
        try:
            return json.loads(secret_string)
        except json.JSONDecodeError:
            # JSON이 아닌 경우 문자열 그대로 반환
            return {'value': secret_string}
            
    except ClientError as e:
        error_code = e.response['Error']['Code']
        if error_code == 'ResourceNotFoundException':
            print(f"❌ 시크릿을 찾을 수 없습니다: {secret_name}")
        elif error_code == 'InvalidRequestException':
            print(f"❌ 잘못된 요청: {secret_name}")
        elif error_code == 'InvalidParameterException':
            print(f"❌ 잘못된 매개변수: {secret_name}")
        elif error_code == 'DecryptionFailureException':
            print(f"❌ 복호화 실패: {secret_name}")
        elif error_code == 'InternalServiceErrorException':
            print(f"❌ 내부 서비스 오류: {secret_name}")
        else:
            print(f"❌ Secrets Manager 오류 ({error_code}): {e}")
        return None
    except Exception as e:
        print(f"❌ 예상치 못한 오류: {e}")
        return None


def get_config_from_secrets(secret_name: Optional[str] = None, region: Optional[str] = None) -> Dict[str, Any]:
    """
    Secrets Manager에서 전체 설정을 가져옵니다.
    
    Expected secret format:
    {
        "aws_accounts": "123456789012:arn:aws:iam::123456789012:role/Role1,987654321098:arn:aws:iam::987654321098:role/Role2",
        "aws_account_id": "123456789012",
        "aws_role_arn": "arn:aws:iam::123456789012:role/YourRole",
        "aws_default_region": "ap-northeast-2",
        "aws_services": "workspaces,ec2,s3,rds",
        "aws_session_name": "isms-automation",
        "aws_external_id": "external-id",
        "google_drive_upload": "true",
        "google_credentials_file": "credentials.json",
        "google_drive_folder_id": "your-folder-id"
    }
    
    Args:
        secret_name: 시크릿 이름 (기본값: 환경변수에서 가져옴)
        region: AWS 리전 (기본값: 환경변수에서 가져옴)
        
    Returns:
        설정 딕셔너리
    """
    # 환경변수에서 기본값 가져오기
    if not secret_name:
        secret_name = os.getenv('ISMS_SECRET_NAME', 'isms-automation-config')
    if not region:
        region = os.getenv('ISMS_SECRET_REGION', 'ap-northeast-2')
    
    print(f"🔐 Secrets Manager에서 설정 로드 중: {secret_name}")
    
    secret_data = get_secret_value(secret_name, region)
    if not secret_data:
        print("❌ Secrets Manager에서 설정을 가져오지 못했습니다. 환경변수 사용.")
        return {}
    
    print("✅ Secrets Manager에서 설정을 성공적으로 로드했습니다.")
    return secret_data


def merge_config_with_secrets(env_config: Dict[str, Any], secrets_config: Dict[str, Any]) -> Dict[str, Any]:
    """
    환경변수 설정과 Secrets Manager 설정을 병합합니다.
    Secrets Manager 값이 우선순위를 가집니다.
    
    Args:
        env_config: 환경변수에서 로드한 설정
        secrets_config: Secrets Manager에서 로드한 설정
        
    Returns:
        병합된 설정
    """
    # 환경변수 설정으로 시작
    merged = env_config.copy()
    
    # Secrets Manager 키를 환경변수 키 형태로 매핑 (대문자 키도 지원)
    key_mapping = {
        'AWS_ACCOUNTS': 'AWS_ACCOUNTS',
        'AWS_ACCOUNT_ID': 'AWS_ACCOUNT_ID',
        'AWS_ROLE_ARN': 'AWS_ROLE_ARN',
        'AWS_DEFAULT_REGION': 'AWS_DEFAULT_REGION',
        'AWS_SERVICES': 'AWS_SERVICES',
        'AWS_EXTERNAL_ID': 'AWS_EXTERNAL_ID',
        'GOOGLE_DRIVE_UPLOAD': 'GOOGLE_DRIVE_UPLOAD',
        'GOOGLE_CREDENTIALS': 'GOOGLE_CREDENTIALS',
        'GOOGLE_SHEETS_ID': 'GOOGLE_SHEETS_ID'
    }
    
    # Secrets Manager 값으로 업데이트
    for secret_key, env_key in key_mapping.items():
        if secret_key in secrets_config and secrets_config[secret_key]:
            # AWS_ACCOUNTS가 JSON 배열인 경우 그대로 전달
            if secret_key == 'AWS_ACCOUNTS' and isinstance(secrets_config[secret_key], list):
                merged[env_key] = secrets_config[secret_key]
            else:
                merged[env_key] = secrets_config[secret_key]
            print(f"   {env_key}: Secrets Manager에서 로드")
    
    return merged


def create_secret_example(secret_name: str, region: str = 'ap-northeast-2') -> str:
    """
    Secrets Manager에 저장할 설정 예시를 생성합니다.
    
    Args:
        secret_name: 시크릿 이름
        region: AWS 리전
        
    Returns:
        JSON 형태의 설정 예시
    """
    example_config = {
        "aws_accounts": "123456789012:arn:aws:iam::123456789012:role/Role1,987654321098:arn:aws:iam::987654321098:role/Role2",
        "aws_account_id": "123456789012",
        "aws_role_arn": "arn:aws:iam::123456789012:role/YourRole",
        "aws_default_region": "ap-northeast-2",
        "aws_services": "workspaces,ec2,s3,rds",
        "aws_session_name": "isms-automation",
        "aws_external_id": "",
        "google_drive_upload": "false",
        "google_credentials_file": "credentials.json",
        "google_drive_folder_id": ""
    }
    
    return json.dumps(example_config, indent=2, ensure_ascii=False)


def update_secret(secret_name: str, config_dict: Dict[str, Any], region: str = 'ap-northeast-2') -> bool:
    """
    Secrets Manager에 설정을 업데이트합니다.
    
    Args:
        secret_name: 시크릿 이름
        config_dict: 업데이트할 설정 딕셔너리
        region: AWS 리전
        
    Returns:
        성공 여부
    """
    try:
        config = SecretsManagerConfig(secret_name=secret_name, region=region)
        client = get_secret_client(config)
        
        # JSON 문자열로 변환
        secret_string = json.dumps(config_dict, ensure_ascii=False, indent=2)
        
        # 시크릿 업데이트
        client.update_secret(
            SecretId=secret_name,
            SecretString=secret_string
        )
        
        print(f"✅ Secrets Manager 업데이트 성공: {secret_name}")
        return True
        
    except ClientError as e:
        error_code = e.response['Error']['Code']
        print(f"❌ Secrets Manager 업데이트 실패 ({error_code}): {e}")
        return False
    except Exception as e:
        print(f"❌ 예상치 못한 오류: {e}")
        return False


def print_secrets_manager_help():
    """Secrets Manager 설정 도움말을 출력합니다."""
    print("""
🔐 AWS Secrets Manager 연동 설정 가이드
=" * 50

## 1. 환경변수로 Secrets Manager 설정

export ISMS_SECRET_NAME='isms-automation-config'
export ISMS_SECRET_REGION='ap-northeast-2'

## 2. AWS Secrets Manager에 시크릿 생성

AWS CLI로 시크릿 생성:
aws secretsmanager create-secret \\
    --name isms-automation-config \\
    --description "ISMS 자동화 도구 설정" \\
    --secret-string '{
        "aws_accounts": "123456789012:arn:aws:iam::123456789012:role/Role1,987654321098:arn:aws:iam::987654321098:role/Role2",
        "aws_account_id": "123456789012",
        "aws_role_arn": "arn:aws:iam::123456789012:role/YourRole",
        "aws_default_region": "ap-northeast-2",
        "aws_services": "workspaces,ec2,s3,rds",
        "aws_session_name": "isms-automation",
        "aws_external_id": "",
        "google_drive_upload": "false",
        "google_credentials_file": "credentials.json",
        "google_drive_folder_id": ""
    }'

## 3. IAM 권한 설정

Secrets Manager 읽기 권한이 필요합니다:
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

## 4. 우선순위

1. Secrets Manager 값 (우선순위 높음)
2. 환경변수 값 (백업)

## 5. 사용법

# Secrets Manager 활성화
export ISMS_SECRET_NAME='isms-automation-config'

# 실행
python main.py
""")