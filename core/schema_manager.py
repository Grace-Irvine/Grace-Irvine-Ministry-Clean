#!/usr/bin/env python3
"""
Schema 管理器
处理列映射、部门信息、动态字段检测
"""

import logging
from typing import Dict, Any, List, Tuple, Optional, Set
from pathlib import Path
import json

logger = logging.getLogger(__name__)


class ColumnMapping:
    """列映射配置类"""
    
    def __init__(self, field_name: str, config: Any, department: Optional[str] = None):
        """
        初始化列映射
        
        Args:
            field_name: 标准字段名（如 'preacher', 'assistant'）
            config: 配置值（字符串或字典）
            department: 所属部门
        """
        self.field_name = field_name
        self.department = department
        
        if isinstance(config, str):
            # 简单映射：\"preacher\": \"讲员\"
            self.sources = [config]
            self.merge = False
            self.is_simple = True
        elif isinstance(config, dict):
            # 高级映射：{\"sources\": [...], \"merge\": true}
            self.sources = config.get('sources', [])
            self.merge = config.get('merge', False)
            self.department = config.get('department', department)
            self.is_simple = False
        else:
            raise ValueError(f"Invalid column config for '{field_name}': {config}")
    
    def matches_source_column(self, source_col: str) -> bool:
        """检查源列名是否匹配此映射"""
        return source_col in self.sources
    
    def __repr__(self):
        return f"ColumnMapping({self.field_name}, sources={self.sources}, merge={self.merge})"


