#!/usr/bin/env python3
"""
测试 OpenAI Apps SDK 对齐
验证工具元数据和响应格式
"""

import asyncio
import json
from mcp_server import handle_list_tools, handle_call_tool


async def test_tool_metadata():
    """测试工具元数据（_meta 字段）"""
    print("=" * 60)
    print("测试 1: 工具元数据")
    print("=" * 60)
    
    tools = await handle_list_tools()
    
    print(f"\n找到 {len(tools)} 个工具\n")
    
    for tool in tools:
        tool_dict = tool.model_dump()
        name = tool_dict.get("name")
        has_meta = "meta" in tool_dict and tool_dict["meta"]
        
        if has_meta:
            meta = tool_dict["meta"]
            invoking = meta.get("openai/toolInvocation/invoking", "N/A")
            invoked = meta.get("openai/toolInvocation/invoked", "N/A")
            print(f"✅ {name}")
            print(f"   invoking: {invoking}")
            print(f"   invoked: {invoked}")
        else:
            print(f"❌ {name} - 缺少 meta 字段")
    
    return all("meta" in t.model_dump() and t.model_dump()["meta"] for t in tools)


async def test_response_format():
    """测试响应格式（text + structuredContent）"""
    print("\n" + "=" * 60)
    print("测试 2: 响应格式")
    print("=" * 60)
    
    # 测试查询工具
    print("\n测试 query_volunteers_by_date...")
    
    try:
        result = await handle_call_tool(
            "query_volunteers_by_date",
            {"date": "2025-10-12"}
        )
        
        if result:
            response_dict = result[0].model_dump()
            
            print(f"\n响应字段:")
            print(f"  type: {response_dict.get('type')}")
            print(f"  text: {response_dict.get('text')}")
            print(f"  structuredContent: {'存在' if 'structuredContent' in response_dict else '缺失'}")
            
            # 验证 text 不是 JSON 字符串
            text = response_dict.get('text', '')
            is_json_string = text.strip().startswith('{') or text.strip().startswith('[')
            
            if is_json_string:
                print(f"\n❌ text 字段仍然是 JSON 字符串")
                return False
            else:
                print(f"\n✅ text 字段是人类可读的描述")
            
            # 验证 structuredContent 存在且是字典
            if 'structuredContent' in response_dict:
                structured = response_dict['structuredContent']
                if isinstance(structured, dict):
                    print(f"✅ structuredContent 是字典对象")
                    print(f"   包含字段: {list(structured.keys())}")
                    return True
                else:
                    print(f"❌ structuredContent 不是字典")
                    return False
            else:
                print(f"❌ 缺少 structuredContent 字段")
                return False
        else:
            print(f"❌ 无响应")
            return False
            
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        return False


async def test_json_serialization():
    """测试 JSON 序列化"""
    print("\n" + "=" * 60)
    print("测试 3: JSON 序列化")
    print("=" * 60)
    
    try:
        tools = await handle_list_tools()
        tools_json = json.dumps(
            {"tools": [t.model_dump() for t in tools]},
            ensure_ascii=False,
            indent=2
        )
        
        print(f"\n工具列表 JSON 大小: {len(tools_json)} 字符")
        
        # 验证 meta 字段在 JSON 中
        if '"meta"' in tools_json:
            print(f"✅ meta 字段正确序列化")
        else:
            print(f"❌ meta 字段未在 JSON 中")
            return False
        
        # 测试响应序列化
        result = await handle_call_tool(
            "query_volunteers_by_date",
            {"date": "2025-10-12"}
        )
        
        if result:
            response_json = json.dumps(
                {"content": [r.model_dump() for r in result]},
                ensure_ascii=False,
                indent=2
            )
            
            print(f"响应 JSON 大小: {len(response_json)} 字符")
            
            # 验证 structuredContent 字段
            if '"structuredContent"' in response_json:
                print(f"✅ structuredContent 字段正确序列化")
                return True
            else:
                print(f"❌ structuredContent 字段未在 JSON 中")
                return False
        else:
            print(f"❌ 无响应")
            return False
            
    except Exception as e:
        print(f"❌ JSON 序列化失败: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """运行所有测试"""
    print("\n🧪 OpenAI Apps SDK 对齐测试\n")
    
    results = {
        "工具元数据": await test_tool_metadata(),
        "响应格式": await test_response_format(),
        "JSON 序列化": await test_json_serialization()
    }
    
    print("\n" + "=" * 60)
    print("测试总结")
    print("=" * 60)
    
    for test_name, passed in results.items():
        status = "✅ 通过" if passed else "❌ 失败"
        print(f"{test_name}: {status}")
    
    all_passed = all(results.values())
    
    if all_passed:
        print("\n🎉 所有测试通过！")
    else:
        print("\n⚠️  部分测试失败，请检查")
    
    return 0 if all_passed else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)

