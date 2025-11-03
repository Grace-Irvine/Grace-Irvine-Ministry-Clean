#!/usr/bin/env python3
"""
智能提取别名脚本
从本地 Excel 文件中智能提取所有人名并生成别名 CSV
"""

import sys
import argparse
from pathlib import Path
from typing import Set, List, Tuple
import pandas as pd
from collections import Counter
import re

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))


def read_excel_with_merged_headers(excel_path: str) -> pd.DataFrame:
    """
    读取带合并表头的 Excel 文件
    第 0 行是部门分类，第 1 行是具体列名
    """
    print(f"📖 读取 Excel 文件: {excel_path}")
    
    # 先读取原始数据
    df_raw = pd.read_excel(excel_path, header=None)
    
    # 第 0 行是部门，第 1 行是列名
    departments = df_raw.iloc[0].fillna('')
    column_names = df_raw.iloc[1].fillna('')
    
    # 合并生成完整列名
    full_column_names = []
    for dept, col in zip(departments, column_names):
        if col and col != '0':
            # 如果有具体列名，使用列名
            full_column_names.append(str(col))
        elif dept:
            # 否则使用部门名
            full_column_names.append(str(dept))
        else:
            # 都没有，使用 Unnamed
            full_column_names.append(f'Unnamed_{len(full_column_names)}')
    
    # 从第 2 行开始是数据
    df = pd.read_excel(excel_path, header=None, skiprows=2)
    df.columns = full_column_names
    
    print(f"✅ 成功读取 {len(df)} 行数据")
    print(f"📊 列名: {list(df.columns[:10])}...")
    print()
    
    return df


def extract_all_people(df: pd.DataFrame) -> List[Tuple[str, int]]:
    """
    从 DataFrame 中提取所有人名
    """
    print("🔍 扫描所有列，寻找人名...")
    
    # 人名相关的关键词
    people_keywords = [
        '讲员', '司会', '读经', '招待', '敬拜', '同工', '司琴',
        '音控', '导播', '摄影', 'ProPresenter', '播放', '更新',
        '助教', '祷告', '服侍', '打扫', '取饭', '财务', '场地', '协调', '外展'
    ]
    
    # 需要排除的关键词（这些是内容，不是人名列）
    exclude_keywords = [
        '日期', '标题', '经文', '系列', '问答', '詩歌', '歌单', '简餐'
    ]
    
    people_counter = Counter()
    processed_columns = []
    
    for col in df.columns:
        col_lower = str(col).lower()
        
        # 跳过明显不是人名的列
        if any(keyword in col for keyword in exclude_keywords):
            continue
        
        # 检查是否可能是人名列
        is_people_column = any(keyword in col for keyword in people_keywords)
        
        if is_people_column or '同工' in col or '协调' in col:
            processed_columns.append(col)
            print(f"  📋 处理列: {col}")
            
            for value in df[col]:
                if pd.notna(value) and value not in ['0', 0, '']:
                    # 清理人名
                    cleaned = clean_name(str(value))
                    
                    # 可能是多个人名，用逗号或中文顿号分隔
                    names = re.split(r'[,，、;；]', cleaned)
                    
                    for name in names:
                        name = name.strip()
                        if name and len(name) > 1 and len(name) < 20:
                            # 过滤明显不是人名的内容
                            if not is_likely_name(name):
                                continue
                            people_counter[name] += 1
    
    print()
    print(f"✅ 处理了 {len(processed_columns)} 个列")
    print(f"✅ 共找到 {len(people_counter)} 个唯一人名")
    print()
    
    # 按出现次数排序
    sorted_people = sorted(people_counter.items(), key=lambda x: x[1], reverse=True)
    
    return sorted_people


def clean_name(name: str) -> str:
    """清理人名"""
    # 去除首尾空格
    name = name.strip()
    
    # 去除常见的非人名字符
    name = name.replace('\n', ' ').replace('\r', '')
    
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
    
    # 去除多余空格
    name = re.sub(r'\s+', ' ', name)
    name = name.strip()
    
    return name


