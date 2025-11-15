"""
AWS EC2 서비스 조회 모듈
"""

from typing import List, Dict, Any
from .base import AWSServiceBase


class EC2Service(AWSServiceBase):
    """AWS EC2 Instance 정보를 조회하는 서비스"""
    
    def get_service_name(self) -> str:
        return 'ec2'
    
    def get_sheet_name(self) -> str:
        return 'EC2_Instances'
    
    def collect_data(self) -> List[Dict[str, Any]]:
        """EC2 Instance 목록을 조회합니다."""
        results = []
        
        try:
            # EC2 인스턴스 조회
            response = self.client.describe_instances()
            
            for reservation in response.get('Reservations', []):
                for instance in reservation.get('Instances', []):
                    # 태그에서 Name 찾기
                    name_tag = ''
                    tags = instance.get('Tags', [])
                    for tag in tags:
                        if tag.get('Key') == 'Name':
                            name_tag = tag.get('Value', '')
                            break
                    
                    # 보안 그룹 정보 수집
                    security_groups = []
                    for sg in instance.get('SecurityGroups', []):
                        security_groups.append(f"{sg.get('GroupName', '')}({sg.get('GroupId', '')})")
                    
                    results.append({
                        'AccountID': self.account_id,
                        'AvailabilityZone': instance.get('Placement', {}).get('AvailabilityZone', ''),
                        'InstanceID': instance.get('InstanceId', ''),
                        'Name': name_tag,
                        'Platform': instance.get('Platform', 'Linux'),
                        'PrivateIPAddress': instance.get('PrivateIpAddress', ''),
                        'PublicIPAddress': instance.get('PublicIpAddress', ''),
                    })
            
        except Exception as e:
            print(f"EC2 조회 중 오류 발생: {e}")
            # 오류가 발생해도 빈 결과 반환
            
        return results