#!/usr/bin/env python3
"""Google Sheets 설정 확인 스크립트"""

from config.secrets_manager import get_config_from_secrets

try:
    config = get_config_from_secrets()
    print('📋 Secrets Manager 설정:')
    
    # Google 관련 키만 확인
    for key in ['GOOGLE_SHEETS_ID', 'GOOGLE_CREDENTIALS']:
        value = config.get(key)
        if value:
            if 'CREDENTIALS' in key:
                print(f'  ✅ {key}: SET (길이: {len(str(value))})')
            else:
                print(f'  ✅ {key}: {value}')
        else:
            print(f'  ❌ {key}: NOT SET')
    
    print(f'\n📋 전체 키 개수: {len(config)}개')
    
except Exception as e:
    print(f'❌ 오류: {str(e)}')