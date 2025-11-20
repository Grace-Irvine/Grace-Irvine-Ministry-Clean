#!/usr/bin/env python3
"""
服务层模块
将清洗层的扁平化数据转换为领域模型（Sermon Domain 和 Volunteer Domain）
"""

import json
import logging
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from pathlib import Path
import pandas as pd

logger = logging.getLogger(__name__)


class DomainTransformer:
    """领域数据转换器基类"""
    
    def __init__(self, domain_name: str, version: str = "1.0"):
        """
        初始化转换器
        
        Args:
            domain_name: 领域名称（如 "sermon" 或 "volunteer"）
            version: 数据版本
        """
        self.domain_name = domain_name
        self.version = version
    
    def generate_metadata(self, records: List[Dict], date_field: str = 'service_date') -> Dict[str, Any]:
        """
        生成元数据
        
        Args:
            records: 记录列表
            date_field: 日期字段名
            
        Returns:
            元数据字典
        """
        dates = [r[date_field] for r in records if r.get(date_field)]
        
        metadata = {
            'domain': self.domain_name,
            'version': self.version,
            'generated_at': datetime.now(timezone.utc).isoformat(),
            'record_count': len(records)
        }
        
        if dates:
            metadata['date_range'] = {
                'start': min(dates),
                'end': max(dates)
            }
        
        return metadata
    
    def transform(self, clean_df: pd.DataFrame, exclude_ids: bool = False) -> Dict[str, Any]:
        """
        转换数据（子类实现）
        
        Args:
            clean_df: 清洗层 DataFrame
            exclude_ids: 是否排除 ID 字段
            
        Returns:
            领域数据字典
        """
        raise NotImplementedError("子类必须实现 transform 方法")


class SermonDomainTransformer(DomainTransformer):
    """证道域转换器"""
    
    def __init__(self):
        super().__init__("sermon", "1.0")
    
    def transform(self, clean_df: pd.DataFrame, exclude_ids: bool = False) -> Dict[str, Any]:
        """
        将清洗层数据转换为证道域格式
        
        Args:
            clean_df: 清洗层 DataFrame
            exclude_ids: 是否排除 ID 字段
            
        Returns:
            证道域数据字典
        """
        logger.info(f"开始转换证道域数据 (exclude_ids={exclude_ids})...")
        
        sermons = []
        
        for _, row in clean_df.iterrows():
            sermon_record = self._transform_row(row, exclude_ids)
            sermons.append(sermon_record)
        
        # 生成元数据
        metadata = self.generate_metadata(sermons)
        
        result = {
            'metadata': metadata,
            'sermons': sermons
        }
        
        logger.info(f"证道域转换完成: {len(sermons)} 条记录")
        return result
    
    def _transform_row(self, row: pd.Series, exclude_ids: bool = False) -> Dict[str, Any]:
        """
        转换单行数据为证道记录
        
        Args:
            row: DataFrame 行
            exclude_ids: 是否排除 ID 字段
            
        Returns:
            证道记录字典
        """
        # 解析 songs JSON 字段
        songs = self._parse_json_field(row.get('songs', ''))
        if isinstance(songs, list) and len(songs) == 1 and isinstance(songs[0], str):
            # 如果只有一个元素且包含分隔符，尝试拆分
            songs = [s.strip() for s in songs[0].replace('，', ',').split(',')]
        
        sermon_record = {
            'service_date': str(row.get('service_date', '')),
            'service_week': int(row.get('service_week', 0)) if pd.notna(row.get('service_week')) else None,
            'service_slot': str(row.get('service_slot', '')),
            'sermon': {
                'title': str(row.get('sermon_title', '')),
                'series': str(row.get('series', '')),
                'scripture': str(row.get('scripture', '')),
                'catechism': str(row.get('catechism', ''))
            },
            'preacher': {
                'name': str(row.get('preacher_name', ''))
            },
            'reading': {
                'name': str(row.get('reading_name', ''))
            },
            'songs': songs if songs else [],
            'source_row': int(row.get('source_row', 0)) if pd.notna(row.get('source_row')) else None,
            'updated_at': str(row.get('updated_at', ''))
        }

        if not exclude_ids:
            sermon_record['preacher']['id'] = str(row.get('preacher_id', ''))
            sermon_record['reading']['id'] = str(row.get('reading_id', ''))
        
        return sermon_record
    
    def _parse_json_field(self, field_value: Any) -> List:
        """
        解析 JSON 字段
        
        Args:
            field_value: 字段值（可能是 JSON 字符串或列表）
            
        Returns:
            解析后的列表
        """
        if pd.isna(field_value) or field_value == '':
            return []
        
        if isinstance(field_value, list):
            return field_value
        
        if isinstance(field_value, str):
            try:
                parsed = json.loads(field_value)
                return parsed if isinstance(parsed, list) else []
            except json.JSONDecodeError:
                # 如果不是有效的 JSON，尝试按分隔符拆分
                return [s.strip() for s in str(field_value).split(',') if s.strip()]
        
        return []


