#!/usr/bin/env python3
"""
测试新增的同工分析提示词
"""

import asyncio
from datetime import datetime, timedelta
import sys
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent))

from mcp_server import server, handle_get_prompt


async def test_analyze_next_sunday_volunteers():
    """测试：分析下周日同工服侍"""
    print("\n" + "="*60)
    print("测试 1: analyze_next_sunday_volunteers")
    print("="*60)
    
    # 不提供日期，让系统自动计算
    result = await handle_get_prompt("analyze_next_sunday_volunteers", {})
    
    print(f"描述: {result.description}")
    print(f"\n提示词内容:")
    for msg in result.messages:
        print(msg.content.text)
    
    # 提供具体日期
    result_with_date = await handle_get_prompt(
        "analyze_next_sunday_volunteers",
        {"date": "2025-10-17"}
    )
    
    print(f"\n\n使用指定日期:")
    print(f"描述: {result_with_date.description}")


async def test_analyze_recent_volunteer_roles():
    """测试：分析最近几周同工岗位分布"""
    print("\n" + "="*60)
    print("测试 2: analyze_recent_volunteer_roles")
    print("="*60)
    
    # 默认参数（4周）
    result = await handle_get_prompt("analyze_recent_volunteer_roles", {})
    
    print(f"描述: {result.description}")
    print(f"\n提示词内容:")
    for msg in result.messages:
        print(msg.content.text[:500] + "...")  # 只显示前500字符
    
    # 自定义参数
    result_custom = await handle_get_prompt(
        "analyze_recent_volunteer_roles",
        {"weeks": "8", "end_date": "2025-10-10"}
    )
    
    print(f"\n\n使用自定义参数 (8周):")
    print(f"描述: {result_custom.description}")


async def test_analyze_volunteer_frequency():
    """测试：分析同工服侍频率"""
    print("\n" + "="*60)
    print("测试 3: analyze_volunteer_frequency")
    print("="*60)
    
    # 使用年份
    result_year = await handle_get_prompt(
        "analyze_volunteer_frequency",
        {"year": "2025"}
    )
    
    print(f"按年份分析:")
    print(f"描述: {result_year.description}")
    print(f"\n提示词内容:")
    for msg in result_year.messages:
        print(msg.content.text[:600] + "...")  # 只显示前600字符
    
    # 使用日期范围
    result_range = await handle_get_prompt(
        "analyze_volunteer_frequency",
        {"start_date": "2025-01-01", "end_date": "2025-06-30"}
    )
    
    print(f"\n\n按日期范围分析:")
    print(f"描述: {result_range.description}")


async def test_all_prompts():
    """运行所有测试"""
    print("\n" + "🚀 "*20)
    print("开始测试同工分析提示词")
    print("🚀 "*20)
    
    try:
        await test_analyze_next_sunday_volunteers()
        await test_analyze_recent_volunteer_roles()
        await test_analyze_volunteer_frequency()
        
        print("\n" + "✅ "*20)
        print("所有测试完成！")
        print("✅ "*20)
        
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()


async def demo_date_calculation():
    """演示日期计算逻辑"""
    print("\n" + "="*60)
    print("日期计算演示")
    print("="*60)
    
    today = datetime.now()
    print(f"今天: {today.strftime('%Y-%m-%d')} (星期{today.weekday()})")
    print(f"weekday 值: 0=周一, 6=周日")
    print(f"今天是星期{today.weekday()}")
    
    # 计算下周日
    days_until_sunday = (6 - today.weekday()) % 7
    if days_until_sunday == 0:
        days_until_sunday = 7
    
    next_sunday = today + timedelta(days=days_until_sunday)
    print(f"\n下周日: {next_sunday.strftime('%Y-%m-%d')}")
    print(f"距离今天: {days_until_sunday} 天")


if __name__ == "__main__":
    # 运行日期计算演示
    asyncio.run(demo_date_calculation())
    
    # 运行所有测试
    asyncio.run(test_all_prompts())

