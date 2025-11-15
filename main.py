#!/usr/bin/env python3
"""
ISMS 자동화 도구 - 선택적 AWS 자원 조회 및 Excel 내보내기
IAM Role 기반으로 지정된 AWS 서비스만 조회하여 하나의 Excel 파일로 저장합니다.

환경변수 설정:
- AWS_SERVICES: 조회할 서비스 (기본값: workspaces,ec2,s3)
  예: AWS_SERVICES=ec2,workspaces 또는 AWS_SERVICES=ec2
"""

import os
import sys
from typing import Dict, List, Optional
from datetime import datetime

# 로컬 모듈들
from services import WorkSpacesService, EC2Service, S3Service, RDSService
from config.aws_regions import get_all_regions, get_region_display_name


def get_aws_config() -> Dict[str, str]:
    """환경변수와 Secrets Manager에서 AWS 설정을 가져옵니다."""
    from config.config import ISMSConfig
    
    # Secrets Manager 사용 여부는 ISMS_SECRET_NAME 환경변수로 결정
    isms_config = ISMSConfig.load()
    
    if isms_config.use_secrets_manager:
        print("🔐 Secrets Manager에서 설정을 로드했습니다.")
    
    # 기존 포맷으로 변환
    config = {
        'region': isms_config.aws.region,
        'accounts': isms_config.aws.accounts,
        'account_id': isms_config.aws.account_id,
        'role_arn': isms_config.aws.role_arn,
        'session_name': isms_config.aws.session_name,
        'external_id': isms_config.aws.external_id,
        'services': isms_config.aws.services,
        'GOOGLE_SHEETS_ID': isms_config.aws.google_sheets_id
    }
    
    return config


def parse_aws_accounts(config: Dict[str, str]) -> List[Dict[str, str]]:
    """AWS 계정 설정을 파싱합니다."""
    accounts = []
    
    # AWS_ACCOUNTS가 JSON 배열인 경우 (Secrets Manager)
    if isinstance(config.get('accounts'), list):
        for account_config in config['accounts']:
            if isinstance(account_config, dict) and 'account_id' in account_config and 'role_arn' in account_config:
                accounts.append({
                    'account_id': account_config['account_id'],
                    'role_arn': account_config['role_arn'],
                    'session_name': config['session_name'],
                    'external_id': config['external_id']
                })
        return accounts
    
    # 다중 계정 설정 확인 (문자열 형태)
    if config['accounts']:
        # AWS_ACCOUNTS="123456789012:arn:aws:iam::123456789012:role/Role1,987654321098:arn:aws:iam::987654321098:role/Role2"
        account_configs = config['accounts'].split(',')
        for account_config in account_configs:
            if ':arn:aws:iam::' in account_config:
                parts = account_config.split(':', 1)
                if len(parts) == 2:
                    account_id = parts[0].strip()
                    role_arn = parts[1].strip()
                    accounts.append({
                        'account_id': account_id,
                        'role_arn': role_arn,
                        'session_name': config['session_name'],
                        'external_id': config['external_id']
                    })
    
    # 단일 계정 설정 (이전 버전 호환)
    elif config['account_id'] and config['role_arn']:
        accounts.append({
            'account_id': config['account_id'],
            'role_arn': config['role_arn'],
            'session_name': config['session_name'],
            'external_id': config['external_id']
        })
    
    return accounts


def parse_selected_services(services_str: str) -> List[str]:
    """서비스 문자열을 파싱하여 유효한 서비스 목록을 반환합니다."""
    available_services = ['workspaces', 'ec2', 's3', 'rds']
    selected = [s.strip() for s in services_str.split(',') if s.strip()]
    
    # 유효한 서비스만 필터링
    valid_services = []
    invalid_services = []
    
    for service in selected:
        if service in available_services:
            valid_services.append(service)
        else:
            invalid_services.append(service)
    
    if invalid_services:
        print(f"⚠️  알 수 없는 서비스 무시: {', '.join(invalid_services)}")
        print(f"📋 사용 가능한 서비스: {', '.join(available_services)}")
    
    if not valid_services:
        print("❌ 유효한 서비스가 없습니다. 기본값 사용: workspaces,ec2,s3,rds")
        return available_services
    
    return valid_services


