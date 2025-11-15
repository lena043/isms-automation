import boto3
from typing import List, Dict, Optional
from botocore.exceptions import ClientError
from aws_auth import (
    get_workspaces_client_with_credentials,
    get_workspaces_client_with_role
)

def list_workspaces(
    access_key_id: str,
    secret_access_key: str,
    session_token: str,
    region: str,
    account_id: str
) -> List[Dict[str, str]]:
    """
    AWS 인증 키를 사용하여 WorkSpaces 목록을 조회합니다.
    
    Args:
        access_key_id: AWS Access Key ID
        secret_access_key: AWS Secret Access Key
        session_token: AWS Session Token
        region: AWS 리전
        account_id: AWS Account ID
        
    Returns:
        WorkSpaces 정보를 담은 딕셔너리 리스트
        
    Raises:
        Exception: AWS API 호출 실패시
    """
    try:
        # AWS 클라이언트 생성 (aws_auth 모듈 사용)
        client = get_workspaces_client_with_credentials(
            access_key_id, secret_access_key, session_token, region
        )
        
        return _describe_workspaces(client, account_id)
        
    except Exception as e:
        raise Exception(f"WorkSpaces 조회 실패: {e}")


def list_workspaces_with_role(
    role_arn: str,
    region: str,
    account_id: str,
    session_name: str = "workspaces-session",
    external_id: Optional[str] = None
) -> List[Dict[str, str]]:
    """
    IAM Role을 사용하여 AWS WorkSpaces 목록을 조회합니다.
    
    Args:
        role_arn: 사용할 IAM Role ARN
        region: AWS 리전
        account_id: AWS Account ID
        session_name: STS 세션 이름
        external_id: 외부 ID (Cross Account Role 사용시)
        
    Returns:
        WorkSpaces 정보를 담은 딕셔너리 리스트
        
    Raises:
        Exception: Role Assume 또는 API 호출 실패시
    """
    try:
        # AWS 클라이언트 생성 (aws_auth 모듈 사용)
        client = get_workspaces_client_with_role(
            role_arn, region, session_name, external_id
        )
        
        workspaces = _describe_workspaces(client, account_id)
        
        # 사용된 Role 정보 추가
        for workspace in workspaces:
            workspace['RoleArn'] = role_arn
            
        return workspaces
        
    except Exception as e:
        raise Exception(f"WorkSpaces 조회 실패 (Role: {role_arn}): {e}")


def list_workspaces_cross_account(
    role_arn: str,
    external_id: str,
    region: str,
    account_id: str,
    session_name: str = "cross-account-workspaces-session"
) -> List[Dict[str, str]]:
    """
    Cross Account IAM Role을 사용하여 다른 계정의 AWS WorkSpaces 목록을 조회합니다.
    
    Args:
        role_arn: Cross Account IAM Role ARN
        external_id: 외부 ID (보안을 위한 추가 인증)
        region: AWS 리전
        account_id: 대상 AWS Account ID
        session_name: STS 세션 이름
        
    Returns:
        WorkSpaces 정보를 담은 딕셔너리 리스트
    """
    return list_workspaces_with_role(
        role_arn=role_arn,
        region=region,
        account_id=account_id,
        session_name=session_name,
        external_id=external_id
    )


def _describe_workspaces(client, account_id: str) -> List[Dict[str, str]]:
    """
    WorkSpaces API를 호출하여 목록을 조회하는 내부 함수
    
    Args:
        client: boto3 WorkSpaces 클라이언트
        account_id: AWS Account ID
        
    Returns:
        WorkSpaces 정보 리스트
    """
    results = []
    next_token = None
    
    while True:
        # API 호출 파라미터 준비
        params = {}
        if next_token:
            params['NextToken'] = next_token
            
        # WorkSpaces 목록 조회
        response = client.describe_workspaces(**params)
        
        # 결과 처리
        for workspace in response.get('Workspaces', []):
            results.append({
                'AccountID': account_id,
                'WorkspaceID': workspace.get('WorkspaceId', ''),
                'UserName': workspace.get('UserName', ''),
                'ComputerName': workspace.get('ComputerName', ''),
                'IPAddress': workspace.get('IpAddress', ''),
                'State': workspace.get('State', ''),
                'BundleId': workspace.get('BundleId', ''),
                'DirectoryId': workspace.get('DirectoryId', '')
            })
        
        # 페이징 처리
        next_token = response.get('NextToken')
        if not next_token:
            break
            
    return results

