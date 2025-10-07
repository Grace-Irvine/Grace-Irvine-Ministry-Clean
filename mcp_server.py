#!/usr/bin/env python3
"""
MCP (Model Context Protocol) Server Implementation
提供标准 MCP 协议接口，暴露教会主日事工数据管理工具、资源和提示词
"""

import os
import sys
import json
import logging
import asyncio
from pathlib import Path
from typing import Any, Dict, List, Optional
from datetime import datetime

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent))

# MCP SDK imports
from mcp.server.models import InitializationOptions
from mcp.server import NotificationOptions, Server
import mcp.server.stdio
import mcp.types as types

# 导入应用层代码
from scripts.clean_pipeline import CleaningPipeline
from scripts.service_layer import ServiceLayerManager
from scripts.validators import Validator
from scripts.alias_utils import AliasUtils

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 配置文件路径
CONFIG_PATH = os.getenv('CONFIG_PATH', 'config/config.json')
LOGS_DIR = Path("logs/service_layer")

# ============================================================
# 辅助函数
# ============================================================

def load_service_layer_data(domain: str, year: Optional[str] = None) -> Dict[str, Any]:
    """加载服务层数据"""
    try:
        if year:
            data_path = LOGS_DIR / year / f"{domain}_{year}.json"
        else:
            data_path = LOGS_DIR / f"{domain}.json"
        
        if not data_path.exists():
            return {"error": f"Data file not found: {data_path}"}
        
        with open(data_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Error loading service layer data: {e}")
        return {"error": str(e)}


def filter_by_date(records: List[Dict], date_str: Optional[str] = None) -> List[Dict]:
    """按日期过滤记录"""
    if not date_str:
        return records
    
    return [r for r in records if r.get('service_date', '').startswith(date_str)]


def filter_by_preacher(sermons: List[Dict], preacher_name: str) -> List[Dict]:
    """按讲员过滤证道记录"""
    return [
        s for s in sermons 
        if s.get('preacher', {}).get('name', '').lower() == preacher_name.lower()
    ]


def get_person_records(records: List[Dict], person_identifier: str) -> List[Dict]:
    """获取某人的所有服侍记录"""
    result = []
    for record in records:
        # 搜索所有可能的位置
        for role, person in record.items():
            if isinstance(person, dict):
                if (person.get('id') == person_identifier or 
                    person.get('name', '').lower() == person_identifier.lower()):
                    result.append({
                        'service_date': record.get('service_date'),
                        'role': role,
                        'person': person
                    })
            elif isinstance(person, list):
                for p in person:
                    if isinstance(p, dict):
                        if (p.get('id') == person_identifier or 
                            p.get('name', '').lower() == person_identifier.lower()):
                            result.append({
                                'service_date': record.get('service_date'),
                                'role': role,
                                'person': p
                            })
    return result


# ============================================================
# MCP Server 实例
# ============================================================

server = Server("ministry-data-mcp")

# ============================================================
# MCP Tools（工具）
# ============================================================

@server.list_tools()
async def handle_list_tools() -> list[types.Tool]:
    """列出所有可用工具"""
    return [
        types.Tool(
            name="clean_ministry_data",
            description="触发数据清洗管线，从原始层读取数据并清洗标准化",
            inputSchema={
                "type": "object",
                "properties": {
                    "dry_run": {
                        "type": "boolean",
                        "description": "是否为测试模式（不写入Google Sheets）",
                        "default": False
                    },
                    "force": {
                        "type": "boolean",
                        "description": "是否强制执行（跳过变化检测）",
                        "default": False
                    }
                }
            }
        ),
        types.Tool(
            name="generate_service_layer",
            description="生成或更新服务层领域数据（sermon 和 volunteer 域）",
            inputSchema={
                "type": "object",
                "properties": {
                    "domains": {
                        "type": "array",
                        "items": {"type": "string", "enum": ["sermon", "volunteer"]},
                        "description": "要生成的领域列表",
                        "default": ["sermon", "volunteer"]
                    },
                    "generate_all_years": {
                        "type": "boolean",
                        "description": "是否生成所有年份的数据",
                        "default": True
                    },
                    "upload_to_bucket": {
                        "type": "boolean",
                        "description": "是否上传到 Cloud Storage",
                        "default": False
                    }
                }
            }
        ),
        types.Tool(
            name="validate_raw_data",
            description="校验原始数据质量，检查必填字段、格式错误等（不执行清洗）",
            inputSchema={
                "type": "object",
                "properties": {
                    "check_duplicates": {
                        "type": "boolean",
                        "description": "是否检查重复记录",
                        "default": True
                    },
                    "generate_report": {
                        "type": "boolean",
                        "description": "是否生成详细报告",
                        "default": True
                    }
                }
            }
        ),
        types.Tool(
            name="add_person_alias",
            description="添加人员别名映射（例如：将'张牧师'和'Pastor Zhang'映射到同一person_id）",
            inputSchema={
                "type": "object",
                "properties": {
                    "alias": {
                        "type": "string",
                        "description": "别名（如'张牧师'）"
                    },
                    "person_id": {
                        "type": "string",
                        "description": "人员ID（如'person_6511_王通'）"
                    },
                    "display_name": {
                        "type": "string",
                        "description": "显示名称"
                    }
                },
                "required": ["alias", "person_id", "display_name"]
            }
        ),
        types.Tool(
            name="get_pipeline_status",
            description="获取数据清洗管线的运行状态和历史记录",
            inputSchema={
                "type": "object",
                "properties": {
                    "last_n_runs": {
                        "type": "integer",
                        "description": "返回最近N次运行记录",
                        "default": 10
                    }
                }
            }
        )
    ]


@server.call_tool()
async def handle_call_tool(
    name: str,
    arguments: dict
) -> list[types.TextContent | types.ImageContent | types.EmbeddedResource]:
    """处理工具调用"""
    
    try:
        if name == "clean_ministry_data":
            # 执行数据清洗
            dry_run = arguments.get("dry_run", False)
            force = arguments.get("force", False)
            
            pipeline = CleaningPipeline(CONFIG_PATH)
            result = pipeline.run(dry_run=dry_run, force_clean=force)
            
            return [types.TextContent(
                type="text",
                text=json.dumps({
                    "success": result.get("success", False),
                    "message": result.get("message", ""),
                    "total_rows": result.get("total_rows", 0),
                    "success_rows": result.get("success_rows", 0),
                    "timestamp": datetime.now().isoformat()
                }, ensure_ascii=False, indent=2)
            )]
        
        elif name == "generate_service_layer":
            # 生成服务层数据
            domains = arguments.get("domains", ["sermon", "volunteer"])
            generate_all_years = arguments.get("generate_all_years", True)
            upload_to_bucket = arguments.get("upload_to_bucket", False)
            
            manager = ServiceLayerManager(CONFIG_PATH)
            
            results = {}
            for domain in domains:
                if domain == "sermon":
                    results["sermon"] = manager.generate_sermon_domain(
                        generate_all_years=generate_all_years,
                        upload_to_bucket=upload_to_bucket
                    )
                elif domain == "volunteer":
                    results["volunteer"] = manager.generate_volunteer_domain(
                        generate_all_years=generate_all_years,
                        upload_to_bucket=upload_to_bucket
                    )
            
            return [types.TextContent(
                type="text",
                text=json.dumps({
                    "success": True,
                    "message": f"Generated {len(domains)} domain(s)",
                    "results": results,
                    "timestamp": datetime.now().isoformat()
                }, ensure_ascii=False, indent=2)
            )]
        
        elif name == "validate_raw_data":
            # 校验原始数据
            check_duplicates = arguments.get("check_duplicates", True)
            generate_report = arguments.get("generate_report", True)
            
            validator = Validator(CONFIG_PATH)
            validation_result = validator.validate()
            
            return [types.TextContent(
                type="text",
                text=json.dumps({
                    "success": validation_result.get("is_valid", False),
                    "errors": validation_result.get("errors", []),
                    "warnings": validation_result.get("warnings", []),
                    "timestamp": datetime.now().isoformat()
                }, ensure_ascii=False, indent=2)
            )]
        
        elif name == "add_person_alias":
            # 添加别名
            alias = arguments.get("alias")
            person_id = arguments.get("person_id")
            display_name = arguments.get("display_name")
            
            if not all([alias, person_id, display_name]):
                raise ValueError("Missing required parameters")
            
            alias_utils = AliasUtils(CONFIG_PATH)
            result = alias_utils.add_alias(alias, person_id, display_name)
            
            return [types.TextContent(
                type="text",
                text=json.dumps({
                    "success": result.get("success", False),
                    "message": result.get("message", ""),
                    "timestamp": datetime.now().isoformat()
                }, ensure_ascii=False, indent=2)
            )]
        
        elif name == "get_pipeline_status":
            # 获取管线状态
            last_n_runs = arguments.get("last_n_runs", 10)
            
            # 读取状态日志
            status_file = Path("logs/pipeline_status.json")
            if status_file.exists():
                with open(status_file, 'r', encoding='utf-8') as f:
                    status_data = json.load(f)
                    runs = status_data.get("runs", [])[-last_n_runs:]
            else:
                runs = []
            
            return [types.TextContent(
                type="text",
                text=json.dumps({
                    "success": True,
                    "runs": runs,
                    "timestamp": datetime.now().isoformat()
                }, ensure_ascii=False, indent=2)
            )]
        
        else:
            raise ValueError(f"Unknown tool: {name}")
    
    except Exception as e:
        logger.error(f"Error calling tool {name}: {e}")
        return [types.TextContent(
            type="text",
            text=json.dumps({
                "success": False,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            })
        )]


# ============================================================
# MCP Resources（资源）
# ============================================================

@server.list_resources()
async def handle_list_resources() -> list[types.Resource]:
    """列出所有可用资源"""
    return [
        types.Resource(
            uri="ministry://sermon/records",
            name="sermon-records",
            description="证道域记录（包含讲道标题、讲员、经文、诗歌等）",
            mimeType="application/json"
        ),
        types.Resource(
            uri="ministry://sermon/by-preacher/{preacher_name}",
            name="sermon-by-preacher",
            description="按讲员查询证道记录",
            mimeType="application/json"
        ),
        types.Resource(
            uri="ministry://sermon/series",
            name="sermon-series",
            description="讲道系列信息和进度",
            mimeType="application/json"
        ),
        types.Resource(
            uri="ministry://volunteer/assignments",
            name="volunteer-assignments",
            description="同工服侍安排（敬拜同工、技术同工等）",
            mimeType="application/json"
        ),
        types.Resource(
            uri="ministry://volunteer/by-person/{person_id}",
            name="volunteer-by-person",
            description="查询某人的所有服侍记录",
            mimeType="application/json"
        ),
        types.Resource(
            uri="ministry://volunteer/availability/{year_month}",
            name="volunteer-availability",
            description="查询某时间范围内的空缺岗位",
            mimeType="application/json"
        ),
        types.Resource(
            uri="ministry://stats/summary",
            name="ministry-stats",
            description="教会主日事工数据的综合统计信息",
            mimeType="application/json"
        ),
        types.Resource(
            uri="ministry://stats/preachers",
            name="preacher-stats",
            description="讲员统计（讲道次数、涉及经文等）",
            mimeType="application/json"
        ),
        types.Resource(
            uri="ministry://stats/volunteers",
            name="volunteer-stats",
            description="同工统计（服侍次数、岗位分布等）",
            mimeType="application/json"
        ),
        types.Resource(
            uri="ministry://config/aliases",
            name="alias-mappings",
            description="人员别名映射表",
            mimeType="application/json"
        )
    ]


@server.read_resource()
async def handle_read_resource(uri: str) -> str:
    """读取资源内容"""
    
    try:
        # 解析 URI
        if uri.startswith("ministry://sermon/records"):
            # 获取证道记录
            year = uri.split("?year=")[1] if "?year=" in uri else None
            data = load_service_layer_data("sermon", year)
            return json.dumps(data, ensure_ascii=False, indent=2)
        
        elif uri.startswith("ministry://sermon/by-preacher/"):
            # 按讲员查询
            preacher_name = uri.split("/")[-1].split("?")[0]
            year = uri.split("?year=")[1] if "?year=" in uri else None
            
            data = load_service_layer_data("sermon", year)
            sermons = data.get("sermons", [])
            filtered = filter_by_preacher(sermons, preacher_name)
            
            return json.dumps({
                "metadata": data.get("metadata", {}),
                "preacher_name": preacher_name,
                "sermons": filtered,
                "total_count": len(filtered)
            }, ensure_ascii=False, indent=2)
        
        elif uri.startswith("ministry://sermon/series"):
            # 获取系列信息
            data = load_service_layer_data("sermon")
            sermons = data.get("sermons", [])
            
            # 统计系列
            series_map = {}
            for sermon in sermons:
                series = sermon.get("sermon", {}).get("series", "未分类")
                if series not in series_map:
                    series_map[series] = []
                series_map[series].append(sermon)
            
            series_list = [
                {
                    "name": name,
                    "count": len(sermons),
                    "sermons": sermons
                }
                for name, sermons in series_map.items()
            ]
            
            return json.dumps({
                "total_series": len(series_list),
                "series": series_list
            }, ensure_ascii=False, indent=2)
        
        elif uri.startswith("ministry://volunteer/assignments"):
            # 获取同工安排
            date = uri.split("?date=")[1] if "?date=" in uri else None
            year = uri.split("?year=")[1] if "?year=" in uri else None
            
            data = load_service_layer_data("volunteer", year)
            volunteers = data.get("volunteers", [])
            
            if date:
                volunteers = filter_by_date(volunteers, date)
            
            return json.dumps({
                "metadata": data.get("metadata", {}),
                "volunteers": volunteers,
                "total_count": len(volunteers)
            }, ensure_ascii=False, indent=2)
        
        elif uri.startswith("ministry://volunteer/by-person/"):
            # 按人员查询
            person_id = uri.split("/")[-1].split("?")[0]
            year = uri.split("?year=")[1] if "?year=" in uri else None
            
            data = load_service_layer_data("volunteer", year)
            volunteers = data.get("volunteers", [])
            person_records = get_person_records(volunteers, person_id)
            
            return json.dumps({
                "person_identifier": person_id,
                "records": person_records,
                "total_count": len(person_records)
            }, ensure_ascii=False, indent=2)
        
        elif uri.startswith("ministry://volunteer/availability/"):
            # 查询空缺
            year_month = uri.split("/")[-1]
            
            data = load_service_layer_data("volunteer")
            volunteers = data.get("volunteers", [])
            
            # 筛选该月的记录
            month_records = filter_by_date(volunteers, year_month)
            
            # 分析空缺
            gaps = []
            for record in month_records:
                service_date = record.get("service_date")
                for role, person in record.items():
                    if role != "service_date" and not person:
                        gaps.append({
                            "service_date": service_date,
                            "role": role,
                            "status": "vacant"
                        })
            
            return json.dumps({
                "year_month": year_month,
                "gaps": gaps,
                "total_gaps": len(gaps)
            }, ensure_ascii=False, indent=2)
        
        elif uri == "ministry://stats/summary":
            # 综合统计
            sermon_data = load_service_layer_data("sermon")
            volunteer_data = load_service_layer_data("volunteer")
            
            return json.dumps({
                "sermon_stats": sermon_data.get("metadata", {}),
                "volunteer_stats": volunteer_data.get("metadata", {})
            }, ensure_ascii=False, indent=2)
        
        elif uri == "ministry://stats/preachers":
            # 讲员统计
            year = uri.split("?year=")[1] if "?year=" in uri else None
            data = load_service_layer_data("sermon", year)
            sermons = data.get("sermons", [])
            
            # 统计讲员
            preacher_map = {}
            for sermon in sermons:
                preacher = sermon.get("preacher", {})
                preacher_name = preacher.get("name", "Unknown")
                if preacher_name not in preacher_map:
                    preacher_map[preacher_name] = {
                        "name": preacher_name,
                        "id": preacher.get("id"),
                        "count": 0,
                        "sermons": []
                    }
                preacher_map[preacher_name]["count"] += 1
                preacher_map[preacher_name]["sermons"].append(sermon)
            
            return json.dumps({
                "total_preachers": len(preacher_map),
                "preachers": list(preacher_map.values())
            }, ensure_ascii=False, indent=2)
        
        elif uri == "ministry://stats/volunteers":
            # 同工统计
            year = uri.split("?year=")[1] if "?year=" in uri else None
            data = load_service_layer_data("volunteer", year)
            volunteers = data.get("volunteers", [])
            
            # 统计同工
            person_map = {}
            for record in volunteers:
                for role, person in record.items():
                    if role != "service_date" and isinstance(person, dict):
                        person_id = person.get("id", "unknown")
                        if person_id not in person_map:
                            person_map[person_id] = {
                                "id": person_id,
                                "name": person.get("name"),
                                "count": 0,
                                "roles": []
                            }
                        person_map[person_id]["count"] += 1
                        person_map[person_id]["roles"].append(role)
            
            return json.dumps({
                "total_volunteers": len(person_map),
                "volunteers": list(person_map.values())
            }, ensure_ascii=False, indent=2)
        
        elif uri == "ministry://config/aliases":
            # 别名映射
            alias_utils = AliasUtils(CONFIG_PATH)
            aliases = alias_utils.get_all_aliases()
            
            return json.dumps({
                "total_aliases": len(aliases),
                "aliases": aliases
            }, ensure_ascii=False, indent=2)
        
        else:
            return json.dumps({"error": f"Unknown resource URI: {uri}"})
    
    except Exception as e:
        logger.error(f"Error reading resource {uri}: {e}")
        return json.dumps({"error": str(e)})


# ============================================================
# MCP Prompts（提示词）
# ============================================================

@server.list_prompts()
async def handle_list_prompts() -> list[types.Prompt]:
    """列出所有可用提示词"""
    return [
        types.Prompt(
            name="analyze_preaching_schedule",
            description="分析讲道安排和系列进度",
            arguments=[
                types.PromptArgument(
                    name="year",
                    description="要分析的年份（如2024）",
                    required=False
                ),
                types.PromptArgument(
                    name="focus",
                    description="分析重点（series/preachers/scripture）",
                    required=False
                )
            ]
        ),
        types.Prompt(
            name="analyze_volunteer_balance",
            description="分析同工服侍负担均衡性",
            arguments=[
                types.PromptArgument(
                    name="year",
                    description="要分析的年份",
                    required=False
                ),
                types.PromptArgument(
                    name="role",
                    description="关注的岗位（worship_lead/audio/video等）",
                    required=False
                )
            ]
        ),
        types.Prompt(
            name="find_scheduling_gaps",
            description="查找排班空缺",
            arguments=[
                types.PromptArgument(
                    name="month",
                    description="查找的月份（YYYY-MM）",
                    required=True
                )
            ]
        ),
        types.Prompt(
            name="check_data_quality",
            description="检查数据质量和完整性",
            arguments=[]
        ),
        types.Prompt(
            name="suggest_alias_merges",
            description="建议可能需要合并的人员别名",
            arguments=[]
        )
    ]


@server.get_prompt()
async def handle_get_prompt(
    name: str,
    arguments: dict | None
) -> types.GetPromptResult:
    """获取提示词内容"""
    
    arguments = arguments or {}
    
    if name == "analyze_preaching_schedule":
        year = arguments.get("year", "2024")
        focus = arguments.get("focus", "全面")
        
        prompt_text = f"""请分析 {year} 年的讲道安排：

1. 列出所有讲道系列及其进度
2. 统计每位讲员的讲道次数
3. 分析涉及的圣经书卷分布
4. 识别可能的排班问题（如空缺、过于集中等）

分析重点：{focus}

请使用以下资源获取数据：
- ministry://sermon/records?year={year}
- ministry://stats/preachers?year={year}
- ministry://sermon/series
"""
        
        return types.GetPromptResult(
            description=f"分析 {year} 年讲道安排",
            messages=[
                types.PromptMessage(
                    role="user",
                    content=types.TextContent(
                        type="text",
                        text=prompt_text
                    )
                )
            ]
        )
    
    elif name == "analyze_volunteer_balance":
        year = arguments.get("year", "2024")
        role = arguments.get("role", "所有岗位")
        
        prompt_text = f"""请分析 {year} 年 {role} 的同工服侍情况：

1. 统计每位同工的服侍次数
2. 计算服侍频率（平均多久服侍一次）
3. 识别服侍过多或过少的同工
4. 建议如何更均衡地分配服侍

请使用以下资源：
- ministry://volunteer/assignments?year={year}
- ministry://stats/volunteers?year={year}
"""
        
        return types.GetPromptResult(
            description=f"分析 {year} 年同工服侍均衡性",
            messages=[
                types.PromptMessage(
                    role="user",
                    content=types.TextContent(
                        type="text",
                        text=prompt_text
                    )
                )
            ]
        )
    
    elif name == "find_scheduling_gaps":
        month = arguments.get("month")
        if not month:
            raise ValueError("month parameter is required")
        
        prompt_text = f"""请查找 {month} 月的排班空缺：

1. 列出所有主日日期
2. 识别哪些岗位尚未安排（讲员、敬拜、技术等）
3. 按紧急程度排序（日期越近越紧急）
4. 建议可以填补空缺的人员（基于历史数据）

请使用以下资源：
- ministry://volunteer/availability/{month}
- ministry://stats/volunteers
"""
        
        return types.GetPromptResult(
            description=f"查找 {month} 月排班空缺",
            messages=[
                types.PromptMessage(
                    role="user",
                    content=types.TextContent(
                        type="text",
                        text=prompt_text
                    )
                )
            ]
        )
    
    elif name == "check_data_quality":
        prompt_text = """请全面检查数据质量：

1. 必填字段完整性（讲员、日期等）
2. 重复记录检测
3. 日期逻辑性（是否为主日、是否有时间跳跃）
4. 人名拼写一致性（可能的别名问题）
5. 生成详细的问题报告和修复建议

请使用工具：
- validate_raw_data (check_duplicates=true, generate_report=true)
"""
        
        return types.GetPromptResult(
            description="检查数据质量",
            messages=[
                types.PromptMessage(
                    role="user",
                    content=types.TextContent(
                        type="text",
                        text=prompt_text
                    )
                )
            ]
        )
    
    elif name == "suggest_alias_merges":
        prompt_text = """请分析并建议可能需要合并的人员别名：

1. 查找相似的人名（如'张牧师'和'张'）
2. 查找中英文名称对应（如'王丽'和'Wang Li'）
3. 识别拼写变体
4. 生成合并建议清单

请使用以下资源：
- ministry://config/aliases
- ministry://stats/volunteers
- ministry://stats/preachers
"""
        
        return types.GetPromptResult(
            description="建议别名合并",
            messages=[
                types.PromptMessage(
                    role="user",
                    content=types.TextContent(
                        type="text",
                        text=prompt_text
                    )
                )
            ]
        )
    
    else:
        raise ValueError(f"Unknown prompt: {name}")


# ============================================================
# 启动服务器
# ============================================================

async def main():
    """主函数 - 启动 MCP 服务器（stdio 模式）"""
    from mcp.server.stdio import stdio_server
    
    async with stdio_server() as (read_stream, write_stream):
        init_options = InitializationOptions(
            server_name="ministry-data",
            server_version="2.0.0",
            capabilities=server.get_capabilities(
                notification_options=NotificationOptions(),
                experimental_capabilities={}
            )
        )
        
        await server.run(
            read_stream,
            write_stream,
            init_options
        )


if __name__ == "__main__":
    asyncio.run(main())

