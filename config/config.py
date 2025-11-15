"""
ISMS 자동화 도구 공통 설정 관리
환경변수, AWS Secrets Manager, 기본값, 검증 등을 담당
"""

import os
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field


@dataclass
class AWSConfig:
    """AWS 관련 설정"""
    region: str = 'ap-northeast-2'
    account_id: str = ''
    
    # 다중 계정 지원
    accounts: str = ''
    
    # 인증 키 방식
    access_key_id: Optional[str] = None
    secret_access_key: Optional[str] = None
    session_token: Optional[str] = None
    
    # IAM Role 방식
    role_arn: Optional[str] = None
    session_name: str = 'isms-automation'
    external_id: Optional[str] = None
    
    # 조회할 서비스 선택
    services: str = 'workspaces,ec2,s3,rds'
    
    # Google Sheets ID
    google_sheets_id: Optional[str] = None
    
    @classmethod
    def from_environment(cls) -> 'AWSConfig':
        """환경변수에서 AWS 설정을 로드합니다."""
        return cls(
            region=os.getenv('AWS_DEFAULT_REGION', 'ap-northeast-2'),
            account_id=os.getenv('AWS_ACCOUNT_ID', ''),
            accounts=os.getenv('AWS_ACCOUNTS', ''),
            access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
            secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY'),
            session_token=os.getenv('AWS_SESSION_TOKEN'),
            role_arn=os.getenv('AWS_ROLE_ARN'),
            session_name=os.getenv('AWS_SESSION_NAME', 'isms-automation'),
            external_id=os.getenv('AWS_EXTERNAL_ID'),
            services=os.getenv('AWS_SERVICES', 'workspaces,ec2,s3,rds'),
            google_sheets_id=os.getenv('GOOGLE_SHEETS_ID', '')
        )
    
    @classmethod
    def from_dict(cls, config_dict: Dict[str, Any]) -> 'AWSConfig':
        """딕셔너리에서 AWS 설정을 로드합니다."""
        return cls(
            region=config_dict.get('AWS_DEFAULT_REGION', 'ap-northeast-2'),
            account_id=config_dict.get('AWS_ACCOUNT_ID', ''),
            accounts=config_dict.get('AWS_ACCOUNTS', ''),
            access_key_id=config_dict.get('AWS_ACCESS_KEY_ID'),
            secret_access_key=config_dict.get('AWS_SECRET_ACCESS_KEY'),
            session_token=config_dict.get('AWS_SESSION_TOKEN'),
            role_arn=config_dict.get('AWS_ROLE_ARN'),
            session_name=config_dict.get('AWS_SESSION_NAME', 'isms-automation'),
            external_id=config_dict.get('AWS_EXTERNAL_ID'),
            services=config_dict.get('AWS_SERVICES', 'workspaces,ec2,s3,rds'),
            google_sheets_id=config_dict.get('GOOGLE_SHEETS_ID')
        )
    
    def has_credentials(self) -> bool:
        """AWS 인증 키가 설정되어 있는지 확인"""
        return all([
            self.access_key_id,
            self.secret_access_key,
            self.session_token
        ])
    
    def has_role(self) -> bool:
        """IAM Role 정보가 설정되어 있는지 확인"""
        return self.role_arn is not None
    
    def has_accounts(self) -> bool:
        """다중 계정 설정이 있는지 확인"""
        return bool(self.accounts)
    
    def validate_credentials(self) -> List[str]:
        """인증 키 설정 검증 (누락된 환경변수 반환)"""
        required_vars = []
        if not self.access_key_id:
            required_vars.append('AWS_ACCESS_KEY_ID')
        if not self.secret_access_key:
            required_vars.append('AWS_SECRET_ACCESS_KEY')
        if not self.session_token:
            required_vars.append('AWS_SESSION_TOKEN')
        return required_vars
    
    def validate_role(self) -> List[str]:
        """Role 설정 검증 (누락된 환경변수 반환)"""
        required_vars = []
        if not self.role_arn:
            required_vars.append('AWS_ROLE_ARN')
        return required_vars
    
    def validate_cross_account_role(self) -> List[str]:
        """Cross Account Role 설정 검증"""
        required_vars = self.validate_role()
        if not self.external_id:
            required_vars.append('AWS_EXTERNAL_ID')
        return required_vars


