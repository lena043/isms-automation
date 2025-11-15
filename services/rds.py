"""
AWS RDS 서비스 조회 모듈
"""

from typing import List, Dict, Any
from .base import AWSServiceBase


class RDSService(AWSServiceBase):
    """AWS RDS Instance 정보를 조회하는 서비스"""
    
    def get_service_name(self) -> str:
        return 'rds'
    
    def get_sheet_name(self) -> str:
        return 'RDS_Instances'
    
    def collect_data(self) -> List[Dict[str, Any]]:
        """RDS Instance 목록을 조회합니다."""
        results = []
        
        try:
            # RDS 인스턴스 조회
            response = self.client.describe_db_instances()
            
            for db_instance in response.get('DBInstances', []):
                
                # 태그 조회 (ARN 필요)
                db_arn = db_instance.get('DBInstanceArn', '')
                tags = []
                name_tag = ''
                
                if db_arn:
                    try:
                        tags_response = self.client.list_tags_for_resource(ResourceName=db_arn)
                        tags = tags_response.get('TagList', [])
                        
                        # Name 태그 찾기
                        for tag in tags:
                            if tag.get('Key') == 'Name':
                                name_tag = tag.get('Value', '')
                                break
                    except Exception as tag_error:
                        print(f"RDS 태그 조회 실패 ({db_instance.get('DBInstanceIdentifier', '')}): {tag_error}")
                
                # 서브넷 그룹 정보
                subnet_group = db_instance.get('DBSubnetGroup', {})
                vpc_id = subnet_group.get('VpcId', '')
                
                # 보안 그룹 정보
                security_groups = []
                for sg in db_instance.get('VpcSecurityGroups', []):
                    security_groups.append(f"{sg.get('VpcSecurityGroupId', '')} ({sg.get('Status', '')})")
                
                # 읽기 전용 복제본 정보
                read_replicas = ', '.join(db_instance.get('ReadReplicaDBInstanceIdentifiers', []))
                
                # 클러스터 정보 (Aurora 등의 경우)
                cluster_id = db_instance.get('DBClusterIdentifier', '')
                
                results.append({
                    'AccountID': self.account_id,
                    'AvailabilityZone': db_instance.get('AvailabilityZone', ''),
                    'ClusterID': cluster_id,  # 클러스터 ID 추가
                    'InstanceID': name_tag,
                    'Engine': db_instance.get('Engine', ''),
                    'RDS': "RDS",
                    'EngineVersion': db_instance.get('EngineVersion', ''),
                    'Endpoint': db_instance.get('Endpoint', {}).get('Address', ''),
                    'Port': db_instance.get('Endpoint', {}).get('Port', ''),
                    'BackupRetentionPeriod': db_instance.get('BackupRetentionPeriod', 0),
                })

        except Exception as e:
            print(f"RDS 조회 중 오류 발생: {e}")
            # 오류가 발생해도 빈 결과 반환
            
        return results