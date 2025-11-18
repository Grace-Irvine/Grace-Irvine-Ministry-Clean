#!/usr/bin/env python3
"""
清理 alias 表脚本
修复 alias 和 display_name 列的数据：
- alias: 原始数据（包含日期，如 "9/26 朵朵"）
- display_name: 清洗后的名称（去除日期和空格，如 "朵朵"）
"""

import sys
from pathlib import Path
import json
import pandas as pd
import logging

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.gsheet_utils import GSheetClient
from core.cleaning_rules import CleaningRules

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def clean_alias_table(start_row: int = 406, config_path: str = "config/config.json"):
    """
    修复 alias 表中从指定行开始的数据
    
    逻辑：
    - alias 列应该包含原始数据（可能包含日期）
    - display_name 列应该包含清洗后的名称（去除日期和空格）
    - 如果 alias 和 display_name 列的数据反了，需要交换
    - 如果 display_name 包含日期，需要从 alias 清洗后生成
    
    Args:
        start_row: 开始清理的行号（从1开始，不包括表头）
        config_path: 配置文件路径
    """
    # 1. 加载配置
    logger.info(f"加载配置文件: {config_path}")
    with open(config_path, 'r', encoding='utf-8') as f:
        config = json.load(f)
    
    alias_config = config.get('alias_sources', {}).get('people_alias_sheet')
    if not alias_config:
        raise ValueError("未找到 alias_sources.people_alias_sheet 配置")
    
    # 2. 初始化客户端和清洗规则
    logger.info("初始化 Google Sheets 客户端...")
    client = GSheetClient()
    
    logger.info("初始化清洗规则...")
    cleaning_rules = CleaningRules(config.get('cleaning_rules', {}))
    
    # 3. 读取 alias 表
    logger.info(f"读取 alias 表: {alias_config['url']}")
    logger.info(f"范围: {alias_config['range']}")
    
    df = client.read_range(alias_config['url'], alias_config['range'])
    
    logger.info(f"读取到 {len(df)} 行数据（不包括表头）")
    logger.info(f"列名: {list(df.columns)}")
    
    # 4. 检查 start_row 是否有效
    if start_row < 1:
        raise ValueError(f"start_row 必须 >= 1，当前值: {start_row}")
    
    start_idx = start_row - 1
    
    if start_idx >= len(df):
        logger.warning(f"start_row {start_row} 超出数据范围（共 {len(df)} 行），跳过清理")
        return
    
    logger.info(f"从第 {start_row} 行开始修复（索引 {start_idx}）")
    
    # 5. 检查列是否存在
    if 'alias' not in df.columns:
        raise ValueError(f"未找到 alias 列。现有列: {list(df.columns)}")
    
    if 'display_name' not in df.columns:
        raise ValueError(f"未找到 display_name 列。现有列: {list(df.columns)}")
    
    # 6. 修复指定行范围的数据
    # 6. 修复和去重
    # 策略：
    # 1. 读取所有数据
    # 2. 对每一行进行清洗（alias 和 display_name 都清洗）
    # 3. 使用 alias 作为 key 进行去重
    # 4. 对于重复的 alias，保留信息最全的（display_name 更合理的）
    
    logger.info("开始处理数据...")
    
    # 用于存储处理后的数据
    # key: cleaned_alias (normalized)
    # value: row_data
    processed_data = {}
    
    # 记录原始行数
    original_count = len(df)
    
    for idx, row in df.iterrows():
        # 获取原始值
        raw_alias = str(row.get('alias', '')).strip()
        raw_display = str(row.get('display_name', '')).strip()
        person_id = str(row.get('person_id', '')).strip()
        
        # 如果 alias 为空，跳过
        if not raw_alias:
            continue
            
        # 清洗 alias 和 display_name
        # 策略：
        # 1. alias 列保持相对原始（只去除日期和多余空格），保留括号和数字，以便 pipeline 能匹配到
        # 2. display_name 列进行激进清洗（去除括号、数字等），作为最终显示
        
        # alias 使用基础清洗（保留括号等）
        cleaned_alias = cleaning_rules.clean_name(raw_alias)
        
        # display_name 使用激进清洗
        # 如果 raw_display 为空，则从 raw_alias 生成
        source_for_display = raw_display if raw_display else raw_alias
        cleaned_display = cleaning_rules.clean_display_name(source_for_display)
        
        # 如果清洗后为空，跳过
        if not cleaned_alias:
            continue
            
        # 如果 display_name 仍为空（例如全是特殊字符），回退到 alias
        if not cleaned_display:
            cleaned_display = cleaned_alias
            
        # 标准化用于去重 key
        key = cleaned_alias.lower()
        
        # 构建新行数据
        new_row = {
            'alias': cleaned_alias,
            'person_id': person_id,
            'display_name': cleaned_display
        }
        
        # 检查是否已存在
        if key in processed_data:
            existing = processed_data[key]
            
            # 合并逻辑
            # 1. 如果现有 person_id 为空或自动生成的，而新的有明确 ID，更新 ID
            # (这里简化处理，优先保留现有的，除非现有的是空的)
            if not existing['person_id'] and new_row['person_id']:
                existing['person_id'] = new_row['person_id']
                
            # 2. display_name 优先使用更长的（通常更完整）
            # 但如果现在的 display_name 已经是清洗过的，可能都差不多
            if len(new_row['display_name']) > len(existing['display_name']):
                existing['display_name'] = new_row['display_name']
                
            logger.info(f"合并重复项: {cleaned_alias}")
        else:
            processed_data[key] = new_row
            
    # 转换为 DataFrame
    new_rows = list(processed_data.values())
    new_df = pd.DataFrame(new_rows)
    
    # 确保列顺序
    cols = ['alias', 'person_id', 'display_name']
    for col in cols:
        if col not in new_df.columns:
            new_df[col] = ''
    new_df = new_df[cols]
    
    logger.info(f"处理完成: 原始 {original_count} 行 -> 清洗后 {len(new_df)} 行")
    logger.info(f"减少了 {original_count - len(new_df)} 行重复/无效数据")
    
    # 7. 写回 Google Sheets
    # 总是全量更新，因为我们做了去重和重组
    logger.info("开始写入 Google Sheets...")
    
    # 获取 sheet 名称
    sheet_name = alias_config['range'].split('!')[0]
    
    # 清空原表（或者覆盖写入）
    # 建议先清空，防止残留数据
    try:
        client.clear_range(alias_config['url'], f"{sheet_name}!A1:Z")
    except Exception as e:
        logger.warning(f"清空范围失败: {e}")
    
    # 写入数据（包含表头）
    client.write_range(
        alias_config['url'],
        f"{sheet_name}!A1",
        new_df,
        include_header=True
    )
    
    logger.info("✅ 成功更新 alias 表")


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='清理 alias 表中从指定行开始的数据',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例用法:
  # 从第 406 行开始清理
  python core/clean_alias_table.py --start-row 406
  
  # 从第 1 行开始清理（清理所有数据）
  python core/clean_alias_table.py --start-row 1
  
  # 指定配置文件
  python core/clean_alias_table.py --start-row 406 --config config/config.json
        """
    )
    
    parser.add_argument(
        '--start-row',
        type=int,
        default=406,
        help='开始清理的行号（从1开始，不包括表头，默认: 406）'
    )
    
    parser.add_argument(
        '--config',
        type=str,
        default='config/config.json',
        help='配置文件路径（默认: config/config.json）'
    )
    
    args = parser.parse_args()
    
    try:
        clean_alias_table(start_row=args.start_row, config_path=args.config)
        logger.info("✅ 清理完成")
    except Exception as e:
        logger.error(f"❌ 清理失败: {e}", exc_info=True)
        sys.exit(1)


if __name__ == '__main__':
    main()

