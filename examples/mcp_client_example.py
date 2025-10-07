#!/usr/bin/env python3
"""
MCP Client 使用示例
演示如何通过 HTTP API 与 MCP Server 交互
"""

import requests
import json
from typing import Dict, Any

# MCP Server 配置
MCP_SERVER_URL = "http://localhost:8080"
BEARER_TOKEN = None  # 如果启用了鉴权，设置 token

# 请求头
headers = {
    "Content-Type": "application/json"
}
if BEARER_TOKEN:
    headers["Authorization"] = f"Bearer {BEARER_TOKEN}"


def json_rpc_request(method: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
    """发送 JSON-RPC 2.0 请求"""
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": method,
        "params": params or {}
    }
    
    response = requests.post(
        f"{MCP_SERVER_URL}/mcp",
        headers=headers,
        json=payload
    )
    
    return response.json()


def list_tools():
    """列出所有工具"""
    print("\n" + "="*60)
    print("📦 Available Tools")
    print("="*60)
    
    response = requests.get(f"{MCP_SERVER_URL}/mcp/tools", headers=headers)
    tools = response.json().get("tools", [])
    
    for tool in tools:
        print(f"\n🔧 {tool['name']}")
        print(f"   {tool['description']}")


def list_resources():
    """列出所有资源"""
    print("\n" + "="*60)
    print("📚 Available Resources")
    print("="*60)
    
    response = requests.get(f"{MCP_SERVER_URL}/mcp/resources", headers=headers)
    resources = response.json().get("resources", [])
    
    for resource in resources:
        print(f"\n📖 {resource['name']}")
        print(f"   URI: {resource['uri']}")
        print(f"   {resource['description']}")


def list_prompts():
    """列出所有提示词"""
    print("\n" + "="*60)
    print("💬 Available Prompts")
    print("="*60)
    
    response = requests.get(f"{MCP_SERVER_URL}/mcp/prompts", headers=headers)
    prompts = response.json().get("prompts", [])
    
    for prompt in prompts:
        print(f"\n💭 {prompt['name']}")
        print(f"   {prompt['description']}")


def call_tool_example():
    """示例：调用工具"""
    print("\n" + "="*60)
    print("🔧 Tool Call Example: validate_raw_data")
    print("="*60)
    
    # 方式 1: 使用便捷端点
    response = requests.post(
        f"{MCP_SERVER_URL}/mcp/tools/validate_raw_data",
        headers=headers,
        json={
            "check_duplicates": True,
            "generate_report": True
        }
    )
    
    result = response.json()
    print(json.dumps(result, indent=2, ensure_ascii=False))
    
    # 方式 2: 使用 JSON-RPC
    # result = json_rpc_request(
    #     "tools/call",
    #     {
    #         "name": "validate_raw_data",
    #         "arguments": {
    #             "check_duplicates": True,
    #             "generate_report": True
    #         }
    #     }
    # )


def read_resource_example():
    """示例：读取资源"""
    print("\n" + "="*60)
    print("📖 Resource Read Example: sermon-records")
    print("="*60)
    
    # 方式 1: 使用便捷端点
    response = requests.get(
        f"{MCP_SERVER_URL}/mcp/resources/read",
        headers=headers,
        params={"uri": "ministry://sermon/records"}
    )
    
    result = response.json()
    
    # 解析内容
    if "contents" in result:
        content = json.loads(result["contents"][0]["text"])
        metadata = content.get("metadata", {})
        sermons = content.get("sermons", [])
        
        print(f"\n📊 Metadata:")
        print(f"   Total: {metadata.get('total_count', 0)}")
        print(f"   Date Range: {metadata.get('date_range', {})}")
        
        print(f"\n📝 First 3 Sermons:")
        for sermon in sermons[:3]:
            print(f"\n   {sermon.get('service_date')}")
            print(f"   Title: {sermon.get('sermon', {}).get('title')}")
            print(f"   Preacher: {sermon.get('preacher', {}).get('name')}")
    else:
        print(json.dumps(result, indent=2, ensure_ascii=False))


