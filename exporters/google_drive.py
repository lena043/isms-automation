"""
Google Drive 연동 모듈
Excel 파일을 Google Sheets로 업로드하고 관리합니다.
"""

import os
import json
from typing import Dict, List, Optional
from pathlib import Path

try:
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaFileUpload
    GOOGLE_AVAILABLE = True
except ImportError:
    GOOGLE_AVAILABLE = False

# Google Drive API 스코프
SCOPES = [
    'https://www.googleapis.com/auth/drive.file',
    'https://www.googleapis.com/auth/spreadsheets'
]


class GoogleDriveUploader:
    """Google Drive에 파일을 업로드하는 클래스"""
    
    def __init__(self, credentials_file: str = 'credentials.json', token_file: str = 'token.json'):
        """
        Google Drive 업로더 초기화
        
        Args:
            credentials_file: Google API 자격증명 파일 경로
            token_file: OAuth 토큰 저장 파일 경로
        """
        if not GOOGLE_AVAILABLE:
            raise ImportError(
                "Google API 라이브러리가 설치되지 않았습니다.\n"
                "다음 명령어로 설치해주세요:\n"
                "pip install google-api-python-client google-auth-httplib2 google-auth-oauthlib"
            )
        
        self.credentials_file = credentials_file
        self.token_file = token_file
        self.service = None
        self.sheets_service = None
        
    def authenticate(self) -> bool:
        """Google API 인증"""
        creds = None
        
        # 기존 토큰 파일이 있으면 로드
        if os.path.exists(self.token_file):
            creds = Credentials.from_authorized_user_file(self.token_file, SCOPES)
        
        # 토큰이 없거나 유효하지 않으면 새로 인증
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                if not os.path.exists(self.credentials_file):
                    print(f"❌ Google API 자격증명 파일을 찾을 수 없습니다: {self.credentials_file}")
                    print("\n📋 설정 방법:")
                    print("1. Google Cloud Console에서 프로젝트 생성")
                    print("2. Google Drive API와 Google Sheets API 활성화")
                    print("3. OAuth 2.0 클라이언트 ID 생성 (데스크톱 애플리케이션)")
                    print("4. JSON 자격증명 파일을 다운로드하여 credentials.json으로 저장")
                    return False
                
                flow = InstalledAppFlow.from_client_secrets_file(self.credentials_file, SCOPES)
                creds = flow.run_local_server(port=0)
            
            # 토큰 저장
            with open(self.token_file, 'w') as token:
                token.write(creds.to_json())
        
        # 서비스 객체 생성
        self.service = build('drive', 'v3', credentials=creds)
        self.sheets_service = build('sheets', 'v4', credentials=creds)
        
        print("✅ Google API 인증 완료")
        return True
    
    def upload_excel_to_sheets(self, excel_file_path: str, folder_id: str = None) -> Dict[str, str]:
        """
        Excel 파일을 Google Sheets로 변환하여 업로드
        
        Args:
            excel_file_path: 업로드할 Excel 파일 경로
            folder_id: 업로드할 Google Drive 폴더 ID (선택사항)
            
        Returns:
            Dict containing file_id, web_url, and sheets_url
        """
        if not self.service:
            if not self.authenticate():
                raise Exception("Google API 인증 실패")
        
        file_name = Path(excel_file_path).stem
        
        # 파일 메타데이터
        file_metadata = {
            'name': f"{file_name}",
            'mimeType': 'application/vnd.google-apps.spreadsheet'  # Google Sheets로 변환
        }
        
        # 폴더 지정
        if folder_id:
            file_metadata['parents'] = [folder_id]
        
        # 파일 업로드
        media = MediaFileUpload(
            excel_file_path,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            resumable=True
        )
        
        print(f"📤 Google Sheets로 업로드 중: {file_name}")
        
        file = self.service.files().create(
            body=file_metadata,
            media_body=media,
            fields='id,name,webViewLink'
        ).execute()
        
        file_id = file.get('id')
        web_url = file.get('webViewLink')
        sheets_url = f"https://docs.google.com/spreadsheets/d/{file_id}/edit"
        
        print(f"✅ Google Sheets 업로드 완료!")
        print(f"📄 파일 ID: {file_id}")
        print(f"🔗 Google Sheets URL: {sheets_url}")
        
        return {
            'file_id': file_id,
            'name': file.get('name'),
            'web_url': web_url,
            'sheets_url': sheets_url
        }
    
    def create_folder(self, folder_name: str, parent_folder_id: str = None) -> str:
        """Google Drive에 폴더 생성"""
        if not self.service:
            if not self.authenticate():
                raise Exception("Google API 인증 실패")
        
        file_metadata = {
            'name': folder_name,
            'mimeType': 'application/vnd.google-apps.folder'
        }
        
        if parent_folder_id:
            file_metadata['parents'] = [parent_folder_id]
        
        folder = self.service.files().create(
            body=file_metadata,
            fields='id,name'
        ).execute()
        
        folder_id = folder.get('id')
        print(f"📁 폴더 생성 완료: {folder_name} (ID: {folder_id})")
        
        return folder_id
    
    def list_files(self, folder_id: str = None, name_contains: str = None) -> List[Dict]:
        """Google Drive 파일 목록 조회"""
        if not self.service:
            if not self.authenticate():
                raise Exception("Google API 인증 실패")
        
        query_parts = []
        
        if folder_id:
            query_parts.append(f"'{folder_id}' in parents")
        
        if name_contains:
            query_parts.append(f"name contains '{name_contains}'")
        
        query = " and ".join(query_parts) if query_parts else None
        
        results = self.service.files().list(
            q=query,
            fields="files(id, name, mimeType, createdTime, webViewLink)"
        ).execute()
        
        files = results.get('files', [])
        return files
    
    def share_file(self, file_id: str, email: str = None, role: str = 'reader') -> bool:
        """파일 공유 권한 설정"""
        if not self.service:
            if not self.authenticate():
                raise Exception("Google API 인증 실패")
        
        try:
            if email:
                # 특정 이메일과 공유
                permission = {
                    'type': 'user',
                    'role': role,
                    'emailAddress': email
                }
            else:
                # 링크가 있는 사람과 공유
                permission = {
                    'type': 'anyone',
                    'role': role
                }
            
            self.service.permissions().create(
                fileId=file_id,
                body=permission
            ).execute()
            
            print(f"✅ 파일 공유 설정 완료 ({role} 권한)")
            return True
            
        except Exception as e:
            print(f"❌ 파일 공유 설정 실패: {e}")
            return False


def upload_inventory_to_drive(excel_file_path: str, 
                            credentials_file: str = 'credentials.json',
                            folder_id: str = None,
                            share_publicly: bool = True) -> Optional[Dict[str, str]]:
    """
    인벤토리 Excel 파일을 Google Drive에 업로드하는 편의 함수
    
    Args:
        excel_file_path: Excel 파일 경로
        credentials_file: Google API 자격증명 파일 경로
        folder_id: 업로드할 폴더 ID
        share_publicly: 공개 공유 여부
        
    Returns:
        업로드 결과 정보 또는 None (실패 시)
    """
    try:
        uploader = GoogleDriveUploader(credentials_file)
        
        # 파일 업로드
        result = uploader.upload_excel_to_sheets(excel_file_path, folder_id)
        
        # 공개 공유 설정
        if share_publicly:
            uploader.share_file(result['file_id'])
        
        return result
        
    except Exception as e:
        print(f"❌ Google Drive 업로드 실패: {e}")
        return None