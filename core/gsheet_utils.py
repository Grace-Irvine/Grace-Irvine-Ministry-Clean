"""
Google Sheets 工具模块
封装读取和写入 Google Sheets 的功能
"""

import os
import re
import json
from typing import List, Dict, Any, Optional, Union, Tuple
from pathlib import Path
import pandas as pd
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError


class GSheetClient:
    """Google Sheets API 客户端"""
    
    SCOPES = ['https://www.googleapis.com/auth/spreadsheets']
    
    def __init__(self, credentials_path: Optional[str] = None):
        """
        初始化 Google Sheets 客户端
        
        Args:
            credentials_path: 服务账号 JSON 文件路径，若为 None 则依次尝试:
                1. 环境变量 GOOGLE_APPLICATION_CREDENTIALS
                2. config.json 中的 service_layer.storage.service_account_file
                3. config/service-account.json (默认路径)
        """
        if credentials_path is None:
            # 优先使用环境变量
            credentials_path = os.environ.get('GOOGLE_APPLICATION_CREDENTIALS')
        
        if not credentials_path:
            # 尝试从 config.json 读取
            credentials_path = self._get_credentials_from_config()
        
        if not credentials_path:
            raise ValueError(
                "未找到 Google 凭证。请：\n"
                "1. 设置 GOOGLE_APPLICATION_CREDENTIALS 环境变量，或\n"
                "2. 在 config.json 的 service_layer.storage.service_account_file 中配置路径，或\n"
                "3. 将凭证文件放在 config/service-account.json"
            )
        
        if not os.path.exists(credentials_path):
            raise FileNotFoundError(f"凭证文件不存在: {credentials_path}")
        
        if not os.path.isfile(credentials_path):
            raise ValueError(f"凭证路径不是文件: {credentials_path}")
        
        try:
            self.credentials = service_account.Credentials.from_service_account_file(
                credentials_path, scopes=self.SCOPES
            )
        except Exception as e:
            raise ValueError(f"无法加载凭证文件 {credentials_path}: {str(e)}")
        self.service = build('sheets', 'v4', credentials=self.credentials)
        self.sheets = self.service.spreadsheets()
    
    def _get_credentials_from_config(self) -> Optional[str]:
        """
        从配置文件中读取 service account 路径
        
        Returns:
            凭证文件路径，如果未找到则返回 None
        """
        # 尝试的配置文件路径列表（按优先级）
        config_paths = [
            'config/config.json',
            '../config/config.json',
            str(Path(__file__).parent.parent / 'config' / 'config.json')
        ]
        
        for config_path in config_paths:
            if os.path.exists(config_path):
                try:
                    with open(config_path, 'r', encoding='utf-8') as f:
                        config = json.load(f)
                    
                    # 从 service_layer.storage.service_account_file 读取
                    credentials_path = config.get('service_layer', {}).get('storage', {}).get('service_account_file')
                    
                    if credentials_path and os.path.exists(credentials_path):
                        return credentials_path
                except Exception:
                    continue
        
        # 尝试默认路径
        default_paths = [
            'config/service-account.json',
            '../config/service-account.json',
            str(Path(__file__).parent.parent / 'config' / 'service-account.json')
        ]
        
        for default_path in default_paths:
            if os.path.exists(default_path):
                return default_path
        
        return None
    
    @staticmethod
    def extract_sheet_id(url: str) -> str:
        """
        从 Google Sheets URL 提取 spreadsheet ID
        
        Args:
            url: Google Sheets URL
            
        Returns:
            spreadsheet ID
        """
        pattern = r'/spreadsheets/d/([a-zA-Z0-9-_]+)'
        match = re.search(pattern, url)
        if not match:
            raise ValueError(f"无法从 URL 提取 Sheet ID: {url}")
        return match.group(1)
    
    def read_range(
        self, 
        url: str, 
        range_name: str,
        return_department_info: bool = False
    ) -> Union[pd.DataFrame, Tuple[pd.DataFrame, Dict[str, str]]]:
        """
        读取 Google Sheet 指定范围的数据
        
        Args:
            url: Google Sheets URL
            range_name: 范围名称，如 "Sheet1!A1:Z100"
            return_department_info: 是否返回部门信息（第1行）
            
        Returns:
            如果 return_department_info=True: (DataFrame, column_to_department_map)
            否则: DataFrame
        """
        sheet_id = self.extract_sheet_id(url)
        
        try:
            result = self.sheets.values().get(
                spreadsheetId=sheet_id,
                range=range_name
            ).execute()
            
            values = result.get('values', [])
            
            if not values:
                raise ValueError(f"指定范围没有数据: {range_name}")
            
            # 存储部门映射信息
            department_map = {}
            
            # 处理可能的两行表头（如果第二行也有列名信息）
            if len(values) >= 2:
                # 检查是否是两行表头的格式
                row1 = values[0]
                row2 = values[1]
                
                # 合并表头：优先使用第2行（更具体），如果第2行为空则使用第1行
                headers = []
                for i in range(max(len(row1), len(row2))):
                    val1 = row1[i] if i < len(row1) else ''
                    val2 = row2[i] if i < len(row2) else ''
                    
                    # 优先使用第2行的值，如果第2行为空则用第1行
                    if val2 and val2.strip():
                        col_name = val2.strip()
                        headers.append(col_name)
                        # 如果第1行有值，作为部门信息
                        if val1 and val1.strip() and return_department_info:
                            department_map[col_name] = val1.strip()
                    elif val1 and val1.strip():
                        headers.append(val1.strip())
                    else:
                        headers.append(f'Column{i+1}')
                
                # 检查第3行是否是数据（通过检查第一列是否像日期）
                if len(values) > 2:
                    third_row_first_col = str(values[2][0]) if values[2] else ''
                    # 如果第3行第1列看起来像日期或数据，则跳过前两行
                    if third_row_first_col and ('/' in third_row_first_col or '-' in third_row_first_col or third_row_first_col.isdigit()):
                        data_rows = values[2:]
                    else:
                        # 否则只跳过第一行
                        headers = values[0]
                        data_rows = values[1:]
                        department_map = {}  # 单行表头没有部门信息
                else:
                    data_rows = values[2:]
            else:
                # 单行表头的标准情况
                headers = values[0]
                data_rows = values[1:]
            
            # 处理行长度不一致的情况
            max_cols = len(headers)
            normalized_rows = []
            for row in data_rows:
                # 补齐列数
                normalized_row = row + [''] * (max_cols - len(row))
                normalized_rows.append(normalized_row[:max_cols])
            
            df = pd.DataFrame(normalized_rows, columns=headers)
            
            if return_department_info:
                return df, department_map
            else:
                return df
            
        except HttpError as e:
            raise RuntimeError(f"读取 Google Sheet 失败: {e}")
    
    def write_range(
        self, 
        url: str, 
        range_name: str, 
        df: pd.DataFrame,
        include_header: bool = True
    ) -> Dict[str, Any]:
        """
        写入数据到 Google Sheet 指定范围
        
        Args:
            url: Google Sheets URL
            range_name: 范围名称，如 "Sheet1!A1"
            df: 要写入的 DataFrame
            include_header: 是否包含表头
            
        Returns:
            API 响应结果
        """
        sheet_id = self.extract_sheet_id(url)
        
        # 准备数据
        values = []
        if include_header:
            values.append(df.columns.tolist())
        
        # 将 DataFrame 转换为列表，处理 NaN 和特殊值
        for _, row in df.iterrows():
            row_values = []
            for val in row:
                if pd.isna(val):
                    row_values.append('')
                elif isinstance(val, (list, dict)):
                    # 对于列表和字典，转换为 JSON 字符串
                    import json
                    row_values.append(json.dumps(val, ensure_ascii=False))
                else:
                    row_values.append(str(val))
            values.append(row_values)
        
        body = {
            'values': values
        }
        
        try:
            result = self.sheets.values().update(
                spreadsheetId=sheet_id,
                range=range_name,
                valueInputOption='RAW',
                body=body
            ).execute()
            
            return result
            
        except HttpError as e:
            raise RuntimeError(f"写入 Google Sheet 失败: {e}")
    
    def clear_range(self, url: str, range_name: str) -> Dict[str, Any]:
        """
        清空 Google Sheet 指定范围的数据
        
        Args:
            url: Google Sheets URL
            range_name: 范围名称
            
        Returns:
            API 响应结果
        """
        sheet_id = self.extract_sheet_id(url)
        
        try:
            result = self.sheets.values().clear(
                spreadsheetId=sheet_id,
                range=range_name
            ).execute()
            
            return result
            
        except HttpError as e:
            raise RuntimeError(f"清空 Google Sheet 失败: {e}")
    
    def append_rows(
        self, 
        url: str, 
        range_name: str, 
        df: pd.DataFrame
    ) -> Dict[str, Any]:
        """
        追加数据到 Google Sheet（不覆盖现有数据）
        
        Args:
            url: Google Sheets URL
            range_name: 范围名称
            df: 要追加的 DataFrame
            
        Returns:
            API 响应结果
        """
        sheet_id = self.extract_sheet_id(url)
        
        # 准备数据（不包含表头）
        values = []
        for _, row in df.iterrows():
            row_values = []
            for val in row:
                if pd.isna(val):
                    row_values.append('')
                elif isinstance(val, (list, dict)):
                    import json
                    row_values.append(json.dumps(val, ensure_ascii=False))
                else:
                    row_values.append(str(val))
            values.append(row_values)
        
        body = {
            'values': values
        }
        
        try:
            result = self.sheets.values().append(
                spreadsheetId=sheet_id,
                range=range_name,
                valueInputOption='RAW',
                insertDataOption='INSERT_ROWS',
                body=body
            ).execute()
            
            return result
            
        except HttpError as e:
            raise RuntimeError(f"追加数据到 Google Sheet 失败: {e}")

