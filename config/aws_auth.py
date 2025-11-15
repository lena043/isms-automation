"""
AWS 인증 관련 간단한 유틸리티
STS Role Assume과 클라이언트 생성 기능 제공
"""

import boto3
from typing import Dict, Optional
from botocore.exceptions import ClientError


def assume_role(role_arn: str, session_name: str = "isms", external_id: Optional[str] = None, region: str = 'us-east-1') -> Dict[str, str]:
    """
    IAM Role을 Assume하여 임시 자격증명을 획득합니다.
    
    Args:
        role_arn: Role ARN (예: arn:aws:iam::123456789012:role/MyRole)
        session_name: 세션 이름
        external_id: 외부 ID (Cross Account용)
        region: AWS 리전
        
    Returns:
        임시 자격증명 딕셔너리
        
    Raises:
        Exception: Role Assume 실패시
    """
    try:
        sts = boto3.client('sts', region_name=region)
        
        params = {
            'RoleArn': role_arn,
            'RoleSessionName': session_name
        }
        
        if external_id:
            params['ExternalId'] = external_id
        
        response = sts.assume_role(**params)
        return response['Credentials']
        
    except ClientError as e:
        error_code = e.response['Error']['Code']
        if error_code == 'AccessDenied':
            raise Exception(f"Role Assume 권한 없음: {role_arn}")
        else:
            raise Exception(f"Role Assume 실패: {e}")


def get_client(service: str, credentials: Dict[str, str], region: str = 'us-east-1'):
    """
    임시 자격증명으로 AWS 서비스 클라이언트를 생성합니다.
    
    Args:
        service: 서비스 이름 ('workspaces', 's3', 'ec2' 등)
        credentials: assume_role()에서 반환된 자격증명
        region: AWS 리전
        
    Returns:
        boto3 클라이언트
    """
    return boto3.client(
        service,
        aws_access_key_id=credentials['AccessKeyId'],
        aws_secret_access_key=credentials['SecretAccessKey'],
        aws_session_token=credentials['SessionToken'],
        region_name=region
    )


def get_client_with_keys(service: str, access_key_id: str, secret_access_key: str, session_token: str, region: str = 'us-east-1'):
    """
    AWS 인증 키로 서비스 클라이언트를 생성합니다.
    """
    return boto3.client(
        service,
        aws_access_key_id=access_key_id,
        aws_secret_access_key=secret_access_key,
        aws_session_token=session_token,
        region_name=region
    )