def is_likely_name(text: str) -> bool:
    """判断是否可能是人名"""
    # 太短或太长的不太可能是人名
    if len(text) < 2 or len(text) > 20:
        return False
    
    # 排除纯数字
    if text.isdigit():
        return False
    
    # 排除常见的非人名内容
    exclude_patterns = [
        r'^\d+$',  # 纯数字
        r'^第\d+',  # 第N...
        r'月\d+日',  # 日期
        r'^\d{4}',  # 年份
    ]
    
    for pattern in exclude_patterns:
        if re.match(pattern, text):
            return False
    
    return True


def generate_alias_csv(
    people_list: List[Tuple[str, int]],
    output_path: str,
    include_count: bool = True
):
    """生成别名 CSV 文件"""
    print(f"📝 生成别名 CSV: {output_path}")
    
    # 准备数据
    rows = []
    for name, count in people_list:
        # 生成默认的 person_id
        # 使用简单的规则，用户可以后续手动调整
        person_id = generate_person_id(name)
        
        row = {
            'alias': name,
            'person_id': person_id,
            'display_name': name
        }
        
        if include_count:
            row['count'] = count
            row['note'] = ''  # 用户可以添加备注
        
        rows.append(row)
    
    # 创建 DataFrame
    df = pd.DataFrame(rows)
    
    # 保存为 CSV
    df.to_csv(output_path, index=False, encoding='utf-8-sig')
    
    print(f"✅ 已生成 {len(rows)} 条别名记录")
    print()
    
    # 显示统计
    print("📊 出现频率最高的前 20 位:")
    top_20 = df.nlargest(min(20, len(df)), 'count') if include_count else df.head(20)
    for i, (_, row) in enumerate(top_20.iterrows(), 1):
        if include_count:
            print(f"  {i:2d}. {row['display_name']:20s} - {row['count']:2d} 次")
        else:
            print(f"  {i:2d}. {row['display_name']}")
    print()
    
    print("💡 提示:")
    print("  1. 请检查并手动编辑 CSV 文件")
    print("  2. 合并同一人的不同写法（如：张立军、Zhang Lijun）")
    print("  3. 将它们的 person_id 改为相同值")
    print("  4. 设置统一的 display_name")
    print("  5. 在 note 列添加备注（如：牧师、长老等）")
    print()


def generate_person_id(name: str) -> str:
    """生成默认的 person_id"""
    # 移除空格和特殊字符
    cleaned = re.sub(r'[^\w]', '', name.lower())
    
    # 如果全是英文，直接使用
    if cleaned.isascii():
        return f"person_{cleaned}"
    
    # 如果包含中文，使用拼音或简单编码
    # 这里使用简单的方案，用户后续可以手动调整
    return f"person_{hash(name) % 10000:04d}_{cleaned[:10]}"


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description='从 Excel 文件智能提取人名并生成别名 CSV',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例用法:
  # 生成别名 CSV（包含出现次数和备注列）
  python scripts/extract_aliases_smart.py --excel tests/data.xlsx
  
  # 指定输出路径
  python scripts/extract_aliases_smart.py --excel tests/data.xlsx -o tests/my_aliases.csv
  
  # 生成用于上传到 Google Sheets 的版本（不含次数）
  python scripts/extract_aliases_smart.py --excel tests/data.xlsx -o tests/aliases_for_sheets.csv --no-count
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
        '--no-count',
        action='store_true',
        help='不在 CSV 中包含出现次数列（用于上传到 Google Sheets）'
    )
    
    args = parser.parse_args()
    
    # 检查文件是否存在
    if not Path(args.excel).exists():
        print(f"❌ 错误: Excel 文件不存在: {args.excel}")
        sys.exit(1)
    
    print("=" * 60)
    print("🎯 智能人名提取工具")
    print("=" * 60)
    print()
    
    # 读取 Excel
    try:
        df = read_excel_with_merged_headers(args.excel)
    except Exception as e:
        print(f"❌ 错误: 读取 Excel 失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    
    # 提取人名
    try:
        people_list = extract_all_people(df)
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
    print(f"  1. 打开并编辑 {args.output}")
    print("  2. 合并同一人的不同别名（修改 person_id 为相同值）")
    print("  3. 测试本地清洗: python scripts/debug_clean_local.py --excel tests/data.xlsx --aliases " + args.output)
    print()


if __name__ == '__main__':
    main()

