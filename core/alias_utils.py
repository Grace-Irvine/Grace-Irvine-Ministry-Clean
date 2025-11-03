"""
别名映射工具模块
处理人名别名，将多个别名映射到统一的 person_id 和显示名
"""

from typing import Dict, Tuple, Optional, List
import pandas as pd
from collections import Counter
import logging
from core.gsheet_utils import GSheetClient

logger = logging.getLogger(__name__)


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
        标准化名字用于匹配（去除空格、日期、转小写）
        
        Args:
            name: 原始名字
            
        Returns:
            标准化后的名字
        """
        import re
        
        # 去除日期格式（如 "9/26 朵朵" -> "朵朵"）
        # 匹配各种日期格式：9/26, 9/26/2024, 9-26, 2024/9/26, 2024-9-26 等
        # 日期可能在开头、中间或末尾
        date_patterns = [
            r'^\d{1,2}[/-]\d{1,2}[/-]?\d{0,4}\s+',  # 9/26, 9/26/2024, 9-26 等（开头）
            r'\s+\d{1,2}[/-]\d{1,2}[/-]?\d{0,4}\s+',  # 中间位置的日期
            r'\s+\d{1,2}[/-]\d{1,2}[/-]?\d{0,4}$',  # 末尾位置的日期
            r'^\d{4}[/-]\d{1,2}[/-]\d{1,2}\s+',  # 2024/9/26 等（开头）
            r'\s+\d{4}[/-]\d{1,2}[/-]\d{1,2}\s+',  # 中间位置的完整日期
            r'\s+\d{4}[/-]\d{1,2}[/-]\d{1,2}$',  # 末尾位置的完整日期
        ]
        
        for pattern in date_patterns:
            name = re.sub(pattern, ' ', name)
        
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
    
    def extract_names_from_cleaned_data(
        self, 
        df: pd.DataFrame, 
        role_fields: List[str]
    ) -> Counter:
        """
        从清洗后的数据中提取所有人名及其出现次数
        
        Args:
            df: 清洗后的 DataFrame
            role_fields: 需要提取人名的角色字段列表
            
        Returns:
            Counter 对象，key 为人名，value 为出现次数
        """
        names_counter = Counter()
        
        for role in role_fields:
            # 查找带 _name 后缀的列（清洗后的数据格式）
            name_col = f"{role}_name"
            
            if name_col in df.columns:
                for value in df[name_col]:
                    if value and not pd.isna(value) and str(value).strip():
                        name = str(value).strip()
                        names_counter[name] += 1
        
        logger.info(f"从数据中提取了 {len(names_counter)} 个唯一人名")
        return names_counter
    
    def detect_new_and_existing(
        self, 
        names_counter: Counter
    ) -> Tuple[List[Tuple[str, int]], List[Tuple[str, int]]]:
        """
        区分新名字和已存在的名字
        
        Args:
            names_counter: 人名计数器
            
        Returns:
            (新名字列表, 已存在名字列表)，每个元组包含 (name, count)
        """
        new_names = []
        existing_names = []
        
        for name, count in names_counter.items():
            normalized = self._normalize_for_matching(name)
            if normalized in self.alias_map:
                existing_names.append((name, count))
            else:
                new_names.append((name, count))
        
        logger.info(f"检测到 {len(new_names)} 个新名字，{len(existing_names)} 个已存在名字")
        return new_names, existing_names
    
    def sync_to_sheet(
        self, 
        client: GSheetClient, 
        url: str, 
        range_name: str, 
        names_counter: Counter
    ) -> Dict[str, int]:
        """
        同步名字和统计到 Google Sheets
        
        读取现有的 alias_sources 数据，对新名字添加新行，对已有名字更新统计
        
        Args:
            client: GSheetClient 实例
            url: Google Sheets URL
            range_name: 范围名称（如 "generated_aliases!A1:D"）
            names_counter: 人名计数器
            
        Returns:
            统计字典 {'new_added': int, 'updated': int}
        """
        logger.info("开始同步别名到 Google Sheets...")
        
        # 1. 读取现有数据
        try:
            existing_df = client.read_range(url, range_name)
            logger.info(f"读取到 {len(existing_df)} 条现有记录")
        except Exception as e:
            logger.warning(f"读取现有数据失败: {e}，将创建新表")
            existing_df = pd.DataFrame(columns=['alias', 'person_id', 'display_name', 'count'])
        
        # 确保列名标准化
        if not existing_df.empty:
            col_mapping = {}
            for col in existing_df.columns:
                col_lower = col.lower()
                if col_lower in ['alias', 'person_id', 'display_name', 'count']:
                    col_mapping[col] = col_lower
            existing_df = existing_df.rename(columns=col_mapping)
        
        # 确保必需列存在
        for col in ['alias', 'person_id', 'display_name', 'count']:
            if col not in existing_df.columns:
                existing_df[col] = ''
        
        # 2. 创建别名到行索引的映射
        alias_to_idx = {}
        for idx, row in existing_df.iterrows():
            alias = str(row['alias']).strip()
            if alias:
                normalized = self._normalize_for_matching(alias)
                alias_to_idx[normalized] = idx
        
        # 3. 区分新名字和已存在的名字
        new_names, existing_names = self.detect_new_and_existing(names_counter)
        
        # 4. 更新已存在名字的统计
        updated_count = 0
        for name, count in existing_names:
            normalized = self._normalize_for_matching(name)
            if normalized in alias_to_idx:
                idx = alias_to_idx[normalized]
                existing_df.at[idx, 'count'] = count
                updated_count += 1
        
        # 5. 添加新名字
        new_rows = []
        for name, count in new_names:
            normalized = self._normalize_for_matching(name)
            person_id = f"person_{normalized}"
            new_row = {
                'alias': name,
                'person_id': person_id,
                'display_name': name,
                'count': count
            }
            new_rows.append(new_row)
        
        if new_rows:
            new_df = pd.DataFrame(new_rows)
            existing_df = pd.concat([existing_df, new_df], ignore_index=True)
        
        # 6. 写回 Google Sheets
        try:
            # 确保列顺序
            final_df = existing_df[['alias', 'person_id', 'display_name', 'count']]
            
            # 写入（包含表头）
            client.write_range(url, range_name.split('!')[0] + '!A1', final_df, include_header=True)
            
            logger.info(f"✅ 成功同步到 Google Sheets")
            logger.info(f"   新增: {len(new_rows)} 个名字")
            logger.info(f"   更新: {updated_count} 个名字的统计")
            
            return {
                'new_added': len(new_rows),
                'updated': updated_count
            }
        except Exception as e:
            logger.error(f"❌ 写入 Google Sheets 失败: {e}")
            raise

