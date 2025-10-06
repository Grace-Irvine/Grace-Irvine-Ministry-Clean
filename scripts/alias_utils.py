"""
别名映射工具模块
处理人名别名，将多个别名映射到统一的 person_id 和显示名
"""

from typing import Dict, Tuple, Optional, List
import pandas as pd
from scripts.gsheet_utils import GSheetClient


class AliasMapper:
    """人名别名映射器"""
    
    def __init__(self):
        """初始化别名映射器"""
        self.alias_map: Dict[str, Tuple[str, str]] = {}
        # alias -> (person_id, display_name)
    
    def load_from_dataframe(self, df: pd.DataFrame) -> None:
        """
        从 DataFrame 加载别名映射
        
        DataFrame 应包含三列：
        - alias: 别名（可能是中文名、英文名、昵称等）
        - person_id: 稳定的人员 ID
        - display_name: 首选显示名
        
        Args:
            df: 包含别名数据的 DataFrame
        """
        required_cols = ['alias', 'person_id', 'display_name']
        
        # 检查列名（不区分大小写）
        df_cols_lower = [col.lower() for col in df.columns]
        for req_col in required_cols:
            if req_col not in df_cols_lower:
                raise ValueError(f"别名数据缺少必需列: {req_col}")
        
        # 标准化列名
        col_mapping = {}
        for i, col in enumerate(df.columns):
            col_lower = col.lower()
            if col_lower in required_cols:
                col_mapping[col] = col_lower
        
        df = df.rename(columns=col_mapping)
        
        # 构建映射
        for _, row in df.iterrows():
            alias = str(row['alias']).strip()
            person_id = str(row['person_id']).strip()
            display_name = str(row['display_name']).strip()
            
            if alias and person_id and display_name:
                # 别名标准化（去空格、转小写）用于匹配
                alias_key = self._normalize_for_matching(alias)
                self.alias_map[alias_key] = (person_id, display_name)
    
    def load_from_sheet(self, client: GSheetClient, url: str, range_name: str) -> None:
        """
        从 Google Sheet 加载别名映射
        
        Args:
            client: GSheetClient 实例
            url: Google Sheets URL
            range_name: 范围名称
        """
        df = client.read_range(url, range_name)
        self.load_from_dataframe(df)
    
    def load_from_csv(self, filepath: str) -> None:
        """
        从 CSV 文件加载别名映射
        
        Args:
            filepath: CSV 文件路径
        """
        df = pd.read_csv(filepath)
        self.load_from_dataframe(df)
    
    @staticmethod
    def _normalize_for_matching(name: str) -> str:
        """
        标准化名字用于匹配（去除空格、转小写）
        
        Args:
            name: 原始名字
            
        Returns:
            标准化后的名字
        """
        import re
        # 去除所有空白字符（包括全角空格）
        name = re.sub(r'\s+', '', name)
        name = name.replace('\u3000', '')  # 全角空格
        return name.lower()
    
    def resolve(self, name: str) -> Tuple[str, str]:
        """
        解析名字，返回 person_id 和 display_name
        
        Args:
            name: 输入的名字（可能是别名）
            
        Returns:
            (person_id, display_name) 元组
            如果找不到匹配，返回生成的 ID 和原名
        """
        if not name or pd.isna(name):
            return ('', '')
        
        name_str = str(name).strip()
        if not name_str:
            return ('', '')
        
        # 标准化用于查找
        normalized = self._normalize_for_matching(name_str)
        
        if normalized in self.alias_map:
            return self.alias_map[normalized]
        
        # 如果找不到映射，生成默认 ID
        # 使用拼音或简单转换作为 ID
        person_id = f"person_{normalized}"
        return (person_id, name_str)
    
    def resolve_list(self, names: List[str]) -> Tuple[List[str], List[str]]:
        """
        解析名字列表，返回 ID 列表和显示名列表
        
        Args:
            names: 名字列表
            
        Returns:
            (person_ids, display_names) 元组，两个列表
        """
        person_ids = []
        display_names = []
        
        for name in names:
            pid, dname = self.resolve(name)
            if pid:  # 只添加非空结果
                person_ids.append(pid)
                display_names.append(dname)
        
        return (person_ids, display_names)
    
    def add_mapping(self, alias: str, person_id: str, display_name: str) -> None:
        """
        手动添加一个别名映射
        
        Args:
            alias: 别名
            person_id: 人员 ID
            display_name: 显示名
        """
        alias_key = self._normalize_for_matching(alias)
        self.alias_map[alias_key] = (person_id, display_name)
    
    def get_stats(self) -> Dict[str, int]:
        """
        获取别名映射的统计信息
        
        Returns:
            统计字典
        """
        unique_persons = len(set(pid for pid, _ in self.alias_map.values()))
        return {
            'total_aliases': len(self.alias_map),
            'unique_persons': unique_persons
        }

