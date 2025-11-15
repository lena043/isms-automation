#!/usr/bin/env python3
"""Google Sheets 연동 테스트 스크립트"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.secrets_manager import get_config_from_secrets
from exporters.sheets_updater import DateBasedSheetsUpdater

# 테스트 데이터
test_data = [
    {
        'BucketName': 'test-bucket-1',
        'Region': 'ap-northeast-2',
        'CreationDate': '2024-11-14',
        'Account': '123456789'
    },
    {
        'InstanceId': 'i-1234567890abcdef0',
        'InstanceType': 't3.micro',
        'Region': 'ap-northeast-2',
        'State': 'running',
        'Account': '123456789'
    }
]

try:
    # 설정 로드
    config = get_config_from_secrets()
    sheets_id = config.get('GOOGLE_SHEETS_ID')
    
    if not sheets_id:
        print('❌ GOOGLE_SHEETS_ID가 없습니다.')
        exit(1)
    
    print(f'📊 Google Sheets ID: {sheets_id}')
    print(f'📊 테스트 데이터: {len(test_data)}행')
    
    # Google Sheets 업데이트 테스트
    updater = DateBasedSheetsUpdater()
    success = updater.update_sheets_from_data(sheets_id, test_data)
    
    if success:
        print('✅ Google Sheets 업데이트 성공!')
        print(f'🔗 링크: {updater.get_sheet_url(sheets_id)}')
    else:
        print('❌ Google Sheets 업데이트 실패')
        
except Exception as e:
    print(f'❌ 오류: {str(e)}')