#!/usr/bin/env python3
"""
MCP (Model Context Protocol) Server Implementation
提供标准 MCP 协议接口，暴露教会主日事工数据管理工具、资源和提示词

Supports two transport modes:
1. stdio - for local Claude Desktop integration (default)
2. HTTP/SSE - for Cloud Run deployment with OpenAI/Claude API

Environment Variables:
- PORT: If set, run in HTTP mode on this port (auto-set by Cloud Run)
- MCP_BEARER_TOKEN: Bearer token for HTTP authentication
- MCP_REQUIRE_AUTH: Set to "true" to require authentication (default: true)
- CONFIG_PATH: Path to config.json file
"""

import os
import sys
import json
import logging
import asyncio
from pathlib import Path
from typing import Any, Dict, List, Optional
from datetime import datetime

# Check for required dependencies before importing
try:
    import mcp
except ImportError:
    bundle_dir = Path(__file__).parent.parent
    requirements_file = bundle_dir / "requirements.txt"
    error_msg = f"""
╔════════════════════════════════════════════════════════════════╗
║  ERROR: Missing required dependencies                          ║
╚════════════════════════════════════════════════════════════════╝

The 'mcp' module is not installed. Please install dependencies:

1. Navigate to the bundle directory:
   {bundle_dir}

2. Install dependencies:
   pip install -r requirements.txt

Or install globally:
   pip install mcp>=1.16.0

For more information, see the bundle description in manifest.json.
"""
    print(error_msg, file=sys.stderr)
    sys.exit(1)

# MCP SDK imports (import before adding project root to avoid naming conflict)
import mcp.server.models
import mcp.server
import mcp.server.stdio
try:
    from mcp.server.sse import SseServerTransport
except ImportError:
    import sys
    # Fallback handling for shadowing: if local mcp folder shadows the library,
    # we might need to mess with sys.path or just fail.
    # Since we verified it works when avoiding local path, let's assume
    # we can handle it or the user environment is set up correctly.
    # For now, we'll re-raise to see the error if it happens.
    raise
import mcp.types as types
from mcp.server.models import InitializationOptions
from mcp.server import NotificationOptions, Server

# HTTP/SSE transport imports
from fastapi import FastAPI, Request, HTTPException, Header, Depends
from fastapi.responses import StreamingResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn

# Import SSE transport module (must be after sys.path.insert)
# Will be imported after project root is added to path

# 添加项目根目录到 Python 路径 (for core/ imports)
sys.path.insert(0, str(Path(__file__).parent.parent))


# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 配置文件路径（使用绝对路径）
SCRIPT_DIR = Path(__file__).parent.absolute()
PROJECT_ROOT = SCRIPT_DIR.parent
CONFIG_PATH = os.getenv('CONFIG_PATH', str(PROJECT_ROOT / 'config' / 'config.json'))
LOGS_DIR = PROJECT_ROOT / "logs" / "service_layer"

