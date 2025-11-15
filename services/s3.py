"""
AWS S3 서비스 조회 모듈
"""

from typing import List, Dict, Any
from .base import AWSServiceBase


class S3Service(AWSServiceBase):
    """AWS S3 Bucket 정보를 조회하는 서비스"""
    
    def get_service_name(self) -> str:
        return 's3'
    
    def get_sheet_name(self) -> str:
        return 'S3_Buckets'
    
    def collect_data(self) -> List[Dict[str, Any]]:
        """S3 Bucket 목록을 조회합니다. (기본 정보만)"""
        results = []
        
        try:
            # S3 버킷 목록 조회 (기본 정보만)
            response = self.client.list_buckets()
            
            for bucket in response.get('Buckets', []):
                bucket_name = bucket.get('Name', '')
                creation_date = str(bucket.get('CreationDate', ''))
                
                results.append({
                    'AccountID': self.account_id,
                    'BucketName': bucket_name,
                    'CreationDate': creation_date
                })
            
        except Exception as e:
            print(f"S3 조회 중 오류 발생: {e}")
            # 오류가 발생해도 빈 결과 반환
            
        return results