class VolunteerDomainTransformer(DomainTransformer):
    """同工域转换器"""
    
    def __init__(self):
        super().__init__("volunteer", "1.0")
    
    def transform(self, clean_df: pd.DataFrame, exclude_ids: bool = False) -> Dict[str, Any]:
        """
        将清洗层数据转换为同工域格式
        
        Args:
            clean_df: 清洗层 DataFrame
            exclude_ids: 是否排除 ID 字段
            
        Returns:
            同工域数据字典
        """
        logger.info(f"开始转换同工域数据 (exclude_ids={exclude_ids})...")
        
        volunteers = []
        
        for _, row in clean_df.iterrows():
            volunteer_record = self._transform_row(row, exclude_ids)
            volunteers.append(volunteer_record)
        
        # 生成元数据
        metadata = self.generate_metadata(volunteers)
        
        result = {
            'metadata': metadata,
            'volunteers': volunteers
        }
        
        logger.info(f"同工域转换完成: {len(volunteers)} 条记录")
        return result
    
    def _transform_row(self, row: pd.Series, exclude_ids: bool = False) -> Dict[str, Any]:
        """
        转换单行数据为同工记录
        
        Args:
            row: DataFrame 行
            exclude_ids: 是否排除 ID 字段
            
        Returns:
            同工记录字典
        """
        def _p(pid, name):
            """构造人员对象"""
            if exclude_ids:
                # 排除 ID，只返回 name
                return {'name': name} if name else None
            
            # 包含 ID
            return {'id': pid, 'name': name} if name else None
            
        # 解析敬拜同工列表（从独立字段收集）
        worship_team = []
        for i in range(1, 3):  # worship_team_1, worship_team_2
            field_id = f'worship_team_{i}_id'
            field_name = f'worship_team_{i}_name'
            person_id = str(row.get(field_id, ''))
            person_name = str(row.get(field_name, ''))
            
            # 清理 None
            if person_id == 'None': person_id = ''
            if person_name == 'None': person_name = ''
            
            if person_name:  # 只添加有名字的
                # 如果没有 ID，尝试使用名字生成一个临时的 ID (可选)
                # 这里如果不返回对象，下面的逻辑会出错吗？
                # _p 返回 dict 或 None
                p = _p(person_id, person_name)
                if p:
                    worship_team.append(p)
        
        def _get_person(role_prefix):
            pid = str(row.get(f'{role_prefix}_id', ''))
            pname = str(row.get(f'{role_prefix}_name', ''))
            if pid == 'None': pid = ''
            if pname == 'None': pname = ''
            return _p(pid, pname)
            
        volunteer_record = {
            'service_date': str(row.get('service_date', '')),
            'service_week': int(row.get('service_week', 0)) if pd.notna(row.get('service_week')) else None,
            'service_slot': str(row.get('service_slot', '')),
            'worship': {
                'department': str(row.get('worship_lead_department', '')),
                'lead': _get_person('worship_lead'),
                'team': worship_team,
                'pianist': _get_person('pianist')
            },
            'technical': {
                'department': str(row.get('audio_department', '')),
                'audio': _get_person('audio'),
                'video': _get_person('video'),
                'propresenter_play': _get_person('propresenter_play'),
                'propresenter_update': _get_person('propresenter_update'),
                'video_editor': _get_person('video_editor')
            },
            # 儿童部
            'education': {
                'department': str(row.get('friday_child_ministry_department', '')),
                'friday_child_ministry': _get_person('friday_child_ministry'),
                'sunday_child_assistants': [
                    _p(str(row.get(f'sunday_child_assistant_{i}_id', '')), str(row.get(f'sunday_child_assistant_{i}_name', '')))
                    for i in range(1, 4)  # sunday_child_assistant_1, sunday_child_assistant_2, sunday_child_assistant_3
                    if row.get(f'sunday_child_assistant_{i}_name')
                ]
            },
            # 外展联络
            'outreach': {
                'department': str(row.get('newcomer_reception_1_department', '')),
                'newcomer_reception_1': _get_person('newcomer_reception_1'),
                'newcomer_reception_2': _get_person('newcomer_reception_2')
            },
            # 饭食部
            'meal': {
                'department': str(row.get('friday_meal_department', '')),
                'friday_meal': _get_person('friday_meal')
            },
            # 祷告部
            'prayer': {
                'department': str(row.get('prayer_lead_department', '')),
                'prayer_lead': _get_person('prayer_lead')
            },
            'source_row': int(row.get('source_row', 0)) if pd.notna(row.get('source_row')) else None,
            'updated_at': str(row.get('updated_at', ''))
        }
        
        # 清理 None 值
        # 这里简化处理，不递归清理了，由 JSON 序列化时处理或前端处理
        
        return volunteer_record


