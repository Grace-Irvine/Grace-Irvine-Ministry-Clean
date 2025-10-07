#!/usr/bin/env python3
"""
从别名表生成同工元数据表
自动填充 person_id, person_name, updated_at 三列
其他列（family_group, unavailable_start, unavailable_end, unavailable_reason, notes）由用户手动填写
"""

import json
import logging
from datetime import datetime
from pathlib import Path
import pandas as pd
import sys

# 添加脚本目录到 Python 路径
sys.path.insert(0, str(Path(__file__).parent))

from gsheet_utils import GSheetClient

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def load_config(config_path='config/config.json'):
    """加载配置文件"""
    with open(config_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def read_alias_data(config):
    """从别名表读取数据"""
    alias_config = config['alias_sources']['people_alias_sheet']
    
    logger.info(f"读取别名表: {alias_config['url']}")
    
    # 使用 GSheetClient
    client = GSheetClient()
    alias_df = client.read_range(alias_config['url'], alias_config['range'])
    
    logger.info(f"别名表共有 {len(alias_df)} 条记录")
    return alias_df


def extract_unique_persons(alias_df):
    """
    从别名表提取唯一的人员
    使用 display_name 作为标准名称
    """
    # 按 person_id 分组，取每组的第一个 display_name
    unique_persons = alias_df.groupby('person_id').first().reset_index()
    unique_persons = unique_persons[['person_id', 'display_name']].copy()
    unique_persons.rename(columns={'display_name': 'person_name'}, inplace=True)
    
    logger.info(f"提取到 {len(unique_persons)} 个唯一人员")
    
    # 检查是否有重名
    name_counts = unique_persons['person_name'].value_counts()
    duplicates = name_counts[name_counts > 1]
    
    if not duplicates.empty:
        logger.warning("⚠️  发现重名的情况：")
        for name, count in duplicates.items():
            logger.warning(f"  - {name}: {count}次")
            # 显示具体的 person_id
            dup_persons = unique_persons[unique_persons['person_name'] == name]
            for _, row in dup_persons.iterrows():
                logger.warning(f"    • {row['person_id']}")
        logger.warning("  建议在 alias 表中修改 display_name 以区分重名人员")
    else:
        logger.info("✅ 无重名情况")
    
    return unique_persons


def read_existing_metadata(config):
    """读取现有的元数据表（如果存在）"""
    metadata_config = config.get('volunteer_metadata_sheet')
    
    if not metadata_config:
        logger.info("元数据表配置不存在，将创建新表")
        return None
    
    try:
        logger.info(f"读取现有元数据表: {metadata_config['url']}")
        
        # 使用 GSheetClient
        client = GSheetClient()
        metadata_df = client.read_range(metadata_config['url'], metadata_config['range'])
        
        logger.info(f"现有元数据表共有 {len(metadata_df)} 条记录")
        return metadata_df
    except Exception as e:
        logger.warning(f"无法读取现有元数据表: {e}")
        logger.info("将创建新表")
        return None


def merge_metadata(unique_persons, existing_metadata):
    """
    合并新旧数据
    - 保留现有的 family_group, unavailable_*, notes 等列
    - 更新 person_name 和 updated_at
    - 添加新人员
    """
    today = datetime.now().strftime('%Y-%m-%d')
    
    # 创建完整的列结构
    columns = [
        'person_id',
        'person_name',
        'family_group',
        'unavailable_start',
        'unavailable_end',
        'unavailable_reason',
        'notes',
        'updated_at'
    ]
    
    if existing_metadata is None or existing_metadata.empty:
        # 没有现有数据，创建新的
        logger.info("创建新的元数据表")
        new_metadata = unique_persons.copy()
        new_metadata['family_group'] = ''
        new_metadata['unavailable_start'] = ''
        new_metadata['unavailable_end'] = ''
        new_metadata['unavailable_reason'] = ''
        new_metadata['notes'] = ''
        new_metadata['updated_at'] = today
        
        # 确保列顺序正确
        new_metadata = new_metadata[columns]
        
        logger.info(f"生成 {len(new_metadata)} 条新记录")
        return new_metadata
    
    # 有现有数据，进行合并
    logger.info("合并新旧数据...")
    
    # 确保现有数据有所有必要的列
    for col in columns:
        if col not in existing_metadata.columns:
            existing_metadata[col] = ''
    
    # 创建一个字典来存储现有数据
    existing_dict = {}
    for _, row in existing_metadata.iterrows():
        person_id = row['person_id']
        existing_dict[person_id] = {
            'family_group': row.get('family_group', ''),
            'unavailable_start': row.get('unavailable_start', ''),
            'unavailable_end': row.get('unavailable_end', ''),
            'unavailable_reason': row.get('unavailable_reason', ''),
            'notes': row.get('notes', ''),
        }
    
    # 构建新的元数据表
    new_records = []
    updated_count = 0
    new_count = 0
    
    for _, person in unique_persons.iterrows():
        person_id = person['person_id']
        person_name = person['person_name']
        
        if person_id in existing_dict:
            # 现有人员，保留其他列的数据，更新 name 和 updated_at
            record = {
                'person_id': person_id,
                'person_name': person_name,  # 更新名称
                **existing_dict[person_id],
                'updated_at': today  # 更新时间
            }
            updated_count += 1
        else:
            # 新人员
            record = {
                'person_id': person_id,
                'person_name': person_name,
                'family_group': '',
                'unavailable_start': '',
                'unavailable_end': '',
                'unavailable_reason': '',
                'notes': '',
                'updated_at': today
            }
            new_count += 1
        
        new_records.append(record)
    
    new_metadata = pd.DataFrame(new_records)
    new_metadata = new_metadata[columns]  # 确保列顺序
    
    logger.info(f"✅ 更新了 {updated_count} 条现有记录")
    logger.info(f"✅ 添加了 {new_count} 条新记录")
    logger.info(f"✅ 总共 {len(new_metadata)} 条记录")
    
    return new_metadata


def write_metadata_to_sheet(config, metadata_df, dry_run=False):
    """将元数据写入 Google Sheets"""
    metadata_config = config.get('volunteer_metadata_sheet')
    
    if not metadata_config:
        raise ValueError("配置文件中缺少 volunteer_metadata_sheet 配置")
    
    if dry_run:
        logger.info("🔍 Dry-run 模式：不写入 Google Sheets")
        logger.info("预览前5条记录：")
        print(metadata_df.head().to_string(index=False))
        return
    
    logger.info(f"写入元数据到 Google Sheets: {metadata_config['url']}")
    
    # 使用 GSheetClient
    client = GSheetClient()
    sheet_name = metadata_config['range'].split('!')[0]
    
    # 写入数据（包含表头）
    client.write_range(metadata_config['url'], f"{sheet_name}!A1", metadata_df)
    
    logger.info(f"✅ 成功写入 {len(metadata_df)} 条记录到 Google Sheets")


def main():
    import argparse
    
    parser = argparse.ArgumentParser(
        description='从别名表生成同工元数据表',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例：
  # 预览模式（不写入）
  python scripts/generate_volunteer_metadata.py --dry-run
  
  # 正式写入
  python scripts/generate_volunteer_metadata.py
  
  # 使用自定义配置
  python scripts/generate_volunteer_metadata.py --config path/to/config.json
        """
    )
    
    parser.add_argument(
        '--config',
        type=str,
        default='config/config.json',
        help='配置文件路径（默认: config/config.json）'
    )
    
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='预览模式，不写入 Google Sheets'
    )
    
    args = parser.parse_args()
    
    try:
        # 1. 加载配置
        logger.info("=" * 60)
        logger.info("生成同工元数据表")
        logger.info("=" * 60)
        config = load_config(args.config)
        
        # 2. 读取别名表
        alias_df = read_alias_data(config)
        
        # 3. 提取唯一人员
        unique_persons = extract_unique_persons(alias_df)
        
        # 4. 读取现有元数据（如果存在）
        existing_metadata = read_existing_metadata(config)
        
        # 5. 合并数据
        metadata_df = merge_metadata(unique_persons, existing_metadata)
        
        # 6. 写入 Google Sheets
        write_metadata_to_sheet(config, metadata_df, dry_run=args.dry_run)
        
        # 7. 打印摘要
        logger.info("")
        logger.info("=" * 60)
        logger.info("✅ 完成！")
        logger.info("=" * 60)
        logger.info(f"总人数: {len(metadata_df)}")
        logger.info("")
        logger.info("📝 下一步：")
        logger.info("  1. 打开 Google Sheets 查看生成的数据")
        logger.info("  2. 手动填写 family_group（家庭关系）")
        logger.info("  3. 手动填写 unavailable_start/end（不可用时间段）")
        logger.info("  4. 手动填写 notes（备注信息）")
        logger.info("")
        logger.info(f"Google Sheets URL: {config.get('volunteer_metadata_sheet', {}).get('url', 'N/A')}")
        logger.info("=" * 60)
        
        return 0
        
    except Exception as e:
        logger.error(f"❌ 执行失败: {e}", exc_info=True)
        return 1


if __name__ == '__main__':
    sys.exit(main())

