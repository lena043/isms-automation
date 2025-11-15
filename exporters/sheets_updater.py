"""
Google Sheets 업데이트 모듈 - 날짜별 워크시트 생성
AWS 리소스 데이터를 서비스별, 날짜별 워크시트로 분류하여 Google Sheets에 업데이트
"""

import os
import json
import pandas as pd
from datetime import datetime
from typing import Optional, Dict, Any, List

# Google Sheets API 라이브러리
try:
    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError
    from google.oauth2.service_account import Credentials
except ImportError:
    print("❌ Google API 라이브러리가 설치되지 않았습니다.")
    print("pip install google-api-python-client google-auth를 실행하세요.")
    exit(1)


class DateBasedSheetsUpdater:
    """Google Sheets 날짜별 워크시트 업데이트"""
    
    def __init__(self):
        self.service = None
        self.credentials = None
        
    def authenticate_service_account(self, credentials_data: str) -> bool:
        """Service Account로 Google Sheets API 인증"""
        try:
            # JSON 문자열을 dict로 파싱
            if isinstance(credentials_data, str):
                creds_dict = json.loads(credentials_data)
            else:
                creds_dict = credentials_data
            
            print("🔑 Service Account 인증 중...")
            
            # 서비스 계정 인증
            self.credentials = Credentials.from_service_account_info(
                creds_dict, 
                scopes=['https://www.googleapis.com/auth/spreadsheets']
            )
            
            # Google Sheets API 서비스 빌드
            self.service = build('sheets', 'v4', credentials=self.credentials)
            
            print("✅ Service Account 인증 성공")
            return True
            
        except json.JSONDecodeError as e:
            print(f"❌ JSON 파싱 오류: {e}")
            return False
        except Exception as e:
            print(f"❌ Service Account 인증 실패: {str(e)}")
            return False
    
    def authenticate_from_config(self) -> bool:
        """설정에서 Google 인증 정보를 가져와서 인증"""
        try:
            from config.secrets_manager import get_config_from_secrets
            
            config = get_config_from_secrets()
            credentials_data = config.get('GOOGLE_CREDENTIALS')
            
            if not credentials_data:
                print("❌ GOOGLE_CREDENTIALS가 설정되지 않았습니다.")
                return False
            
            return self.authenticate_service_account(credentials_data)
            
        except Exception as e:
            print(f"❌ 설정 로드 실패: {str(e)}")
            return False
    
    def check_sheet_access(self, sheet_id: str) -> bool:
        """Google Sheets 접근 권한 확인"""
        if not self.service:
            if not self.authenticate_from_config():
                return False
        
        try:
            # 시트 메타데이터 가져오기로 접근 권한 확인
            result = self.service.spreadsheets().get(spreadsheetId=sheet_id).execute()
            sheet_title = result.get('properties', {}).get('title', 'Unknown')
            print(f"✅ Google Sheets 접근 확인: {sheet_title}")
            return True
            
        except HttpError as e:
            if e.resp.status == 403:
                print("❌ Google Sheets 접근 권한 없음")
                print("💡 Service Account에게 편집 권한을 부여하세요:")
                if self.credentials and hasattr(self.credentials, 'service_account_email'):
                    print(f"   📧 {self.credentials.service_account_email}")
            elif e.resp.status == 404:
                print("❌ Google Sheets를 찾을 수 없음")
            else:
                print(f"❌ HTTP 오류 ({e.resp.status}): {e}")
            return False
        except Exception as e:
            print(f"❌ 시트 접근 확인 실패: {str(e)}")
            return False
    
    def get_sheet_url(self, sheet_id: str) -> str:
        """Google Sheets URL 생성"""
        return f"https://docs.google.com/spreadsheets/d/{sheet_id}"
    
    def classify_service_by_columns(self, df: pd.DataFrame) -> str:
        """데이터프레임 컬럼을 기반으로 서비스 분류"""
        columns = [col.lower() for col in df.columns]
        
        # 컬럼명 기반 우선순위 분류
        if any('bucket' in col for col in columns):
            return 's3'
        elif any('instance' in col for col in columns):
            return 'ec2'  
        elif any('database' in col or 'rds' in col or 'db' in col for col in columns):
            return 'rds'
        elif any('workspace' in col for col in columns):
            return 'workspaces'
        else:
            return 'unknown'
    
    def classify_service_by_data(self, row: Dict) -> str:
        """개별 행의 데이터를 기반으로 서비스 분류"""
        # _service_type이 있으면 최우선으로 사용 (main.py에서 추가한 서비스 타입)
        if '_service_type' in row and row['_service_type'] and str(row['_service_type']).lower() != 'nan':
            return str(row['_service_type']).lower()
        
        # 기존 service 컬럼이 있으면 우선 사용
        if 'service' in row and row['service'] and str(row['service']).lower() != 'nan':
            return str(row['service']).lower()
        
        # resource_type이 있으면 사용
        if 'resource_type' in row and row['resource_type']:
            resource_type = str(row['resource_type']).lower()
            if 'bucket' in resource_type or 's3' in resource_type:
                return 's3'
            elif 'instance' in resource_type or 'ec2' in resource_type:
                return 'ec2'
            elif 'database' in resource_type or 'rds' in resource_type or 'db' in resource_type:
                return 'rds'
            elif 'workspace' in resource_type:
                return 'workspaces'
        
        # 개별 행 데이터의 값들을 확인해서 서비스 분류
        for key, value in row.items():
            key_lower = str(key).lower()
            value_str = str(value).lower() if value and str(value) != 'nan' else ''
            
            # EC2 우선 확인 (InstanceId가 있으면 EC2)
            if 'instanceid' in key_lower and value_str and value_str != 'nan':
                return 'ec2'
            elif 'instance' in key_lower and ('i-' in value_str or 'ami-' in value_str):
                return 'ec2'
            
            # S3 확인
            elif 'bucketname' in key_lower and value_str and value_str != 'nan':
                return 's3'
            elif 'bucket' in key_lower or ('bucket' in value_str and 'amazonaws.com' in value_str):
                return 's3'
                
            # RDS 확인
            elif any(db_term in key_lower for db_term in ['database', 'rds', 'mysql', 'postgres', 'oracle']) and value_str:
                return 'rds'
                
            # WorkSpaces 확인
            elif 'workspace' in key_lower and value_str:
                return 'workspaces'
        
        return 'unknown'
    
    def get_or_create_worksheet(self, sheet_id: str, worksheet_name: str) -> bool:
        """워크시트 가져오기 또는 생성"""
        if not self.service:
            if not self.authenticate_from_config():
                return False
        
        try:
            # 기존 워크시트 목록 가져오기
            result = self.service.spreadsheets().get(spreadsheetId=sheet_id).execute()
            existing_sheets = result.get('sheets', [])
            
            # 워크시트가 이미 있는지 확인
            for sheet in existing_sheets:
                if sheet['properties']['title'] == worksheet_name:
                    print(f"📄 기존 워크시트 사용: {worksheet_name}")
                    return True
            
            # 워크시트 생성
            request_body = {
                'requests': [{
                    'addSheet': {
                        'properties': {
                            'title': worksheet_name
                        }
                    }
                }]
            }
            
            self.service.spreadsheets().batchUpdate(
                spreadsheetId=sheet_id,
                body=request_body
            ).execute()
            
            print(f"📄 새 워크시트 생성: {worksheet_name}")
            return True
            
        except Exception as e:
            print(f"❌ 워크시트 생성 실패 ({worksheet_name}): {str(e)}")
            return False
    
    def update_worksheet_data(self, sheet_id: str, worksheet_name: str, data: List[Dict]) -> bool:
        """워크시트에 데이터 업데이트"""
        if not self.service or not data:
            return False
        
        try:
            # 데이터프레임으로 변환
            df = pd.DataFrame(data)
            
            # 내부 컬럼 제거 (_로 시작하는 컬럼)
            internal_columns = [col for col in df.columns if col.startswith('_')]
            if internal_columns:
                df = df.drop(columns=internal_columns)
                print(f"   제거된 내부 컬럼: {', '.join(internal_columns)}")
            
            # 비어있는 컬럼 제거 (모든 값이 NaN이거나 빈 문자열인 컬럼)
            empty_columns = []
            for col in df.columns:
                # 컬럼의 모든 값이 비어있는지 확인
                if df[col].isna().all() or (df[col].fillna('').astype(str).str.strip() == '').all():
                    empty_columns.append(col)
            
            # 빈 컬럼 제거
            if empty_columns:
                df = df.drop(columns=empty_columns)
                print(f"   제거된 빈 컬럼 ({len(empty_columns)}개): {', '.join(empty_columns[:5])}{'...' if len(empty_columns) > 5 else ''}")
            
            # 데이터 준비
            headers = list(df.columns)
            values = [headers] + df.fillna('').values.tolist()
            
            # 시트 범위 (A1부터)
            range_name = f"{worksheet_name}!A1"
            
            # 기존 데이터 지우기
            clear_request = self.service.spreadsheets().values().clear(
                spreadsheetId=sheet_id,
                range=f"{worksheet_name}!A:Z"
            )
            clear_request.execute()
            
            # 새 데이터 업데이트
            value_range_body = {
                'values': values
            }
            
            request = self.service.spreadsheets().values().update(
                spreadsheetId=sheet_id,
                range=range_name,
                valueInputOption='RAW',
                body=value_range_body
            )
            
            result = request.execute()
            updated_cells = result.get('updatedCells', 0)
            
            print(f"✅ {worksheet_name}: {len(data)}행, {updated_cells}셀 업데이트")
            return True
            
        except Exception as e:
            print(f"❌ 데이터 업데이트 실패 ({worksheet_name}): {str(e)}")
            return False
    
    def update_sheets_from_data(self, sheet_id: str, resources_data: List[Dict]) -> bool:
        """리소스 데이터를 받아서 서비스별 워크시트에 업데이트"""
        try:
            if not resources_data:
                print("❌ 업데이트할 데이터가 없습니다.")
                return False
            
            print(f"📊 리소스 데이터 처리 중: {len(resources_data)}행")
            
            # 데이터프레임 생성
            df = pd.DataFrame(resources_data)
            
            print(f"📋 컬럼: {list(df.columns)}")
            
            # 전체 데이터프레임으로 기본 서비스 분류
            default_service = self.classify_service_by_columns(df)
            print(f"🔍 컬럼 기반 서비스 분류: {default_service}")
            
            # 오늘 날짜
            today = datetime.now().strftime('%Y%m%d')
            
            # 서비스별 데이터 분류
            service_data = {}
            
            for _, row in df.iterrows():
                # 개별 행 기반 서비스 분류 (기본값 사용)
                service = self.classify_service_by_data(row.to_dict())
                
                # unknown인 경우 전체 컬럼 기반 분류 사용
                if service == 'unknown':
                    service = default_service
                
                if service not in service_data:
                    service_data[service] = []
                
                # 행 데이터에 서비스 정보 추가
                row_dict = row.to_dict()
                row_dict['service'] = service
                service_data[service].append(row_dict)
            
            print(f"📊 발견된 서비스: {list(service_data.keys())}")
            for service, data in service_data.items():
                print(f"   - {service}: {len(data)}행")
            
            # 서비스별 워크시트 생성 및 업데이트
            success_count = 0
            total_services = len(service_data)
            
            for service, data in service_data.items():
                worksheet_name = f"{service}-{today}"
                
                print(f"\n[{success_count+1}/{total_services}] 처리 중: {worksheet_name}")
                
                # 워크시트 생성/관리
                if self.get_or_create_worksheet(sheet_id, worksheet_name):
                    # 데이터 업데이트
                    if self.update_worksheet_data(sheet_id, worksheet_name, data):
                        success_count += 1
                    else:
                        print(f"❌ {worksheet_name} 데이터 업데이트 실패")
                else:
                    print(f"❌ {worksheet_name} 워크시트 생성 실패")
            
            print(f"\n📊 완료 결과: {success_count}/{total_services} 서비스 처리 성공")
            
            if success_count > 0:
                print(f"✅ Google Sheets 업데이트 완료!")
                return True
            else:
                print(f"❌ 모든 서비스 처리 실패")
                return False
                
        except Exception as e:
            print(f"❌ 데이터 처리 실패: {str(e)}")
            return False