"""
Excel 내보내기 모듈
"""

import pandas as pd
from typing import List, Dict, Any
from datetime import datetime
import os


class ExcelExporter:
    """Excel 파일로 데이터를 내보내는 클래스"""
    
    def __init__(self, filename: str = None):
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"aws_resources_{timestamp}.xlsx"
        
        self.filename = filename
        self.data_sheets = []
    
    def add_sheet_data(self, sheet_name: str, data: List[Dict[str, Any]], service_info: Dict[str, Any] = None):
        """시트 데이터를 추가합니다. (빈 데이터는 추가하지 않음)"""
        if not data:
            # 빈 데이터는 시트를 추가하지 않음
            return
        
        self.data_sheets.append({
            'sheet_name': sheet_name,
            'data': data,
            'service_info': service_info or {}
        })
    
    def export_to_excel(self, create_summary: bool = True) -> str:
        """Excel 파일로 내보내기"""
        if not self.data_sheets:
            raise Exception("내보낼 데이터가 없습니다.")
        
        with pd.ExcelWriter(self.filename, engine='openpyxl') as writer:
            # 요약 시트 생성 (옵션)
            if create_summary:
                summary_data = self._create_summary()
                summary_df = pd.DataFrame(summary_data)
                summary_df.to_excel(writer, sheet_name='Summary', index=False)
            
            # 각 서비스별 시트 생성
            for sheet_info in self.data_sheets:
                sheet_name = sheet_info['sheet_name']
                data = sheet_info['data']
                
                # 시트명이 31자 초과시 자르기 (Excel 제한)
                if len(sheet_name) > 31:
                    sheet_name = sheet_name[:31]
                
                # 특수 문자 제거 (Excel 시트명 제한)
                invalid_chars = ['[', ']', ':', '*', '?', '/', '\\']
                for char in invalid_chars:
                    sheet_name = sheet_name.replace(char, '_')
                
                # DataFrame 생성 및 저장
                df = pd.DataFrame(data)
                df.to_excel(writer, sheet_name=sheet_name, index=False)
                
                # 열 너비 자동 조정
                worksheet = writer.sheets[sheet_name]
                for column in worksheet.columns:
                    max_length = 0
                    column_letter = column[0].column_letter
                    for cell in column:
                        try:
                            if len(str(cell.value)) > max_length:
                                max_length = len(str(cell.value))
                        except:
                            pass
                    # 최대 50자로 제한
                    adjusted_width = min(max_length + 2, 50)
                    worksheet.column_dimensions[column_letter].width = adjusted_width
        
        return os.path.abspath(self.filename)
    
    def _create_summary(self) -> List[Dict[str, Any]]:
        """요약 시트 데이터 생성"""
        summary = []
        total_resources = 0
        
        # 각 서비스별 요약 정보
        for sheet_info in self.data_sheets:
            service_info = sheet_info['service_info']
            data_count = len(sheet_info['data'])
            
            # 빈 메시지 시트는 제외
            if data_count == 1 and 'Message' in sheet_info['data'][0]:
                data_count = 0
            
            summary.append({
                'Service': service_info.get('service', sheet_info['sheet_name']),
                'Sheet Name': sheet_info['sheet_name'],
                'Region': service_info.get('region', ''),
                'Account ID': service_info.get('account_id', ''),
                'Resource Count': data_count
            })
            
            total_resources += data_count
        
        # 총계 행 추가
        summary.append({
            'Service': '** TOTAL **',
            'Sheet Name': f'{len(self.data_sheets)} sheets',
            'Region': 'All',
            'Account ID': 'All',
            'Resource Count': total_resources
        })
        
        # 생성 정보 추가
        summary.append({})  # 빈 행
        summary.append({
            'Service': 'Report Info',
            'Sheet Name': 'Generated',
            'Region': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            'Account ID': 'ISMS Automation Tool',
            'Resource Count': 'v1.0'
        })
        
        return summary