class WorshipDomainTransformer(DomainTransformer):
    """敬拜域转换器"""
    
    def __init__(self):
        super().__init__("worship", "1.0")
    
    def transform(self, clean_df: pd.DataFrame, exclude_ids: bool = False) -> Dict[str, Any]:
        """
        将清洗层数据转换为敬拜域格式
        
        Args:
            clean_df: 清洗层 DataFrame
            exclude_ids: 是否排除 ID 字段
            
        Returns:
            敬拜域数据字典
        """
        logger.info(f"开始转换敬拜域数据 (exclude_ids={exclude_ids})...")
        
        services = []
        
        for _, row in clean_df.iterrows():
            # 只处理有日期的记录
            if not row.get('service_date'):
                continue
                
            service_record = self._transform_row(row, exclude_ids)
            services.append(service_record)
        
        # 生成元数据
        metadata = self.generate_metadata(services)
        
        result = {
            'metadata': metadata,
            'services': services
        }
        
        logger.info(f"敬拜域转换完成: {len(services)} 条记录")
        return result
    
    def _transform_row(self, row: pd.Series, exclude_ids: bool = False) -> Dict[str, Any]:
        """
        转换单行数据为敬拜记录
        
        Args:
            row: DataFrame 行
            exclude_ids: 是否排除 ID 字段
            
        Returns:
            敬拜记录字典
        """
        def _p(pid, pname):
            if not pname or pname == 'None' or pd.isna(pname):
                return None
            if exclude_ids:
                return {'name': pname}
            return {'id': pid if pid and pid != 'None' else '', 'name': pname}

        # 敬拜团队 (包含 Lead 和 Members)
        worship_team = []
        
        # Lead
        lead_name = str(row.get('worship_lead_name', '')).strip()
        lead_id = str(row.get('worship_lead_id', '')).strip()
        lead = _p(lead_id, lead_name)
        if lead:
            lead['role'] = 'lead'
            worship_team.append(lead)

        # Team members
        for i in range(1, 3):
            p_name = str(row.get(f'worship_team_{i}_name', '')).strip()
            p_id = str(row.get(f'worship_team_{i}_id', '')).strip()
            member = _p(p_id, p_name)
            if member:
                member['role'] = 'vocalist'
                worship_team.append(member)
        
        # Pianist
        pianist_name = str(row.get('pianist_name', '')).strip()
        pianist_id = str(row.get('pianist_id', '')).strip()
        pianist = _p(pianist_id, pianist_name)

        # Songs
        songs_json = row.get('songs', '[]')
        songs = []
        if songs_json:
            try:
                if isinstance(songs_json, str):
                    parsed = json.loads(songs_json)
                    if isinstance(parsed, list):
                        songs = parsed
                elif isinstance(songs_json, list):
                    songs = songs_json
            except:
                pass

        return {
            'date': str(row.get('service_date', '')),
            'worship_team': worship_team,
            'pianist': pianist,
            'songs': songs
        }
    
    def _parse_person_list(self, ids_field: Any, names_field: Any) -> List[Dict[str, str]]:
        """
        解析人员列表（ID 和 Name 配对）
        
        Args:
            ids_field: ID 列表字段（JSON 字符串或列表）
            names_field: 姓名列表字段（JSON 字符串或列表）
            
        Returns:
            人员对象列表
        """
        ids = self._parse_json_field(ids_field)
        names = self._parse_json_field(names_field)
        
        # 配对 ID 和 Name
        person_list = []
        max_len = max(len(ids), len(names))
        
        for i in range(max_len):
            person = {
                'id': ids[i] if i < len(ids) else '',
                'name': names[i] if i < len(names) else ''
            }
            person_list.append(person)
        
        return person_list
    
    def _parse_json_field(self, field_value: Any) -> List:
        """
        解析 JSON 字段
        
        Args:
            field_value: 字段值（可能是 JSON 字符串或列表）
            
        Returns:
            解析后的列表
        """
        if pd.isna(field_value) or field_value == '':
            return []
        
        if isinstance(field_value, list):
            return field_value
        
        if isinstance(field_value, str):
            try:
                parsed = json.loads(field_value)
                return parsed if isinstance(parsed, list) else []
            except json.JSONDecodeError:
                return []
        
        return []


