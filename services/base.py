"""
AWS 서비스 조회를 위한 베이스 클래스
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
import boto3
from config import assume_role, get_client, get_client_with_keys


class AWSServiceBase(ABC):
    """AWS 서비스 조회를 위한 베이스 클래스"""
    
    def __init__(self, region: str = 'us-east-1', account_id: str = ''):
        self.region = region
        self.account_id = account_id
        self.client = None
    
    @abstractmethod
    def get_service_name(self) -> str:
        """서비스 이름 반환 (예: 'workspaces', 's3', 'ec2')"""
        pass
    
    @abstractmethod
    def get_sheet_name(self) -> str:
        """Excel 시트 이름 반환"""
        pass
    
    @abstractmethod
    def collect_data(self) -> List[Dict[str, Any]]:
        """서비스 데이터 수집"""
        pass
    
    def setup_with_credentials(
        self, 
        access_key_id: str, 
        secret_access_key: str, 
        session_token: str
    ):
        """AWS 인증 키로 클라이언트 설정"""
        self.client = get_client_with_keys(
            self.get_service_name(),
            access_key_id,
            secret_access_key, 
            session_token,
            self.region
        )
    
    def setup_with_role(
        self,
        role_arn: str,
        session_name: str = "isms",
        external_id: Optional[str] = None
    ):
        """IAM Role로 클라이언트 설정"""
        credentials = assume_role(role_arn, session_name, external_id, self.region)
        self.client = get_client(self.get_service_name(), credentials, self.region)
    
    def get_data_with_metadata(self) -> Dict[str, Any]:
        """메타데이터와 함께 데이터 반환"""
        if not self.client:
            raise Exception(f"{self.get_service_name()} 클라이언트가 설정되지 않았습니다.")
        
        data = self.collect_data()
        
        return {
            'service': self.get_service_name(),
            'sheet_name': self.get_sheet_name(), 
            'region': self.region,
            'account_id': self.account_id,
            'data': data,
            'count': len(data)
        }