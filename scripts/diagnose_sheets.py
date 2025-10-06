#!/usr/bin/env python3
"""
诊断 Google Sheets 配置
检查权限、工作表名称等
"""

import os
import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.gsheet_utils import GSheetClient


def diagnose_sheet(client, sheet_url, sheet_name):
    """诊断单个 Google Sheet"""
    print(f"\n{'='*60}")
    print(f"📊 诊断: {sheet_name}")
    print(f"{'='*60}")
    
    try:
        sheet_id = client.extract_sheet_id(sheet_url)
        print(f"✅ Sheet ID: {sheet_id}")
        
        # 尝试获取工作表元数据
        result = client.sheets.get(spreadsheetId=sheet_id).execute()
        
        print(f"✅ Sheet 标题: {result['properties']['title']}")
        print(f"\n📋 工作表列表:")
        
        for i, sheet in enumerate(result.get('sheets', []), 1):
            sheet_props = sheet['properties']
            sheet_title = sheet_props['title']
            sheet_id = sheet_props['sheetId']
            row_count = sheet_props.get('gridProperties', {}).get('rowCount', 0)
            col_count = sheet_props.get('gridProperties', {}).get('columnCount', 0)
            
            print(f"  {i}. {sheet_title}")
            print(f"     - Sheet ID: {sheet_id}")
            print(f"     - 大小: {row_count} 行 × {col_count} 列")
        
        return True
        
    except Exception as e:
        print(f"❌ 错误: {e}")
        return False


def suggest_range(sheets_list):
    """建议使用的范围"""
    print(f"\n💡 建议的配置:")
    print(f"\n对于原始表，尝试以下范围之一:")
    for sheet in sheets_list:
        sheet_title = sheet['properties']['title']
        print(f'  "range": "{sheet_title}!A1:Z"')


def main():
    """主函数"""
    print("=" * 60)
    print("🔍 Google Sheets 配置诊断工具")
    print("=" * 60)
    
    # 检查凭证
    creds = os.environ.get('GOOGLE_APPLICATION_CREDENTIALS')
    if not creds:
        print("\n❌ 错误: GOOGLE_APPLICATION_CREDENTIALS 环境变量未设置")
        sys.exit(1)
    
    print(f"\n✅ 凭证文件: {creds}")
    
    # 读取配置
    config_path = "config/config.json"
    with open(config_path, 'r', encoding='utf-8') as f:
        config = json.load(f)
    
    # 创建客户端
    try:
        client = GSheetClient()
    except Exception as e:
        print(f"\n❌ 创建客户端失败: {e}")
        sys.exit(1)
    
    # 诊断源表
    source_url = config['source_sheet']['url']
    source_ok = diagnose_sheet(client, source_url, "原始表（源表）")
    
    # 诊断目标表
    target_url = config['target_sheet']['url']
    target_ok = diagnose_sheet(client, target_url, "清洗表（目标表）")
    
    # 诊断别名表
    alias_url = config['alias_sources']['people_alias_sheet']['url']
    alias_ok = diagnose_sheet(client, alias_url, "别名表")
    
    # 总结
    print(f"\n{'='*60}")
    print("📊 诊断总结")
    print(f"{'='*60}")
    print(f"原始表: {'✅ 可访问' if source_ok else '❌ 无法访问'}")
    print(f"目标表: {'✅ 可访问' if target_ok else '❌ 无法访问'}")
    print(f"别名表: {'✅ 可访问' if alias_ok else '❌ 无法访问'}")
    
    if not all([source_ok, target_ok, alias_ok]):
        print("\n⚠️  请检查服务账号权限：")
        print("1. 在每个 Google Sheet 中点击 '共享'")
        print("2. 添加服务账号邮箱（从 JSON 文件的 client_email 字段获取）")
        print("3. 设置适当的权限：")
        print("   - 原始表：查看者（Viewer）")
        print("   - 目标表：编辑者（Editor）")
        print("   - 别名表：查看者（Viewer）")
    
    print()


if __name__ == '__main__':
    main()