class ServiceLayerManager:
    """服务层管理器"""
    
    def __init__(self):
        """初始化服务层管理器"""
        self.transformers = {
            'sermon': SermonDomainTransformer(),
            'volunteer': VolunteerDomainTransformer(),
            'worship': WorshipDomainTransformer()
        }
    
    def generate_domain_data(
        self, 
        clean_df: pd.DataFrame, 
        domains: Optional[List[str]] = None,
        exclude_ids: bool = False
    ) -> Dict[str, Dict[str, Any]]:
        """
        生成领域数据
        
        Args:
            clean_df: 清洗层 DataFrame
            domains: 要生成的领域列表（None 表示生成所有）
            exclude_ids: 是否排除 ID 字段
            
        Returns:
            领域数据字典，格式：{'sermon': {...}, 'volunteer': {...}}
        """
        if domains is None:
            domains = list(self.transformers.keys())
        
        result = {}
        
        for domain in domains:
            if domain not in self.transformers:
                logger.warning(f"未知的领域: {domain}，跳过")
                continue
            
            transformer = self.transformers[domain]
            domain_data = transformer.transform(clean_df, exclude_ids)
            result[domain] = domain_data
        
        return result
    
    def save_domain_data(
        self, 
        domain_data: Dict[str, Any], 
        output_dir: Path,
        domain_name: str
    ) -> Path:
        """
        保存领域数据到 JSON 文件
        
        Args:
            domain_data: 领域数据字典
            output_dir: 输出目录
            domain_name: 领域名称
            
        Returns:
            保存的文件路径
        """
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        output_file = output_dir / f'{domain_name}.json'
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(domain_data, f, ensure_ascii=False, indent=2)
        
        logger.info(f"已保存 {domain_name} 域数据到: {output_file}")
        return output_file
    
    def generate_and_save(
        self,
        clean_df: pd.DataFrame,
        output_dir: Path,
        domains: Optional[List[str]] = None,
        exclude_ids: bool = False
    ) -> Dict[str, Path]:
        """
        生成并保存领域数据
        
        Args:
            clean_df: 清洗层 DataFrame
            output_dir: 输出目录
            domains: 要生成的领域列表
            exclude_ids: 是否排除 ID 字段
            
        Returns:
            保存的文件路径字典
        """
        # 生成领域数据
        domain_data_dict = self.generate_domain_data(clean_df, domains, exclude_ids)
        
        # 保存每个领域的数据
        saved_files = {}
        for domain_name, domain_data in domain_data_dict.items():
            file_path = self.save_domain_data(domain_data, output_dir, domain_name)
            saved_files[domain_name] = file_path
        
        return saved_files
    
    def generate_all_years(
        self,
        clean_df: pd.DataFrame,
        output_dir: Path,
        domains: Optional[List[str]] = None
    ) -> Dict[str, Dict[str, Path]]:
        """
        生成所有年份的领域数据
        
        Args:
            clean_df: 清洗层 DataFrame
            output_dir: 输出目录
            domains: 要生成的领域列表
            
        Returns:
            按年份保存的文件路径字典，格式：{year: {domain: path}}
        """
        if domains is None:
            domains = list(self.transformers.keys())
        
        # 获取所有年份
        clean_df['year'] = clean_df['service_date'].str[:4]
        years = sorted(clean_df['year'].unique())
        
        logger.info(f"发现 {len(years)} 个年份: {', '.join(years)}")
        
        all_saved_files = {}
        
        # 为每个年份生成数据
        for year in years:
            logger.info(f"生成 {year} 年数据...")
            
            # 筛选该年份的数据
            year_df = clean_df[clean_df['year'] == year].copy()
            
            # 生成领域数据
            domain_data_dict = self.generate_domain_data(year_df, domains)
            
            # 保存到年份目录
            year_dir = Path(output_dir) / year
            year_dir.mkdir(parents=True, exist_ok=True)
            
            saved_files = {}
            for domain_name, domain_data in domain_data_dict.items():
                file_name = f'{domain_name}_{year}.json'
                file_path = year_dir / file_name
                
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(domain_data, f, ensure_ascii=False, indent=2)
                
                saved_files[domain_name] = file_path
                logger.info(f"  已保存 {domain_name}: {file_path}")
            
            all_saved_files[year] = saved_files
        
        # 同时生成 latest（所有数据），exclude_ids=True
        logger.info("生成 latest 文件 (exclude_ids=True)...")
        latest_files = self.generate_and_save(clean_df, output_dir, domains, exclude_ids=True)
        all_saved_files['latest'] = latest_files
        
        return all_saved_files