def get_prompt_example():
    """示例：获取提示词"""
    print("\n" + "="*60)
    print("💭 Prompt Example: analyze_preaching_schedule")
    print("="*60)
    
    response = requests.get(
        f"{MCP_SERVER_URL}/mcp/prompts/analyze_preaching_schedule",
        headers=headers,
        params={"arguments": json.dumps({"year": "2024"})}
    )
    
    result = response.json()
    
    if "messages" in result:
        for message in result["messages"]:
            print(f"\n{message['role'].upper()}:")
            print(message['content']['text'])
    else:
        print(json.dumps(result, indent=2, ensure_ascii=False))


def query_by_preacher_example():
    """示例：按讲员查询证道"""
    print("\n" + "="*60)
    print("🔍 Query Example: Sermons by Preacher")
    print("="*60)
    
    preacher_name = "王通"  # 修改为实际讲员名称
    
    response = requests.get(
        f"{MCP_SERVER_URL}/mcp/resources/read",
        headers=headers,
        params={"uri": f"ministry://sermon/by-preacher/{preacher_name}"}
    )
    
    result = response.json()
    
    if "contents" in result:
        content = json.loads(result["contents"][0]["text"])
        sermons = content.get("sermons", [])
        
        print(f"\n讲员: {preacher_name}")
        print(f"讲道次数: {len(sermons)}")
        
        print(f"\n最近 5 次讲道:")
        for sermon in sermons[-5:]:
            print(f"   {sermon.get('service_date')} - {sermon.get('sermon', {}).get('title')}")


def get_volunteer_stats_example():
    """示例：获取同工统计"""
    print("\n" + "="*60)
    print("📊 Stats Example: Volunteer Statistics")
    print("="*60)
    
    response = requests.get(
        f"{MCP_SERVER_URL}/mcp/resources/read",
        headers=headers,
        params={"uri": "ministry://stats/volunteers"}
    )
    
    result = response.json()
    
    if "contents" in result:
        content = json.loads(result["contents"][0]["text"])
        volunteers = content.get("volunteers", [])
        
        print(f"\n总同工数: {content.get('total_volunteers', 0)}")
        
        # 按服侍次数排序
        sorted_volunteers = sorted(
            volunteers,
            key=lambda x: x.get('count', 0),
            reverse=True
        )
        
        print(f"\n服侍次数 Top 10:")
        for i, volunteer in enumerate(sorted_volunteers[:10], 1):
            print(f"   {i}. {volunteer.get('name')} - {volunteer.get('count')} 次")


def main():
    """主函数"""
    print("\n" + "="*60)
    print("🚀 MCP Client Example")
    print("="*60)
    
    try:
        # 健康检查
        print("\n🏥 Health Check...")
        response = requests.get(f"{MCP_SERVER_URL}/health", headers=headers)
        print(f"   Status: {response.json().get('status')}")
        
        # 列出功能
        list_tools()
        list_resources()
        list_prompts()
        
        # 示例操作
        print("\n\n" + "="*60)
        print("📝 Running Examples")
        print("="*60)
        
        # 1. 校验数据
        call_tool_example()
        
        # 2. 读取资源
        read_resource_example()
        
        # 3. 按讲员查询
        query_by_preacher_example()
        
        # 4. 同工统计
        get_volunteer_stats_example()
        
        # 5. 获取提示词
        get_prompt_example()
        
        print("\n" + "="*60)
        print("✅ Examples completed successfully!")
        print("="*60)
    
    except requests.exceptions.ConnectionError:
        print("\n❌ Error: Cannot connect to MCP Server")
        print(f"   Make sure server is running at {MCP_SERVER_URL}")
        print("   Start with: python3 mcp_http_server.py")
    
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()

