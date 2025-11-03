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
    updated_count = 0
    changes = []
    
    for idx in range(start_idx, len(df)):
        alias_value = str(df.at[idx, 'alias']) if pd.notna(df.at[idx, 'alias']) else ''
        display_name_value = str(df.at[idx, 'display_name']) if pd.notna(df.at[idx, 'display_name']) else ''
        
        # 检查是否需要修复
        # 情况1: alias 已经被清洗了（不包含日期），但 display_name 包含日期
        #        需要交换它们
        alias_has_date = any(c in alias_value for c in '/-') and any(c.isdigit() for c in alias_value)
        display_has_date = any(c in display_name_value for c in '/-') and any(c.isdigit() for c in display_name_value)
        
        # 判断逻辑：
        # 如果 display_name 包含日期，说明数据可能反了
        # 或者需要从某个值清洗后生成 display_name
        
        # 策略：
        # 1. 如果 display_name 包含日期，而 alias 不包含，说明数据反了，需要交换
        # 2. 如果两者都包含日期，选择较长的作为 alias（原始数据）
        # 3. 如果两者都不包含日期，检查哪个更可能包含日期（通过长度或格式）
        # 4. 无论如何，最终 display_name 应该是清洗后的（不含日期）
        
        # 清洗后的名称（应该放入 display_name）
        cleaned_display = cleaning_rules.clean_name(display_name_value)
        cleaned_alias = cleaning_rules.clean_name(alias_value)
        
        # 确定哪个是原始数据（可能包含日期）
        if display_has_date and not alias_has_date:
            # display_name 包含日期，alias 不包含 -> 数据反了
            original_data = display_name_value
            should_be_display = cleaned_alias
            logger.info(f"第 {idx + 2} 行: 检测到数据反了，交换 alias 和 display_name")
            needs_swap = True
        elif alias_has_date and not display_has_date:
            # alias 包含日期，display_name 不包含 -> 正确
            original_data = alias_value
            should_be_display = cleaned_alias
            needs_swap = False
        elif display_has_date and alias_has_date:
            # 两者都包含日期，选择较长的作为原始数据
            if len(display_name_value) >= len(alias_value):
                original_data = display_name_value
                should_be_display = cleaned_display
                needs_swap = True
            else:
                original_data = alias_value
                should_be_display = cleaned_alias
                needs_swap = False
        else:
            # 两者都不包含日期，检查哪个更像原始数据
            # 如果 display_name 是清洗后的，alias 应该是原始数据
            # 但由于两者都已经被清洗，我们无法确定原始数据
            # 这种情况下，我们假设 alias 是原始数据，display_name 应该从 alias 清洗
            original_data = alias_value if alias_value else display_name_value
            should_be_display = cleaned_alias if alias_value else cleaned_display
            needs_swap = False
        
        # 如果清洗后的值不等于当前值，或者需要交换，则更新
        new_alias = original_data
        new_display = should_be_display
        
        if needs_swap or (alias_value != new_alias) or (display_name_value != new_display):
            old_alias = alias_value
            old_display = display_name_value
            
            df.at[idx, 'alias'] = new_alias
            df.at[idx, 'display_name'] = new_display
            
            updated_count += 1
            changes.append({
                'row': idx + 2,  # +2 因为索引从0开始且有表头
                'old_alias': old_alias,
                'new_alias': new_alias,
                'old_display': old_display,
                'new_display': new_display
            })
            logger.info(f"第 {idx + 2} 行:")
            logger.info(f"  alias: '{old_alias}' -> '{new_alias}'")
            logger.info(f"  display_name: '{old_display}' -> '{new_display}'")
    
    # 7. 如果有更新，写回 Google Sheets
    if updated_count > 0:
        logger.info(f"共更新 {updated_count} 行数据")
        logger.info("开始写入 Google Sheets...")
        
        # 获取 sheet 名称
        sheet_name = alias_config['range'].split('!')[0]
        
        # 写入数据（包含表头）
        client.write_range(
            alias_config['url'],
            f"{sheet_name}!A1",
            df,
            include_header=True
        )
        
        logger.info("✅ 成功更新 alias 表")
        
        # 显示部分更改摘要
        if len(changes) <= 10:
            logger.info("\n所有更改:")
            for change in changes:
                logger.info(f"  第 {change['row']} 行:")
                logger.info(f"    alias: '{change['old_alias']}' -> '{change['new_alias']}'")
                logger.info(f"    display_name: '{change['old_display']}' -> '{change['new_display']}'")
        else:
            logger.info(f"\n前 10 个更改:")
            for change in changes[:10]:
                logger.info(f"  第 {change['row']} 行:")
                logger.info(f"    alias: '{change['old_alias']}' -> '{change['new_alias']}'")
                logger.info(f"    display_name: '{change['old_display']}' -> '{change['new_display']}'")
            logger.info(f"  ... 还有 {len(changes) - 10} 个更改")
    else:
        logger.info("没有需要更新的数据")


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

