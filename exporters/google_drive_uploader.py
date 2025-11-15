"""
Google Drive 업로더 모듈
Excel 파일을 Google Drive에 업로드하고 Google Sheets로 변환
Secrets Manager에서 Google Service Account 키를 로드
"""

import os
import json
import tempfile
from typing import Optional, Dict, Any
import boto3
from botocore.exceptions import ClientError

try:
    from google.oauth2.service_account import Credentials
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaFileUpload
    GOOGLE_DRIVE_AVAILABLE = True
except ImportError:
    GOOGLE_DRIVE_AVAILABLE = False
    print("⚠️  Google Drive 기능을 사용하려면 다음을 설치하세요:")
    print("   pip install google-api-python-client google-auth-httplib2 google-auth-oauthlib")


class GoogleDriveUploader:
    """Google Drive 업로더 클래스"""
    
    def __init__(self, credentials_source: Optional[str] = None):
        """
        Args:
            credentials_source: 'file', 'secrets', 또는 None (자동 감지)
        """
        self.credentials = None
        self.drive_service = None
        self.sheets_service = None
        self.credentials_source = credentials_source
        
    def _get_credentials_from_secrets(self, secret_name: str = None, region: str = None) -> Optional[Dict]:
        """Secrets Manager에서 Google Service Account 키를 가져옵니다."""
        if not secret_name:
            # 기본값: GOOGLE_CREDENTIALS_SECRET 환경변수 또는 'dev/google-credentials'
            secret_name = os.getenv('GOOGLE_CREDENTIALS_SECRET', 'dev/google-credentials')
        if not region:
            region = os.getenv('ISMS_SECRET_REGION', 'ap-northeast-2')
            
        try:
            print(f"🔐 Google 자격증명을 Secrets Manager에서 로드 중: {secret_name}")
            
            client = boto3.client('secretsmanager', region_name=region)
            response = client.get_secret_value(SecretId=secret_name)
            
            # JSON 파싱
            credential_data = json.loads(response['SecretString'])
            print("✅ Google 자격증명을 성공적으로 로드했습니다.")
            
            return credential_data
            
        except ClientError as e:
            print(f"❌ Secrets Manager에서 Google 자격증명 로드 실패: {e}")
            return None
        except json.JSONDecodeError as e:
            print(f"❌ Google 자격증명 JSON 파싱 실패: {e}")
            return None
    
    def _get_credentials_from_main_secret(self, secret_name: str = None, region: str = None) -> Optional[Dict]:
        """메인 시크릿(dev/isms)에서 Google 자격증명을 가져옵니다."""
        if not secret_name:
            secret_name = os.getenv('ISMS_SECRET_NAME', 'dev/isms')
        if not region:
            region = os.getenv('ISMS_SECRET_REGION', 'ap-northeast-2')
            
        try:
            print(f"🔐 메인 시크릿에서 Google 자격증명 로드 중: {secret_name}")
            
            client = boto3.client('secretsmanager', region_name=region)
            response = client.get_secret_value(SecretId=secret_name)
            
            secret_data = json.loads(response['SecretString'])
            
            # GOOGLE_CREDENTIALS 키에서 자격증명 추출
            if 'GOOGLE_CREDENTIALS' in secret_data:
                google_creds = secret_data['GOOGLE_CREDENTIALS']
                if isinstance(google_creds, str):
                    # 문자열인 경우 JSON 파싱
                    credential_data = json.loads(google_creds)
                    print("✅ Google 자격증명을 성공적으로 파싱했습니다.")
                    return credential_data
                elif isinstance(google_creds, dict):
                    # 이미 딕셔너리인 경우
                    print("✅ Google 자격증명을 성공적으로 로드했습니다.")
                    return google_creds
            else:
                print("❌ GOOGLE_CREDENTIALS 키를 찾을 수 없습니다.")
                return None
                    
        except Exception as e:
            print(f"❌ 메인 시크릿에서 Google 자격증명 로드 실패: {e}")
            
        return None
    
    def _get_credentials_from_config(self, config_data: any) -> Optional[Dict]:
        """설정에서 직접 Google 자격증명을 가져옵니다."""
        try:
            if isinstance(config_data, str):
                # JSON 문자열인 경우
                print("📋 설정에서 Google 자격증명 파싱 중...")
                return json.loads(config_data)
            elif isinstance(config_data, dict):
                # 이미 딕셔너리인 경우
                print("📋 설정에서 Google 자격증명 로드 중...")
                return config_data
            else:
                print("❌ 지원하지 않는 자격증명 형태입니다.")
                return None
        except Exception as e:
            print(f"❌ 설정에서 Google 자격증명 처리 실패: {e}")
            return None
    
    def _get_credentials_from_file(self, credentials_file: str) -> Optional[Dict]:
        """파일에서 Google Service Account 키를 가져옵니다."""
        try:
            if os.path.exists(credentials_file):
                print(f"📄 파일에서 Google 자격증명 로드 중: {credentials_file}")
                with open(credentials_file, 'r', encoding='utf-8') as f:
                    credential_data = json.load(f)
                print("✅ 파일에서 Google 자격증명을 성공적으로 로드했습니다.")
                return credential_data
            else:
                print(f"❌ Google 자격증명 파일을 찾을 수 없습니다: {credentials_file}")
                return None
        except Exception as e:
            print(f"❌ 파일에서 Google 자격증명 로드 실패: {e}")
            return None
    
    def authenticate(self, credentials_file: str = 'credentials.json', google_credentials: any = None) -> bool:
        """Google Drive API 인증을 수행합니다."""
        if not GOOGLE_DRIVE_AVAILABLE:
            return False
            
        credential_data = None
        
        # 우선순위: 직접 전달된 자격증명 > Secrets Manager > 파일
        if google_credentials:
            credential_data = self._get_credentials_from_config(google_credentials)
        elif self.credentials_source == 'file':
            credential_data = self._get_credentials_from_file(credentials_file)
        elif self.credentials_source == 'secrets':
            credential_data = (self._get_credentials_from_secrets() or 
                             self._get_credentials_from_main_secret())
        else:
            # 자동 감지: Secrets Manager 먼저 시도, 실패하면 파일
            credential_data = (self._get_credentials_from_secrets() or 
                             self._get_credentials_from_main_secret() or
                             self._get_credentials_from_file(credentials_file))
        
        if not credential_data:
            print("❌ Google 자격증명을 찾을 수 없습니다.")
            return False
        
        try:
            # Google OAuth2 자격증명 생성
            self.credentials = Credentials.from_service_account_info(
                credential_data,
                scopes=[
                    'https://www.googleapis.com/auth/drive',
                    'https://www.googleapis.com/auth/spreadsheets'
                ]
            )
            
            # Google Drive 및 Sheets 서비스 생성
            self.drive_service = build('drive', 'v3', credentials=self.credentials)
            self.sheets_service = build('sheets', 'v4', credentials=self.credentials)
            
            print("✅ Google Drive API 인증 성공")
            return True
            
        except Exception as e:
            print(f"❌ Google Drive API 인증 실패: {e}")
            return False
    
    def upload_excel_file(
        self, 
        excel_file_path: str, 
        folder_id: Optional[str] = None,
        convert_to_sheets: bool = True,
        share_publicly: bool = False
    ) -> Optional[Dict[str, str]]:
        """Excel 파일을 Google Drive에 업로드합니다."""
        
        if not self.drive_service:
            print("❌ Google Drive 서비스가 초기화되지 않았습니다.")
            return None
        
        try:
            # 파일 이름 추출
            file_name = os.path.basename(excel_file_path)
            sheets_name = file_name.replace('.xlsx', '').replace('.xls', '') + '_sheets'
            
            print(f"📤 '{file_name}'을 Google Drive에 업로드 중...")
            
            # 파일 메타데이터
            file_metadata = {
                'name': file_name
            }
            
            # 폴더 지정
            if folder_id:
                file_metadata['parents'] = [folder_id]
            
            # 미디어 업로드
            media = MediaFileUpload(
                excel_file_path,
                mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            )
            
            # Excel 파일 업로드
            excel_file = self.drive_service.files().create(
                body=file_metadata,
                media_body=media,
                fields='id,name,webViewLink'
            ).execute()
            
            result = {
                'excel_file_id': excel_file.get('id'),
                'excel_file_name': excel_file.get('name'),
                'excel_url': excel_file.get('webViewLink')
            }
            
            print(f"✅ Excel 파일 업로드 완료: {result['excel_file_name']}")
            
            # Google Sheets로 변환
            if convert_to_sheets:
                print("🔄 Google Sheets로 변환 중...")
                
                sheets_metadata = {
                    'name': sheets_name,
                    'mimeType': 'application/vnd.google-apps.spreadsheet'
                }
                
                if folder_id:
                    sheets_metadata['parents'] = [folder_id]
                
                # Excel을 Sheets로 변환
                sheets_file = self.drive_service.files().copy(
                    fileId=excel_file.get('id'),
                    body=sheets_metadata,
                    fields='id,name,webViewLink'
                ).execute()
                
                result.update({
                    'sheets_file_id': sheets_file.get('id'),
                    'sheets_file_name': sheets_file.get('name'),
                    'sheets_url': sheets_file.get('webViewLink')
                })
                
                print(f"✅ Google Sheets 변환 완료: {result['sheets_file_name']}")
            
            # 공개 공유 설정
            if share_publicly:
                for file_id, file_type in [(result['excel_file_id'], 'Excel'), 
                                          (result.get('sheets_file_id'), 'Sheets')]:
                    if file_id:
                        try:
                            self.drive_service.permissions().create(
                                fileId=file_id,
                                body={
                                    'role': 'reader',
                                    'type': 'anyone'
                                }
                            ).execute()
                            print(f"🌐 {file_type} 파일을 공개로 설정했습니다.")
                        except Exception as e:
                            print(f"⚠️  {file_type} 파일 공개 설정 실패: {e}")
            
            return result
            
        except Exception as e:
            print(f"❌ Google Drive 업로드 실패: {e}")
            return None


