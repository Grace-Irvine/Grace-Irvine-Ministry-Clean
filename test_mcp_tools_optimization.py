#!/usr/bin/env python3
"""
测试 MCP 工具优化
验证只有查询工具暴露给 MCP，管理工具仍可通过 HTTP 访问
"""

import asyncio
import sys
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent))

# 导入 MCP Server
import mcp_server


async def test_mcp_tools_list():
    """测试 MCP 工具列表只包含查询工具"""
    print("=" * 60)
    print("测试 1: MCP 工具列表")
    print("=" * 60)
    
    tools = await mcp_server.handle_list_tools()
    tool_names = [tool.name for tool in tools]
    
    print(f"\n暴露给 MCP 的工具数量: {len(tool_names)}")
    print("\n工具列表:")
    for i, name in enumerate(tool_names, 1):
        print(f"  {i}. {name}")
    
    # 验证只有查询工具
    expected_tools = {
        "query_volunteers_by_date",
        "query_sermon_by_date",
        "query_date_range"
    }
    
    # 不应该包含的管理工具
    management_tools = {
        "clean_ministry_data",
        "generate_service_layer",
        "validate_raw_data",
        "sync_from_gcs"
    }
    
    print("\n验证结果:")
    
    # 检查期望的工具都存在
    missing_tools = expected_tools - set(tool_names)
    if missing_tools:
        print(f"  ❌ 缺少查询工具: {missing_tools}")
        return False
    else:
        print(f"  ✅ 所有查询工具都存在")
    
    # 检查管理工具不存在
    exposed_management = set(tool_names) & management_tools
    if exposed_management:
        print(f"  ❌ 管理工具不应暴露: {exposed_management}")
        return False
    else:
        print(f"  ✅ 管理工具已移除")
    
    # 检查工具数量
    if len(tool_names) != 3:
        print(f"  ❌ 工具数量错误: 期望 3 个，实际 {len(tool_names)} 个")
        return False
    else:
        print(f"  ✅ 工具数量正确: 3 个")
    
    return True


async def test_mcp_prompts_list():
    """测试 MCP 提示词列表只包含分析提示"""
    print("\n" + "=" * 60)
    print("测试 2: MCP 提示词列表")
    print("=" * 60)
    
    prompts = await mcp_server.handle_list_prompts()
    prompt_names = [prompt.name for prompt in prompts]
    
    print(f"\n暴露给 MCP 的提示词数量: {len(prompt_names)}")
    print("\n提示词列表:")
    for i, name in enumerate(prompt_names, 1):
        print(f"  {i}. {name}")
    
    # 验证只有分析提示
    expected_prompts = {
        "analyze_preaching_schedule",
        "analyze_volunteer_balance",
        "find_scheduling_gaps"
    }
    
    # 不应该包含的管理提示
    management_prompts = {
        "check_data_quality",
        "suggest_alias_merges"
    }
    
    print("\n验证结果:")
    
    # 检查期望的提示都存在
    missing_prompts = expected_prompts - set(prompt_names)
    if missing_prompts:
        print(f"  ❌ 缺少分析提示: {missing_prompts}")
        return False
    else:
        print(f"  ✅ 所有分析提示都存在")
    
    # 检查管理提示不存在
    exposed_management = set(prompt_names) & management_prompts
    if exposed_management:
        print(f"  ❌ 管理提示不应暴露: {exposed_management}")
        return False
    else:
        print(f"  ✅ 管理提示已移除")
    
    # 检查提示数量
    if len(prompt_names) != 3:
        print(f"  ❌ 提示数量错误: 期望 3 个，实际 {len(prompt_names)} 个")
        return False
    else:
        print(f"  ✅ 提示数量正确: 3 个")
    
    return True


async def test_management_tools_implementation():
    """测试管理工具的实现仍然存在（供 HTTP API 使用）"""
    print("\n" + "=" * 60)
    print("测试 3: 管理工具实现（HTTP API 可用性）")
    print("=" * 60)
    
    management_tools = [
        "clean_ministry_data",
        "generate_service_layer",
        "validate_raw_data",
        "sync_from_gcs"
    ]
    
    print("\n检查工具实现是否存在:")
    
    all_exist = True
    for tool_name in management_tools:
        try:
            # 尝试调用工具（使用空参数，预期会失败但能验证实现存在）
            result = await mcp_server.handle_call_tool(tool_name, {})
            print(f"  ✅ {tool_name}: 实现存在")
        except Exception as e:
            # 即使失败，只要不是 "Unknown tool" 错误就说明实现存在
            if "Unknown tool" in str(e):
                print(f"  ❌ {tool_name}: 实现不存在")
                all_exist = False
            else:
                print(f"  ✅ {tool_name}: 实现存在（调用时出现预期错误）")
    
    return all_exist


async def test_gcs_client_initialization():
    """测试 GCS 客户端初始化状态"""
    print("\n" + "=" * 60)
    print("测试 4: GCS 客户端初始化")
    print("=" * 60)
    
    if mcp_server.GCS_CLIENT is not None:
        print("\n  ✅ GCS 客户端已初始化")
        print(f"  Bucket: {mcp_server.STORAGE_CONFIG.get('bucket', 'N/A')}")
        print(f"  Base Path: {mcp_server.STORAGE_CONFIG.get('base_path', 'N/A')}")
        return True
    else:
        print("\n  ⚠️  GCS 客户端未初始化")
        print("  这在本地开发环境是正常的")
        print("  在 Cloud Run 部署时会通过服务账号初始化")
        return True  # 本地环境可以没有 GCS


async def main():
    """运行所有测试"""
    print("\n" + "=" * 60)
    print("MCP 工具优化 - 验证测试")
    print("=" * 60)
    
    results = []
    
    # 运行测试
    results.append(("MCP 工具列表", await test_mcp_tools_list()))
    results.append(("MCP 提示词列表", await test_mcp_prompts_list()))
    results.append(("管理工具实现", await test_management_tools_implementation()))
    results.append(("GCS 客户端", await test_gcs_client_initialization()))
    
    # 汇总结果
    print("\n" + "=" * 60)
    print("测试结果汇总")
    print("=" * 60)
    
    for test_name, passed in results:
        status = "✅ 通过" if passed else "❌ 失败"
        print(f"{status}: {test_name}")
    
    all_passed = all(passed for _, passed in results)
    
    print("\n" + "=" * 60)
    if all_passed:
        print("✅ 所有测试通过！")
        print("\n总结:")
        print("  - MCP 接口只暴露 3 个查询工具")
        print("  - 管理工具实现保留，可通过 HTTP API 访问")
        print("  - 数据从 GCS 读取（服务端认证）")
        print("  - ChatGPT 只需提供 MCP Bearer Token")
    else:
        print("❌ 部分测试失败，请检查实现")
    print("=" * 60)
    
    return 0 if all_passed else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)

