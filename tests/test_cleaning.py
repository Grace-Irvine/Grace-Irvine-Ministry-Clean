"""
数据清洗单元测试
测试清洗规则、别名映射、歌曲拆分等功能
"""

import pytest
import pandas as pd
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from core.cleaning_rules import CleaningRules
from core.alias_utils import AliasMapper
from core.validators import DataValidator


@pytest.fixture
def cleaning_config():
    """测试用的清洗配置"""
    return {
        'date_format': 'YYYY-MM-DD',
        'strip_spaces': True,
        'trim_fullwidth_spaces': True,
        'split_songs_delimiters': ['、', ',', '/', '|'],
        'normalize_scripture': True,
        'merge_columns': {
            'worship_team': ['worship_team_1', 'worship_team_2']
        }
    }


@pytest.fixture
def cleaning_rules(cleaning_config):
    """创建 CleaningRules 实例"""
    return CleaningRules(cleaning_config)


@pytest.fixture
def alias_mapper():
    """创建并加载别名映射"""
    mapper = AliasMapper()
    # 加载测试别名数据
    test_aliases_path = Path(__file__).parent / 'sample_aliases.csv'
    if test_aliases_path.exists():
        mapper.load_from_csv(str(test_aliases_path))
    return mapper


class TestCleaningRules:
    """测试清洗规则"""
    
    def test_clean_text_basic(self, cleaning_rules):
        """测试基本文本清理"""
        assert cleaning_rules.clean_text('  hello  ') == 'hello'
        assert cleaning_rules.clean_text('hello　world') == 'hello world'  # 全角空格
        assert cleaning_rules.clean_text('hello   world') == 'hello world'  # 多空格
        assert cleaning_rules.clean_text('-') == ''
        assert cleaning_rules.clean_text('N/A') == ''
        assert cleaning_rules.clean_text(None) == ''
        assert cleaning_rules.clean_text('') == ''
    
    def test_clean_date_formats(self, cleaning_rules):
        """测试日期格式清洗"""
        # 标准格式
        assert cleaning_rules.clean_date('2025-10-05') == '2025-10-05'
        assert cleaning_rules.clean_date('2025/10/05') == '2025-10-05'
        
        # 中文格式
        assert cleaning_rules.clean_date('2025年10月5日') == '2025-10-05'
        assert cleaning_rules.clean_date('2025年10月05日') == '2025-10-05'
        
        # 美式格式
        assert cleaning_rules.clean_date('10/05/2025') == '2025-10-05'
        
        # 无效格式
        assert cleaning_rules.clean_date('invalid-date') is None
        assert cleaning_rules.clean_date('') is None
        assert cleaning_rules.clean_date(None) is None
    
    def test_clean_scripture(self, cleaning_rules):
        """测试经文引用清理"""
        assert cleaning_rules.clean_scripture('以弗所书4:1-6') == '以弗所书 4:1-6'
        assert cleaning_rules.clean_scripture('  以弗所书 4:1-6  ') == '以弗所书 4:1-6'
        assert cleaning_rules.clean_scripture('John3:16') == 'John 3:16'
    
    def test_split_songs(self, cleaning_rules):
        """测试歌曲拆分"""
        # 单个分隔符
        result = cleaning_rules.split_songs('奇异恩典、我心灵得安宁')
        assert result == ['奇异恩典', '我心灵得安宁']
        
        # 多个分隔符
        result = cleaning_rules.split_songs('奇异恩典 / 我心灵得安宁')
        assert result == ['奇异恩典', '我心灵得安宁']
        
        result = cleaning_rules.split_songs('奇异恩典|宝贵十架|荣耀归主名')
        assert result == ['奇异恩典', '宝贵十架', '荣耀归主名']
        
        # 混合分隔符
        result = cleaning_rules.split_songs('奇异恩典、我心灵得安宁 / 宝贵十架')
        assert len(result) == 3
        
        # 去重
        result = cleaning_rules.split_songs('奇异恩典、奇异恩典')
        assert result == ['奇异恩典']
        
        # 空值
        assert cleaning_rules.split_songs('') == []
        assert cleaning_rules.split_songs(None) == []
    
    def test_merge_columns(self, cleaning_rules):
        """测试列合并"""
        row = pd.Series({
            'worship_team_1': '陈明',
            'worship_team_2': '林芳'
        })
        result = cleaning_rules.merge_columns(row, ['worship_team_1', 'worship_team_2'])
        assert result == ['陈明', '林芳']
        
        # 带空值
        row = pd.Series({
            'worship_team_1': '陈明',
            'worship_team_2': ''
        })
        result = cleaning_rules.merge_columns(row, ['worship_team_1', 'worship_team_2'])
        assert result == ['陈明']
        
        # 去重
        row = pd.Series({
            'worship_team_1': '陈明',
            'worship_team_2': '陈明'
        })
        result = cleaning_rules.merge_columns(row, ['worship_team_1', 'worship_team_2'])
        assert result == ['陈明']
    
    def test_get_service_week(self, cleaning_rules):
        """测试服务周数计算"""
        week = cleaning_rules.get_service_week('2025-10-05')
        assert isinstance(week, int)
        assert 1 <= week <= 53
        
        assert cleaning_rules.get_service_week('') is None
        assert cleaning_rules.get_service_week(None) is None