def upload_inventory_to_drive(
    excel_file_path: str,
    credentials_file: str = 'credentials.json',
    folder_id: Optional[str] = None,
    share_publicly: bool = False,
    credentials_source: Optional[str] = None,
    google_credentials: any = None
) -> Optional[Dict[str, str]]:
    """
    Excel 파일을 Google Drive에 업로드하는 편의 함수
    
    Args:
        excel_file_path: 업로드할 Excel 파일 경로
        credentials_file: Google Service Account 키 파일 (Secrets Manager 사용 시 무시됨)
        folder_id: Google Drive 폴더 ID (선택사항)
        share_publicly: 공개 공유 여부
        credentials_source: 'file', 'secrets', 또는 None (자동)
        google_credentials: 직접 전달할 Google 자격증명 (JSON 문자열 또는 딕셔너리)
    
    Returns:
        업로드 결과 딕셔너리 또는 None
    """
    if not GOOGLE_DRIVE_AVAILABLE:
        return None
    
    uploader = GoogleDriveUploader(credentials_source=credentials_source)
    
    if not uploader.authenticate(credentials_file, google_credentials):
        return None
    
    return uploader.upload_excel_file(
        excel_file_path=excel_file_path,
        folder_id=folder_id,
        convert_to_sheets=True,
        share_publicly=share_publicly
    )