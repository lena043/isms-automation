"""
AWS WorkSpaces 서비스 조회 모듈
"""

from typing import List, Dict, Any
from .base import AWSServiceBase


class WorkSpacesService(AWSServiceBase):
    """AWS WorkSpaces 정보를 조회하는 서비스"""
    
    def get_service_name(self) -> str:
        return 'workspaces'
    
    def get_sheet_name(self) -> str:
        return 'WorkSpaces'
    
    def collect_data(self) -> List[Dict[str, Any]]:
        """WorkSpaces 목록을 조회합니다."""
        results = []
        next_token = None
        
        while True:
            # API 호출 파라미터 준비
            params = {}
            if next_token:
                params['NextToken'] = next_token
                
            # WorkSpaces 목록 조회
            response = self.client.describe_workspaces(**params)
            
            # 결과 처리
            for workspace in response.get('Workspaces', []):
                results.append({
                    'WorkspaceID': workspace.get('WorkspaceId', ''),
                    'UserName': workspace.get('UserName', ''),
                    'ComputerName': workspace.get('ComputerName', ''),
                    'IPAddress': workspace.get('IpAddress', ''),
                })
            
            # 페이징 처리
            next_token = response.get('NextToken')
            if not next_token:
                break
                
        return results