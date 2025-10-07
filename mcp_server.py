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

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 配置文件路径（使用绝对路径）
SCRIPT_DIR = Path(__file__).parent.absolute()
CONFIG_PATH = os.getenv('CONFIG_PATH', str(SCRIPT_DIR / 'config' / 'config.json'))
LOGS_DIR = SCRIPT_DIR / "logs" / "service_layer"

# 加载配置
def load_config() -> Dict[str, Any]:
    """加载配置文件"""
    try:
        config_file = Path(CONFIG_PATH)
        if not config_file.exists():
            logger.error(f"Config file not found: {config_file}")
            return {}
        
        with open(config_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Failed to load config: {e}")
        return {}

CONFIG = load_config()
STORAGE_CONFIG = CONFIG.get('service_layer', {}).get('storage', {})

# 初始化 GCS 客户端（如果配置了）
GCS_CLIENT = None
if STORAGE_CONFIG.get('provider') == 'gcs':
    try:
        from scripts.cloud_storage_utils import DomainStorageManager
        
        # 转换服务账号文件路径为绝对路径
        service_account_file = STORAGE_CONFIG.get('service_account_file')
        if service_account_file and not Path(service_account_file).is_absolute():
            service_account_file = str(SCRIPT_DIR / service_account_file)
        
        bucket_name = STORAGE_CONFIG.get('bucket', '')
        base_path = STORAGE_CONFIG.get('base_path', 'domains/')
        
        logger.info(f"Initializing GCS client: bucket={bucket_name}, service_account={service_account_file}")
        
        GCS_CLIENT = DomainStorageManager(
            bucket_name=bucket_name,
            service_account_file=service_account_file,
            base_path=base_path
        )
        logger.info(f"✅ GCS client initialized successfully: bucket={bucket_name}")
    except Exception as e:
        logger.error(f"❌ Failed to initialize GCS client: {e}", exc_info=True)
        GCS_CLIENT = None

# ============================================================
# 辅助函数
# ============================================================

def load_service_layer_data(domain: str, year: Optional[str] = None) -> Dict[str, Any]:
    """
    加载服务层数据
    优先从 GCS 读取，如果失败则回退到本地文件
    """
    # 1. 尝试从 GCS 读取
    if GCS_CLIENT:
        try:
            version = year if year else 'latest'
            logger.info(f"Loading {domain} data from GCS (version: {version})")
            data = GCS_CLIENT.download_domain_data(domain, version)
            logger.info(f"Successfully loaded {domain} from GCS")
            return data
        except Exception as e:
            logger.warning(f"Failed to load from GCS, falling back to local: {e}")
    
    # 2. 回退到本地文件
    try:
        if year:
            data_path = LOGS_DIR / year / f"{domain}_{year}.json"
        else:
            data_path = LOGS_DIR / f"{domain}.json"
        
        if not data_path.exists():
            return {"error": f"Data not found in GCS or local: {domain} (year={year})"}
        
        logger.info(f"Loading {domain} data from local file: {data_path}")
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
        # ========== 查询工具（常用） ==========
        types.Tool(
            name="query_volunteers_by_date",
            description="查询指定日期的同工服侍安排（如：下个主日的服侍人员）",
            inputSchema={
                "type": "object",
                "properties": {
                    "date": {
                        "type": "string",
                        "description": "日期（格式：YYYY-MM-DD），如 '2025-10-12'"
                    },
                    "year": {
                        "type": "string",
                        "description": "可选：指定年份（如 '2025'），默认使用 latest",
                        "default": None
                    }
                },
                "required": ["date"]
            }
        ),
        types.Tool(
            name="query_sermon_by_date",
            description="查询指定日期的证道信息（讲员、题目、经文等）",
            inputSchema={
                "type": "object",
                "properties": {
                    "date": {
                        "type": "string",
                        "description": "日期（格式：YYYY-MM-DD）"
                    },
                    "year": {
                        "type": "string",
                        "description": "可选：指定年份",
                        "default": None
                    }
                },
                "required": ["date"]
            }
        ),
        types.Tool(
            name="query_date_range",
            description="查询一段时间范围内的所有服侍安排",
            inputSchema={
                "type": "object",
                "properties": {
                    "start_date": {
                        "type": "string",
                        "description": "开始日期（YYYY-MM-DD）"
                    },
                    "end_date": {
                        "type": "string",
                        "description": "结束日期（YYYY-MM-DD）"
                    },
                    "domain": {
                        "type": "string",
                        "enum": ["volunteer", "sermon", "both"],
                        "description": "查询的域",
                        "default": "both"
                    }
                },
                "required": ["start_date", "end_date"]
            }
        ),
        
        # ========== 数据管理工具（管理员使用） ==========
        types.Tool(
            name="clean_ministry_data",
            description="[管理员] 触发数据清洗管线，从原始层读取数据并清洗标准化",
            inputSchema={
                "type": "object",
                "properties": {
                    "dry_run": {
                        "type": "boolean",
                        "description": "是否为测试模式（不写入Google Sheets）",
                        "default": False
                    }
                }
            }
        ),
        types.Tool(
            name="generate_service_layer",
            description="[管理员] 生成或更新服务层领域数据（sermon 和 volunteer 域）",
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
                        "default": True
                    }
                }
            }
        ),
        types.Tool(
            name="validate_raw_data",
            description="[管理员] 校验原始数据质量，检查必填字段、格式错误等（不执行清洗）",
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
            name="sync_from_gcs",
            description="[管理员] 从 Google Cloud Storage 同步最新的服务层数据到本地",
            inputSchema={
                "type": "object",
                "properties": {
                    "domains": {
                        "type": "array",
                        "items": {"type": "string", "enum": ["sermon", "volunteer"]},
                        "description": "要同步的领域",
                        "default": ["sermon", "volunteer"]
                    },
                    "versions": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "要同步的版本列表（如 ['latest', '2025', '2024']）",
                        "default": ["latest"]
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
        # ========== 查询工具 ==========
        if name == "query_volunteers_by_date":
            date = arguments.get("date")
            year = arguments.get("year")
            
            # 加载 volunteer 数据
            data = load_service_layer_data("volunteer", year)
            
            if "error" in data:
                return [types.TextContent(
                    type="text",
                    text=json.dumps({
                        "success": False,
                        "error": data["error"],
                        "timestamp": datetime.now().isoformat()
                    }, ensure_ascii=False, indent=2)
                )]
            
            # 过滤指定日期
            volunteers = data.get("volunteers", [])
            result = [v for v in volunteers if v.get("service_date", "").startswith(date)]
            
            return [types.TextContent(
                type="text",
                text=json.dumps({
                    "success": True,
                    "date": date,
                    "assignments": result,
                    "count": len(result),
                    "timestamp": datetime.now().isoformat()
                }, ensure_ascii=False, indent=2)
            )]
        
        elif name == "query_sermon_by_date":
            date = arguments.get("date")
            year = arguments.get("year")
            
            # 加载 sermon 数据
            data = load_service_layer_data("sermon", year)
            
            if "error" in data:
                return [types.TextContent(
                    type="text",
                    text=json.dumps({
                        "success": False,
                        "error": data["error"],
                        "timestamp": datetime.now().isoformat()
                    }, ensure_ascii=False, indent=2)
                )]
            
            # 过滤指定日期
            sermons = data.get("sermons", [])
            result = [s for s in sermons if s.get("service_date", "").startswith(date)]
            
            return [types.TextContent(
                type="text",
                text=json.dumps({
                    "success": True,
                    "date": date,
                    "sermons": result,
                    "count": len(result),
                    "timestamp": datetime.now().isoformat()
                }, ensure_ascii=False, indent=2)
            )]
        
        elif name == "query_date_range":
            start_date = arguments.get("start_date")
            end_date = arguments.get("end_date")
            domain = arguments.get("domain", "both")
            
            results = {}
            
            # 查询 volunteer
            if domain in ["volunteer", "both"]:
                volunteer_data = load_service_layer_data("volunteer")
                if "error" not in volunteer_data:
                    volunteers = volunteer_data.get("volunteers", [])
                    filtered = [
                        v for v in volunteers
                        if start_date <= v.get("service_date", "") <= end_date
                    ]
                    results["volunteer"] = {
                        "count": len(filtered),
                        "records": filtered
                    }
            
            # 查询 sermon
            if domain in ["sermon", "both"]:
                sermon_data = load_service_layer_data("sermon")
                if "error" not in sermon_data:
                    sermons = sermon_data.get("sermons", [])
                    filtered = [
                        s for s in sermons
                        if start_date <= s.get("service_date", "") <= end_date
                    ]
                    results["sermon"] = {
                        "count": len(filtered),
                        "records": filtered
                    }
            
            return [types.TextContent(
                type="text",
                text=json.dumps({
                    "success": True,
                    "start_date": start_date,
                    "end_date": end_date,
                    "results": results,
                    "timestamp": datetime.now().isoformat()
                }, ensure_ascii=False, indent=2)
            )]
        
        elif name == "sync_from_gcs":
            domains = arguments.get("domains", ["sermon", "volunteer"])
            versions = arguments.get("versions", ["latest"])
            
            if not GCS_CLIENT:
                # 提供详细的诊断信息
                diagnostic_info = {
                    "config_path": CONFIG_PATH,
                    "config_exists": Path(CONFIG_PATH).exists(),
                    "storage_config": STORAGE_CONFIG,
                    "script_dir": str(SCRIPT_DIR),
                }
                
                # 检查服务账号文件
                service_account_file = STORAGE_CONFIG.get('service_account_file')
                if service_account_file:
                    sa_path = Path(service_account_file)
                    if not sa_path.is_absolute():
                        sa_path = SCRIPT_DIR / service_account_file
                    diagnostic_info["service_account_file"] = str(sa_path)
                    diagnostic_info["service_account_exists"] = sa_path.exists()
                
                return [types.TextContent(
                    type="text",
                    text=json.dumps({
                        "success": False,
                        "error": "GCS client not initialized. Check configuration and logs.",
                        "diagnostic": diagnostic_info,
                        "suggestions": [
                            "1. Check if config/config.json exists",
                            "2. Check if config/service-account.json exists",
                            "3. Verify google-cloud-storage is installed: pip install google-cloud-storage",
                            "4. Check MCP Server logs for detailed error messages"
                        ],
                        "timestamp": datetime.now().isoformat()
                    }, ensure_ascii=False, indent=2)
                )]
            
            synced_files = {}
            
            for domain in domains:
                synced_files[domain] = {}
                for version in versions:
                    try:
                        # 从 GCS 下载
                        data = GCS_CLIENT.download_domain_data(domain, version)
                        
                        # 保存到本地
                        if version == "latest":
                            local_path = LOGS_DIR / f"{domain}.json"
                        else:
                            local_path = LOGS_DIR / version / f"{domain}_{version}.json"
                        
                        local_path.parent.mkdir(parents=True, exist_ok=True)
                        
                        with open(local_path, 'w', encoding='utf-8') as f:
                            json.dump(data, f, ensure_ascii=False, indent=2)
                        
                        synced_files[domain][version] = str(local_path)
                        logger.info(f"Synced {domain}/{version} to {local_path}")
                        
                    except Exception as e:
                        logger.error(f"Failed to sync {domain}/{version}: {e}")
                        synced_files[domain][version] = f"Error: {str(e)}"
            
            return [types.TextContent(
                type="text",
                text=json.dumps({
                    "success": True,
                    "message": "Sync completed",
                    "synced_files": synced_files,
                    "timestamp": datetime.now().isoformat()
                }, ensure_ascii=False, indent=2)
            )]
        
        # ========== 数据管理工具 ==========
        elif name == "clean_ministry_data":
            # 执行数据清洗
            dry_run = arguments.get("dry_run", False)
            force = arguments.get("force", False)  # Note: force parameter not currently used by run()
            
            pipeline = CleaningPipeline(CONFIG_PATH)
            exit_code = pipeline.run(dry_run=dry_run)
            
            return [types.TextContent(
                type="text",
                text=json.dumps({
                    "success": exit_code == 0,
                    "message": "Data cleaning completed successfully" if exit_code == 0 else "Data cleaning completed with errors",
                    "exit_code": exit_code,
                    "timestamp": datetime.now().isoformat()
                }, ensure_ascii=False, indent=2)
            )]
        
        elif name == "generate_service_layer":
            # 生成服务层数据
            domains = arguments.get("domains", ["sermon", "volunteer"])
            generate_all_years = arguments.get("generate_all_years", True)
            upload_to_bucket = arguments.get("upload_to_bucket", False)
            
            # First, we need cleaned data
            # Load from the clean_preview.json file if it exists
            clean_data_path = Path("logs/clean_preview.json")
            if not clean_data_path.exists():
                return [types.TextContent(
                    type="text",
                    text=json.dumps({
                        "success": False,
                        "error": "No cleaned data found. Please run clean_ministry_data first.",
                        "timestamp": datetime.now().isoformat()
                    }, ensure_ascii=False, indent=2)
                )]
            
            import pandas as pd
            clean_df = pd.read_json(clean_data_path)
            
            manager = ServiceLayerManager()
            output_dir = Path("logs/service_layer")
            
            if generate_all_years:
                saved_files = manager.generate_all_years(clean_df, output_dir, domains)
            else:
                saved_files = manager.generate_and_save(clean_df, output_dir, domains)
            
            # Convert Path objects to strings for JSON serialization
            results = {}
            for key, value in saved_files.items():
                if isinstance(value, dict):
                    results[key] = {k: str(v) for k, v in value.items()}
                else:
                    results[key] = str(value)
            
            return [types.TextContent(
                type="text",
                text=json.dumps({
                    "success": True,
                    "message": f"Generated {len(domains)} domain(s)",
                    "files": results,
                    "timestamp": datetime.now().isoformat()
                }, ensure_ascii=False, indent=2)
            )]
        
        elif name == "validate_raw_data":
            # 校验原始数据
            check_duplicates = arguments.get("check_duplicates", True)
            generate_report = arguments.get("generate_report", True)
            
            try:
                # 创建清洗管线并运行验证
                pipeline = CleaningPipeline(CONFIG_PATH)
                exit_code = pipeline.run(dry_run=True)
                
                # Try to load the validation report from the most recent file
                log_dir = Path('logs')
                report_files = sorted(log_dir.glob('validation_report_*.txt'), reverse=True)
                report_summary = "Check logs/validation_report_*.txt for details"
                
                if report_files:
                    with open(report_files[0], 'r', encoding='utf-8') as f:
                        report_summary = f.read()[:1000]  # First 1000 chars
                
                return [types.TextContent(
                    type="text",
                    text=json.dumps({
                        "success": exit_code == 0,
                        "message": "Data validation completed via dry-run",
                        "exit_code": exit_code,
                        "report_preview": report_summary,
                        "timestamp": datetime.now().isoformat()
                    }, ensure_ascii=False, indent=2)
                )]
            except Exception as e:
                return [types.TextContent(
                    type="text",
                    text=json.dumps({
                        "success": False,
                        "error": f"Validation failed: {str(e)}",
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
        # 将 URI 转换为字符串（MCP SDK 可能传递 AnyUrl 对象）
        uri_str = str(uri)
        
        # 解析 URI
        if uri_str.startswith("ministry://sermon/records"):
            # 获取证道记录
            year = uri_str.split("?year=")[1] if "?year=" in uri_str else None
            data = load_service_layer_data("sermon", year)
            return json.dumps(data, ensure_ascii=False, indent=2)
        
        elif uri_str.startswith("ministry://sermon/by-preacher/"):
            # 按讲员查询
            preacher_name = uri_str.split("/")[-1].split("?")[0]
            year = uri_str.split("?year=")[1] if "?year=" in uri_str else None
            
            data = load_service_layer_data("sermon", year)
            sermons = data.get("sermons", [])
            filtered = filter_by_preacher(sermons, preacher_name)
            
            return json.dumps({
                "metadata": data.get("metadata", {}),
                "preacher_name": preacher_name,
                "sermons": filtered,
                "total_count": len(filtered)
            }, ensure_ascii=False, indent=2)
        
        elif uri_str.startswith("ministry://sermon/series"):
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
        
        elif uri_str.startswith("ministry://volunteer/assignments"):
            # 获取同工安排
            date = uri_str.split("?date=")[1] if "?date=" in uri_str else None
            year = uri_str.split("?year=")[1] if "?year=" in uri_str else None
            
            data = load_service_layer_data("volunteer", year)
            volunteers = data.get("volunteers", [])
            
            if date:
                volunteers = filter_by_date(volunteers, date)
            
            return json.dumps({
                "metadata": data.get("metadata", {}),
                "volunteers": volunteers,
                "total_count": len(volunteers)
            }, ensure_ascii=False, indent=2)
        
        elif uri_str.startswith("ministry://volunteer/by-person/"):
            # 按人员查询
            person_id = uri_str.split("/")[-1].split("?")[0]
            year = uri_str.split("?year=")[1] if "?year=" in uri_str else None
            
            data = load_service_layer_data("volunteer", year)
            volunteers = data.get("volunteers", [])
            person_records = get_person_records(volunteers, person_id)
            
            return json.dumps({
                "person_identifier": person_id,
                "records": person_records,
                "total_count": len(person_records)
            }, ensure_ascii=False, indent=2)
        
        elif uri_str.startswith("ministry://volunteer/availability/"):
            # 查询空缺
            year_month = uri_str.split("/")[-1]
            
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
        
        elif uri_str == "ministry://stats/summary":
            # 综合统计
            sermon_data = load_service_layer_data("sermon")
            volunteer_data = load_service_layer_data("volunteer")
            
            return json.dumps({
                "sermon_stats": sermon_data.get("metadata", {}),
                "volunteer_stats": volunteer_data.get("metadata", {})
            }, ensure_ascii=False, indent=2)
        
        elif uri_str == "ministry://stats/preachers" or uri_str.startswith("ministry://stats/preachers?"):
            # 讲员统计
            year = uri_str.split("?year=")[1] if "?year=" in uri_str else None
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
        
        elif uri_str == "ministry://stats/volunteers" or uri_str.startswith("ministry://stats/volunteers?"):
            # 同工统计
            year = uri_str.split("?year=")[1] if "?year=" in uri_str else None
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
        
        elif uri_str == "ministry://config/aliases":
            # 别名映射（从配置文件读取）
            try:
                with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                
                aliases_url = config.get("data_sources", {}).get("aliases_sheet_url", "")
                aliases_range = config.get("data_sources", {}).get("aliases_range", "Aliases!A:C")
                
                return json.dumps({
                    "message": "Alias mappings are stored in Google Sheets",
                    "sheets_url": aliases_url,
                    "range": aliases_range,
                    "instructions": "Use Google Sheets API or read the service layer data to see resolved aliases"
                }, ensure_ascii=False, indent=2)
            except Exception as e:
                return json.dumps({
                    "error": f"Could not load alias configuration: {str(e)}"
                }, ensure_ascii=False, indent=2)
        
        else:
            return json.dumps({"error": f"Unknown resource URI: {uri_str}"})
    
    except Exception as e:
        logger.error(f"Error reading resource {uri_str}: {e}")
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

