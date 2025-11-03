"""
数据清洗规则模块
实现各种数据清洗和标准化规则
"""

import re
from typing import List, Optional, Any
from datetime import datetime
import pandas as pd
from dateutil import parser as date_parser


class CleaningRules:
    """数据清洗规则集合"""
    
    def __init__(self, config: dict):
        """
        初始化清洗规则
        
        Args:
            config: 清洗配置字典（来自 config.json 的 cleaning_rules）
        """
        self.config = config
        self.date_format = config.get('date_format', 'YYYY-MM-DD')
        self.strip_spaces = config.get('strip_spaces', True)
        self.trim_fullwidth_spaces = config.get('trim_fullwidth_spaces', True)
        self.split_songs_delimiters = config.get('split_songs_delimiters', ['、', ',', '/', '|'])
        self.normalize_scripture = config.get('normalize_scripture', True)
    
    def clean_text(self, text: Any) -> str:
        """
        清理文本：去除首尾空格、标准化空白字符、处理占位符
        
        Args:
            text: 输入文本
            
        Returns:
            清理后的文本
        """
        if pd.isna(text) or text is None:
            return ''
        
        text_str = str(text).strip()
        
        # 处理占位符
        if text_str in ['-', 'N/A', 'n/a', 'NA', 'null', 'None', '无', '—', '──']:
            return ''
        
        if self.trim_fullwidth_spaces:
            # 去除全角空格
            text_str = text_str.replace('\u3000', ' ')
        
        if self.strip_spaces:
            # 去除首尾空格
            text_str = text_str.strip()
            # 多个空格合并为一个
            text_str = re.sub(r'\s+', ' ', text_str)
        
        return text_str
    
    def clean_date(self, date_str: Any) -> Optional[str]:
        """
        清理和标准化日期
        
        Args:
            date_str: 日期字符串（支持多种格式）
            
        Returns:
            标准化的日期字符串（YYYY-MM-DD）或 None
        """
        if pd.isna(date_str) or not date_str:
            return None
        
        date_str = self.clean_text(date_str)
        if not date_str:
            return None
        
        try:
            # 使用 dateutil 解析多种日期格式
            dt = date_parser.parse(date_str, fuzzy=True)
            return dt.strftime('%Y-%m-%d')
        except (ValueError, TypeError, date_parser.ParserError):
            # 尝试手动解析常见的中文格式
            try:
                # 匹配 YYYY年MM月DD日 格式
                match = re.search(r'(\d{4})\s*年\s*(\d{1,2})\s*月\s*(\d{1,2})\s*日?', date_str)
                if match:
                    year, month, day = match.groups()
                    return f"{year}-{month.zfill(2)}-{day.zfill(2)}"
                
                # 匹配 YYYY/MM/DD 或 YYYY-MM-DD 格式
                match = re.search(r'(\d{4})[-/](\d{1,2})[-/](\d{1,2})', date_str)
                if match:
                    year, month, day = match.groups()
                    return f"{year}-{month.zfill(2)}-{day.zfill(2)}"
            except Exception:
                pass
            
            return None
    
    def clean_scripture(self, scripture: Any) -> str:
        """
        清理和标准化经文引用
        
        Args:
            scripture: 经文引用字符串
            
        Returns:
            标准化的经文引用
        """
        scripture_str = self.clean_text(scripture)
        
        if not scripture_str or not self.normalize_scripture:
            return scripture_str
        
        # 标准化空格
        # 在书名和章节之间、章节和经节之间保持一个空格
        scripture_str = re.sub(r'\s+', ' ', scripture_str)
        
        # 标准化书名和章节之间的空格
        # 例如："以弗所书4:1-6" -> "以弗所书 4:1-6"
        scripture_str = re.sub(r'([a-zA-Z\u4e00-\u9fff])(\d)', r'\1 \2', scripture_str)
        
        return scripture_str.strip()
    
    def split_songs(self, songs_str: Any) -> List[str]:
        """
        拆分歌曲字符串为列表
        
        Args:
            songs_str: 歌曲字符串，可能包含多个分隔符
            
        Returns:
            歌曲列表
        """
        songs_str = self.clean_text(songs_str)
        if not songs_str:
            return []
        
        # 构建正则表达式，匹配任意配置的分隔符
        delimiters_pattern = '|'.join(re.escape(d) for d in self.split_songs_delimiters)
        songs = re.split(delimiters_pattern, songs_str)
        
        # 清理每首歌曲的名称
        cleaned_songs = []
        for song in songs:
            song_clean = song.strip()
            if song_clean and song_clean not in cleaned_songs:
                cleaned_songs.append(song_clean)
        
        return cleaned_songs
    
    def merge_columns(self, row: pd.Series, source_cols: List[str]) -> List[str]:
        """
        合并多个列的值为列表（过滤空值）
        
        Args:
            row: DataFrame 行
            source_cols: 源列名列表
            
        Returns:
            合并后的值列表
        """
        merged = []
        for col in source_cols:
            if col in row:
                val = self.clean_text(row[col])
                if val and val not in merged:
                    merged.append(val)
        return merged
    
    def get_service_week(self, date_str: str) -> Optional[int]:
        """
        从日期计算服务周数（ISO 周数）
        
        Args:
            date_str: 日期字符串（YYYY-MM-DD）
            
        Returns:
            周数或 None
        """
        if not date_str:
            return None
        
        try:
            dt = datetime.strptime(date_str, '%Y-%m-%d')
            return dt.isocalendar()[1]  # ISO 周数
        except ValueError:
            return None
    
    def infer_service_slot(self, time_str: Optional[str] = None) -> str:
        """
        推断服务时段（早堂/午堂等）
        
        Args:
            time_str: 时间字符串（可选）
            
        Returns:
            服务时段标识，默认为 'morning'
        """
        if not time_str:
            return 'morning'
        
        time_str = self.clean_text(time_str).lower()
        
        if any(keyword in time_str for keyword in ['早', 'morning', '上午', '9', '10']):
            return 'morning'
        elif any(keyword in time_str for keyword in ['午', 'noon', '中午', '12', '13']):
            return 'noon'
        elif any(keyword in time_str for keyword in ['晚', 'evening', '下午', '15', '16', '17', '18', '19']):
            return 'evening'
        else:
            return 'morning'
    
    def clean_name(self, name: Any) -> str:
        """
        清理人名
        
        Args:
            name: 人名
            
        Returns:
            清理后的人名
        """
        name_str = self.clean_text(name)
        
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
            name_str = re.sub(pattern, ' ', name_str)
        
        # 再次清理文本（去除多余空格）
        name_str = self.clean_text(name_str)
        
        # 去除常见的职位后缀（如果配置允许）
        if self.config.get('capitalize_names', True):
            # 保持原样，不强制大写（中文名不需要）
            pass
        
        return name_str
    
    @staticmethod
    def validate_not_empty(value: Any, field_name: str) -> None:
        """
        校验字段非空
        
        Args:
            value: 字段值
            field_name: 字段名
            
        Raises:
            ValueError: 如果字段为空
        """
        if pd.isna(value) or not str(value).strip():
            raise ValueError(f"必填字段 '{field_name}' 不能为空")