@dataclass  
class ServiceConfig:
    """서비스별 설정"""
    name: str
    enabled: bool = True
    config: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ISMSConfig:
    """ISMS 자동화 도구 전체 설정"""
    aws: AWSConfig = field(default_factory=AWSConfig)
    services: Dict[str, ServiceConfig] = field(default_factory=dict)
    output_format: str = 'table'  # table, json, csv
    verbose: bool = False
    use_secrets_manager: bool = False
    
    @classmethod
    def load(cls, use_secrets_manager: Optional[bool] = None) -> 'ISMSConfig':
        """설정을 로드합니다. (환경변수 + Secrets Manager)"""
        config = cls()
        
        # Secrets Manager 사용 여부 결정
        if use_secrets_manager is None:
            use_secrets_manager = bool(os.getenv('ISMS_SECRET_NAME'))
        
        config.use_secrets_manager = use_secrets_manager
        
        if use_secrets_manager:
            # Secrets Manager에서 설정 로드
            try:
                from .secrets_manager import get_config_from_secrets, merge_config_with_secrets
                
                # 환경변수로 기본 설정 로드
                env_config = {
                    'AWS_DEFAULT_REGION': os.getenv('AWS_DEFAULT_REGION', 'ap-northeast-2'),
                    'AWS_ACCOUNT_ID': os.getenv('AWS_ACCOUNT_ID', ''),
                    'AWS_ACCOUNTS': os.getenv('AWS_ACCOUNTS', ''),
                    'AWS_ROLE_ARN': os.getenv('AWS_ROLE_ARN'),
                    'AWS_SESSION_NAME': os.getenv('AWS_SESSION_NAME', 'isms-automation'),
                    'AWS_EXTERNAL_ID': os.getenv('AWS_EXTERNAL_ID'),
                    'AWS_SERVICES': os.getenv('AWS_SERVICES', 'workspaces,ec2,s3,rds'),
                    'GOOGLE_DRIVE_UPLOAD': os.getenv('GOOGLE_DRIVE_UPLOAD', 'false'),
                    'GOOGLE_CREDENTIALS_FILE': os.getenv('GOOGLE_CREDENTIALS_FILE', 'credentials.json'),
                    'GOOGLE_DRIVE_FOLDER_ID': os.getenv('GOOGLE_DRIVE_FOLDER_ID', '')
                }
                
                # Secrets Manager에서 설정 가져오기
                secrets_config = get_config_from_secrets()
                
                # 설정 병합 (Secrets Manager 우선)
                merged_config = merge_config_with_secrets(env_config, secrets_config)
                
                # AWS 설정 로드
                config.aws = AWSConfig.from_dict(merged_config)
                
            except Exception as e:
                print(f"⚠️  Secrets Manager 로드 실패, 환경변수 사용: {e}")
                config.aws = AWSConfig.from_environment()
        else:
            # 환경변수에서만 설정 로드
            config.aws = AWSConfig.from_environment()
        
        # 기타 설정
        config.verbose = os.getenv('ISMS_VERBOSE', 'false').lower() == 'true'
        config.output_format = os.getenv('ISMS_OUTPUT_FORMAT', 'table')
        
        # 서비스별 설정 (레거시 호환)
        config.services = {
            'workspaces': ServiceConfig(
                name='workspaces',
                enabled=os.getenv('ISMS_WORKSPACES_ENABLED', 'true').lower() == 'true'
            ),
            's3': ServiceConfig(
                name='s3',
                enabled=os.getenv('ISMS_S3_ENABLED', 'false').lower() == 'true'
            ),
            'ec2': ServiceConfig(
                name='ec2',
                enabled=os.getenv('ISMS_EC2_ENABLED', 'false').lower() == 'true'
            ),
            'rds': ServiceConfig(
                name='rds',
                enabled=os.getenv('ISMS_RDS_ENABLED', 'false').lower() == 'true'
            )
        }
        
        return config
    
    def get_available_auth_methods(self) -> List[str]:
        """사용 가능한 인증 방법 목록을 반환"""
        methods = []
        
        if self.aws.has_credentials():
            methods.append('credentials')
        
        if self.aws.has_role():
            methods.append('role')
            if self.aws.external_id:
                methods.append('cross_account')
        
        return methods
    
    def get_enabled_services(self) -> List[str]:
        """활성화된 서비스 목록을 반환"""
        return [
            name for name, service in self.services.items() 
            if service.enabled
        ]


def print_config_help():
    """설정 도움말을 출력합니다."""
    print("""
ISMS 자동화 도구 환경변수 설정 가이드
=" * 50

## AWS 인증 설정

### 1. AWS 인증 키 사용
export AWS_ACCESS_KEY_ID='your-access-key'
export AWS_SECRET_ACCESS_KEY='your-secret-key'  
export AWS_SESSION_TOKEN='your-session-token'
export AWS_DEFAULT_REGION='us-east-1'
export AWS_ACCOUNT_ID='123456789012'

### 2. IAM Role 사용
export AWS_ROLE_ARN='arn:aws:iam::123456789012:role/YourRole'
export AWS_DEFAULT_REGION='us-east-1'
export AWS_ACCOUNT_ID='123456789012'
export AWS_SESSION_NAME='custom-session-name'  # 선택사항

### 3. Cross Account IAM Role 사용
export AWS_ROLE_ARN='arn:aws:iam::987654321098:role/CrossAccountRole'
export AWS_EXTERNAL_ID='unique-external-id-12345'
export AWS_DEFAULT_REGION='us-west-2'
export AWS_ACCOUNT_ID='987654321098'

## 서비스 활성화 설정
export ISMS_WORKSPACES_ENABLED='true'   # WorkSpaces 조회 활성화
export ISMS_S3_ENABLED='true'           # S3 조회 활성화 (향후)
export ISMS_EC2_ENABLED='true'          # EC2 조회 활성화 (향후)

## 출력 설정
export ISMS_OUTPUT_FORMAT='table'       # table, json, csv
export ISMS_VERBOSE='true'              # 상세 출력 활성화
""")


def validate_config(config: ISMSConfig) -> List[str]:
    """전체 설정을 검증하고 오류 메시지를 반환합니다."""
    errors = []
    
    # AWS 설정 검증
    if not config.aws.account_id:
        errors.append("AWS_ACCOUNT_ID가 설정되지 않았습니다.")
    
    # 인증 방법이 하나도 없는 경우
    if not config.aws.has_credentials() and not config.aws.has_role():
        errors.append("AWS 인증 정보가 설정되지 않았습니다. (인증 키 또는 IAM Role 중 하나 필요)")
    
    # 활성화된 서비스가 없는 경우
    if not config.get_enabled_services():
        errors.append("활성화된 서비스가 없습니다.")
    
    return errors


# 전역 설정 인스턴스
_config_instance: Optional[ISMSConfig] = None


def get_config() -> ISMSConfig:
    """전역 설정 인스턴스를 반환합니다."""
    global _config_instance
    if _config_instance is None:
        _config_instance = ISMSConfig.load()
    return _config_instance


def reload_config() -> ISMSConfig:
    """설정을 다시 로드합니다."""
    global _config_instance
    _config_instance = ISMSConfig.load()
    return _config_instance