def setup_services(accounts: List[Dict[str, str]], config: Dict[str, str], regions: List[str]) -> List:
    """선택된 AWS 서비스들을 다중 계정으로 설정합니다."""
    selected_services = parse_selected_services(config['services'])
    all_services = []
    
    print(f"🎯 조회할 서비스: {', '.join(selected_services).upper()}")
    print(f"🏢 조회할 계정: {len(accounts)}개")
    
    for account in accounts:
        account_id = account['account_id']
        print(f"   - 계정 {account_id}")
        
        # S3는 글로벌 서비스이므로 각 계정마다 한 번만 추가
        if 's3' in selected_services:
            s3_service = S3Service(regions[0], account_id)
            setup_service_auth(s3_service, account)
            all_services.append(s3_service)
        
        # 리전별 서비스들 (각 계정별로)
        for region in regions:
            if 'workspaces' in selected_services:
                workspaces_service = WorkSpacesService(region, account_id)
                setup_service_auth(workspaces_service, account)
                all_services.append(workspaces_service)
            
            if 'ec2' in selected_services:
                ec2_service = EC2Service(region, account_id)
                setup_service_auth(ec2_service, account)
                all_services.append(ec2_service)
            
            if 'rds' in selected_services:
                rds_service = RDSService(region, account_id)
                setup_service_auth(rds_service, account)
                all_services.append(rds_service)
    
    return all_services


def setup_service_auth(service, account_config: Dict[str, str]):
    """개별 서비스에 인증 설정 (Role 방식만)"""
    # External ID가 있으면 Cross Account Role
    if account_config['external_id']:
        service.setup_with_role(
            account_config['role_arn'],
            account_config['session_name'],
            account_config['external_id']
        )
    else:
        # 일반 IAM Role
        service.setup_with_role(
            account_config['role_arn'],
            account_config['session_name']
        )


def collect_all_data(services: List) -> List[Dict]:
    """모든 서비스에서 데이터를 수집합니다."""
    results = []
    total_services = len(services)
    
    print("\n🔄 AWS 자원 조회 중...")
    print("-" * 70)
    
    for idx, service in enumerate(services, 1):
        service_name = service.get_service_name().upper()
        region = service.region
        region_display = get_region_display_name(region)
        
        # 진행률 표시
        progress = f"[{idx:2d}/{total_services:2d}]"
        print(f"{progress} 📋 {service_name:12} ({region} - {region_display}) 조회 중...", end=" ", flush=True)
        
        try:
            data_with_meta = service.get_data_with_metadata()
            count = data_with_meta['count']
            print(f"✅ {count:3d}개 발견")
            results.append(data_with_meta)
            
        except Exception as e:
            print(f"❌ 오류: {e}")
            # 오류가 발생해도 빈 데이터로 추가
            results.append({
                'service': service.get_service_name(),
                'sheet_name': service.get_sheet_name(),
                'region': service.region,
                'account_id': service.account_id,
                'data': [],
                'count': 0,
                'error': str(e)
            })
    
    return results