class SchemaManager:
    """Schema 管理器"""
    
    def __init__(self, config: Dict[str, Any]):
        """
        初始化 Schema 管理器
        
        Args:
            config: 完整的配置字典
        """
        self.config = config
        self.departments = config.get('departments', {})
        self.column_configs = config.get('columns', {})
        self.schema_validation = config.get('schema_validation', {
            'enabled': True,
            'auto_detect_new_columns': True,
            'strict_mode': False
        })
        
        # 解析列映射
        self.column_mappings: List[ColumnMapping] = []
        self.source_to_field_map: Dict[str, str] = {}
        self.field_to_mapping_map: Dict[str, ColumnMapping] = {}
        self._parse_column_mappings()
        
        # 构建部门到角色的映射
        self.role_to_department_map: Dict[str, str] = {}
        self._build_role_department_map()
        
        logger.info(
            f"SchemaManager 初始化完成: "
            f"{len(self.column_mappings)} 个列映射, "
            f"{len(self.departments)} 个部门"
        )
    
    def _parse_column_mappings(self) -> None:
        """解析列映射配置"""
        for field_name, config in self.column_configs.items():
            # 跳过非映射配置
            if field_name.startswith('_'):
                continue
            
            try:
                mapping = ColumnMapping(field_name, config)
                self.column_mappings.append(mapping)
                self.field_to_mapping_map[field_name] = mapping
                
                # 构建源列到字段的映射
                for source_col in mapping.sources:
                    self.source_to_field_map[source_col] = field_name
                
            except Exception as e:
                logger.warning(f"解析列映射失败 '{field_name}': {e}")
    
    def _build_role_department_map(self) -> None:
        """构建角色到部门的映射"""
        for dept_key, dept_config in self.departments.items():
            dept_name = dept_config.get('name', dept_key)
            roles = dept_config.get('roles', [])
            
            for role in roles:
                self.role_to_department_map[role] = dept_name
    
    def get_standard_field_name(self, source_column: str) -> Optional[str]:
        """
        获取源列对应的标准字段名
        
        Args:
            source_column: 源列名（如 \"讲员\", \"助教1\"）
            
        Returns:
            标准字段名（如 'preacher', 'assistant'）或 None
        """
        return self.source_to_field_map.get(source_column)
    
    def get_mapping(self, field_name: str) -> Optional[ColumnMapping]:
        """
        获取字段的映射配置
        
        Args:
            field_name: 标准字段名
            
        Returns:
            ColumnMapping 或 None
        """
        return self.field_to_mapping_map.get(field_name)
    
    def get_department(self, field_name: str) -> Optional[str]:
        """
        获取字段所属的部门
        
        Args:
            field_name: 标准字段名
            
        Returns:
            部门名称或 None
        """
        # 优先从映射配置中获取
        mapping = self.get_mapping(field_name)
        if mapping and mapping.department:
            # 如果是部门 key，转换为部门名称
            dept_config = self.departments.get(mapping.department, {})
            return dept_config.get('name', mapping.department)
        
        # 从角色到部门的映射中获取
        return self.role_to_department_map.get(field_name)
    
    def map_source_columns(
        self, 
        source_columns: List[str]
    ) -> Tuple[Dict[str, str], List[str]]:
        """
        映射源列名到标准字段名
        
        Args:
            source_columns: 源列名列表
            
        Returns:
            (映射字典, 未配置的列列表)
        """
        mapped = {}
        unmapped = []
        
        for source_col in source_columns:
            field_name = self.get_standard_field_name(source_col)
            if field_name:
                mapped[source_col] = field_name
            else:
                # 检查是否应该忽略（空列、Unnamed等）
                if source_col and not source_col.startswith('Unnamed') and source_col.strip():
                    unmapped.append(source_col)
        
        return mapped, unmapped
    
    def get_merge_groups(self) -> Dict[str, List[str]]:
        """
        获取需要合并的字段组
        
        Returns:
            字典，key 为字段名，value 为源列名列表
        """
        merge_groups = {}
        
        for mapping in self.column_mappings:
            if mapping.merge and len(mapping.sources) > 1:
                merge_groups[mapping.field_name] = mapping.sources
        
        return merge_groups
    
    def detect_new_columns(
        self, 
        source_columns: List[str]
    ) -> List[str]:
        """
        检测未配置的新列
        
        Args:
            source_columns: 源列名列表
            
        Returns:
            新列列表
        """
        if not self.schema_validation.get('auto_detect_new_columns', True):
            return []
        
        _, unmapped = self.map_source_columns(source_columns)
        return unmapped
    
    def generate_config_suggestions(
        self, 
        new_columns: List[str],
        department_mapping: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """
        为新列生成配置建议
        
        Args:
            new_columns: 新列列表
            department_mapping: 列到部门的映射（可选）
            
        Returns:
            配置建议字典
        """
        suggestions = {
            'new_columns_detected': len(new_columns),
            'columns': {}
        }
        
        for col in new_columns:
            # 尝试智能推断字段名
            field_name = self._suggest_field_name(col)
            
            suggestion = {
                'source_column': col,
                'suggested_field': field_name,
                'department': department_mapping.get(col) if department_mapping else None,
                'config_example_simple': f'"{field_name}": "{col}"',
                'config_example_advanced': {
                    'sources': [col],
                    'merge': False,
                    'department': department_mapping.get(col) if department_mapping else 'unknown'
                }
            }
            
            suggestions['columns'][col] = suggestion
        
        return suggestions
    
    def _suggest_field_name(self, source_column: str) -> str:
        """
        智能推断字段名
        
        Args:
            source_column: 源列名
            
        Returns:
            建议的字段名
        """
        # 移除数字后缀
        import re
        base_name = re.sub(r'\d+$', '', source_column)
        
        # 转换为英文（简单映射）
        name_map = {
            '助教': 'assistant',
            '同工': 'team_member',
            '敬拜': 'worship',
            '司琴': 'pianist',
            '音控': 'audio',
            '导播': 'video',
            '摄影': 'photographer',
            '讲员': 'preacher',
            '读经': 'reading',
        }
        
        for cn, en in name_map.items():
            if cn in base_name:
                return en
        
        # 默认返回拼音或原名
        return base_name.lower().replace(' ', '_')
    
    def validate_schema(self, source_columns: List[str]) -> Dict[str, Any]:
        """
        校验 schema
        
        Args:
            source_columns: 源列名列表
            
        Returns:
            校验报告
        """
        if not self.schema_validation.get('enabled', True):
            return {'validated': False, 'reason': 'Schema validation disabled'}
        
        new_columns = self.detect_new_columns(source_columns)
        mapped, unmapped = self.map_source_columns(source_columns)
        
        report = {
            'validated': True,
            'total_columns': len(source_columns),
            'mapped_columns': len(mapped),
            'unmapped_columns': len(unmapped),
            'new_columns': new_columns,
            'strict_mode': self.schema_validation.get('strict_mode', False)
        }
        
        if new_columns:
            logger.warning(
                f"检测到 {len(new_columns)} 个未配置的列: {', '.join(new_columns)}"
            )
            
            if self.schema_validation.get('strict_mode', False):
                report['validated'] = False
                report['error'] = f"Strict mode: 发现未配置的列"
        
        return report
    
    def get_all_role_fields(self) -> List[str]:
        """
        获取所有角色字段名
        
        Returns:
            角色字段名列表
        """
        # 从映射中提取角色字段（排除非角色字段如 service_date, sermon_title 等）
        non_role_fields = {
            'service_date', 'series', 'sermon_title', 'scripture', 
            'catechism', 'reading', 'songs', 'notes'
        }
        
        role_fields = []
        for field_name in self.field_to_mapping_map.keys():
            if field_name not in non_role_fields:
                role_fields.append(field_name)
        
        return role_fields


def load_schema_manager(config_path: str) -> SchemaManager:
    """
    从配置文件加载 SchemaManager
    
    Args:
        config_path: 配置文件路径
        
    Returns:
        SchemaManager 实例
    """
    with open(config_path, 'r', encoding='utf-8') as f:
        config = json.load(f)
    
    return SchemaManager(config)


if __name__ == '__main__':
    # 测试
    logging.basicConfig(level=logging.INFO)
    
    test_config = {
        'departments': {
            'worship': {
                'name': '敬拜部',
                'roles': ['worship_lead', 'worship_team', 'pianist']
            },
            'technical': {
                'name': '技术部',
                'roles': ['audio', 'video', 'propresenter_play']
            }
        },
        'columns': {
            'preacher': '讲员',
            'worship_lead': '敬拜带领',
            'worship_team': {
                'sources': ['敬拜同工1', '敬拜同工2'],
                'merge': True,
                'department': 'worship'
            },
            'assistant': {
                'sources': ['助教', '助教1', '助教2'],
                'merge': True
            }
        }
    }
    
    manager = SchemaManager(test_config)
    
    # 测试映射
    print("\n=== 测试列映射 ===")
    print(f"'讲员' -> {manager.get_standard_field_name('讲员')}")
    print(f"'助教1' -> {manager.get_standard_field_name('助教1')}")
    
    # 测试部门
    print("\n=== 测试部门查询 ===")
    print(f"worship_lead 部门: {manager.get_department('worship_lead')}")
    print(f"audio 部门: {manager.get_department('audio')}")
    
    # 测试新列检测
    print("\n=== 测试新列检测 ===")
    source_cols = ['讲员', '助教1', '助教3', '新角色']
    new_cols = manager.detect_new_columns(source_cols)
    print(f"新列: {new_cols}")
    
    # 生成配置建议
    if new_cols:
        suggestions = manager.generate_config_suggestions(new_cols)
        print("\n=== 配置建议 ===")
        print(json.dumps(suggestions, ensure_ascii=False, indent=2))

