#!/usr/bin/env python3
"""
从本地 Excel 文件生成别名 CSV 表格
用于调试和准备别名数据
"""

import sys
import argparse
from pathlib import Path
from typing import Set, List, Tuple
import pandas as pd
from collections import Counter

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.cleaning_rules import CleaningRules


def extract_people_from_excel(excel_path: str, config_path: str = "config/config.json") -> List[Tuple[str, int]]:
    """
    从 Excel 文件中提取所有人名
    
    Args:
        excel_path: Excel 文件路径
        config_path: 配置文件路径
        
    Returns:
        人名列表，格式为 [(name, count), ...]，按出现次数排序
    """
    import json
    
    # 读取配置
    with open(config_path, 'r', encoding='utf-8') as f:
        config = json.load(f)
    
    # 读取 Excel 文件
    print(f"📖 读取 Excel 文件: {excel_path}")
    df = pd.read_excel(excel_path)
    print(f"✅ 成功读取 {len(df)} 行数据")
    print(f"📊 列名: {list(df.columns)}")
    print()
    
    # 获取人名相关的列（从配置中获取）
    people_columns = [
        'preacher',
        'worship_lead',
        'worship_team_1',
        'worship_team_2',
        'pianist',
        'audio',
        'video',
        'propresenter_play',
        'propresenter_update',
        'assistant'
    ]
    
    # 获取中文列名
    column_mapping = config['columns']
    chinese_people_columns = [column_mapping.get(col) for col in people_columns if col in column_mapping]
    
    print(f"🔍 检查以下人名列: {chinese_people_columns}")
    print()
    
    # 初始化清洗规则
    cleaning_rules = CleaningRules(config['cleaning_rules'])
    
    # 收集所有人名
    people_counter = Counter()
    
    for col in chinese_people_columns:
        if col in df.columns:
            print(f"📋 处理列: {col}")
            for value in df[col]:
                # 清理人名
                cleaned = cleaning_rules.clean_name(value)
                if cleaned:
                    people_counter[cleaned] += 1
                    print(f"  - {cleaned}")
    
    print()
    print(f"✅ 共找到 {len(people_counter)} 个唯一人名")
    print()
    
    # 按出现次数排序
    sorted_people = sorted(people_counter.items(), key=lambda x: x[1], reverse=True)
    
    return sorted_people


def generate_alias_csv(
    people_list: List[Tuple[str, int]],
    output_path: str,
    include_count: bool = True
):
    """
    生成别名 CSV 文件
    
    Args:
        people_list: 人名列表 [(name, count), ...]
        output_path: 输出文件路径
        include_count: 是否包含出现次数列
    """
    print(f"📝 生成别名 CSV: {output_path}")
    
    # 准备数据
    rows = []
    for name, count in people_list:
        # 生成默认的 person_id（使用拼音或简单转换）
        # 这里用简单的规则，用户可以后续手动调整
        person_id = f"person_{name.lower().replace(' ', '_')}"
        
        row = {
            'alias': name,
            'person_id': person_id,
            'display_name': name
        }
        
        if include_count:
            row['count'] = count
        
        rows.append(row)
    
    # 创建 DataFrame
    df = pd.DataFrame(rows)
    
    # 保存为 CSV
    df.to_csv(output_path, index=False, encoding='utf-8-sig')
    
    print(f"✅ 已生成 {len(rows)} 条别名记录")
    print()
    print("📋 前 10 条记录预览:")
    print(df.head(10).to_string(index=False))
    print()
    
    if include_count:
        print("📊 出现频率最高的前 10 位:")
        top_10 = df.nlargest(10, 'count')
        for _, row in top_10.iterrows():
            print(f"  {row['display_name']:20s} - {row['count']:2d} 次")
        print()
    
    print("💡 提示:")
    print("  1. 请检查并手动编辑 CSV 文件")
    print("  2. 合并同一人的不同写法（如：张牧师、Pastor Zhang、张）")
    print("  3. 将它们的 person_id 改为相同值")
    print("  4. 设置统一的 display_name")
    print()


def preview_data(excel_path: str, n_rows: int = 5):
    """
    预览 Excel 文件的前几行数据
    
    Args:
        excel_path: Excel 文件路径
        n_rows: 预览行数
    """
    print(f"👀 预览 Excel 文件: {excel_path}")
    print()
    
    df = pd.read_excel(excel_path)
    
    print(f"📊 总行数: {len(df)}")
    print(f"📊 总列数: {len(df.columns)}")
    print()
    
    print(f"📋 列名列表:")
    for i, col in enumerate(df.columns, 1):
        print(f"  {i:2d}. {col}")
    print()
    
    print(f"📖 前 {n_rows} 行数据:")
    print(df.head(n_rows).to_string())
    print()


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description='从 Excel 文件生成别名 CSV 表格',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例用法:
  # 预览 Excel 数据
  python scripts/generate_aliases_from_excel.py --excel tests/data.xlsx --preview
  
  # 生成别名 CSV（包含出现次数）
  python scripts/generate_aliases_from_excel.py --excel tests/data.xlsx -o tests/aliases.csv
  
  # 生成别名 CSV（不包含出现次数，用于上传到 Google Sheets）
  python scripts/generate_aliases_from_excel.py --excel tests/data.xlsx -o tests/aliases.csv --no-count
        """
    )
    
    parser.add_argument(
        '--excel',
        type=str,
        required=True,
        help='Excel 文件路径'
    )
    parser.add_argument(
        '-o', '--output',
        type=str,
        default='tests/generated_aliases.csv',
        help='输出 CSV 文件路径（默认: tests/generated_aliases.csv）'
    )
    parser.add_argument(
        '--config',
        type=str,
        default='config/config.json',
        help='配置文件路径（默认: config/config.json）'
    )
    parser.add_argument(
        '--preview',
        action='store_true',
        help='仅预览 Excel 数据，不生成 CSV'
    )
    parser.add_argument(
        '--no-count',
        action='store_true',
        help='不在 CSV 中包含出现次数列（用于上传到 Google Sheets）'
    )
    
    args = parser.parse_args()
    
    # 检查文件是否存在
    if not Path(args.excel).exists():
        print(f"❌ 错误: Excel 文件不存在: {args.excel}")
        sys.exit(1)
    
    # 预览模式
    if args.preview:
        preview_data(args.excel)
        return
    
    # 提取人名
    try:
        people_list = extract_people_from_excel(args.excel, args.config)
    except Exception as e:
        print(f"❌ 错误: 提取人名失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    
    if not people_list:
        print("⚠️  警告: 未找到任何人名")
        sys.exit(0)
    
    # 生成 CSV
    try:
        generate_alias_csv(
            people_list,
            args.output,
            include_count=not args.no_count
        )
    except Exception as e:
        print(f"❌ 错误: 生成 CSV 失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    
    print(f"🎉 完成！别名 CSV 已保存到: {args.output}")
    print()
    print("📝 下一步:")
    print(f"  1. 编辑 {args.output}，合并同一人的不同写法")
    print("  2. 测试本地清洗: python scripts/debug_clean_local.py")
    print("  3. 上传到 Google Sheets（使用 --no-count 选项重新生成）")
    print()


if __name__ == '__main__':
    main()