class TestAliasMapper:
    """测试别名映射"""
    
    def test_resolve_exact_match(self, alias_mapper):
        """测试精确匹配"""
        person_id, display_name = alias_mapper.resolve('张牧师')
        assert person_id == 'preacher_zhang'
        assert display_name == '张牧师'
    
    def test_resolve_alias(self, alias_mapper):
        """测试别名解析"""
        # 英文别名
        person_id, display_name = alias_mapper.resolve('Pastor Zhang')
        assert person_id == 'preacher_zhang'
        assert display_name == '张牧师'
        
        # 短名
        person_id, display_name = alias_mapper.resolve('张')
        assert person_id == 'preacher_zhang'
        assert display_name == '张牧师'
    
    def test_resolve_case_insensitive(self, alias_mapper):
        """测试大小写不敏感"""
        person_id, display_name = alias_mapper.resolve('wangli')
        assert person_id == 'person_wangli'
        assert display_name == '王丽'
    
    def test_resolve_with_spaces(self, alias_mapper):
        """测试带空格的名字"""
        # 空格应该被忽略
        person_id, display_name = alias_mapper.resolve('  王丽  ')
        assert person_id == 'person_wangli'
        assert display_name == '王丽'
    
    def test_resolve_unknown(self, alias_mapper):
        """测试未知名字"""
        person_id, display_name = alias_mapper.resolve('未知人员')
        # 应该生成默认 ID
        assert person_id.startswith('person_')
        assert display_name == '未知人员'
    
    def test_resolve_empty(self, alias_mapper):
        """测试空值"""
        person_id, display_name = alias_mapper.resolve('')
        assert person_id == ''
        assert display_name == ''
        
        person_id, display_name = alias_mapper.resolve(None)
        assert person_id == ''
        assert display_name == ''
    
    def test_resolve_list(self, alias_mapper):
        """测试列表解析"""
        names = ['张牧师', 'Pastor Zhang', '未知人员']
        ids, displays = alias_mapper.resolve_list(names)
        
        assert len(ids) == 3
        assert len(displays) == 3
        assert ids[0] == 'preacher_zhang'
        assert ids[1] == 'preacher_zhang'


class TestDataValidator:
    """测试数据校验器"""
    
    @pytest.fixture
    def validator_config(self):
        """校验器配置"""
        return {
            'cleaning_rules': {
                'role_whitelist': ['敬拜带领', '司琴', '音控']
            }
        }
    
    def test_validate_required_fields(self, validator_config):
        """测试必填字段校验"""
        validator = DataValidator(validator_config)
        
        # 有效数据
        df = pd.DataFrame([
            {'service_date': '2025-10-05', 'sermon_title': '主里合一'}
        ])
        report = validator.validate_dataframe(df)
        assert report.error_rows == 0
        
        # 缺少必填字段
        df = pd.DataFrame([
            {'service_date': '', 'sermon_title': '主里合一'}
        ])
        report = validator.validate_dataframe(df)
        assert report.error_rows > 0
    
    def test_validate_date_format(self, validator_config):
        """测试日期格式校验"""
        validator = DataValidator(validator_config)
        
        # 有效日期
        df = pd.DataFrame([
            {'service_date': '2025-10-05'}
        ])
        report = validator.validate_dataframe(df)
        assert report.error_rows == 0
        
        # 无效日期格式
        df = pd.DataFrame([
            {'service_date': 'invalid-date'}
        ])
        report = validator.validate_dataframe(df)
        assert report.error_rows > 0
        
        # 无效日期值
        df = pd.DataFrame([
            {'service_date': '2025-13-32'}
        ])
        report = validator.validate_dataframe(df)
        assert report.error_rows > 0
    
    def test_validate_duplicates(self, validator_config):
        """测试重复记录检测"""
        validator = DataValidator(validator_config)
        
        # 重复的日期和时段
        df = pd.DataFrame([
            {'service_date': '2025-10-05', 'service_slot': 'morning'},
            {'service_date': '2025-10-05', 'service_slot': 'morning'}
        ])
        report = validator.validate_dataframe(df)
        assert report.warning_rows > 0


def test_full_pipeline_with_sample_data():
    """使用样例数据测试完整管线"""
    # 读取样例数据
    sample_path = Path(__file__).parent / 'sample_raw.csv'
    if not sample_path.exists():
        pytest.skip("样例数据文件不存在")
    
    df = pd.read_csv(sample_path)
    
    # 创建清洗规则
    config = {
        'date_format': 'YYYY-MM-DD',
        'strip_spaces': True,
        'trim_fullwidth_spaces': True,
        'split_songs_delimiters': ['、', ',', '/', '|'],
        'normalize_scripture': True
    }
    rules = CleaningRules(config)
    
    # 创建别名映射
    mapper = AliasMapper()
    alias_path = Path(__file__).parent / 'sample_aliases.csv'
    if alias_path.exists():
        mapper.load_from_csv(str(alias_path))
    
    # 测试每行数据
    for idx, row in df.iterrows():
        # 测试日期清洗
        date_result = rules.clean_date(row['主日日期'])
        if date_result:
            # 有效日期应该是 YYYY-MM-DD 格式
            assert len(date_result) == 10
            assert date_result[4] == '-'
            assert date_result[7] == '-'
        
        # 测试歌曲拆分
        if pd.notna(row['詩歌']) and row['詩歌']:
            songs = rules.split_songs(row['詩歌'])
            assert isinstance(songs, list)
        
        # 测试人名解析
        if pd.notna(row['讲员']) and row['讲员']:
            person_id, display_name = mapper.resolve(row['讲员'])
            assert person_id
            assert display_name


if __name__ == '__main__':
    pytest.main([__file__, '-v'])