def main():
    """메인 함수 - 다중 계정 AWS 자원 조회"""
    print("🚀 ISMS 자동화 도구 - 다중 계정 AWS 자원 조회")
    print("=" * 60)
    
    try:
        # AWS 설정 로드
        config = get_aws_config()
        
        # 계정 설정 파싱
        accounts = parse_aws_accounts(config)
        
        if not accounts:
            print("❌ AWS 계정 설정이 없습니다!")
            return 1
        
        print(f"🌍 기본 리전: {config['region']}")
        print(f"� 조회할 계정 수: {len(accounts)}개")
        
        for i, account in enumerate(accounts, 1):
            print(f"   {i}. 계정 {account['account_id']} - {account['role_arn']}")
        
        if config['external_id']:
            print(f"🔑 External ID: {config['external_id']}")
        
        # 모든 리전에서 검색 (자동)
        regions = get_all_regions()
        print(f"\n🌐 검색 리전: {len(regions)}개 모든 AWS 리전")
        
        # 주요 리전들만 표시
        print("주요 검색 리전:")
        for region in regions[:8]:
            print(f"   - {region} ({get_region_display_name(region)})")
        if len(regions) > 8:
            print(f"   - ... 외 {len(regions)-8}개 더")
        
        print(f"\n⏰ 다중 계정 및 모든 리전 검색으로 시간이 다소 걸릴 수 있습니다.")
        
        # 서비스 설정
        services = setup_services(accounts, config, regions)
        
        # 데이터 수집
        all_data = collect_all_data(services)

        # 결과 요약
        print("\n" + "=" * 70)
        print("✅ 다중 계정 조회 완료!")
        print("\n📊 수집된 자원 요약:")
        print("-" * 70)

        total_resources = 0
        success_count = 0
        error_count = 0
        all_resources = []  # Google Sheets로 보낼 모든 리소스

        # 계정별로 그룹화하여 표시
        accounts_summary = {}
        for data_info in all_data:
            account_id = data_info['account_id']
            if account_id not in accounts_summary:
                accounts_summary[account_id] = {'total': 0, 'success': 0, 'error': 0}
            
            count = data_info['count']
            service_name = data_info['service'].upper()
            region = data_info['region']
            region_display = get_region_display_name(region)
            
            if 'error' in data_info:
                status = f"❌ 오류: {data_info['error'][:20]}..."
                error_count += 1
                accounts_summary[account_id]['error'] += 1
            else:
                status = f"✅ {count:3d}개"
                success_count += 1
                total_resources += count
                accounts_summary[account_id]['total'] += count
                accounts_summary[account_id]['success'] += 1
                
                # 리소스 데이터 수집 (Google Sheets로 보낼 데이터)
                if 'data' in data_info:
                    # 각 리소스에 서비스 타입 추가
                    for resource in data_info['data']:
                        resource['_service_type'] = data_info['service'].lower()
                    all_resources.extend(data_info['data'])

            print(f"   [{account_id}] {service_name:12} ({region}): {status}")
        
        print("-" * 70)
        print("📈 계정별 요약:")
        for account_id, summary in accounts_summary.items():
            print(f"   계정 {account_id}: {summary['total']:,}개 자원, 성공 {summary['success']}개, 실패 {summary['error']}개")
        
        print("-" * 70)
        print(f"🎯 총 자원 개수: {total_resources:,}개")
        print(f"📈 전체 성공: {success_count}개 서비스, 실패: {error_count}개 서비스")
        print("=" * 70)
        
        # Google Sheets 직접 업데이트 (Excel 파일 생성 없이)
        google_sheets_id = config.get('GOOGLE_SHEETS_ID')
        
        if google_sheets_id and all_resources:
            try:
                print(f"\n☁️  Google Sheets 업데이트 중...")
                print(f"📊 총 {len(all_resources)}개 리소스를 업데이트합니다...")
                
                from exporters.sheets_updater import DateBasedSheetsUpdater
                sheets_updater = DateBasedSheetsUpdater()
                
                success = sheets_updater.update_sheets_from_data(google_sheets_id, all_resources)
                
                if success:
                    print(f"\n🎉 Google Sheets 업데이트 완료!")
                    print(f"🔗 {sheets_updater.get_sheet_url(google_sheets_id)}")
                    
                    from datetime import datetime
                    today = datetime.now().strftime('%Y%m%d')
                    print(f"\n📅 생성된 워크시트 (예상):")
                    services_str = config.get('services', 'ec2,s3,rds')
                    services = services_str.split(',')
                    for service in services:
                        service_name = service.strip()
                        print(f"   - {service_name}-{today}")
                else:
                    print("❌ Google Sheets 업데이트에 실패했습니다.")
                    
            except Exception as e:
                print(f"❌ Google Sheets 업데이트 중 오류: {str(e)}")
                
        elif not google_sheets_id:
            print("\n❌ GOOGLE_SHEETS_ID가 설정되지 않았습니다.")
            print("   💡 Secrets Manager에서 GOOGLE_SHEETS_ID를 설정하세요.")
        else:
            print("\n⚠️  수집된 리소스가 없어 Google Sheets를 업데이트하지 않습니다.")
            
        return 0
        
    except KeyboardInterrupt:
        print("\n\n⚠️ 사용자에 의해 중단되었습니다.")
        return 1
    except Exception as e:
        print(f"\n❌ 오류 발생: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