def main():
    """测试服务层功能"""
    import sys
    import argparse
    
    # 设置日志
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    parser = argparse.ArgumentParser(description='生成服务层领域数据')
    parser.add_argument(
        '--input',
        type=str,
        default='logs/clean_preview.json',
        help='清洗层数据文件路径（JSON 或 CSV）'
    )
    parser.add_argument(
        '--output-dir',
        type=str,
        default='logs/service_layer',
        help='输出目录'
    )
    parser.add_argument(
        '--domains',
        nargs='+',
        choices=['sermon', 'volunteer', 'worship'],
        help='要生成的领域（默认全部）'
    )
    
    args = parser.parse_args()
    
    # 读取清洗层数据
    input_path = Path(args.input)
    
    if not input_path.exists():
        logger.error(f"输入文件不存在: {input_path}")
        sys.exit(1)
    
    logger.info(f"读取清洗层数据: {input_path}")
    
    if input_path.suffix == '.json':
        clean_df = pd.read_json(input_path)
    elif input_path.suffix == '.csv':
        clean_df = pd.read_csv(input_path)
    else:
        logger.error("不支持的文件格式，仅支持 JSON 或 CSV")
        sys.exit(1)
    
    logger.info(f"成功读取 {len(clean_df)} 条记录")
    
    # 生成服务层数据
    manager = ServiceLayerManager()
    saved_files = manager.generate_and_save(
        clean_df,
        Path(args.output_dir),
        args.domains
    )
    
    # 打印摘要
    print("\n" + "=" * 60)
    print("服务层数据生成完成")
    print("=" * 60)
    for domain, file_path in saved_files.items():
        print(f"  {domain.upper()}: {file_path}")
    print("=" * 60)


if __name__ == '__main__':
    main()