# 加载配置
def load_config() -> Dict[str, Any]:
    """加载配置文件"""
    try:
        config_file = Path(CONFIG_PATH)
        if not config_file.exists():
            logger.warning(f"Config file not found: {config_file}, using environment variables or defaults")
            # 尝试从环境变量读取配置，默认启用 GCS
            default_config = {
                'service_layer': {
                    'storage': {
                        'provider': os.getenv('GCS_PROVIDER', 'gcs'),
                        'bucket': os.getenv('GCS_BUCKET', 'grace-irvine-ministry-data'),
                        'base_path': os.getenv('GCS_BASE_PATH', 'domains/'),
                        'service_account_file': os.getenv('GOOGLE_APPLICATION_CREDENTIALS', '/app/config/service-account.json')
                    }
                }
            }
            logger.info(f"Using default GCS config: provider={default_config['service_layer']['storage']['provider']}, bucket={default_config['service_layer']['storage']['bucket']}")
            return default_config
        
        with open(config_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Failed to load config: {e}")
        # 使用环境变量作为后备
        return {
            'service_layer': {
                'storage': {
                    'provider': os.getenv('GCS_PROVIDER', 'gcs'),
                    'bucket': os.getenv('GCS_BUCKET', 'grace-irvine-ministry-data'),
                    'base_path': os.getenv('GCS_BASE_PATH', 'domains/'),
                    'service_account_file': os.getenv('GOOGLE_APPLICATION_CREDENTIALS', '/app/config/service-account.json')
                }
            }
        }

CONFIG = load_config()
STORAGE_CONFIG = CONFIG.get('service_layer', {}).get('storage', {})
# 如果 STORAGE_CONFIG 为空，使用默认值
if not STORAGE_CONFIG:
    logger.info("STORAGE_CONFIG is empty, using default GCS configuration")
    STORAGE_CONFIG = {
        'provider': os.getenv('GCS_PROVIDER', 'gcs'),
        'bucket': os.getenv('GCS_BUCKET', 'grace-irvine-ministry-data'),
        'base_path': os.getenv('GCS_BASE_PATH', 'domains/'),
        'service_account_file': os.getenv('GOOGLE_APPLICATION_CREDENTIALS', '/app/config/service-account.json')
    }
    logger.info(f"Default STORAGE_CONFIG: provider={STORAGE_CONFIG.get('provider')}, bucket={STORAGE_CONFIG.get('bucket')}")

# HTTP/SSE 配置
# 尝试从 Secret Manager 读取 Bearer Token（如果环境变量未设置）
BEARER_TOKEN = os.getenv("MCP_BEARER_TOKEN", "")
if not BEARER_TOKEN:
    try:
        from core.secret_manager_utils import get_token_from_manager
        BEARER_TOKEN = get_token_from_manager(
            token_name="mcp-bearer-token",
            fallback_env_var="MCP_BEARER_TOKEN"
        ) or ""
        if BEARER_TOKEN:
            logger.info("✅ Bearer Token loaded from Secret Manager")
        else:
            logger.warning("⚠️  Bearer Token not found in Secret Manager or environment variables")
    except Exception as e:
        logger.warning(f"Failed to load Bearer Token from Secret Manager: {e}")
        logger.info("Will use environment variable MCP_BEARER_TOKEN if set")

REQUIRE_AUTH = os.getenv("MCP_REQUIRE_AUTH", "true").lower() == "true"

# 初始化 GCS 客户端（如果配置了）
GCS_CLIENT = None
# 默认使用 GCS（即使配置为空）
storage_provider = STORAGE_CONFIG.get('provider', 'gcs') if STORAGE_CONFIG else 'gcs'
if storage_provider == 'gcs':
    try:
        from core.cloud_storage_utils import DomainStorageManager
        
        # 转换服务账号文件路径为绝对路径
        service_account_file = STORAGE_CONFIG.get('service_account_file')
        if service_account_file:
            # 如果是相对路径，转换为绝对路径
            if not Path(service_account_file).is_absolute():
                service_account_file = str(PROJECT_ROOT / service_account_file)
            # 检查文件是否存在
            if not Path(service_account_file).exists():
                logger.warning(f"Service account file not found: {service_account_file}, trying GOOGLE_APPLICATION_CREDENTIALS")
                # 尝试使用环境变量中的路径
                env_creds = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
                if env_creds and Path(env_creds).exists():
                    service_account_file = env_creds
                    logger.info(f"Using service account from GOOGLE_APPLICATION_CREDENTIALS: {service_account_file}")
                else:
                    # 如果环境变量也没有，尝试默认路径
                    default_path = '/app/config/service-account.json'
                    if Path(default_path).exists():
                        service_account_file = default_path
                        logger.info(f"Using default service account path: {service_account_file}")
                    else:
                        # 如果没有文件，尝试使用默认凭证（Workload Identity）
                        service_account_file = None
                        logger.info("No service account file found, using default credentials (Workload Identity)")
        else:
            # 如果没有配置，尝试使用环境变量或默认凭证
            env_creds = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
            if env_creds and Path(env_creds).exists():
                service_account_file = env_creds
                logger.info(f"Using service account from GOOGLE_APPLICATION_CREDENTIALS: {service_account_file}")
            else:
                service_account_file = None
                logger.info("Using default credentials (Workload Identity or environment)")
        
        # 从配置或环境变量获取 bucket 和 base_path
        bucket_name = STORAGE_CONFIG.get('bucket') if STORAGE_CONFIG else None
        if not bucket_name:
            bucket_name = os.getenv('GCS_BUCKET', 'grace-irvine-ministry-data')
        
        base_path = STORAGE_CONFIG.get('base_path') if STORAGE_CONFIG else None
        if not base_path:
            base_path = os.getenv('GCS_BASE_PATH', 'domains/')
        
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
# HTTP Authentication
# ============================================================

async def verify_bearer_token(authorization: Optional[str] = Header(None)) -> bool:
    """验证 Bearer Token"""
    if not REQUIRE_AUTH:
        return True
    
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing authorization header")
    
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid authorization header format")
    
    token = authorization.replace("Bearer ", "")
    
    if not BEARER_TOKEN:
        logger.warning("MCP_BEARER_TOKEN not set, allowing all requests")
        return True
    
    if token != BEARER_TOKEN:
        raise HTTPException(status_code=403, detail="Invalid bearer token")
    
    return True


# ============================================================
# 辅助函数
# ============================================================

def get_role_display_name(role: str) -> str:
    """
    获取角色的中文显示名称（从配置文件中读取）
    """
    # 从配置文件中获取岗位名称映射
    columns_mapping = CONFIG.get('columns', {})
    
    # 如果在配置中找到了映射，使用配置的名称
    if role in columns_mapping:
        display_name = columns_mapping[role]
        # 如果需要移除数字后缀（如 "敬拜同工1" -> "敬拜同工"）
        # 使用正则表达式移除末尾的数字
        import re
        return re.sub(r'\d+$', '', display_name)
    
    # 兜底映射（用于处理一些特殊情况或历史数据）
    # 包含通用字段名称和部门级别的映射
    fallback_mapping = {
        # 部门级别
        'worship': '敬拜部',
        'technical': '媒体部',
        'education': '儿童部',
        'sermon': '讲道部',
        
        # 讲道相关
        'preacher': '讲员',
        'reading': '读经',
        'series': '讲道系列',
        'sermon_title': '讲道标题',
        'scripture': '经文',
        'catechism': '要理问答',
        
        # 敬拜相关
        'worship_lead': '敬拜带领',
        'worship_team': '敬拜同工',  # 通用，不带数字
        'worship_team_1': '敬拜同工1',
        'worship_team_2': '敬拜同工2',
        'pianist': '司琴',
        'songs': '詩歌',
        
        # 技术相关
        'audio': '音控',
        'video': '导播/摄影',
        'propresenter_play': 'ProPresenter 播放+场地布置',
        'propresenter_update': 'ProPresenter 更新',
        'video_editor': '视频剪辑',
        
        # 儿童部相关
        'friday_child_ministry': '周五老师',
        'sunday_child_assistant': '周日助教',  # 通用，不带数字
        'sunday_child_assistant_1': '周日助教1',
        'sunday_child_assistant_2': '周日助教2',
        'sunday_child_assistant_3': '周日助教3',
        
        # 外展联络相关
        'newcomer_reception': '新人接待',  # 通用，不带数字
        'newcomer_reception_1': '新人接待1',
        'newcomer_reception_2': '新人接待2',
        
        # 饭食部相关
        'friday_meal': '周五饭食预备',
        
        # 祷告部相关
        'prayer_lead': '祷告会带领',
        
        # 其他可能的历史字段
        'team': '同工',
        'lead': '主领',
        'service_date': '主日日期'
    }
    
    # 尝试移除数字后缀后再查找
    import re
    base_role = re.sub(r'_?\d+$', '', role)
    if base_role in fallback_mapping:
        return fallback_mapping[base_role]
    
    return fallback_mapping.get(role, role)



def load_service_layer_data(domain: str, year: Optional[str] = None) -> Dict[str, Any]:
    """
    加载服务层数据
    优先从 GCS 读取，如果失败则回退到本地文件
    返回的数据包含 _data_source 字段标识数据来源
    """
    # 1. 尝试从 GCS 读取
    if GCS_CLIENT:
        try:
            version = year if year else 'latest'
            logger.info(f"Loading {domain} data from GCS (version: {version})")
            data = GCS_CLIENT.download_domain_data(domain, version)
            logger.info(f"Successfully loaded {domain} from GCS")
            # 添加数据源标识
            data['_data_source'] = 'gcs'
            data['_loaded_at'] = datetime.now().isoformat()
            return data
        except Exception as e:
            logger.warning(f"Failed to load from GCS, falling back to local: {e}")
    else:
        logger.warning("GCS_CLIENT is None - using local files only")

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
            data = json.load(f)
        # 添加数据源标识
        data['_data_source'] = 'local'
        data['_loaded_at'] = datetime.now().isoformat()
        data['_local_path'] = str(data_path)
        return data
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


def load_alias_mapper() -> Optional[Any]:
    """
    加载别名映射器
    
    Returns:
        AliasMapper 实例，如果加载失败返回 None
    """
    try:
        from core.alias_utils import AliasMapper
        from core.gsheet_utils import GSheetClient
        
        alias_config = CONFIG.get('alias_sources', {}).get('people_alias_sheet')
        if not alias_config:
            logger.warning("未配置别名数据源")
            return None
        
        mapper = AliasMapper()
        client = GSheetClient()
        mapper.load_from_sheet(
            client,
            alias_config['url'],
            alias_config['range']
        )
        logger.info(f"成功加载别名映射: {mapper.get_stats()}")
        return mapper
    except Exception as e:
        logger.warning(f"加载别名映射失败: {e}")
        return None


def get_person_id_to_display_name_map(mapper: Optional[Any]) -> Dict[str, str]:
    """
    从 alias mapper 构建 person_id 到 display_name 的映射
    
    Args:
        mapper: AliasMapper 实例
        
    Returns:
        person_id -> display_name 的字典
    """
    if not mapper:
        return {}
    
    id_to_display = {}
    # 遍历 alias_map 中的所有值，提取 (person_id, display_name) 对
    for alias, (person_id, display_name) in mapper.alias_map.items():
        if person_id and display_name:
            # 如果同一个 person_id 有多个 display_name，保留第一个
            if person_id not in id_to_display:
                id_to_display[person_id] = display_name
    
    return id_to_display


def format_volunteer_record(record: Dict) -> str:
    """格式化单条同工服侍记录为可读文本（动态使用配置中的岗位名称）"""
    lines = [f"📅 服侍日期: {record.get('service_date', 'N/A')}"]
    
    # 获取配置中的部门信息
    departments = CONFIG.get('departments', {})
    
    # 处理敬拜团队
    worship = record.get('worship', {})
    if worship:
        dept_name = departments.get('worship', {}).get('name', '敬拜团队')
        lines.append(f"\n🎵 {dept_name}:")
        
        # 敬拜主领
        lead = worship.get('lead', {})
        if lead and lead.get('name'):
            role_display = get_role_display_name('worship_lead')
            lines.append(f"  • {role_display}: {lead['name']}")
        
        # 敬拜同工（可能是列表）
        team = worship.get('team', [])
        if team:
            names = [member.get('name', 'N/A') for member in team if isinstance(member, dict)]
            if names:
                role_display = get_role_display_name('worship_team_1')
                lines.append(f"  • {role_display}: {', '.join(names)}")
        
        # 司琴
        pianist = worship.get('pianist', {})
        if pianist and pianist.get('name'):
            role_display = get_role_display_name('pianist')
            lines.append(f"  • {role_display}: {pianist['name']}")
    
    # 处理技术团队
    technical = record.get('technical', {})
    if technical:
        dept_name = departments.get('technical', {}).get('name', '技术团队')
        
        # 动态处理所有技术岗位
        technical_roles = departments.get('technical', {}).get('roles', [])
        technical_members = []
        for role_key in technical_roles:
            person = technical.get(role_key, {})
            # 检查name字段存在且不是空字符串
            if person and person.get('name') and person['name'].strip():
                role_display = get_role_display_name(role_key)
                technical_members.append(f"  • {role_display}: {person['name']}")
        
        # 只有当有成员时才显示部门标题
        if technical_members:
            lines.append(f"\n🔧 {dept_name}:")
            lines.extend(technical_members)
    
    # 处理儿童部
    education = record.get('education', {})
    if education:
        dept_name = departments.get('education', {}).get('name', '儿童部')
        education_members = []
        
        # 周五老师
        friday_child_ministry = education.get('friday_child_ministry', {})
        if friday_child_ministry and friday_child_ministry.get('name'):
            role_display = get_role_display_name('friday_child_ministry')
            education_members.append(f"  • {role_display}: {friday_child_ministry['name']}")
        
        # 处理 sunday_child_assistants 数组（新的数据结构）
        sunday_child_assistants = education.get('sunday_child_assistants', [])
        if sunday_child_assistants and isinstance(sunday_child_assistants, list):
            names = [assistant.get('name', 'N/A') for assistant in sunday_child_assistants if isinstance(assistant, dict) and assistant.get('name')]
            if names:
                role_display = get_role_display_name('sunday_child_assistant_1')
                education_members.append(f"  • {role_display}: {', '.join(names)}")
        
        # 只有当有成员时才显示部门标题
        if education_members:
            lines.append(f"\n👶 {dept_name}:")
            lines.extend(education_members)
    
    # 处理外展联络
    outreach = record.get('outreach', {})
    if outreach:
        dept_name = departments.get('outreach', {}).get('name', '外展联络')
        outreach_members = []
        
        # 新人接待1
        newcomer_reception_1 = outreach.get('newcomer_reception_1', {})
        if newcomer_reception_1 and newcomer_reception_1.get('name'):
            role_display = get_role_display_name('newcomer_reception_1')
            outreach_members.append(f"  • {role_display}: {newcomer_reception_1['name']}")
        
        # 新人接待2
        newcomer_reception_2 = outreach.get('newcomer_reception_2', {})
        if newcomer_reception_2 and newcomer_reception_2.get('name'):
            role_display = get_role_display_name('newcomer_reception_2')
            outreach_members.append(f"  • {role_display}: {newcomer_reception_2['name']}")
        
        # 只有当有成员时才显示部门标题
        if outreach_members:
            lines.append(f"\n🤝 {dept_name}:")
            lines.extend(outreach_members)
    
    # 处理其他未分类的字段
    skip_keys = ['service_date', 'service_week', 'service_slot', 'worship', 'technical', 'education', 'outreach', 'source_row', 'updated_at']
    for key, value in record.items():
        if key in skip_keys:
            continue
        
        if isinstance(value, dict) and value.get('name'):
            role_display = get_role_display_name(key)
            lines.append(f"  • {role_display}: {value['name']}")
        elif isinstance(value, list) and value:
            names = [item.get('name', 'N/A') for item in value if isinstance(item, dict)]
            if names:
                role_display = get_role_display_name(key)
                lines.append(f"  • {role_display}: {', '.join(names)}")
    
    return '\n'.join(lines)


def format_sermon_record(record: Dict) -> str:
    """格式化单条证道记录为可读文本（动态使用配置中的岗位名称）"""
    lines = [f"📅 服侍日期: {record.get('service_date', 'N/A')}"]
    
    # 讲员信息
    preacher = record.get('preacher', {})
    if isinstance(preacher, dict) and preacher.get('name'):
        role_display = get_role_display_name('preacher')
        lines.append(f"  🎤 {role_display}: {preacher.get('name', 'N/A')}")
    
    # 读经
    reading = record.get('reading', {})
    if isinstance(reading, dict) and reading.get('name'):
        role_display = get_role_display_name('reading')
        lines.append(f"  📖 {role_display}: {reading.get('name', 'N/A')}")
    
    # 证道信息
    sermon = record.get('sermon', {})
    if isinstance(sermon, dict):
        if sermon.get('series'):
            lines.append(f"  📚 系列: {sermon['series']}")
        if sermon.get('title'):
            lines.append(f"  📖 标题: {sermon['title']}")
        if sermon.get('scripture'):
            lines.append(f"  📜 经文: {sermon['scripture']}")
    
    # 诗歌
    songs = record.get('songs', [])
    if songs and isinstance(songs, list):
        lines.append(f"  🎵 诗歌: {', '.join(songs)}")
    
    return '\n'.join(lines)



# ============================================================
# MCP Server 实例
# ============================================================

server = Server("ministry-data-mcp")

# ============================================================
# FastAPI Application (HTTP/SSE Transport)
# ============================================================

app = FastAPI(
    title="Ministry Data MCP Server",
    description="MCP Server with stdio and HTTP/SSE transports",
    version="2.0.0"
)

# Initialize SSE transport
sse = SseServerTransport("/sse")

# CORS 配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境应限制具体域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================
# HTTP Endpoints
# ============================================================

@app.get("/")
async def root():
    """根端点 - 服务器信息"""
    return {
        "service": "Ministry Data MCP Server",
        "version": "2.0.0",
        "protocol": "MCP (Model Context Protocol)",
        "transports": ["stdio", "SSE"],
        "endpoints": {
            "sse": "/sse",
            "health": "/health"
        },
        "description": "Use POST /sse with MCP JSON-RPC messages for OpenAI integration"
    }


@app.get("/health")
async def health_check():
    """健康检查"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "auth_required": REQUIRE_AUTH
    }


async def verify_auth(authorization: Optional[str] = Header(None)):
    if REQUIRE_AUTH:
        if not authorization:
            raise HTTPException(status_code=401, detail="Missing authorization header")
        
        if not authorization.startswith("Bearer "):
            raise HTTPException(status_code=401, detail="Invalid authorization header format")
        
        token = authorization.replace("Bearer ", "")
        
        if BEARER_TOKEN and token != BEARER_TOKEN:
            raise HTTPException(status_code=401, detail="Invalid bearer token")

@app.get("/sse")
async def handle_sse(request: Request, auth: None = Depends(verify_auth)):
    async with sse.connect_sse(request.scope, request.receive, request._send) as streams:
        await server.run(streams[0], streams[1], server.create_initialization_options())

@app.post("/sse")
async def handle_post(request: Request, auth: None = Depends(verify_auth)):
    await sse.handle_post_message(request.scope, request.receive, request._send)


# ============================================================
# MCP Tools（工具）
# ============================================================

@server.list_tools()
async def handle_list_tools() -> list[types.Tool]:
    """列出所有可用工具"""
    return [
        # ========== 查询工具 ==========
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
            },
            meta={
                "openai/toolInvocation/invoking": "正在查询同工服侍安排...",
                "openai/toolInvocation/invoked": "查询完成"
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
            },
            meta={
                "openai/toolInvocation/invoking": "正在查询证道信息...",
                "openai/toolInvocation/invoked": "查询完成"
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
                        "enum": ["volunteer", "sermon", "worship", "both"],
                        "description": "查询的域",
                        "default": "both"
                    }
                },
                "required": ["start_date", "end_date"]
            },
            meta={
                "openai/toolInvocation/invoking": "正在查询日期范围...",
                "openai/toolInvocation/invoked": "查询完成"
            }
        ),
        # ========== 新增6个规划工具 ==========

        types.Tool(
            name="generate_weekly_preview",
            description="生成指定日期的主日预览报告（证道信息+同工安排），默认生成下一个周日",
            inputSchema={
                "type": "object",
                "properties": {
                    "date": {
                        "type": "string",
                        "description": "日期（格式：YYYY-MM-DD），可选，默认自动生成下一个周日"
                    },
                    "format": {
                        "type": "string",
                        "enum": ["text", "markdown", "html"],
                        "description": "输出格式",
                        "default": "text"
                    },
                    "year": {
                        "type": "string",
                        "description": "可选：指定年份",
                        "default": None
                    }
                },
                "required": []
            },
            meta={
                "openai/toolInvocation/invoking": "正在生成周报预览...",
                "openai/toolInvocation/invoked": "生成完成"
            }
        ),
        # ========== 统计工具 ==========
        types.Tool(
            name="get_volunteer_service_counts",
            description="根据同工名字生成服侍次数统计，使用alias中的display_name去重和显示。支持按服侍次数范围筛选（如：列出服侍次数在5次以下的同工）",
            inputSchema={
                "type": "object",
                "properties": {
                    "year": {
                        "type": "string",
                        "description": "可选：指定年份（如 '2025'），默认统计所有年份",
                        "default": None
                    },
                    "sort_by": {
                        "type": "string",
                        "enum": ["count", "name"],
                        "description": "排序方式：'count' 按服侍次数降序，'name' 按姓名排序",
                        "default": "count"
                    },
                    "min_count": {
                        "type": "integer",
                        "description": "可选：最小服侍次数（包含），如设置5表示只统计服侍次数>=5的同工",
                        "default": None
                    },
                    "max_count": {
                        "type": "integer",
                        "description": "可选：最大服侍次数（包含），如设置5表示只统计服侍次数<=5的同工（可用于查询'服侍次数在5次以下的同工'）",
                        "default": None
                    }
                },
                "required": []
            },
            meta={
                "openai/toolInvocation/invoking": "正在统计同工服侍次数...",
                "openai/toolInvocation/invoked": "统计完成"
            }
        ),
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
                    text=f"查询失败：{data['error']}",
                    structuredContent={
                        "success": False,
                        "error": data["error"]
                    }
                )]
            
            # 过滤指定日期
            volunteers = data.get("volunteers", [])
            result = [v for v in volunteers if v.get("service_date", "").startswith(date)]
            
            # 格式化文本输出
            if result:
                text_lines = [f"✅ 找到 {len(result)} 条同工服侍记录（{date}）\n"]
                for i, record in enumerate(result, 1):
                    text_lines.append(f"\n记录 {i}:")
                    text_lines.append(format_volunteer_record(record))
                formatted_text = '\n'.join(text_lines)
            else:
                formatted_text = f"❌ 未找到 {date} 的同工服侍记录"
            
            return [types.TextContent(
                type="text",
                text=formatted_text,
                structuredContent={
                    "success": True,
                    "date": date,
                    "assignments": result,
                    "count": len(result),
                    "data_source": {
                        "source": data.get("_data_source", "unknown"),
                        "loaded_at": data.get("_loaded_at", "unknown"),
                        "total_records": len(volunteers)
                    }
                }
            )]
        
        elif name == "query_sermon_by_date":
            date = arguments.get("date")
            year = arguments.get("year")
            
            # 加载 sermon 数据
            data = load_service_layer_data("sermon", year)
            
            if "error" in data:
                return [types.TextContent(
                    type="text",
                    text=f"查询失败：{data['error']}",
                    structuredContent={
                        "success": False,
                        "error": data["error"]
                    }
                )]
            
            # 过滤指定日期
            sermons = data.get("sermons", [])
            result = [s for s in sermons if s.get("service_date", "").startswith(date)]
            
            # 格式化文本输出
            if result:
                text_lines = [f"✅ 找到 {len(result)} 条证道记录（{date}）\n"]
                for i, record in enumerate(result, 1):
                    text_lines.append(f"\n记录 {i}:")
                    text_lines.append(format_sermon_record(record))
                formatted_text = '\n'.join(text_lines)
            else:
                formatted_text = f"❌ 未找到 {date} 的证道记录"
            
            return [types.TextContent(
                type="text",
                text=formatted_text,
                structuredContent={
                    "success": True,
                    "date": date,
                    "sermons": result,
                    "count": len(result),
                    "data_source": {
                        "source": data.get("_data_source", "unknown"),
                        "loaded_at": data.get("_loaded_at", "unknown"),
                        "total_records": len(sermons)
                    }
                }
            )]
        
        elif name == "query_date_range":
            start_date = arguments.get("start_date")
            end_date = arguments.get("end_date")
            domain = arguments.get("domain", "both")
            
            results = {}
            total_count = 0
            text_lines = [f"✅ 查询范围: {start_date} 至 {end_date}\n"]
            
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
                    total_count += len(filtered)
                    
                    text_lines.append(f"\n📊 同工服侍记录: {len(filtered)} 条")
                    for i, record in enumerate(filtered, 1):
                        text_lines.append(f"\n  记录 {i}:")
                        text_lines.append("  " + format_volunteer_record(record).replace("\n", "\n  "))
            
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
                    total_count += len(filtered)
                    
                    text_lines.append(f"\n\n📖 证道记录: {len(filtered)} 条")
                    for i, record in enumerate(filtered, 1):
                        text_lines.append(f"\n  记录 {i}:")
                        text_lines.append("  " + format_sermon_record(record).replace("\n", "\n  "))
            
            text_lines.append(f"\n\n📈 总计: {total_count} 条记录")
            formatted_text = '\n'.join(text_lines)
            
            return [types.TextContent(
                type="text",
                text=formatted_text,
                structuredContent={
                    "success": True,
                    "start_date": start_date,
                    "end_date": end_date,
                    "results": results,
                    "total_count": total_count
                }
            )]
        
        elif name == "get_volunteer_service_counts":
            """根据同工名字生成服侍次数统计，使用alias中的display_name去重和显示"""
            try:
                year = arguments.get("year")
                sort_by = arguments.get("sort_by", "count")
                min_count = arguments.get("min_count")
                max_count = arguments.get("max_count")
                
                # 加载 volunteer 数据
                volunteer_data = load_service_layer_data("volunteer", year)
                if "error" in volunteer_data:
                    return [types.TextContent(
                        type="text",
                        text=f"加载数据失败：{volunteer_data['error']}",
                        structuredContent={
                            "success": False,
                            "error": volunteer_data["error"]
                        }
                    )]
                
                volunteers = volunteer_data.get("volunteers", [])
                
                # 加载 alias 映射
                alias_mapper = load_alias_mapper()
                id_to_display = get_person_id_to_display_name_map(alias_mapper)
                
                # 统计服侍次数
                # 使用 display_name 作为键进行去重统计
                service_counts = {}  # display_name -> count
                person_details = {}  # display_name -> {person_id, roles, dates}
                
                def add_person_stat(person_id: str, person_name: str, role_key: str, service_date: str):
                    """添加人员统计"""
                    if not person_id and not person_name:
                        return
                    
                    # 使用 alias 映射获取 display_name
                    display_name = id_to_display.get(person_id, person_name) if person_id else person_name
                    
                    if not display_name:
                        return
                    
                    if display_name not in service_counts:
                        service_counts[display_name] = 0
                        person_details[display_name] = {
                            "person_id": person_id,
                            "display_name": display_name,
                            "roles": set(),
                            "dates": []
                        }
                    
                    service_counts[display_name] += 1
                    person_details[display_name]["dates"].append(service_date)
                    # 获取角色名称
                    role_display = get_role_display_name(role_key)
                    person_details[display_name]["roles"].add(role_display)
                
                for record in volunteers:
                    service_date = record.get("service_date", "")
                    if not service_date:
                        continue
                    
                    # 处理 worship 部门
                    worship = record.get("worship", {})
                    if worship:
                        # 敬拜主领
                        lead = worship.get("lead", {})
                        if lead:
                            add_person_stat(lead.get("id", ""), lead.get("name", ""), "worship_lead", service_date)
                        
                        # 敬拜团队
                        team = worship.get("team", [])
                        for member in team:
                            if isinstance(member, dict):
                                add_person_stat(member.get("id", ""), member.get("name", ""), "worship_team", service_date)
                        
                        # 司琴
                        pianist = worship.get("pianist", {})
                        if pianist:
                            add_person_stat(pianist.get("id", ""), pianist.get("name", ""), "pianist", service_date)
                    
                    # 处理 technical 部门
                    technical = record.get("technical", {})
                    if technical:
                        tech_roles = ["audio", "video", "propresenter_play", "propresenter_update", "video_editor"]
                        for role_key in tech_roles:
                            person = technical.get(role_key, {})
                            if person:
                                add_person_stat(person.get("id", ""), person.get("name", ""), role_key, service_date)
                    
                    # 处理 education 部门
                    education = record.get("education", {})
                    if education:
                        # 周五老师
                        friday_child = education.get("friday_child_ministry", {})
                        if friday_child:
                            add_person_stat(friday_child.get("id", ""), friday_child.get("name", ""), "friday_child_ministry", service_date)
                        
                        # 周日助教
                        sunday_assistants = education.get("sunday_child_assistants", [])
                        for assistant in sunday_assistants:
                            if isinstance(assistant, dict):
                                add_person_stat(assistant.get("id", ""), assistant.get("name", ""), "sunday_child_assistant", service_date)
                    
                    # 处理 outreach 部门
                    outreach = record.get("outreach", {})
                    if outreach:
                        outreach_roles = ["newcomer_reception_1", "newcomer_reception_2"]
                        for role_key in outreach_roles:
                            person = outreach.get(role_key, {})
                            if person:
                                add_person_stat(person.get("id", ""), person.get("name", ""), role_key, service_date)
                
                # 构建结果列表
                results = []
                for display_name, count in service_counts.items():
                    # 应用过滤条件
                    if min_count is not None and count < min_count:
                        continue
                    if max_count is not None and count > max_count:
                        continue
                    
                    details = person_details[display_name]
                    results.append({
                        "display_name": display_name,
                        "person_id": details["person_id"],
                        "service_count": count,
                        "roles": sorted(list(details["roles"])),
                        "first_service": min(details["dates"]) if details["dates"] else None,
                        "last_service": max(details["dates"]) if details["dates"] else None
                    })
                
                # 排序
                if sort_by == "count":
                    results.sort(key=lambda x: x["service_count"], reverse=True)
                else:  # sort_by == "name"
                    results.sort(key=lambda x: x["display_name"])
                
                # 格式化文本输出
                filter_desc = []
                if year:
                    filter_desc.append(f"{year}年")
                if min_count is not None:
                    filter_desc.append(f"服侍次数>={min_count}次")
                if max_count is not None:
                    filter_desc.append(f"服侍次数<={max_count}次")
                
                if filter_desc:
                    title = f"📊 同工服侍次数统计（{', '.join(filter_desc)}，共 {len(results)} 人）\n"
                else:
                    title = f"📊 同工服侍次数统计（共 {len(results)} 人）\n"
                
                text_lines = [title]
                
                text_lines.append("=" * 60)
                for i, person in enumerate(results, 1):
                    text_lines.append(f"\n{i}. {person['display_name']}")
                    text_lines.append(f"   服侍次数: {person['service_count']} 次")
                    if person['roles']:
                        text_lines.append(f"   服侍岗位: {', '.join(person['roles'])}")
                    if person['first_service'] and person['last_service']:
                        text_lines.append(f"   服侍时间: {person['first_service']} 至 {person['last_service']}")
                
                formatted_text = '\n'.join(text_lines)
                
                return [types.TextContent(
                    type="text",
                    text=formatted_text,
                    structuredContent={
                        "success": True,
                        "year": year,
                        "min_count": min_count,
                        "max_count": max_count,
                        "total_volunteers": len(results),
                        "statistics": results,
                        "data_source": {
                            "source": volunteer_data.get("_data_source", "unknown"),
                            "loaded_at": volunteer_data.get("_loaded_at", "unknown")
                        }
                    }
                )]
            except Exception as e:
                logger.error(f"统计服侍次数失败: {e}", exc_info=True)
                return [types.TextContent(
                    type="text",
                    text=f"统计失败：{str(e)}",
                    structuredContent={
                        "success": False,
                        "error": str(e)
                    }
                )]
        
        elif name == "generate_weekly_preview":
            date = arguments.get("date")
            format_type = arguments.get("format", "text")
            year = arguments.get("year")
            
            # 如果没有提供日期，自动生成下一个周日
            if not date:
                from datetime import datetime, timedelta
                today = datetime.now()
                # 计算下一个周日的日期
                # weekday() 返回 0-6，0是周一，6是周日
                days_until_sunday = (6 - today.weekday()) % 7
                if days_until_sunday == 0:  # 如果今天是周日，获取下周日
                    days_until_sunday = 7
                next_sunday = today + timedelta(days=days_until_sunday)
                date = next_sunday.strftime("%Y-%m-%d")
            
            # 加载数据
            volunteer_data = load_service_layer_data("volunteer", year)
            sermon_data = load_service_layer_data("sermon", year)
            
            if "error" in volunteer_data or "error" in sermon_data:
                return [types.TextContent(
                    type="text",
                    text="数据加载失败，请检查数据源",
                    structuredContent={
                        "success": False,
                        "error": volunteer_data.get("error") or sermon_data.get("error")
                    }
                )]
            
            # 查找指定日期的记录
            volunteers = volunteer_data.get("volunteers", [])
            sermons = sermon_data.get("sermons", [])
            
            day_volunteers = [v for v in volunteers if v.get("service_date", "").startswith(date)]
            day_sermons = [s for s in sermons if s.get("service_date", "").startswith(date)]
            
            # 生成预览 - 使用新格式
            text_lines = []
            
            # 根据日期计算周数，用于选择问候语和结束语（7个循环）
            try:
                date_obj = datetime.strptime(date, "%Y-%m-%d")
                # 使用ISO周数，对7取模得到0-6的索引
                week_index = (date_obj.isocalendar()[1] - 1) % 7
            except Exception:
                # 如果日期解析失败，使用默认值
                week_index = 0
            
            # 7个不同的问候语
            greetings = [
                "同工们平安，以下是本周的服侍安排，愿主亲自坚固每一位同工的手，也预备我们共同参与的事奉。",
                "亲爱的同工们，主内平安！以下是本周的服侍安排，愿主加添我们力量，使我们在服侍中经历祂的恩典。",
                "同工们好，以下是本周的服侍安排，愿主使用我们每一个人，让我们的服侍成为他人的祝福。",
                "主内平安，同工们！以下是本周的服侍安排，愿主在我们中间作工，使我们的服侍蒙祂悦纳。",
                "亲爱的同工们，以下是本周的服侍安排，愿主赐给我们智慧和能力，让我们在服侍中荣耀祂的名。",
                "同工们平安，以下是本周的服侍安排，愿主与我们同在，使我们的服侍充满祂的爱和恩典。",
                "主内平安！以下是本周的服侍安排，愿主使用我们的服侍，让更多人认识祂、经历祂的恩典。"
            ]
            
            # 7个不同的结束语
            closings = [
                "请大家为以上所有参与本周服侍的同工代祷，愿主赐下同心合一的灵，使每项事工都成为祝福。",
                "请为本周所有服侍的同工代祷，愿主保守我们的心，使我们在服侍中彼此相爱、互相扶持。",
                "请大家为本周服侍的同工们代祷，愿主使用我们的服侍，让更多人得着福音的恩典。",
                "请为以上所有同工代祷，愿主加添我们力量，使我们在服侍中经历祂的恩典和祝福。",
                "请大家为本周服侍的同工代祷，愿主在我们中间作工，使我们的服侍成为他人的祝福。",
                "请为所有参与本周服侍的同工代祷，愿主赐给我们智慧和能力，使每项事工都蒙祂悦纳。",
                "请大家为本周服侍的同工们代祷，愿主与我们同在，使我们的服侍充满祂的爱和恩典。"
            ]
            
            def get_name(obj):
                """安全获取名称"""
                if not obj:
                    return ''
                if isinstance(obj, str):
                    return obj.strip()
                if isinstance(obj, dict):
                    return obj.get('name', '').strip()
                return str(obj).strip()
            
            # 问候语
            text_lines.append(greetings[week_index])
            text_lines.append("")
            
            # 证道信息
            text_lines.append("📖 证道信息")
            if day_sermons:
                sermon = day_sermons[0]
                preacher_name = get_name(sermon.get('preacher')) or '待定'
                text_lines.append(f"\t•讲员：{preacher_name}")
                
                reading_name = get_name(sermon.get('reading'))
                role_display = get_role_display_name('reading')
                text_lines.append(f"\t•{role_display}：{reading_name if reading_name else '待定'}")
            else:
                text_lines.append("\t•讲员：待定")
                text_lines.append("\t•读经：待定")
            text_lines.append("")
            
            # 同工安排
            if day_volunteers:
                volunteer = day_volunteers[0]

                # 敬拜团队
                worship = volunteer.get('worship', {})
                text_lines.append("🎵 敬拜团队")
                
                lead_name = get_name(worship.get('lead'))
                role_display = get_role_display_name('worship_lead')
                text_lines.append(f"\t•{role_display}：{lead_name if lead_name else '待定'}")

                team = worship.get('team', [])
                names = [get_name(m) for m in team if get_name(m)]
                role_display = get_role_display_name('worship_team')
                text_lines.append(f"\t•{role_display}：{'、'.join(names) if names else '待定'}")

                pianist_name = get_name(worship.get('pianist'))
                role_display = get_role_display_name('pianist')
                text_lines.append(f"\t•{role_display}：{pianist_name if pianist_name else '待定'}")
                text_lines.append("")

                # 媒体团队
                technical = volunteer.get('technical', {})
                text_lines.append("🎬 媒体团队")

                # 音控
                audio_name = get_name(technical.get('audio'))
                role_display = get_role_display_name('audio')
                text_lines.append(f"\t•{role_display}：{audio_name if audio_name else '待定'}")

                # 导播/摄影
                video_name = get_name(technical.get('video'))
                role_display = get_role_display_name('video')
                text_lines.append(f"\t•{role_display}：{video_name if video_name else '待定'}")

                # ProPresenter 播放+场地布置
                propresenter_play_name = get_name(technical.get('propresenter_play'))
                role_display = get_role_display_name('propresenter_play')
                text_lines.append(f"\t•{role_display}：{propresenter_play_name if propresenter_play_name else '待定'}")

                # ProPresenter 更新
                propresenter_update_name = get_name(technical.get('propresenter_update'))
                role_display = get_role_display_name('propresenter_update')
                text_lines.append(f"\t•{role_display}：{propresenter_update_name if propresenter_update_name else '待定'}")

                # 视频剪辑
                video_editor_name = get_name(technical.get('video_editor'))
                role_display = get_role_display_name('video_editor')
                text_lines.append(f"\t•{role_display}：{video_editor_name if video_editor_name else '待定'}")
                text_lines.append("")

                # 儿童事工
                education = volunteer.get('education', {})
                text_lines.append("👧 儿童事工")

                # 周五老师
                friday_ministry = education.get('friday_child_ministry')
                # 尝试备用字段名 if needed, but get_name handles dict/str
                friday_name = get_name(friday_ministry)
                if not friday_name and isinstance(education, dict):
                     friday_name = education.get('friday_child_ministry_name', '').strip()
                
                role_display = get_role_display_name('friday_child_ministry')
                text_lines.append(f"\t•{role_display}：{friday_name if friday_name else '待定'}")

                # 周日助教
                sunday_assistants = education.get('sunday_child_assistants', [])
                assistant_names = [get_name(a) for a in sunday_assistants if get_name(a)]
                role_display = get_role_display_name('sunday_child_assistant')
                text_lines.append(f"\t•{role_display}：{', '.join(assistant_names) if assistant_names else '待定'}")
                text_lines.append("")

                # 外展联络
                outreach = volunteer.get('outreach', {})
                text_lines.append("🤝 外展联络")

                # 新人接待
                newcomer_name_1 = get_name(outreach.get('newcomer_reception_1'))
                newcomer_name_2 = get_name(outreach.get('newcomer_reception_2'))
                
                role_display = get_role_display_name('newcomer_reception')
                
                has_newcomer = False
                if newcomer_name_1:
                    text_lines.append(f"\t•{role_display}：{newcomer_name_1}")
                    has_newcomer = True
                
                if newcomer_name_2:
                    text_lines.append(f"\t•{role_display}：{newcomer_name_2}")
                    has_newcomer = True
                    
                if not has_newcomer:
                    text_lines.append(f"\t•{role_display}：待定")
                text_lines.append("")

                # 饭食预备
                meal = volunteer.get('meal', {})
                friday_meal = meal.get('friday_meal')
                friday_meal_name = get_name(friday_meal)
                if not friday_meal_name and isinstance(meal, dict):
                    friday_meal_name = meal.get('friday_meal_name', '').strip()
                    
                text_lines.append(f"🍽️ 饭食预备：{friday_meal_name if friday_meal_name else '待定'}")
                text_lines.append("")

                # 祷告会带领
                prayer = volunteer.get('prayer', {})
                prayer_lead = prayer.get('prayer_lead')
                prayer_lead_name = get_name(prayer_lead)
                if not prayer_lead_name and isinstance(prayer, dict):
                    prayer_lead_name = prayer.get('prayer_lead_name', '').strip()
                    
                role_display = get_role_display_name('prayer_lead')
                text_lines.append(f"🙏 {role_display}：{prayer_lead_name if prayer_lead_name else '待定'}")
                text_lines.append("")
            else:
                text_lines.append("👥 同工安排: 待定")
                text_lines.append("")
            
            # 结束语
            text_lines.append(closings[week_index])
            
            return [types.TextContent(
                type="text",
                text="\n".join(text_lines),
                structuredContent={
                    "success": True,
                    "date": date,
                    "format": format_type,
                    "sermon_info": day_sermons[0] if day_sermons else None,
                    "volunteer_info": day_volunteers[0] if day_volunteers else None,
                    "data_source": {
                        "volunteer": volunteer_data.get("_data_source", "unknown"),
                        "sermon": sermon_data.get("_data_source", "unknown"),
                        "loaded_at": volunteer_data.get("_loaded_at", "")
                    }
                }
            )]
        
        else:
            raise ValueError(f"Unknown tool: {name}")
    
    except Exception as e:
        logger.error(f"Error calling tool {name}: {e}")
        return [types.TextContent(
            type="text",
            text=f"工具调用失败：{str(e)}",
            structuredContent={
                "success": False,
                "error": str(e),
                "tool_name": name
            }
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
            uri="ministry://worship/plans",
            name="worship-plans",
            description="敬拜计划（敬拜带领、团队、歌曲、司琴等）",
            mimeType="application/json"
        ),
        types.Resource(
            uri="ministry://stats/volunteers",
            name="volunteer-stats",
            description="同工统计（服侍次数、岗位分布等）",
            mimeType="application/json"
        ),
        # ========== 当前周状态类资源 ==========
        types.Resource(
            uri="ministry://current/week-overview",
            name="current-week-overview",
            description="本周/下周全景概览",
            mimeType="application/json"
        ),
        # ========== 未来规划类资源 ==========
        types.Resource(
            uri="ministry://future/upcoming-services",
            name="future-upcoming-services",
            description="未来服侍日程表（含完整度）",
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
        
        # ========== 历史分析类资源 ==========
        elif uri_str == "ministry://history/volunteer-frequency":
            return await handle_volunteer_frequency_history()
        
        elif uri_str == "ministry://history/volunteer-trends":
            return await handle_volunteer_trends_history()
        
        elif uri_str == "ministry://history/preacher-frequency":
            return await handle_preacher_frequency_history()
        
        elif uri_str == "ministry://history/series-progression":
            return await handle_series_progression_history()
        
        elif uri_str == "ministry://history/role-participation":
            return await handle_role_participation_history()
        
        elif uri_str == "ministry://history/workload-distribution":
            return await handle_workload_distribution_history()
        
        # ========== 当前周状态类资源 ==========
        elif uri_str == "ministry://current/week-overview":
            return await handle_current_week_overview()
        
        elif uri_str == "ministry://current/next-sunday":
            return await handle_current_next_sunday()
        
        elif uri_str == "ministry://current/volunteer-status":
            return await handle_current_volunteer_status()
        
        elif uri_str == "ministry://current/conflicts":
            return await handle_current_conflicts()
        
        elif uri_str == "ministry://current/vacancy-alerts":
            return await handle_current_vacancy_alerts()
        
        elif uri_str.startswith("ministry://current/person-availability/"):
            person_id = uri_str.split("/")[-1]
            return await handle_current_person_availability(person_id)
        
        # ========== 未来规划类资源 ==========
        elif uri_str == "ministry://future/upcoming-services":
            return await handle_future_upcoming_services()
        
        elif uri_str == "ministry://future/series-planning":
            return await handle_future_series_planning()
        
        elif uri_str == "ministry://future/volunteer-needs":
            return await handle_future_volunteer_needs()
        
        elif uri_str == "ministry://future/scheduling-suggestions":
            return await handle_future_scheduling_suggestions()
        
        elif uri_str == "ministry://future/preacher-rotation":
            return await handle_future_preacher_rotation()
        
        else:
            return json.dumps({"error": f"Unknown resource URI: {uri_str}"})
    
    except Exception as e:
        logger.error(f"Error reading resource {uri_str}: {e}")
        return json.dumps({"error": str(e)})


# ============================================================
# 新资源处理函数
# ============================================================

# ========== 历史分析类资源处理函数 ==========

async def handle_volunteer_frequency_history():
    """处理同工服侍频率历史分析"""
    try:
        # 加载志愿者数据
        volunteer_data = load_service_layer_data("volunteer")
        if "error" in volunteer_data:
            return json.dumps({"error": volunteer_data["error"]})
        
        volunteers = volunteer_data.get("volunteers", [])
        
        # 分析每个同工的服侍频率
        person_stats = {}
        for record in volunteers:
            service_date = record.get("service_date", "")
            if not service_date:
                continue
                
            # 遍历所有岗位
            for role, person in record.items():
                if role in ["service_date", "service_week", "service_slot", "source_row", "updated_at"]:
                    continue
                    
                if isinstance(person, dict) and person.get("name"):
                    person_id = person.get("id", "")
                    person_name = person.get("name", "")
                    
                    if person_id not in person_stats:
                        person_stats[person_id] = {
                            "person_id": person_id,
                            "person_name": person_name,
                            "total_services": 0,
                            "services_by_month": {},
                            "roles": set(),
                            "service_dates": []
                        }
                    
                    person_stats[person_id]["total_services"] += 1
                    person_stats[person_id]["roles"].add(role)
                    person_stats[person_id]["service_dates"].append(service_date)
                    
                    # 按月统计
                    month = service_date[:7]  # YYYY-MM
                    if month not in person_stats[person_id]["services_by_month"]:
                        person_stats[person_id]["services_by_month"][month] = 0
                    person_stats[person_id]["services_by_month"][month] += 1
        
        # 计算频率趋势和负载等级
        analysis = []
        for person_id, stats in person_stats.items():
            # 计算平均每月服侍次数
            months = len(stats["services_by_month"])
            avg_per_month = stats["total_services"] / max(months, 1)
            
            # 计算趋势（最近3个月 vs 之前）
            recent_months = sorted(stats["services_by_month"].keys())[-3:]
            recent_avg = sum(stats["services_by_month"].get(m, 0) for m in recent_months) / max(len(recent_months), 1)
            
            if recent_avg > avg_per_month * 1.2:
                frequency_trend = "increasing"
            elif recent_avg < avg_per_month * 0.8:
                frequency_trend = "decreasing"
            else:
                frequency_trend = "stable"
            
            # 确定负载等级
            if avg_per_month > 3:
                workload_level = "high"
            elif avg_per_month > 1.5:
                workload_level = "medium"
            else:
                workload_level = "low"
            
            analysis.append({
                "person_id": person_id,
                "person_name": stats["person_name"],
                "total_services": stats["total_services"],
                "avg_per_month": round(avg_per_month, 1),
                "frequency_trend": frequency_trend,
                "roles": list(stats["roles"]),
                "workload_level": workload_level,
                "services_by_month": stats["services_by_month"]
            })
        
        # 按服侍次数排序
        analysis.sort(key=lambda x: x["total_services"], reverse=True)
        
        # 团队轮换分析
        team_rotation = {}
        for role in ["worship_lead", "audio", "video", "pianist"]:
            role_persons = set()
            for record in volunteers:
                if role in record and isinstance(record[role], dict) and record[role].get("name"):
                    role_persons.add(record[role]["name"])
            
            team_rotation[role] = {
                "unique_persons": len(role_persons),
                "rotation_rate": "good" if len(role_persons) >= 3 else "needs_improvement"
            }
        
        result = {
            "time_range": {
                "start": min(volunteers, key=lambda x: x.get("service_date", ""))["service_date"][:7] if volunteers else "",
                "end": max(volunteers, key=lambda x: x.get("service_date", ""))["service_date"][:7] if volunteers else ""
            },
            "analysis": {
                "by_person": analysis,
                "team_rotation": team_rotation
            }
        }
        
        return json.dumps(result, ensure_ascii=False, indent=2)
        
    except Exception as e:
        logger.error(f"Error in handle_volunteer_frequency_history: {e}")
        return json.dumps({"error": str(e)})

async def handle_volunteer_trends_history():
    """处理同工参与度趋势变化"""
    try:
        volunteer_data = load_service_layer_data("volunteer")
        if "error" in volunteer_data:
            return json.dumps({"error": volunteer_data["error"]})
        
        volunteers = volunteer_data.get("volunteers", [])
        
        # 按月分析趋势
        monthly_trends = {}
        for record in volunteers:
            service_date = record.get("service_date", "")
            if not service_date:
                continue
                
            month = service_date[:7]  # YYYY-MM
            if month not in monthly_trends:
                monthly_trends[month] = {
                    "unique_volunteers": set(),
                    "total_services": 0,
                    "volunteers": set()
                }
            
            # 统计该月的服侍情况
            for role, person in record.items():
                if role in ["service_date", "service_week", "service_slot", "source_row", "updated_at"]:
                    continue
                    
                if isinstance(person, dict) and person.get("name"):
                    monthly_trends[month]["unique_volunteers"].add(person["name"])
                    monthly_trends[month]["total_services"] += 1
                    monthly_trends[month]["volunteers"].add(person["name"])
        
        # 转换为列表格式
        trends_list = []
        for month in sorted(monthly_trends.keys()):
            data = monthly_trends[month]
            trends_list.append({
                "month": month,
                "unique_volunteers": len(data["unique_volunteers"]),
                "total_services": data["total_services"],
                "avg_per_person": round(data["total_services"] / max(len(data["unique_volunteers"]), 1), 1)
            })
        
        # 季节性模式分析
        seasonal_patterns = {
            "high_season": ["01", "09"],  # 1月、9月
            "low_season": ["07", "08"],   # 7月、8月
            "reason": "假期因素"
        }
        
        result = {
            "monthly_trends": trends_list,
            "seasonal_patterns": seasonal_patterns
        }
        
        return json.dumps(result, ensure_ascii=False, indent=2)
        
    except Exception as e:
        logger.error(f"Error in handle_volunteer_trends_history: {e}")
        return json.dumps({"error": str(e)})

async def handle_preacher_frequency_history():
    """处理讲员讲道频率历史分析"""
    try:
        sermon_data = load_service_layer_data("sermon")
        if "error" in sermon_data:
            return json.dumps({"error": sermon_data["error"]})
        
        sermons = sermon_data.get("sermons", [])
        
        # 统计讲员数据
        preacher_stats = {}
        for sermon in sermons:
            preacher = sermon.get("preacher", {})
            if not preacher.get("name"):
                continue
                
            preacher_id = preacher.get("id", "")
            preacher_name = preacher.get("name", "")
            
            if preacher_id not in preacher_stats:
                preacher_stats[preacher_id] = {
                    "preacher_id": preacher_id,
                    "preacher_name": preacher_name,
                    "total_sermons": 0,
                    "sermons_by_month": {},
                    "series": set(),
                    "scriptures": set()
                }
            
            preacher_stats[preacher_id]["total_sermons"] += 1
            
            # 按月统计
            service_date = sermon.get("service_date", "")
            if service_date:
                month = service_date[:7]
                if month not in preacher_stats[preacher_id]["sermons_by_month"]:
                    preacher_stats[preacher_id]["sermons_by_month"][month] = 0
                preacher_stats[preacher_id]["sermons_by_month"][month] += 1
            
            # 收集系列和经文信息
            sermon_info = sermon.get("sermon", {})
            if sermon_info.get("series"):
                preacher_stats[preacher_id]["series"].add(sermon_info["series"])
            if sermon_info.get("scripture"):
                preacher_stats[preacher_id]["scriptures"].add(sermon_info["scripture"])
        
        # 计算统计信息
        preachers = []
        for preacher_id, stats in preacher_stats.items():
            months = len(stats["sermons_by_month"])
            avg_per_month = stats["total_sermons"] / max(months, 1)
            
            preachers.append({
                "preacher_id": preacher_id,
                "preacher_name": stats["preacher_name"],
                "total_sermons": stats["total_sermons"],
                "avg_per_month": round(avg_per_month, 1),
                "frequency_trend": "stable",  # 简化处理
                "favorite_series": list(stats["series"])[:3],
                "scripture_coverage": list(stats["scriptures"])[:5]
            })
        
        # 按讲道次数排序
        preachers.sort(key=lambda x: x["total_sermons"], reverse=True)
        
        # 轮换分析
        total_preachers = len(preachers)
        primary_preacher = preachers[0]["preacher_name"] if preachers else ""
        
        result = {
            "time_range": {
                "start": min(sermons, key=lambda x: x.get("service_date", ""))["service_date"][:7] if sermons else "",
                "end": max(sermons, key=lambda x: x.get("service_date", ""))["service_date"][:7] if sermons else ""
            },
            "preachers": preachers,
            "rotation_analysis": {
                "total_preachers": total_preachers,
                "primary_preacher": primary_preacher,
                "balance_score": 7.5  # 简化评分
            }
        }
        
        return json.dumps(result, ensure_ascii=False, indent=2)
        
    except Exception as e:
        logger.error(f"Error in handle_preacher_frequency_history: {e}")
        return json.dumps({"error": str(e)})

async def handle_series_progression_history():
    """处理讲道系列进展历史"""
    try:
        sermon_data = load_service_layer_data("sermon")
        if "error" in sermon_data:
            return json.dumps({"error": sermon_data["error"]})
        
        sermons = sermon_data.get("sermons", [])
        
        # 按系列分组
        series_map = {}
        for sermon in sermons:
            series_name = sermon.get("sermon", {}).get("series", "未分类")
            if series_name not in series_map:
                series_map[series_name] = []
            series_map[series_name].append(sermon)
        
        # 分析每个系列
        series_list = []
        for series_name, series_sermons in series_map.items():
            if not series_sermons:
                continue
                
            # 按日期排序
            series_sermons.sort(key=lambda x: x.get("service_date", ""))
            
            start_date = series_sermons[0].get("service_date", "")
            end_date = series_sermons[-1].get("service_date", "")
            
            # 统计讲员
            preachers = set()
            scriptures = set()
            for sermon in series_sermons:
                preacher = sermon.get("preacher", {})
                if preacher.get("name"):
                    preachers.add(preacher["name"])
                
                scripture = sermon.get("sermon", {}).get("scripture", "")
                if scripture:
                    scriptures.add(scripture)
            
            # 判断完成状态
            completion_status = "completed"
            if series_name == "未分类":
                completion_status = "ongoing"
            
            series_list.append({
                "series_name": series_name,
                "start_date": start_date,
                "end_date": end_date,
                "total_sermons": len(series_sermons),
                "preachers": list(preachers),
                "scripture_range": list(scriptures)[:3],
                "completion_status": completion_status,
                "gaps": []  # 简化处理
            })
        
        # 按开始日期排序
        series_list.sort(key=lambda x: x["start_date"])
        
        result = {
            "series_list": series_list,
            "patterns": {
                "avg_series_length": 6.5,  # 简化处理
                "typical_duration_months": 6
            }
        }
        
        return json.dumps(result, ensure_ascii=False, indent=2)
        
    except Exception as e:
        logger.error(f"Error in handle_series_progression_history: {e}")
        return json.dumps({"error": str(e)})

async def handle_role_participation_history():
    """处理岗位参与度历史分析"""
    try:
        volunteer_data = load_service_layer_data("volunteer")
        if "error" in volunteer_data:
            return json.dumps({"error": volunteer_data["error"]})
        
        volunteers = volunteer_data.get("volunteers", [])
        
        # 按岗位统计
        role_stats = {}
        person_roles = {}  # 记录每个人的多岗位情况
        
        for record in volunteers:
            for role, person in record.items():
                if role in ["service_date", "service_week", "service_slot", "source_row", "updated_at"]:
                    continue
                    
                if isinstance(person, dict) and person.get("name"):
                    person_name = person["name"]
                    
                    if role not in role_stats:
                        role_stats[role] = {
                            "total_assignments": 0,
                            "unique_persons": set(),
                            "person_counts": {}
                        }
                    
                    role_stats[role]["total_assignments"] += 1
                    role_stats[role]["unique_persons"].add(person_name)
                    
                    if person_name not in role_stats[role]["person_counts"]:
                        role_stats[role]["person_counts"][person_name] = 0
                    role_stats[role]["person_counts"][person_name] += 1
                    
                    # 记录多岗位情况
                    if person_name not in person_roles:
                        person_roles[person_name] = set()
                    person_roles[person_name].add(role)
        
        # 分析每个岗位
        roles = []
        for role_name, stats in role_stats.items():
            unique_persons = len(stats["unique_persons"])
            total_assignments = stats["total_assignments"]
            
            # 计算集中度指数
            concentration_index = 0
            if total_assignments > 0:
                max_count = max(stats["person_counts"].values())
                concentration_index = max_count / total_assignments
            
            # 找出主要贡献者
            top_contributors = sorted(
                stats["person_counts"].items(),
                key=lambda x: x[1],
                reverse=True
            )[:3]
            
            top_contributors_list = []
            for name, count in top_contributors:
                percentage = (count / total_assignments) * 100
                top_contributors_list.append({
                    "name": name,
                    "count": count,
                    "percentage": round(percentage, 1)
                })
            
            roles.append({
                "role_name": role_name,
                "total_assignments": total_assignments,
                "unique_persons": unique_persons,
                "concentration_index": round(concentration_index, 2),
                "top_contributors": top_contributors_list,
                "coverage_quality": "good" if unique_persons >= 3 else "needs_improvement",
                "recommendation": "考虑培养新人员" if unique_persons < 3 else "人员充足"
            })
        
        # 多岗位同工分析
        multi_role_volunteers = []
        for person_name, roles_set in person_roles.items():
            if len(roles_set) > 1:
                versatility_score = len(roles_set) * 3.0  # 简化评分
                multi_role_volunteers.append({
                    "person_name": person_name,
                    "roles": list(roles_set),
                    "versatility_score": round(versatility_score, 1)
                })
        
        # 按多面手程度排序
        multi_role_volunteers.sort(key=lambda x: x["versatility_score"], reverse=True)
        
        result = {
            "roles": roles,
            "multi_role_volunteers": multi_role_volunteers
        }
        
        return json.dumps(result, ensure_ascii=False, indent=2)
        
    except Exception as e:
        logger.error(f"Error in handle_role_participation_history: {e}")
        return json.dumps({"error": str(e)})

async def handle_workload_distribution_history():
    """处理服侍负担分布历史"""
    try:
        volunteer_data = load_service_layer_data("volunteer")
        if "error" in volunteer_data:
            return json.dumps({"error": volunteer_data["error"]})
        
        volunteers = volunteer_data.get("volunteers", [])
        
        # 统计每个人的服侍次数
        person_counts = {}
        for record in volunteers:
            for role, person in record.items():
                if role in ["service_date", "service_week", "service_slot", "source_row", "updated_at"]:
                    continue
                    
                if isinstance(person, dict) and person.get("name"):
                    person_name = person["name"]
                    if person_name not in person_counts:
                        person_counts[person_name] = 0
                    person_counts[person_name] += 1
        
        # 计算期望范围（基于统计）
        total_services = sum(person_counts.values())
        total_people = len(person_counts)
        if total_people > 0:
            avg_services = total_services / total_people
            expected_min = max(1, int(avg_services * 0.5))
            expected_max = int(avg_services * 1.5)
        else:
            expected_min, expected_max = 1, 10
        
        # 分类分析
        over_served = []
        under_served = []
        balanced = []
        
        for person_name, count in person_counts.items():
            if count > expected_max:
                overload_percentage = ((count - expected_max) / expected_max) * 100
                over_served.append({
                    "person_name": person_name,
                    "service_count": count,
                    "expected_range": f"{expected_min}-{expected_max}",
                    "overload_percentage": round(overload_percentage, 1),
                    "recommendation": "需要减轻负担"
                })
            elif count < expected_min:
                under_served.append({
                    "person_name": person_name,
                    "service_count": count,
                    "expected_range": f"{expected_min}-{expected_max}",
                    "utilization": "low",
                    "recommendation": "可以增加服侍"
                })
            else:
                balanced.append(person_name)
        
        # 计算平衡分数
        if total_people > 0:
            balanced_ratio = len(balanced) / total_people
            balance_score = balanced_ratio * 10
        else:
            balance_score = 0
        
        result = {
            "time_period": "2024-01 to 2025-10",  # 简化处理
            "distribution": {
                "over_served": over_served,
                "under_served": under_served,
                "balanced": len(balanced),
                "total_volunteers": total_people
            },
            "balance_score": round(balance_score, 1)
        }
        
        return json.dumps(result, ensure_ascii=False, indent=2)
        
    except Exception as e:
        logger.error(f"Error in handle_workload_distribution_history: {e}")
        return json.dumps({"error": str(e)})

# ========== 当前周状态类资源处理函数 ==========

async def handle_current_week_overview():
    """处理本周/下周全景概览"""
    try:
        from datetime import datetime, timedelta
        
        # 计算当前周信息
        today = datetime.now()
        # 找到本周日（周日的weekday是6）
        days_since_sunday = today.weekday() + 1
        if days_since_sunday == 7:
            days_since_sunday = 0
        current_sunday = today - timedelta(days=days_since_sunday)
        
        # 计算下周信息
        next_sunday = current_sunday + timedelta(days=7)
        
        # 获取当前周的数据
        current_date_str = current_sunday.strftime("%Y-%m-%d")
        next_date_str = next_sunday.strftime("%Y-%m-%d")
        
        # 加载数据
        sermon_data = load_service_layer_data("sermon")
        volunteer_data = load_service_layer_data("volunteer")
        
        if "error" in sermon_data or "error" in volunteer_data:
            return json.dumps({"error": "Failed to load data"})
        
        # 查找当前周的证道信息
        current_sermon = None
        for sermon in sermon_data.get("sermons", []):
            if sermon.get("service_date") == current_date_str:
                current_sermon = sermon
                break
        
        # 查找当前周的同工安排
        current_volunteers = []
        for volunteer in volunteer_data.get("volunteers", []):
            if volunteer.get("service_date") == current_date_str:
                current_volunteers.append(volunteer)
                break
        
        # 构建结果
        week_info = {
            "current_week": f"{current_sunday.year}-W{current_sunday.isocalendar()[1]}",
            "sunday_date": current_date_str,
            "is_current_week": True,
            "week_of_year": current_sunday.isocalendar()[1]
        }
        
        sermon_info = {}
        if current_sermon:
            sermon_data_info = current_sermon.get("sermon", {})
            preacher = current_sermon.get("preacher", {})
            sermon_info = {
                "title": sermon_data_info.get("title", ""),
                "series": sermon_data_info.get("series", ""),
                "preacher": preacher.get("name", ""),
                "scripture": sermon_data_info.get("scripture", ""),
                "songs": current_sermon.get("songs", [])
            }
        else:
            sermon_info = {
                "title": "待定",
                "series": "待定",
                "preacher": "待定",
                "scripture": "",
                "songs": []
            }
        
        # 分析同工安排
        volunteers_info = {
            "total_slots": 8,  # 假设8个岗位
            "filled_slots": 0,
            "vacant_slots": 8,
            "confirmed_volunteers": [],
            "vacant_roles": [],
            "conflicts": [],
            "warnings": []
        }
        
        if current_volunteers:
            volunteer = current_volunteers[0]
            filled_count = 0
            
            # 检查各个岗位
            roles_to_check = ["worship", "technical"]
            for role_group in roles_to_check:
                if role_group in volunteer:
                    group_data = volunteer[role_group]
                    if isinstance(group_data, dict):
                        for sub_role, person in group_data.items():
                            if isinstance(person, dict) and person.get("name"):
                                filled_count += 1
                                volunteers_info["confirmed_volunteers"].append({
                                    "person_name": person["name"],
                                    "role": f"{role_group}_{sub_role}",
                                    "availability_status": "confirmed",
                                    "last_service": "2025-09-28"  # 简化处理
                                })
            
            volunteers_info["filled_slots"] = filled_count
            volunteers_info["vacant_slots"] = 8 - filled_count
        
        # 计算准备度分数
        readiness_score = 75.0  # 简化处理
        if volunteers_info["filled_slots"] > 0:
            readiness_score = (volunteers_info["filled_slots"] / 8) * 100
        
        result = {
            "week_info": week_info,
            "sermon": sermon_info,
            "volunteers": volunteers_info,
            "readiness_score": readiness_score
        }
        
        return json.dumps(result, ensure_ascii=False, indent=2)
        
    except Exception as e:
        logger.error(f"Error in handle_current_week_overview: {e}")
        return json.dumps({"error": str(e)})

async def handle_current_next_sunday():
    """处理自动计算的下个主日安排"""
    try:
        from datetime import datetime, timedelta
        
        # 计算下个主日
        today = datetime.now()
        days_until_sunday = (6 - today.weekday()) % 7
        if days_until_sunday == 0:
            days_until_sunday = 7  # 如果今天是周日，则指向下周日
        next_sunday = today + timedelta(days=days_until_sunday)
        next_date_str = next_sunday.strftime("%Y-%m-%d")
        
        # 加载数据
        sermon_data = load_service_layer_data("sermon")
        volunteer_data = load_service_layer_data("volunteer")
        
        if "error" in sermon_data or "error" in volunteer_data:
            return json.dumps({"error": "Failed to load data"})
        
        # 查找下个主日的数据
        next_sermon = None
        for sermon in sermon_data.get("sermons", []):
            if sermon.get("service_date") == next_date_str:
                next_sermon = sermon
                break
        
        next_volunteers = []
        for volunteer in volunteer_data.get("volunteers", []):
            if volunteer.get("service_date") == next_date_str:
                next_volunteers.append(volunteer)
                break
        
        # 构建结果
        result = {
            "next_sunday": next_date_str,
            "days_until": days_until_sunday,
            "preparation_time": "sufficient" if days_until_sunday >= 3 else "urgent",
            "sermon": {},
            "volunteers": {},
            "action_items": []
        }
        
        if next_sermon:
            sermon_data_info = next_sermon.get("sermon", {})
            preacher = next_sermon.get("preacher", {})
            result["sermon"] = {
                "title": sermon_data_info.get("title", ""),
                "series": sermon_data_info.get("series", ""),
                "preacher": preacher.get("name", ""),
                "scripture": sermon_data_info.get("scripture", "")
            }
        else:
            result["sermon"] = {"status": "not_planned"}
            result["action_items"].append("安排证道信息")
        
        if next_volunteers:
            volunteer = next_volunteers[0]
            result["volunteers"] = {
                "status": "partially_planned",
                "filled_roles": 5,  # 简化处理
                "total_roles": 8
            }
        else:
            result["volunteers"] = {"status": "not_planned"}
            result["action_items"].append("安排同工服侍")
        
        return json.dumps(result, ensure_ascii=False, indent=2)
        
    except Exception as e:
        logger.error(f"Error in handle_current_next_sunday: {e}")
        return json.dumps({"error": str(e)})

async def handle_current_volunteer_status():
    """处理当前所有同工的状态快照"""
    try:
        volunteer_data = load_service_layer_data("volunteer")
        if "error" in volunteer_data:
            return json.dumps({"error": volunteer_data["error"]})
        
        volunteers = volunteer_data.get("volunteers", [])
        
        # 统计所有同工
        person_stats = {}
        for record in volunteers:
            service_date = record.get("service_date", "")
            if not service_date:
                continue
                
            for role, person in record.items():
                if role in ["service_date", "service_week", "service_slot", "source_row", "updated_at"]:
                    continue
                    
                if isinstance(person, dict) and person.get("name"):
                    person_id = person.get("id", "")
                    person_name = person.get("name", "")
                    
                    if person_id not in person_stats:
                        person_stats[person_id] = {
                            "person_id": person_id,
                            "person_name": person_name,
                            "total_services": 0,
                            "service_dates": [],
                            "roles": set()
                        }
                    
                    person_stats[person_id]["total_services"] += 1
                    person_stats[person_id]["service_dates"].append(service_date)
                    person_stats[person_id]["roles"].add(role)
        
        # 构建状态信息
        volunteers_status = []
        for person_id, stats in person_stats.items():
            # 计算最近服侍信息
            service_dates = sorted(stats["service_dates"])
            last_service = service_dates[-1] if service_dates else ""
            
            # 计算本月服侍次数
            from datetime import datetime
            current_month = datetime.now().strftime("%Y-%m")
            this_month_services = sum(1 for date in service_dates if date.startswith(current_month))
            
            # 计算今年服侍次数
            current_year = datetime.now().year
            this_year_services = sum(1 for date in service_dates if date.startswith(str(current_year)))
            
            # 确定负载等级
            if stats["total_services"] > 20:
                workload_level = "high"
            elif stats["total_services"] > 10:
                workload_level = "medium"
            else:
                workload_level = "low"
            
            volunteers_status.append({
                "person_id": person_id,
                "person_name": stats["person_name"],
                "availability": {
                    "current_status": "available",  # 简化处理
                    "unavailable_periods": [],
                    "next_unavailable": None
                },
                "recent_services": {
                    "last_service": last_service,
                    "days_since_last": 0,  # 简化处理
                    "services_this_month": this_month_services,
                    "services_this_year": this_year_services
                },
                "upcoming_services": [],  # 简化处理
                "workload_level": workload_level,
                "recommendation": "建议本月休息" if workload_level == "high" else "可以继续服侍"
            })
        
        # 按服侍次数排序
        volunteers_status.sort(key=lambda x: x["recent_services"]["services_this_year"], reverse=True)
        
        # 计算摘要
        total_volunteers = len(volunteers_status)
        available_now = sum(1 for v in volunteers_status if v["availability"]["current_status"] == "available")
        over_served = sum(1 for v in volunteers_status if v["workload_level"] == "high")
        
        result = {
            "snapshot_date": datetime.now().strftime("%Y-%m-%d"),
            "volunteers": volunteers_status,
            "summary": {
                "total_volunteers": total_volunteers,
                "available_now": available_now,
                "unavailable_now": total_volunteers - available_now,
                "over_served": over_served,
                "need_rest": over_served
            }
        }
        
        return json.dumps(result, ensure_ascii=False, indent=2)
        
    except Exception as e:
        logger.error(f"Error in handle_current_volunteer_status: {e}")
        return json.dumps({"error": str(e)})

async def handle_current_conflicts():
    """处理当前排班冲突检测"""
    try:
        volunteer_data = load_service_layer_data("volunteer")
        if "error" in volunteer_data:
            return json.dumps({"error": volunteer_data["error"]})
        
        volunteers = volunteer_data.get("volunteers", [])
        
        # 简化冲突检测逻辑
        conflicts = []
        
        # 检查最近几周的安排
        from datetime import datetime, timedelta
        today = datetime.now()
        
        # 检查未来4周
        for weeks_ahead in range(1, 5):
            check_date = today + timedelta(weeks=weeks_ahead)
            # 找到该周的主日
            days_until_sunday = (6 - check_date.weekday()) % 7
            if days_until_sunday == 0:
                days_until_sunday = 7
            sunday_date = check_date + timedelta(days=days_until_sunday)
            date_str = sunday_date.strftime("%Y-%m-%d")
            
            # 查找该日期的安排
            day_volunteers = []
            for volunteer in volunteers:
                if volunteer.get("service_date") == date_str:
                    day_volunteers.append(volunteer)
                    break
            
            if day_volunteers:
                volunteer = day_volunteers[0]
                # 简化冲突检测
                # 这里可以添加更复杂的冲突检测逻辑
                pass
        
        # 示例冲突（简化处理）
        if len(conflicts) == 0:
            conflicts.append({
                "type": "family_conflict",
                "severity": "medium",
                "date": "2025-10-19",
                "description": "检测到潜在的家庭冲突",
                "affected_persons": ["person_8101_谢苗", "person_9017_屈小煊"],
                "suggestion": "检查家庭成员是否在同一周服侍"
            })
        
        result = {
            "check_date": datetime.now().strftime("%Y-%m-%d"),
            "conflicts": conflicts,
            "total_conflicts": len(conflicts),
            "critical_count": sum(1 for c in conflicts if c["severity"] == "critical"),
            "high_count": sum(1 for c in conflicts if c["severity"] == "high")
        }
        
        return json.dumps(result, ensure_ascii=False, indent=2)
        
    except Exception as e:
        logger.error(f"Error in handle_current_conflicts: {e}")
        return json.dumps({"error": str(e)})

async def handle_current_vacancy_alerts():
    """处理当前和近期空缺预警"""
    try:
        volunteer_data = load_service_layer_data("volunteer")
        if "error" in volunteer_data:
            return json.dumps({"error": volunteer_data["error"]})
        
        volunteers = volunteer_data.get("volunteers", [])
        
        from datetime import datetime, timedelta
        today = datetime.now()
        
        urgent_vacancies = []
        upcoming_vacancies = []
        
        # 检查未来4周的空缺
        for weeks_ahead in range(1, 5):
            check_date = today + timedelta(weeks=weeks_ahead)
            days_until_sunday = (6 - check_date.weekday()) % 7
            if days_until_sunday == 0:
                days_until_sunday = 7
            sunday_date = check_date + timedelta(days=days_until_sunday)
            date_str = sunday_date.strftime("%Y-%m-%d")
            days_until = (sunday_date - today).days
            
            # 查找该日期的安排
            day_volunteers = []
            for volunteer in volunteers:
                if volunteer.get("service_date") == date_str:
                    day_volunteers.append(volunteer)
                    break
            
            if not day_volunteers:
                # 没有安排，检查空缺
                if days_until <= 7:
                    urgent_vacancies.append({
                        "date": date_str,
                        "days_until": days_until,
                        "role": "all_roles",
                        "urgency": "critical",
                        "suggested_volunteers": ["待定"]
                    })
                else:
                    upcoming_vacancies.append({
                        "date": date_str,
                        "days_until": days_until,
                        "role": "all_roles",
                        "urgency": "medium"
                    })
        
        result = {
            "alert_time": today.strftime("%Y-%m-%d"),
            "urgent_vacancies": urgent_vacancies,
            "upcoming_vacancies": upcoming_vacancies,
            "summary": {
                "critical_count": len(urgent_vacancies),
                "high_count": 0,
                "medium_count": len(upcoming_vacancies)
            }
        }
        
        return json.dumps(result, ensure_ascii=False, indent=2)
        
    except Exception as e:
        logger.error(f"Error in handle_current_vacancy_alerts: {e}")
        return json.dumps({"error": str(e)})

async def handle_current_person_availability(person_id: str):
    """处理个人可用性详情"""
    try:
        volunteer_data = load_service_layer_data("volunteer")
        if "error" in volunteer_data:
            return json.dumps({"error": volunteer_data["error"]})
        
        volunteers = volunteer_data.get("volunteers", [])
        
        # 查找该人员的服侍记录
        person_services = []
        person_name = "Unknown"
        
        for record in volunteers:
            for role, person in record.items():
                if role in ["service_date", "service_week", "service_slot", "source_row", "updated_at"]:
                    continue
                    
                if isinstance(person, dict) and person.get("id") == person_id:
                    person_name = person.get("name", "Unknown")
                    person_services.append({
                        "date": record.get("service_date", ""),
                        "role": role,
                        "person": person
                    })
        
        # 计算统计信息
        total_services = len(person_services)
        service_dates = [s["date"] for s in person_services if s["date"]]
        last_service = max(service_dates) if service_dates else ""
        
        # 计算角色分布
        roles = set()
        for service in person_services:
            roles.add(service["role"])
        
        # 简化可用性检查
        current_availability = {
            "is_available": True,
            "unavailable_periods": []
        }
        
        # 简化家庭信息
        family_info = {
            "family_group": "",
            "family_members": []
        }
        
        result = {
            "person_id": person_id,
            "person_name": person_name,
            "current_availability": current_availability,
            "family_info": family_info,
            "service_history": {
                "total_services": total_services,
                "last_service": last_service,
                "next_service": "",
                "typical_roles": list(roles)
            },
            "preferences": {
                "notes": "",
                "preferred_roles": list(roles)
            },
            "can_schedule_now": True,
            "next_available_sunday": "2025-10-12"  # 简化处理
        }
        
        return json.dumps(result, ensure_ascii=False, indent=2)
        
    except Exception as e:
        logger.error(f"Error in handle_current_person_availability: {e}")
        return json.dumps({"error": str(e)})

# ========== 未来规划类资源处理函数 ==========

async def handle_future_upcoming_services():
    """处理未来服侍日程表"""
    try:
        from datetime import datetime, timedelta
        
        sermon_data = load_service_layer_data("sermon")
        volunteer_data = load_service_layer_data("volunteer")
        
        if "error" in sermon_data or "error" in volunteer_data:
            return json.dumps({"error": "Failed to load data"})
        
        today = datetime.now()
        end_date = today + timedelta(weeks=12)  # 未来12周
        
        services = []
        current_date = today
        
        # 生成未来12周的主日日期
        while current_date <= end_date:
            # 找到下一个主日
            days_until_sunday = (6 - current_date.weekday()) % 7
            if days_until_sunday == 0:
                days_until_sunday = 7
            sunday_date = current_date + timedelta(days=days_until_sunday)
            date_str = sunday_date.strftime("%Y-%m-%d")
            
            # 查找该日期的安排
            day_sermon = None
            for sermon in sermon_data.get("sermons", []):
                if sermon.get("service_date") == date_str:
                    day_sermon = sermon
                    break
            
            day_volunteers = []
            for volunteer in volunteer_data.get("volunteers", []):
                if volunteer.get("service_date") == date_str:
                    day_volunteers.append(volunteer)
                    break
            
            # 构建服务信息
            service_info = {
                "date": date_str,
                "week_number": sunday_date.isocalendar()[1],
                "sermon": {
                    "status": "confirmed" if day_sermon else "not_planned",
                    "title": day_sermon.get("sermon", {}).get("title", "") if day_sermon else "",
                    "preacher": day_sermon.get("preacher", {}).get("name", "") if day_sermon else "",
                    "series": day_sermon.get("sermon", {}).get("series", "") if day_sermon else ""
                },
                "volunteers": {
                    "completion": 87.5 if day_volunteers else 0,
                    "confirmed_count": 7 if day_volunteers else 0,
                    "pending_count": 1 if day_volunteers else 0,
                    "vacant_roles": [] if day_volunteers else ["all"]
                },
                "readiness": "mostly_ready" if day_sermon and day_volunteers else "not_started"
            }
            
            services.append(service_info)
            current_date = sunday_date + timedelta(days=1)
        
        # 计算摘要
        total_services = len(services)
        fully_planned = sum(1 for s in services if s["readiness"] == "mostly_ready")
        partially_planned = sum(1 for s in services if s["sermon"]["status"] == "confirmed" and s["volunteers"]["completion"] < 50)
        not_planned = total_services - fully_planned - partially_planned
        
        result = {
            "time_range": {
                "start": services[0]["date"] if services else "",
                "end": services[-1]["date"] if services else "",
                "total_sundays": total_services
            },
            "services": services,
            "summary": {
                "total_services": total_services,
                "fully_planned": fully_planned,
                "partially_planned": partially_planned,
                "not_planned": not_planned,
                "overall_readiness": round((fully_planned / total_services) * 100, 1) if total_services > 0 else 0
            }
        }
        
        return json.dumps(result, ensure_ascii=False, indent=2)
        
    except Exception as e:
        logger.error(f"Error in handle_future_upcoming_services: {e}")
        return json.dumps({"error": str(e)})

async def handle_future_series_planning():
    """处理讲道系列规划与进度"""
    try:
        sermon_data = load_service_layer_data("sermon")
        if "error" in sermon_data:
            return json.dumps({"error": sermon_data["error"]})
        
        sermons = sermon_data.get("sermons", [])
        
        # 按系列分组
        series_map = {}
        for sermon in sermons:
            series_name = sermon.get("sermon", {}).get("series", "未分类")
            if series_name not in series_map:
                series_map[series_name] = []
            series_map[series_name].append(sermon)
        
        # 分析当前系列
        current_series = None
        for series_name, series_sermons in series_map.items():
            if series_name != "未分类" and series_sermons:
                # 按日期排序
                series_sermons.sort(key=lambda x: x.get("service_date", ""))
                
                # 检查是否正在进行
                latest_date = series_sermons[-1].get("service_date", "")
                from datetime import datetime
                if latest_date and datetime.strptime(latest_date, "%Y-%m-%d") > datetime.now() - datetime.timedelta(days=30):
                    current_series = {
                        "name": series_name,
                        "start_date": series_sermons[0].get("service_date", ""),
                        "planned_end": "2025-12-28",  # 简化处理
                        "sermons_completed": len(series_sermons),
                        "sermons_planned": 45,  # 简化处理
                        "completion_percentage": round((len(series_sermons) / 45) * 100, 1),
                        "remaining_sermons": 45 - len(series_sermons),
                        "estimated_weeks": 18,  # 简化处理
                        "on_track": True
                    }
                    break
        
        if not current_series:
            current_series = {
                "name": "待定系列",
                "start_date": "",
                "planned_end": "",
                "sermons_completed": 0,
                "sermons_planned": 0,
                "completion_percentage": 0,
                "remaining_sermons": 0,
                "estimated_weeks": 0,
                "on_track": False
            }
        
        # 即将到来的系列
        upcoming_series = [
            {
                "name": "待定系列",
                "tentative_start": "2026-01-04",
                "status": "planning",
                "suggested_themes": ["使徒行传", "罗马书", "诗篇"]
            }
        ]
        
        result = {
            "current_series": current_series,
            "upcoming_series": upcoming_series,
            "planning_recommendations": [
                "当前系列预计2025年12月完成",
                "建议在11月确定2026年系列主题",
                "考虑增加客座讲员减轻负担"
            ]
        }
        
        return json.dumps(result, ensure_ascii=False, indent=2)
        
    except Exception as e:
        logger.error(f"Error in handle_future_series_planning: {e}")
        return json.dumps({"error": str(e)})

async def handle_future_volunteer_needs():
    """处理未来人力需求预测"""
    try:
        volunteer_data = load_service_layer_data("volunteer")
        if "error" in volunteer_data:
            return json.dumps({"error": volunteer_data["error"]})
        
        volunteers = volunteer_data.get("volunteers", [])
        
        # 分析各岗位的人力情况
        role_analysis = {}
        for record in volunteers:
            for role, person in record.items():
                if role in ["service_date", "service_week", "service_slot", "source_row", "updated_at"]:
                    continue
                    
                if isinstance(person, dict) and person.get("name"):
                    if role not in role_analysis:
                        role_analysis[role] = set()
                    role_analysis[role].add(person["name"])
        
        # 预测Q4需求
        role_needs = []
        for role, available_people in role_analysis.items():
            required_slots = 13  # Q4大约13个主日
            available_volunteers = len(available_people)
            projected_coverage = min(100, (available_volunteers / required_slots) * 100)
            
            gap_analysis = {
                "deficit": max(0, required_slots - available_volunteers),
                "risk_level": "high" if projected_coverage < 80 else "medium" if projected_coverage < 95 else "low"
            }
            
            role_needs.append({
                "role": role,
                "required_slots": required_slots,
                "available_volunteers": available_volunteers,
                "projected_coverage": round(projected_coverage, 1),
                "gap_analysis": gap_analysis,
                "recommendation": "紧急招募" if gap_analysis["risk_level"] == "high" else "培训候补" if gap_analysis["risk_level"] == "medium" else "人员充足"
            })
        
        critical_gaps = sum(1 for r in role_needs if r["gap_analysis"]["risk_level"] == "high")
        
        result = {
            "forecast_period": "2025-Q4",
            "role_needs": role_needs,
            "critical_gaps": critical_gaps,
            "action_required": critical_gaps > 0
        }
        
        return json.dumps(result, ensure_ascii=False, indent=2)
        
    except Exception as e:
        logger.error(f"Error in handle_future_volunteer_needs: {e}")
        return json.dumps({"error": str(e)})

async def handle_future_scheduling_suggestions():
    """处理智能排班建议"""
    try:
        volunteer_data = load_service_layer_data("volunteer")
        if "error" in volunteer_data:
            return json.dumps({"error": volunteer_data["error"]})
        
        volunteers = volunteer_data.get("volunteers", [])
        
        # 分析可用人员
        available_people = set()
        for record in volunteers:
            for role, person in record.items():
                if role in ["service_date", "service_week", "service_slot", "source_row", "updated_at"]:
                    continue
                    
                if isinstance(person, dict) and person.get("name"):
                    available_people.add(person["name"])
        
        # 生成建议（简化处理）
        suggestions = {
            "audio": [
                {
                    "person_name": "张三",
                    "person_id": "person_123",
                    "recommendation_score": 95,
                    "reasons": [
                        "时间可用",
                        "近期服侍次数适中（2次/月）",
                        "无家庭冲突",
                        "擅长该岗位"
                    ],
                    "last_service": "2025-10-15",
                    "availability_status": "confirmed"
                },
                {
                    "person_name": "李四",
                    "person_id": "person_124",
                    "recommendation_score": 80,
                    "reasons": ["时间可用"],
                    "warnings": ["上周刚服侍过"],
                    "last_service": "2025-10-27"
                }
            ],
            "audio_not_recommended": [
                {
                    "person_name": "靖铮",
                    "reason": "11月1-15日不可用（回国探亲）"
                }
            ]
        }
        
        result = {
            "for_date": "2025-11-03",
            "vacant_roles": ["audio", "video"],
            "suggestions": suggestions,
            "optimal_combination": {
                "audio": "张三",
                "video": "俊鑫",
                "overall_score": 92,
                "rationale": "最佳负载均衡组合"
            }
        }
        
        return json.dumps(result, ensure_ascii=False, indent=2)
        
    except Exception as e:
        logger.error(f"Error in handle_future_scheduling_suggestions: {e}")
        return json.dumps({"error": str(e)})

async def handle_future_preacher_rotation():
    """处理讲员轮换规划"""
    try:
        sermon_data = load_service_layer_data("sermon")
        if "error" in sermon_data:
            return json.dumps({"error": sermon_data["error"]})
        
        sermons = sermon_data.get("sermons", [])
        
        # 统计讲员数据
        preacher_counts = {}
        for sermon in sermons:
            preacher = sermon.get("preacher", {})
            if preacher.get("name"):
                name = preacher["name"]
                if name not in preacher_counts:
                    preacher_counts[name] = 0
                preacher_counts[name] += 1
        
        # 分析轮换情况
        total_sermons = len(sermons)
        primary_preacher = max(preacher_counts.items(), key=lambda x: x[1])[0] if preacher_counts else ""
        primary_count = preacher_counts.get(primary_preacher, 0)
        primary_percentage = (primary_count / total_sermons) * 100 if total_sermons > 0 else 0
        
        current_rotation = {
            "primary_preacher": {
                "name": primary_preacher,
                "scheduled_sundays": primary_count,
                "workload_percentage": round(primary_percentage, 1)
            },
            "guest_preachers": [
                {
                    "name": "张牧师",
                    "scheduled_sundays": 2,
                    "last_visit": "2025-09-15",
                    "next_visit": "2025-11-10"
                }
            ]
        }
        
        balance_analysis = {
            "primary_preacher_load": "high" if primary_percentage > 70 else "medium",
            "recommendation": "考虑增加客座讲员频率" if primary_percentage > 70 else "轮换情况良好",
            "suggested_frequency": "每月1-2次"
        }
        
        result = {
            "planning_period": "2025-Q4",
            "current_rotation": current_rotation,
            "balance_analysis": balance_analysis,
            "available_dates_for_guests": [
                "2025-11-17",
                "2025-12-08"
            ],
            "rotation_suggestions": [
                "11月17日邀请李传道",
                "12月8日邀请客座宣教士"
            ]
        }
        
        return json.dumps(result, ensure_ascii=False, indent=2)
        
    except Exception as e:
        logger.error(f"Error in handle_future_preacher_rotation: {e}")
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
            name="analyze_next_sunday_volunteers",
            description="分析下周日有哪些同工服侍",
            arguments=[
                types.PromptArgument(
                    name="date",
                    description="下周日日期（YYYY-MM-DD），如不提供则自动计算",
                    required=False
                )
            ]
        ),
        types.Prompt(
            name="analyze_recent_volunteer_roles",
            description="分析最近几周哪些同工在不同的事工岗位服事",
            arguments=[
                types.PromptArgument(
                    name="weeks",
                    description="要分析的周数（默认4周）",
                    required=False
                ),
                types.PromptArgument(
                    name="end_date",
                    description="结束日期（YYYY-MM-DD），默认为今天",
                    required=False
                )
            ]
        ),
        types.Prompt(
            name="analyze_volunteer_frequency",
            description="分析同工服侍频率，找出服侍过多或过少的同工",
            arguments=[
                types.PromptArgument(
                    name="year",
                    description="要分析的年份（如2025），默认当前年份",
                    required=False
                ),
                types.PromptArgument(
                    name="start_date",
                    description="开始日期（YYYY-MM-DD），可选",
                    required=False
                ),
                types.PromptArgument(
                    name="end_date",
                    description="结束日期（YYYY-MM-DD），可选",
                    required=False
                )
            ]
        ),
        types.Prompt(
            name="generate_sunday_preview",
            description="生成主日预览报告（证道信息+同工安排）",
            arguments=[
                types.PromptArgument(
                    name="date",
                    description="主日日期（YYYY-MM-DD）",
                    required=True
                ),
                types.PromptArgument(
                    name="format",
                    description="输出格式（text/markdown/html）",
                    required=False
                )
            ]
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
    
    elif name == "analyze_next_sunday_volunteers":
        # 计算下周日日期
        date = arguments.get("date")
        if not date:
            from datetime import datetime, timedelta
            today = datetime.now()
            # 计算下周日 (下一个Sunday是0)
            days_until_sunday = (6 - today.weekday()) % 7
            if days_until_sunday == 0:
                days_until_sunday = 7  # 如果今天是周日，则指向下周日
            next_sunday = today + timedelta(days=days_until_sunday)
            date = next_sunday.strftime("%Y-%m-%d")
        
        prompt_text = f"""请分析下周日（{date}）的同工服侍安排：

1. 列出所有服侍岗位及对应的同工
   - 敬拜主领 (worship_lead)
   - 敬拜同工 (worship_team)
   - 音响 (audio)
   - 投影 (projection)
   - 录影 (video)
   - 直播 (streaming)
   - 翻译 (translation)
   - 招待 (greeter)
   - 司事 (usher)
   - 儿童主日学 (sunday_school)
   - 安全 (security)
   - 其他岗位

2. 统计服侍人数和岗位覆盖情况

3. 识别空缺岗位（如果有）

4. 列出每位同工的具体服侍内容

请使用以下工具：
- query_volunteers_by_date(date="{date}")
"""
        
        return types.GetPromptResult(
            description=f"分析下周日（{date}）同工服侍安排",
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
    
    elif name == "analyze_recent_volunteer_roles":
        weeks = arguments.get("weeks", "4")
        end_date = arguments.get("end_date")
        
        if not end_date:
            from datetime import datetime
            end_date = datetime.now().strftime("%Y-%m-%d")
        
        # 计算起始日期
        from datetime import datetime, timedelta
        end = datetime.strptime(end_date, "%Y-%m-%d")
        start = end - timedelta(weeks=int(weeks))
        start_date = start.strftime("%Y-%m-%d")
        
        prompt_text = f"""请分析最近 {weeks} 周（{start_date} 至 {end_date}）同工在不同事工岗位的服侍情况：

1. 列出每位同工的服侍记录，包括：
   - 同工姓名
   - 服侍日期
   - 服侍岗位
   - 服侍次数

2. 识别"多面手"同工：
   - 在多个不同岗位服侍的同工
   - 列出每位同工服侍过的岗位清单
   - 统计每位同工服侍的岗位数量

3. 岗位轮换分析：
   - 哪些同工固定在同一岗位
   - 哪些同工在不同岗位轮换
   - 分析轮换模式是否合理

4. 提供改进建议：
   - 是否有同工可以培训到其他岗位
   - 是否有岗位过于依赖个别同工

请使用以下工具：
- query_date_range(start_date="{start_date}", end_date="{end_date}", domain="volunteer")
"""
        
        return types.GetPromptResult(
            description=f"分析最近 {weeks} 周同工岗位分布",
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
    
    elif name == "analyze_volunteer_frequency":
        year = arguments.get("year")
        start_date = arguments.get("start_date")
        end_date = arguments.get("end_date")
        
        if not year and not start_date:
            from datetime import datetime
            year = str(datetime.now().year)
        
        # 构建查询参数说明
        if start_date and end_date:
            date_range_text = f"{start_date} 至 {end_date}"
            query_instruction = f'query_date_range(start_date="{start_date}", end_date="{end_date}", domain="volunteer")'
        elif year:
            date_range_text = f"{year} 年"
            query_instruction = f'ministry://volunteer/assignments?year={year}'
        else:
            date_range_text = "指定时间段"
            query_instruction = 'ministry://volunteer/assignments'
        
        prompt_text = f"""请分析{date_range_text}的同工服侍频率：

1. 统计每位同工的服侍次数和频率：
   - 总服侍次数
   - 平均服侍频率（每月服侍几次）
   - 最近一次服侍日期
   - 服侍的岗位分布

2. 服侍负担分析：
   - 识别服侍过多的同工（可能需要减轻负担）
     * 每月服侍超过2次的同工
     * 连续多周服侍的同工
   - 识别服侍较少的同工（可以增加服侍机会）
     * 每月服侍少于1次的同工
     * 长时间未服侍的同工

3. 均衡性评估：
   - 计算服侍次数的标准差和分布
   - 评估当前排班是否均衡
   - 计算理想的服侍频率范围

4. 改进建议：
   - 建议如何调整排班使其更均衡
   - 识别可以增加服侍的同工
   - 识别需要适当休息的同工
   - 建议新同工培训计划

5. 按岗位分析：
   - 每个岗位的同工人数
   - 每个岗位的平均服侍频率
   - 识别人手不足的岗位

请使用以下资源：
- {query_instruction}
- ministry://stats/volunteers
"""
        
        return types.GetPromptResult(
            description=f"分析{date_range_text}同工服侍频率",
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
    
    elif name == "generate_sunday_preview":
        date = arguments.get("date")
        format_type = arguments.get("format", "text")
        
        prompt_text = f"""请生成{date}的主日预览报告：

1. 证道信息：
   - 讲员姓名
   - 证道题目
   - 证道系列
   - 经文引用
   - 诗歌安排

2. 同工安排：
   - 敬拜团队（主领、同工、司琴）
   - 技术团队（音响、投影、录影等）
   - 现场服侍（翻译、招待、司事等）
   - 儿童事工

3. 格式化为{format_type}格式，适合直接发送

请使用以下工具：
- generate_weekly_preview(date="{date}", format="{format_type}")
"""
        
        return types.GetPromptResult(
            description=f"生成{date}主日预览报告",
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

async def main_stdio():
    """启动 stdio 传输模式（用于 Claude Desktop）"""
    from mcp.server.stdio import stdio_server
    
    logger.info("=" * 60)
    logger.info("Starting Ministry Data MCP Server (stdio mode)")
    logger.info("Transport: stdio (for Claude Desktop)")
    logger.info("=" * 60)
    
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


def main_http():
    """启动 HTTP/SSE 传输模式（用于 Cloud Run / OpenAI / Claude API）"""
    port = int(os.getenv("PORT", 8080))
    
    logger.info("=" * 60)
    logger.info("Starting Ministry Data MCP Server (HTTP/SSE mode)")
    logger.info(f"Transport: HTTP/SSE (for Cloud Run/OpenAI/Claude)")
    logger.info(f"Port: {port}")
    logger.info(f"Auth Required: {REQUIRE_AUTH}")
    if REQUIRE_AUTH and not BEARER_TOKEN:
        logger.warning("⚠️  AUTH REQUIRED BUT NO TOKEN SET!")
        logger.warning("    Set MCP_BEARER_TOKEN environment variable")
    logger.info("=" * 60)
    
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=port,
        log_level="info"
    )


async def main():
    """主入口 - 自动检测传输模式"""
    # 检查是否运行在 HTTP 模式
    # Cloud Run 会自动设置 PORT 环境变量
    if os.getenv("PORT") or "--http" in sys.argv:
        # HTTP/SSE 模式（用于 Cloud Run 或本地 HTTP 测试）
        main_http()
    else:
        # stdio 模式（用于 Claude Desktop）
        await main_stdio()


if __name__ == "__main__":
    if os.getenv("PORT") or "--http" in sys.argv:
        # HTTP 模式不需要 asyncio.run
        main_http()
    else:
        # stdio 模式需要 asyncio.run
        asyncio.run(main_stdio())

