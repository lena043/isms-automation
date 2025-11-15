"""
AWS 리전 관리 유틸리티
"""

from typing import List, Dict
import boto3


# AWS 주요 리전 목록
AWS_REGIONS = [
    'us-east-1',      # 미국 동부 (버지니아 북부)
    'ap-northeast-2' # 아시아 태평양 (서울) - 기본
]

# 글로벌 서비스 (리전에 관계없음)
GLOBAL_SERVICES = ['s3', 'iam', 'cloudfront', 'route53']

# 리전별 서비스
REGIONAL_SERVICES = ['ec2', 'workspaces', 'rds', 'lambda', 'ecs']


def get_default_region() -> str:
    """기본 리전 반환"""
    return 'ap-northeast-2'


def get_all_regions() -> List[str]:
    """모든 AWS 리전 목록 반환"""
    return AWS_REGIONS.copy()


def get_region_display_name(region: str) -> str:
    """리전의 표시 이름 반환"""
    region_names = {
        'us-east-1': '미국 동부 (버지니아)',
        'ap-northeast-2': '아시아 태평양 (서울)'
    }
    return region_names.get(region, region)


def is_global_service(service_name: str) -> bool:
    """글로벌 서비스인지 확인"""
    return service_name.lower() in GLOBAL_SERVICES


def get_available_regions_for_service(service_name: str) -> List[str]:
    """서비스가 사용 가능한 리전 목록 반환"""
    if is_global_service(service_name):
        return [get_default_region()]  # 글로벌 서비스는 기본 리전에서만 조회
    return get_all_regions()


def get_regions_from_aws() -> List[str]:
    """AWS API를 통해 실제 사용 가능한 리전 목록 조회"""
    try:
        ec2 = boto3.client('ec2', region_name=get_default_region())
        response = ec2.describe_regions()
        regions = [region['RegionName'] for region in response['Regions']]
        return sorted(regions)
    except Exception as e:
        print(f"AWS 리전 목록 조회 실패: {e}")
        return get_all_regions()  # 실패시 하드코딩된 목록 사용