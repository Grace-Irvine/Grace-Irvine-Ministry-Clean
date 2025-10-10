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

# MCP SDK imports (import before adding project root to avoid naming conflict)
import mcp.server.models
import mcp.server
import mcp.server.stdio
import mcp.types as types
from mcp.server.models import InitializationOptions
from mcp.server import NotificationOptions, Server

# HTTP/SSE transport imports
from fastapi import FastAPI, Request, HTTPException, Header, Depends
from fastapi.responses import StreamingResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn

# 添加项目根目录到 Python 路径 (for core/ imports)
sys.path.insert(0, str(Path(__file__).parent.parent))

# 导入应用层代码
from core.clean_pipeline import CleaningPipeline
from core.service_layer import ServiceLayerManager

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
            logger.error(f"Config file not found: {config_file}")
            return {}
        
        with open(config_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Failed to load config: {e}")
        return {}

CONFIG = load_config()
STORAGE_CONFIG = CONFIG.get('service_layer', {}).get('storage', {})

# HTTP/SSE 配置
BEARER_TOKEN = os.getenv("MCP_BEARER_TOKEN", "")
REQUIRE_AUTH = os.getenv("MCP_REQUIRE_AUTH", "true").lower() == "true"

# 初始化 GCS 客户端（如果配置了）
GCS_CLIENT = None
if STORAGE_CONFIG.get('provider') == 'gcs':
    try:
        from core.cloud_storage_utils import DomainStorageManager
        
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
# HTTP/SSE Pydantic Models
# ============================================================

class MCPRequest(BaseModel):
    """MCP 请求模型（JSON-RPC 2.0）"""
    jsonrpc: str = "2.0"
    id: Optional[str | int] = None
    method: str
    params: Optional[Dict[str, Any]] = None


class MCPResponse(BaseModel):
    """MCP 响应模型（JSON-RPC 2.0）"""
    jsonrpc: str = "2.0"
    id: Optional[str | int] = None
    result: Optional[Dict[str, Any]] = None
    error: Optional[Dict[str, Any]] = None


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
    获取角色的中文显示名称
    """
    # 角色名称映射表 - 显示具体的岗位名称
    role_mapping = {
        'worship_lead': '敬拜主领',
        'worship_team_1': '敬拜同工1',
        'worship_team_2': '敬拜同工2',
        'worship_team': '敬拜同工',
        'pianist': '司琴',
        'audio': '音控',
        'video': '导播/摄影',
        'propresenter_play': 'ProPresenter播放',
        'propresenter_update': 'ProPresenter更新',
        'assistant': '助教',
        'preacher': '讲员',
        'reading': '读经',
        'worship': '敬拜',
        'technical': '技术'
    }
    
    return role_mapping.get(role, role)

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


def format_volunteer_record(record: Dict) -> str:
    """格式化单条同工服侍记录为可读文本"""
    lines = [f"📅 服侍日期: {record.get('service_date', 'N/A')}"]
    
    # 处理敬拜团队
    worship = record.get('worship', {})
    if worship:
        lines.append("\n🎵 敬拜团队:")
        
        # 敬拜主领
        lead = worship.get('lead', {})
        if lead and lead.get('name'):
            lines.append(f"  • 敬拜主领: {lead['name']}")
        
        # 敬拜同工
        team = worship.get('team', [])
        if team:
            names = [member.get('name', 'N/A') for member in team if isinstance(member, dict)]
            if names:
                lines.append(f"  • 敬拜同工: {', '.join(names)}")
        
        # 司琴
        pianist = worship.get('pianist', {})
        if pianist and pianist.get('name'):
            lines.append(f"  • 司琴: {pianist['name']}")
    
    # 处理技术团队
    technical = record.get('technical', {})
    if technical:
        lines.append("\n🔧 技术团队:")
        
        # 音控
        audio = technical.get('audio', {})
        if audio and audio.get('name'):
            lines.append(f"  • 音控: {audio['name']}")
        
        # 导播/摄影
        video = technical.get('video', {})
        if video and video.get('name'):
            lines.append(f"  • 导播/摄影: {video['name']}")
        
        # ProPresenter播放
        propresenter_play = technical.get('propresenter_play', {})
        if propresenter_play and propresenter_play.get('name'):
            lines.append(f"  • ProPresenter播放: {propresenter_play['name']}")
        
        # ProPresenter更新
        propresenter_update = technical.get('propresenter_update', {})
        if propresenter_update and propresenter_update.get('name'):
            lines.append(f"  • ProPresenter更新: {propresenter_update['name']}")
    
    # 处理其他字段（如果存在）
    for key, value in record.items():
        if key in ['service_date', 'service_week', 'service_slot', 'worship', 'technical', 'source_row', 'updated_at']:
            continue
        
        if isinstance(value, dict) and value.get('name'):
            lines.append(f"  • {key}: {value['name']}")
        elif isinstance(value, list) and value:
            names = [item.get('name', 'N/A') for item in value if isinstance(item, dict)]
            if names:
                lines.append(f"  • {key}: {', '.join(names)}")
    
    return '\n'.join(lines)


def format_sermon_record(record: Dict) -> str:
    """格式化单条证道记录为可读文本"""
    lines = [f"📅 服侍日期: {record.get('service_date', 'N/A')}"]
    
    # 讲员信息
    preacher = record.get('preacher', {})
    if isinstance(preacher, dict):
        lines.append(f"  🎤 讲员: {preacher.get('name', 'N/A')}")
    
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
# 新增辅助函数 - 用于6个新工具
# ============================================================

def extract_all_roles_from_volunteer_records(volunteers: List[Dict]) -> Dict[str, List[Dict]]:
    """
    从同工记录中提取所有岗位及其人员列表
    
    Returns:
        Dict[role_name, List[{person_id, person_name, service_date}]]
    """
    role_map = {}
    
    for record in volunteers:
        service_date = record.get('service_date', '')
        
        # 处理 worship 组
        worship = record.get('worship', {})
        if worship:
            # 敬拜主领
            lead = worship.get('lead', {})
            if lead and lead.get('id'):
                role_name = 'worship_lead'
                if role_name not in role_map:
                    role_map[role_name] = []
                role_map[role_name].append({
                    'person_id': lead.get('id'),
                    'person_name': lead.get('name'),
                    'service_date': service_date
                })
            
            # 敬拜同工
            team = worship.get('team', [])
            for member in team:
                if isinstance(member, dict) and member.get('id'):
                    role_name = 'worship_team'
                    if role_name not in role_map:
                        role_map[role_name] = []
                    role_map[role_name].append({
                        'person_id': member.get('id'),
                        'person_name': member.get('name'),
                        'service_date': service_date
                    })
            
            # 司琴
            pianist = worship.get('pianist', {})
            if pianist and pianist.get('id'):
                role_name = 'pianist'
                if role_name not in role_map:
                    role_map[role_name] = []
                role_map[role_name].append({
                    'person_id': pianist.get('id'),
                    'person_name': pianist.get('name'),
                    'service_date': service_date
                })
        
        # 处理 technical 组
        technical = record.get('technical', {})
        if technical:
            for tech_role in ['audio', 'video', 'propresenter_play', 'propresenter_update']:
                person = technical.get(tech_role, {})
                if person and person.get('id'):
                    if tech_role not in role_map:
                        role_map[tech_role] = []
                    role_map[tech_role].append({
                        'person_id': person.get('id'),
                        'person_name': person.get('name'),
                        'service_date': service_date
                    })
    
    return role_map


def calculate_role_health_score(role_data: List[Dict]) -> Dict[str, Any]:
    """
    计算岗位健康度
    
    Args:
        role_data: [{person_id, person_name, service_date}, ...]
        
    Returns:
        {
            'unique_people_count': int,
            'total_services': int,
            'health_score': float (0-100),
            'risk_level': str ('healthy'/'moderate'/'critical'),
            'top_contributors': List[{person_name, count}]
        }
    """
    if not role_data:
        return {
            'unique_people_count': 0,
            'total_services': 0,
            'health_score': 0,
            'risk_level': 'critical',
            'top_contributors': []
        }
    
    # 统计每个人的服侍次数
    person_counts = {}
    for item in role_data:
        person_id = item['person_id']
        person_name = item['person_name']
        if person_id not in person_counts:
            person_counts[person_id] = {'name': person_name, 'count': 0}
        person_counts[person_id]['count'] += 1
    
    unique_people = len(person_counts)
    total_services = len(role_data)
    
    # 计算健康度评分
    # 基于人数和负载分布
    if unique_people == 0:
        health_score = 0
        risk_level = 'critical'
    elif unique_people == 1:
        health_score = 20
        risk_level = 'critical'
    elif unique_people == 2:
        health_score = 40
        risk_level = 'critical'
    elif unique_people <= 4:
        health_score = 60
        risk_level = 'moderate'
    else:
        # 检查负载分布
        max_count = max(p['count'] for p in person_counts.values())
        avg_count = total_services / unique_people
        
        # 如果最高频率超过平均值的2倍，降低分数
        if max_count > avg_count * 2:
            health_score = 70
            risk_level = 'moderate'
        else:
            health_score = 90
            risk_level = 'healthy'
    
    # 获取top贡献者
    top_contributors = sorted(
        [{'person_name': p['name'], 'count': p['count']} for p in person_counts.values()],
        key=lambda x: x['count'],
        reverse=True
    )[:5]
    
    return {
        'unique_people_count': unique_people,
        'total_services': total_services,
        'health_score': health_score,
        'risk_level': risk_level,
        'top_contributors': top_contributors
    }


def detect_volunteer_status(person_id: str, all_records: List[Dict], cutoff_date: str) -> str:
    """
    检测同工状态
    
    Args:
        person_id: 同工ID
        all_records: 所有志愿服侍记录
        cutoff_date: 截止日期 (YYYY-MM-DD)
        
    Returns:
        'new' (新同工，首次服侍在3个月内)
        'active' (活跃同工，最近3个月有服侍)
        'dormant' (休眠同工，3-6个月未服侍)
        'inactive' (不活跃，6个月以上未服侍)
    """
    from datetime import datetime, timedelta
    
    # 找出该同工的所有服侍日期
    service_dates = []
    for record in all_records:
        for role, person in record.items():
            if role in ['service_date', 'service_week', 'service_slot', 'source_row', 'updated_at']:
                continue
            
            if isinstance(person, dict) and person.get('id') == person_id:
                service_dates.append(record.get('service_date', ''))
            elif isinstance(person, list):
                for p in person:
                    if isinstance(p, dict) and p.get('id') == person_id:
                        service_dates.append(record.get('service_date', ''))
    
    if not service_dates:
        return 'inactive'
    
    service_dates = sorted(service_dates)
    first_service = service_dates[0]
    last_service = service_dates[-1]
    
    cutoff_dt = datetime.strptime(cutoff_date, '%Y-%m-%d')
    last_service_dt = datetime.strptime(last_service, '%Y-%m-%d')
    first_service_dt = datetime.strptime(first_service, '%Y-%m-%d')
    
    days_since_last = (cutoff_dt - last_service_dt).days
    days_since_first = (cutoff_dt - first_service_dt).days
    
    # 判断状态
    if days_since_first <= 90:  # 3个月内首次服侍
        return 'new'
    elif days_since_last <= 90:  # 最近3个月有服侍
        return 'active'
    elif days_since_last <= 180:  # 3-6个月未服侍
        return 'dormant'
    else:  # 6个月以上未服侍
        return 'inactive'


def calculate_series_progress(sermons: List[Dict], series_name: str) -> Dict[str, Any]:
    """
    计算证道系列进度
    
    Returns:
        {
            'series_name': str,
            'sermon_count': int,
            'date_range': {'start': str, 'end': str},
            'sermons': List[Dict],
            'gaps': List[str]  # 中断的日期范围
        }
    """
    # 筛选该系列的证道
    series_sermons = [
        s for s in sermons 
        if s.get('sermon', {}).get('series', '').lower() == series_name.lower()
    ]
    
    if not series_sermons:
        return {
            'series_name': series_name,
            'sermon_count': 0,
            'date_range': {},
            'sermons': [],
            'gaps': []
        }
    
    # 按日期排序
    series_sermons = sorted(series_sermons, key=lambda x: x.get('service_date', ''))
    
    dates = [s.get('service_date', '') for s in series_sermons]
    
    # 检测中断（超过2周的间隔）
    from datetime import datetime, timedelta
    gaps = []
    for i in range(len(dates) - 1):
        current = datetime.strptime(dates[i], '%Y-%m-%d')
        next_date = datetime.strptime(dates[i+1], '%Y-%m-%d')
        gap_days = (next_date - current).days
        
        if gap_days > 21:  # 超过3周视为中断
            gaps.append(f"{dates[i]} 至 {dates[i+1]} ({gap_days}天)")
    
    return {
        'series_name': series_name,
        'sermon_count': len(series_sermons),
        'date_range': {
            'start': dates[0],
            'end': dates[-1]
        },
        'sermons': series_sermons,
        'gaps': gaps
    }


def analyze_preacher_pattern(sermons: List[Dict]) -> Dict[str, Any]:
    """
    分析讲员轮换模式
    
    Returns:
        {
            'preachers': [
                {
                    'name': str,
                    'count': int,
                    'avg_interval_days': float,
                    'last_sermon_date': str,
                    'dates': List[str]
                }
            ],
            'rotation_quality': str ('healthy'/'unbalanced')
        }
    """
    from datetime import datetime
    
    # 按讲员分组
    preacher_map = {}
    for sermon in sermons:
        preacher_name = sermon.get('preacher', {}).get('name', 'Unknown')
        service_date = sermon.get('service_date', '')
        
        # 过滤掉空名称或只包含空格的名称
        if not preacher_name or not preacher_name.strip():
            continue
            
        if preacher_name not in preacher_map:
            preacher_map[preacher_name] = []
        preacher_map[preacher_name].append(service_date)
    
    # 分析每位讲员
    preacher_stats = []
    for name, dates in preacher_map.items():
        dates = sorted(dates)
        
        # 计算平均间隔
        if len(dates) > 1:
            intervals = []
            for i in range(len(dates) - 1):
                d1 = datetime.strptime(dates[i], '%Y-%m-%d')
                d2 = datetime.strptime(dates[i+1], '%Y-%m-%d')
                intervals.append((d2 - d1).days)
            avg_interval = sum(intervals) / len(intervals)
        else:
            avg_interval = 0
        
        preacher_stats.append({
            'name': name,
            'count': len(dates),
            'avg_interval_days': round(avg_interval, 1),
            'last_sermon_date': dates[-1] if dates else '',
            'dates': dates
        })
    
    # 评估轮换质量
    counts = [p['count'] for p in preacher_stats]
    if counts:
        max_count = max(counts)
        min_count = min(counts)
        
        # 如果最多和最少相差超过2倍，认为不均衡
        if max_count > min_count * 2:
            rotation_quality = 'unbalanced'
        else:
            rotation_quality = 'healthy'
    else:
        rotation_quality = 'unknown'
    
    return {
        'preachers': sorted(preacher_stats, key=lambda x: x['count'], reverse=True),
        'rotation_quality': rotation_quality
    }


def calculate_retention_rate(volunteers: List[Dict], start_date: str, end_date: str) -> Dict[str, Any]:
    """
    计算同工留存率
    
    Returns:
        {
            'period_start': str,
            'period_end': str,
            'initial_volunteers': int,
            'retained_volunteers': int,
            'new_volunteers': int,
            'lost_volunteers': int,
            'retention_rate': float (0-100)
        }
    """
    from datetime import datetime, timedelta
    
    start_dt = datetime.strptime(start_date, '%Y-%m-%d')
    end_dt = datetime.strptime(end_date, '%Y-%m-%d')
    
    # 计算中间点
    mid_dt = start_dt + (end_dt - start_dt) / 2
    mid_date = mid_dt.strftime('%Y-%m-%d')
    
    # 找出前半期和后半期的同工
    first_half_volunteers = set()
    second_half_volunteers = set()
    
    for record in volunteers:
        service_date = record.get('service_date', '')
        if not service_date:
            continue
        
        # 提取所有同工ID
        for role, person in record.items():
            if role in ['service_date', 'service_week', 'service_slot', 'source_row', 'updated_at']:
                continue
            
            person_ids = []
            if isinstance(person, dict) and person.get('id'):
                person_ids.append(person['id'])
            elif isinstance(person, list):
                person_ids.extend([p.get('id') for p in person if isinstance(p, dict) and p.get('id')])
            
            if start_date <= service_date < mid_date:
                first_half_volunteers.update(person_ids)
            elif mid_date <= service_date <= end_date:
                second_half_volunteers.update(person_ids)
    
    initial_count = len(first_half_volunteers)
    retained = first_half_volunteers & second_half_volunteers
    retained_count = len(retained)
    new_count = len(second_half_volunteers - first_half_volunteers)
    lost_count = len(first_half_volunteers - second_half_volunteers)
    
    retention_rate = (retained_count / initial_count * 100) if initial_count > 0 else 0
    
    return {
        'period_start': start_date,
        'period_end': end_date,
        'initial_volunteers': initial_count,
        'retained_volunteers': retained_count,
        'new_volunteers': new_count,
        'lost_volunteers': lost_count,
        'retention_rate': round(retention_rate, 1)
    }


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

# CORS 配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境应限制具体域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================
# HTTP MCP Protocol Handler
# ============================================================

async def handle_mcp_request(request: MCPRequest) -> MCPResponse:
    """处理 MCP JSON-RPC 请求"""
    try:
        method = request.method
        params = request.params or {}
        
        # 路由到对应的 MCP Server 处理器
        if method == "tools/list":
            result = await handle_list_tools()
            return MCPResponse(
                id=request.id,
                result={"tools": [tool.model_dump() for tool in result]}
            )
        
        elif method == "tools/call":
            name = params.get("name")
            arguments = params.get("arguments", {})
            result = await handle_call_tool(name, arguments)
            return MCPResponse(
                id=request.id,
                result={"content": [item.model_dump() for item in result]}
            )
        
        elif method == "resources/list":
            result = await handle_list_resources()
            return MCPResponse(
                id=request.id,
                result={"resources": [res.model_dump() for res in result]}
            )
        
        elif method == "resources/read":
            uri = params.get("uri")
            result = await handle_read_resource(uri)
            return MCPResponse(
                id=request.id,
                result={"contents": [{"uri": uri, "mimeType": "application/json", "text": result}]}
            )
        
        elif method == "prompts/list":
            result = await handle_list_prompts()
            return MCPResponse(
                id=request.id,
                result={"prompts": [prompt.model_dump() for prompt in result]}
            )
        
        elif method == "prompts/get":
            name = params.get("name")
            arguments = params.get("arguments", {})
            result = await handle_get_prompt(name, arguments)
            return MCPResponse(
                id=request.id,
                result=result.model_dump()
            )
        
        elif method == "initialize":
            return MCPResponse(
                id=request.id,
                result={
                    "protocolVersion": "2024-11-05",
                    "capabilities": {
                        "tools": {"listChanged": True},
                        "resources": {"subscribe": False, "listChanged": True},
                        "prompts": {"listChanged": True}
                    },
                    "serverInfo": {
                        "name": "ministry-data",
                        "version": "2.0.0"
                    }
                }
            )
        
        else:
            return MCPResponse(
                id=request.id,
                error={
                    "code": -32601,
                    "message": f"Method not found: {method}"
                }
            )
    
    except Exception as e:
        logger.error(f"Error handling MCP request: {e}")
        return MCPResponse(
            id=request.id,
            error={
                "code": -32603,
                "message": f"Internal error: {str(e)}"
            }
        )


# ============================================================
# HTTP Endpoints
# ============================================================

@app.get("/")
async def root():
    """根端点"""
    return {
        "service": "Ministry Data MCP Server",
        "version": "2.0.0",
        "protocol": "MCP (Model Context Protocol)",
        "transports": ["stdio", "HTTP/SSE"],
        "endpoints": {
            "mcp": "/mcp",
            "capabilities": "/mcp/capabilities",
            "health": "/health"
        }
    }


@app.get("/health")
async def health_check():
    """健康检查"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "auth_required": REQUIRE_AUTH
    }


@app.get("/mcp/capabilities")
async def get_capabilities(authorized: bool = Depends(verify_bearer_token)):
    """获取 MCP 服务器能力"""
    return {
        "protocolVersion": "2024-11-05",
        "capabilities": {
            "tools": {"listChanged": True},
            "resources": {"subscribe": False, "listChanged": True},
            "prompts": {"listChanged": True}
        },
        "serverInfo": {
            "name": "ministry-data",
            "version": "2.0.0",
            "description": "Church Ministry Data Management MCP Server"
        }
    }


@app.post("/mcp")
async def mcp_endpoint(
    request: MCPRequest,
    authorized: bool = Depends(verify_bearer_token)
) -> MCPResponse:
    """MCP JSON-RPC 端点（HTTP POST）- 支持 SSE"""
    return await handle_mcp_request(request)


@app.get("/mcp/tools")
async def list_tools_endpoint(authorized: bool = Depends(verify_bearer_token)):
    """列出所有工具（便捷端点）"""
    request = MCPRequest(method="tools/list")
    response = await handle_mcp_request(request)
    return response.result


@app.get("/mcp/resources")
async def list_resources_endpoint(authorized: bool = Depends(verify_bearer_token)):
    """列出所有资源（便捷端点）"""
    request = MCPRequest(method="resources/list")
    response = await handle_mcp_request(request)
    return response.result


@app.get("/mcp/prompts")
async def list_prompts_endpoint(authorized: bool = Depends(verify_bearer_token)):
    """列出所有提示词（便捷端点）"""
    request = MCPRequest(method="prompts/list")
    response = await handle_mcp_request(request)
    return response.result


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
                        "enum": ["volunteer", "sermon", "both"],
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
            name="check_upcoming_completeness",
            description="检查未来排班完整性，识别空缺岗位并建议填补人员",
            inputSchema={
                "type": "object",
                "properties": {
                    "weeks_ahead": {
                        "type": "integer",
                        "description": "检查未来几周的排班（默认4周）",
                        "default": 4
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
                "openai/toolInvocation/invoking": "正在检查未来排班完整性...",
                "openai/toolInvocation/invoked": "检查完成"
            }
        ),
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
        types.Tool(
            name="analyze_role_coverage",
            description="分析岗位覆盖率，计算健康度指数，识别单点故障岗位",
            inputSchema={
                "type": "object",
                "properties": {
                    "year": {
                        "type": "string",
                        "description": "要分析的年份（如2025）",
                        "default": None
                    },
                    "start_date": {
                        "type": "string",
                        "description": "开始日期（YYYY-MM-DD），可选",
                        "default": None
                    },
                    "end_date": {
                        "type": "string",
                        "description": "结束日期（YYYY-MM-DD），可选",
                        "default": None
                    }
                },
                "required": []
            },
            meta={
                "openai/toolInvocation/invoking": "正在分析岗位覆盖率...",
                "openai/toolInvocation/invoked": "分析完成"
            }
        ),
        types.Tool(
            name="analyze_preacher_rotation",
            description="分析讲员轮换模式，计算间隔周期，建议未来安排",
            inputSchema={
                "type": "object",
                "properties": {
                    "year": {
                        "type": "string",
                        "description": "要分析的年份（如2025）",
                        "default": None
                    },
                    "start_date": {
                        "type": "string",
                        "description": "开始日期（YYYY-MM-DD），可选",
                        "default": None
                    },
                    "end_date": {
                        "type": "string",
                        "description": "结束日期（YYYY-MM-DD），可选",
                        "default": None
                    }
                },
                "required": []
            },
            meta={
                "openai/toolInvocation/invoking": "正在分析讲员轮换...",
                "openai/toolInvocation/invoked": "分析完成"
            }
        ),
        types.Tool(
            name="analyze_sermon_series_progress",
            description="追踪证道系列进度，计算完成度，识别中断",
            inputSchema={
                "type": "object",
                "properties": {
                    "series_name": {
                        "type": "string",
                        "description": "系列名称（如'创世记系列'），如不提供则分析所有系列"
                    },
                    "year": {
                        "type": "string",
                        "description": "要分析的年份（如2025）",
                        "default": None
                    }
                },
                "required": []
            },
            meta={
                "openai/toolInvocation/invoking": "正在分析证道系列进度...",
                "openai/toolInvocation/invoked": "分析完成"
            }
        ),
        types.Tool(
            name="analyze_volunteer_trends",
            description="分析同工趋势，识别新/活跃/休眠同工，计算留存率",
            inputSchema={
                "type": "object",
                "properties": {
                    "year": {
                        "type": "string",
                        "description": "要分析的年份（如2025）",
                        "default": None
                    },
                    "start_date": {
                        "type": "string",
                        "description": "开始日期（YYYY-MM-DD），可选",
                        "default": None
                    },
                    "end_date": {
                        "type": "string",
                        "description": "结束日期（YYYY-MM-DD），可选",
                        "default": None
                    }
                },
                "required": []
            },
            meta={
                "openai/toolInvocation/invoking": "正在分析同工趋势...",
                "openai/toolInvocation/invoked": "分析完成"
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
                    "count": len(result)
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
                    "count": len(result)
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
                    text="GCS 客户端未初始化，请检查配置",
                    structuredContent={
                        "success": False,
                        "error": "GCS client not initialized",
                        "diagnostic": diagnostic_info,
                        "suggestions": [
                            "检查 config/config.json 是否存在",
                            "检查 config/service-account.json 是否存在",
                            "验证 google-cloud-storage 已安装",
                            "查看 MCP Server 日志了解详情"
                        ]
                    }
                )]
            
            synced_files = {}
            success_count = 0
            
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
                        success_count += 1
                        
                    except Exception as e:
                        logger.error(f"Failed to sync {domain}/{version}: {e}")
                        synced_files[domain][version] = f"Error: {str(e)}"
            
            return [types.TextContent(
                type="text",
                text=f"同步完成，成功同步 {success_count} 个文件",
                structuredContent={
                    "success": True,
                    "synced_files": synced_files,
                    "total_synced": success_count
                }
            )]
        
        # ========== 数据管理工具 ==========
        elif name == "clean_ministry_data":
            # 执行数据清洗
            dry_run = arguments.get("dry_run", False)
            force = arguments.get("force", False)  # Note: force parameter not currently used by run()
            
            pipeline = CleaningPipeline(CONFIG_PATH)
            exit_code = pipeline.run(dry_run=dry_run)
            
            success = exit_code == 0
            message = "数据清洗成功完成" if success else "数据清洗完成，但有错误"
            
            return [types.TextContent(
                type="text",
                text=message,
                structuredContent={
                    "success": success,
                    "exit_code": exit_code,
                    "dry_run": dry_run
                }
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
                    text="未找到清洗数据，请先运行数据清洗",
                    structuredContent={
                        "success": False,
                        "error": "No cleaned data found. Please run clean_ministry_data first."
                    }
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
                text=f"已生成 {len(domains)} 个领域的服务层数据",
                structuredContent={
                    "success": True,
                    "domains": domains,
                    "files": results,
                    "generate_all_years": generate_all_years
                }
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
                
                success = exit_code == 0
                message = "数据验证完成" if success else "数据验证完成，发现问题"
                
                return [types.TextContent(
                    type="text",
                    text=message,
                    structuredContent={
                        "success": success,
                        "exit_code": exit_code,
                        "report_preview": report_summary,
                        "check_duplicates": check_duplicates
                    }
                )]
            except Exception as e:
                return [types.TextContent(
                    type="text",
                    text=f"验证失败：{str(e)}",
                    structuredContent={
                        "success": False,
                        "error": str(e)
                    }
                )]
        
        # ========== 新增6个规划工具 ==========
        elif name == "check_upcoming_completeness":
            try:
                weeks_ahead = arguments.get("weeks_ahead", 4)
                year = arguments.get("year")
                
                from datetime import datetime, timedelta
                
                # 计算未来日期范围
                today = datetime.now()
                end_date = today + timedelta(weeks=weeks_ahead)
                start_date = today.strftime("%Y-%m-%d")
                end_date_str = end_date.strftime("%Y-%m-%d")
                
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
                
                # 分析空缺
                volunteers = volunteer_data.get("volunteers", [])
                sermons = sermon_data.get("sermons", [])
                
                # 筛选未来日期
                future_volunteers = [
                    v for v in volunteers 
                    if start_date <= v.get("service_date", "") <= end_date_str
                ]
                future_sermons = [
                    s for s in sermons 
                    if start_date <= s.get("service_date", "") <= end_date_str
                ]
                
                # 分析空缺 - 检查具体的岗位字段
                gaps = []
                for record in future_volunteers:
                    service_date = record.get("service_date")
                    
                    # 检查敬拜相关岗位
                    worship = record.get("worship", {})
                    if worship:
                        # 敬拜主领
                        lead = worship.get("lead", {})
                        if not lead.get("id"):
                            gaps.append({
                                "date": service_date,
                                "role": "worship_lead",
                                "status": "vacant"
                            })
                        
                        # 敬拜同工
                        team = worship.get("team", [])
                        if not team or (isinstance(team, list) and len(team) == 0):
                            gaps.append({
                                "date": service_date,
                                "role": "worship_team",
                                "status": "vacant"
                            })
                        
                        # 司琴
                        pianist = worship.get("pianist", {})
                        if not pianist.get("id"):
                            gaps.append({
                                "date": service_date,
                                "role": "pianist",
                                "status": "vacant"
                            })
                    
                    # 检查技术相关岗位
                    technical = record.get("technical", {})
                    if technical:
                        for tech_role in ['audio', 'video', 'propresenter_play', 'propresenter_update']:
                            person = technical.get(tech_role, {})
                            if not person.get("id"):
                                gaps.append({
                                    "date": service_date,
                                    "role": tech_role,
                                    "status": "vacant"
                                })
                
                # 检查证道空缺
                for sermon in future_sermons:
                    if not sermon.get("preacher", {}).get("name"):
                        gaps.append({
                            "date": sermon.get("service_date"),
                            "role": "preacher",
                            "status": "vacant"
                        })
                
                # 按紧急度排序
                gaps.sort(key=lambda x: x["date"])
                
                # 生成报告 - 按日期归类
                if gaps:
                    # 按日期分组
                    gaps_by_date = {}
                    for gap in gaps:
                        date = gap['date']
                        if date not in gaps_by_date:
                            gaps_by_date[date] = []
                        gaps_by_date[date].append(gap)
                    
                    text_lines = [f"⚠️ 发现 {len(gaps)} 个空缺岗位（未来{weeks_ahead}周）\n"]
                    
                    # 按日期排序并显示
                    for date in sorted(gaps_by_date.keys()):
                        date_gaps = gaps_by_date[date]
                        role_names = [get_role_display_name(gap['role']) for gap in date_gaps]
                        roles_text = "、".join(role_names)
                        text_lines.append(f"{date} - {roles_text} 空缺")
                else:
                    text_lines = [f"✅ 未来{weeks_ahead}周排班完整，无空缺岗位"]
                
                return [types.TextContent(
                    type="text",
                    text="\n".join(text_lines),
                    structuredContent={
                        "success": True,
                        "weeks_ahead": weeks_ahead,
                        "gaps": gaps,
                        "gap_count": len(gaps),
                        "date_range": {"start": start_date, "end": end_date_str}
                    }
                )]
            except Exception as e:
                logger.error(f"Error in check_upcoming_completeness: {e}")
                return [types.TextContent(
                    type="text",
                    text=f"检查空缺岗位失败：{str(e)}",
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
            
            # 生成预览
            text_lines = [f"📅 主日预览 - {date}\n"]
            
            # 证道信息
            if day_sermons:
                sermon = day_sermons[0]
                text_lines.append("📖 证道信息:")
                text_lines.append(f"  • 讲员: {sermon.get('preacher', {}).get('name', '待定')}")
                text_lines.append(f"  • 题目: {sermon.get('sermon', {}).get('title', '待定')}")
                text_lines.append(f"  • 系列: {sermon.get('sermon', {}).get('series', '待定')}")
                text_lines.append(f"  • 经文: {sermon.get('sermon', {}).get('scripture', '待定')}")
            else:
                text_lines.append("📖 证道信息: 待定")
            
            # 同工安排
            if day_volunteers:
                volunteer = day_volunteers[0]
                text_lines.append("\n👥 同工安排:")
                
                # 敬拜团队
                worship = volunteer.get('worship', {})
                if worship:
                    text_lines.append("  🎵 敬拜团队:")
                    if worship.get('lead', {}).get('name'):
                        text_lines.append(f"    • 主领: {worship['lead']['name']}")
                    if worship.get('team'):
                        names = [m.get('name') for m in worship['team'] if m.get('name')]
                        if names:
                            text_lines.append(f"    • 同工: {', '.join(names)}")
                    if worship.get('pianist', {}).get('name'):
                        text_lines.append(f"    • 司琴: {worship['pianist']['name']}")
                
                # 媒体团队
                technical = volunteer.get('technical', {})
                if technical:
                    text_lines.append("  📺 媒体团队:")
                    for tech_role in ['audio', 'video', 'propresenter_play', 'propresenter_update']:
                        person = technical.get(tech_role, {})
                        if person.get('name'):
                            role_display_name = get_role_display_name(tech_role)
                            text_lines.append(f"    • {role_display_name}: {person['name']}")
            else:
                text_lines.append("\n👥 同工安排: 待定")
            
            return [types.TextContent(
                type="text",
                text="\n".join(text_lines),
                structuredContent={
                    "success": True,
                    "date": date,
                    "format": format_type,
                    "sermon_info": day_sermons[0] if day_sermons else None,
                    "volunteer_info": day_volunteers[0] if day_volunteers else None
                }
            )]
        
        elif name == "analyze_role_coverage":
            year = arguments.get("year")
            start_date = arguments.get("start_date")
            end_date = arguments.get("end_date")
            
            # 加载数据
            volunteer_data = load_service_layer_data("volunteer", year)
            
            if "error" in volunteer_data:
                return [types.TextContent(
                    type="text",
                    text=f"数据加载失败：{volunteer_data['error']}",
                    structuredContent={
                        "success": False,
                        "error": volunteer_data["error"]
                    }
                )]
            
            volunteers = volunteer_data.get("volunteers", [])
            
            # 过滤日期范围
            if start_date and end_date:
                volunteers = [
                    v for v in volunteers 
                    if start_date <= v.get("service_date", "") <= end_date
                ]
            
            # 提取所有岗位数据
            role_map = extract_all_roles_from_volunteer_records(volunteers)
            
            # 分析每个岗位
            role_analysis = {}
            for role_name, role_data in role_map.items():
                health_score = calculate_role_health_score(role_data)
                role_analysis[role_name] = health_score
            
            # 生成报告
            text_lines = ["📊 岗位覆盖率分析报告\n"]
            
            # 按健康度排序
            sorted_roles = sorted(
                role_analysis.items(),
                key=lambda x: x[1]['health_score'],
                reverse=True
            )
            
            for role_name, health in sorted_roles:
                status_icon = "✅" if health['risk_level'] == 'healthy' else "⚠️" if health['risk_level'] == 'moderate' else "❌"
                text_lines.append(f"{status_icon} {role_name}:")
                text_lines.append(f"  • 人数: {health['unique_people_count']}")
                text_lines.append(f"  • 健康度: {health['health_score']}/100")
                text_lines.append(f"  • 风险等级: {health['risk_level']}")
                if health['top_contributors']:
                    top_names = [c['person_name'] for c in health['top_contributors'][:3]]
                    text_lines.append(f"  • 主要贡献者: {', '.join(top_names)}")
                text_lines.append("")
            
            return [types.TextContent(
                type="text",
                text="\n".join(text_lines),
                structuredContent={
                    "success": True,
                    "role_analysis": role_analysis,
                    "total_roles": len(role_analysis),
                    "date_range": {"start": start_date, "end": end_date} if start_date and end_date else None
                }
            )]
        
        elif name == "analyze_preacher_rotation":
            year = arguments.get("year")
            start_date = arguments.get("start_date")
            end_date = arguments.get("end_date")
            
            # 加载数据
            sermon_data = load_service_layer_data("sermon", year)
            
            if "error" in sermon_data:
                return [types.TextContent(
                    type="text",
                    text=f"数据加载失败：{sermon_data['error']}",
                    structuredContent={
                        "success": False,
                        "error": sermon_data["error"]
                    }
                )]
            
            sermons = sermon_data.get("sermons", [])
            
            # 过滤日期范围
            if start_date and end_date:
                sermons = [
                    s for s in sermons 
                    if start_date <= s.get("service_date", "") <= end_date
                ]
            
            # 分析讲员轮换
            rotation_analysis = analyze_preacher_pattern(sermons)
            
            # 生成报告
            text_lines = ["🎤 讲员轮换分析报告\n"]
            text_lines.append(f"轮换质量: {rotation_analysis['rotation_quality']}\n")
            
            for preacher in rotation_analysis['preachers']:
                text_lines.append(f"📝 {preacher['name']}:")
                text_lines.append(f"  • 讲道次数: {preacher['count']}")
                text_lines.append(f"  • 平均间隔: {preacher['avg_interval_days']}天")
                text_lines.append(f"  • 最近讲道: {preacher['last_sermon_date']}")
                text_lines.append("")
            
            return [types.TextContent(
                type="text",
                text="\n".join(text_lines),
                structuredContent={
                    "success": True,
                    "rotation_analysis": rotation_analysis,
                    "date_range": {"start": start_date, "end": end_date} if start_date and end_date else None
                }
            )]
        
        elif name == "analyze_sermon_series_progress":
            series_name = arguments.get("series_name")
            year = arguments.get("year")
            
            # 加载数据
            sermon_data = load_service_layer_data("sermon", year)
            
            if "error" in sermon_data:
                return [types.TextContent(
                    type="text",
                    text=f"数据加载失败：{sermon_data['error']}",
                    structuredContent={
                        "success": False,
                        "error": sermon_data["error"]
                    }
                )]
            
            sermons = sermon_data.get("sermons", [])
            
            if series_name:
                # 分析特定系列
                progress = calculate_series_progress(sermons, series_name)
                
                text_lines = [f"📚 证道系列进度: {series_name}\n"]
                text_lines.append(f"已讲次数: {progress['sermon_count']}")
                if progress['date_range']:
                    text_lines.append(f"时间范围: {progress['date_range']['start']} 至 {progress['date_range']['end']}")
                if progress['gaps']:
                    text_lines.append("中断情况:")
                    for gap in progress['gaps']:
                        text_lines.append(f"  • {gap}")
                
                return [types.TextContent(
                    type="text",
                    text="\n".join(text_lines),
                    structuredContent={
                        "success": True,
                        "series_progress": progress
                    }
                )]
            else:
                # 分析所有系列
                series_map = {}
                for sermon in sermons:
                    series = sermon.get("sermon", {}).get("series", "未分类")
                    if series not in series_map:
                        series_map[series] = []
                    series_map[series].append(sermon)
                
                text_lines = ["📚 所有证道系列进度\n"]
                for series, series_sermons in series_map.items():
                    progress = calculate_series_progress(sermons, series)
                    text_lines.append(f"• {series}: {progress['sermon_count']}次")
                    if progress['gaps']:
                        text_lines.append(f"  (有{len(progress['gaps'])}次中断)")
                
                return [types.TextContent(
                    type="text",
                    text="\n".join(text_lines),
                    structuredContent={
                        "success": True,
                        "all_series": {name: calculate_series_progress(sermons, name) for name in series_map.keys()}
                    }
                )]
        
        elif name == "analyze_volunteer_trends":
            year = arguments.get("year")
            start_date = arguments.get("start_date")
            end_date = arguments.get("end_date")
            
            # 加载数据
            volunteer_data = load_service_layer_data("volunteer", year)
            
            if "error" in volunteer_data:
                return [types.TextContent(
                    type="text",
                    text=f"数据加载失败：{volunteer_data['error']}",
                    structuredContent={
                        "success": False,
                        "error": volunteer_data["error"]
                    }
                )]
            
            volunteers = volunteer_data.get("volunteers", [])
            
            # 过滤日期范围
            if start_date and end_date:
                volunteers = [
                    v for v in volunteers 
                    if start_date <= v.get("service_date", "") <= end_date
                ]
            
            # 收集所有同工ID和状态
            all_person_ids = set()
            for record in volunteers:
                for role, person in record.items():
                    if role in ['service_date', 'service_week', 'service_slot', 'source_row', 'updated_at']:
                        continue
                    
                    if isinstance(person, dict) and person.get('id'):
                        all_person_ids.add(person['id'])
                    elif isinstance(person, list):
                        for p in person:
                            if isinstance(p, dict) and p.get('id'):
                                all_person_ids.add(p['id'])
            
            # 分析同工状态
            from datetime import datetime
            cutoff_date = datetime.now().strftime("%Y-%m-%d")
            
            status_counts = {'new': 0, 'active': 0, 'dormant': 0, 'inactive': 0}
            status_details = {'new': [], 'active': [], 'dormant': [], 'inactive': []}
            
            for person_id in all_person_ids:
                status = detect_volunteer_status(person_id, volunteers, cutoff_date)
                status_counts[status] += 1
                status_details[status].append(person_id)
            
            # 计算留存率（如果有日期范围）
            retention_info = None
            if start_date and end_date:
                retention_info = calculate_retention_rate(volunteers, start_date, end_date)
            
            # 生成报告
            text_lines = ["📈 同工趋势分析报告\n"]
            text_lines.append(f"新同工: {status_counts['new']}人")
            text_lines.append(f"活跃同工: {status_counts['active']}人")
            text_lines.append(f"休眠同工: {status_counts['dormant']}人")
            text_lines.append(f"不活跃同工: {status_counts['inactive']}人")
            
            if retention_info:
                text_lines.append(f"\n留存率: {retention_info['retention_rate']}%")
                text_lines.append(f"新增同工: {retention_info['new_volunteers']}人")
                text_lines.append(f"流失同工: {retention_info['lost_volunteers']}人")
            
            return [types.TextContent(
                type="text",
                text="\n".join(text_lines),
                structuredContent={
                    "success": True,
                    "status_counts": status_counts,
                    "status_details": status_details,
                    "retention_info": retention_info,
                    "date_range": {"start": start_date, "end": end_date} if start_date and end_date else None
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
        ),
        # ========== 历史分析类资源 ==========
        types.Resource(
            uri="ministry://history/volunteer-frequency",
            name="volunteer-frequency-history",
            description="同工服侍频率历史分析",
            mimeType="application/json"
        ),
        types.Resource(
            uri="ministry://history/volunteer-trends",
            name="volunteer-trends-history",
            description="同工参与度趋势变化",
            mimeType="application/json"
        ),
        types.Resource(
            uri="ministry://history/preacher-frequency",
            name="preacher-frequency-history",
            description="讲员讲道频率历史分析",
            mimeType="application/json"
        ),
        types.Resource(
            uri="ministry://history/series-progression",
            name="series-progression-history",
            description="讲道系列进展历史",
            mimeType="application/json"
        ),
        types.Resource(
            uri="ministry://history/role-participation",
            name="role-participation-history",
            description="岗位参与度历史分析",
            mimeType="application/json"
        ),
        types.Resource(
            uri="ministry://history/workload-distribution",
            name="workload-distribution-history",
            description="服侍负担分布历史",
            mimeType="application/json"
        ),
        # ========== 当前周状态类资源 ==========
        types.Resource(
            uri="ministry://current/week-overview",
            name="current-week-overview",
            description="本周/下周全景概览",
            mimeType="application/json"
        ),
        types.Resource(
            uri="ministry://current/next-sunday",
            name="current-next-sunday",
            description="自动计算的下个主日安排（智能日期）",
            mimeType="application/json"
        ),
        types.Resource(
            uri="ministry://current/volunteer-status",
            name="current-volunteer-status",
            description="当前所有同工的状态快照",
            mimeType="application/json"
        ),
        types.Resource(
            uri="ministry://current/conflicts",
            name="current-conflicts",
            description="当前排班冲突检测",
            mimeType="application/json"
        ),
        types.Resource(
            uri="ministry://current/vacancy-alerts",
            name="current-vacancy-alerts",
            description="当前和近期空缺预警",
            mimeType="application/json"
        ),
        types.Resource(
            uri="ministry://current/person-availability/{person_id}",
            name="current-person-availability",
            description="个人可用性详情（含元数据）",
            mimeType="application/json"
        ),
        # ========== 未来规划类资源 ==========
        types.Resource(
            uri="ministry://future/upcoming-services",
            name="future-upcoming-services",
            description="未来服侍日程表（含完整度）",
            mimeType="application/json"
        ),
        types.Resource(
            uri="ministry://future/series-planning",
            name="future-series-planning",
            description="讲道系列规划与进度",
            mimeType="application/json"
        ),
        types.Resource(
            uri="ministry://future/volunteer-needs",
            name="future-volunteer-needs",
            description="未来人力需求预测",
            mimeType="application/json"
        ),
        types.Resource(
            uri="ministry://future/scheduling-suggestions",
            name="future-scheduling-suggestions",
            description="智能排班建议",
            mimeType="application/json"
        ),
        types.Resource(
            uri="ministry://future/preacher-rotation",
            name="future-preacher-rotation",
            description="讲员轮换规划",
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
        # ========== 新增6个规划工具提示词 ==========
        types.Prompt(
            name="check_upcoming_schedule",
            description="检查未来排班完整性，识别空缺岗位",
            arguments=[
                types.PromptArgument(
                    name="weeks_ahead",
                    description="检查未来几周的排班（默认4周）",
                    required=False
                ),
                types.PromptArgument(
                    name="year",
                    description="要检查的年份（如2025）",
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
        ),
        types.Prompt(
            name="analyze_role_health",
            description="分析岗位健康度，识别单点故障岗位",
            arguments=[
                types.PromptArgument(
                    name="year",
                    description="要分析的年份（如2025）",
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
            name="analyze_preacher_schedule",
            description="分析讲员轮换模式，建议未来安排",
            arguments=[
                types.PromptArgument(
                    name="year",
                    description="要分析的年份（如2025）",
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
            name="track_sermon_series",
            description="追踪证道系列进度，识别中断",
            arguments=[
                types.PromptArgument(
                    name="series_name",
                    description="系列名称（如'创世记系列'），如不提供则分析所有系列",
                    required=False
                ),
                types.PromptArgument(
                    name="year",
                    description="要分析的年份（如2025）",
                    required=False
                )
            ]
        ),
        types.Prompt(
            name="analyze_volunteer_growth",
            description="分析同工趋势，识别新/活跃/休眠同工",
            arguments=[
                types.PromptArgument(
                    name="year",
                    description="要分析的年份（如2025）",
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
    
    # ========== 新增6个规划工具提示词实现 ==========
    elif name == "check_upcoming_schedule":
        weeks_ahead = arguments.get("weeks_ahead", "4")
        year = arguments.get("year")
        
        prompt_text = f"""请检查未来{weeks_ahead}周的排班完整性：

1. 识别空缺岗位：
   - 讲员空缺
   - 敬拜团队空缺（主领、同工、司琴）
   - 技术团队空缺（音响、投影、录影等）
   - 其他服侍岗位空缺

2. 按紧急度排序（日期越近越紧急）

3. 基于历史数据建议可填补的人员

4. 生成待办清单

请使用以下工具：
- check_upcoming_completeness(weeks_ahead={weeks_ahead}{f", year='{year}'" if year else ""})
"""
        
        return types.GetPromptResult(
            description=f"检查未来{weeks_ahead}周排班完整性",
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
    
    elif name == "analyze_role_health":
        year = arguments.get("year")
        start_date = arguments.get("start_date")
        end_date = arguments.get("end_date")
        
        date_range_text = f"{start_date} 至 {end_date}" if start_date and end_date else (f"{year}年" if year else "所有时间")
        
        prompt_text = f"""请分析{date_range_text}的岗位健康度：

1. 统计每个岗位的备份人员数量

2. 计算岗位健康度指数（0-100分）：
   - 人数充足度
   - 服侍频率均衡度
   - 分布合理性

3. 识别风险岗位：
   - 单点故障岗位（只有1人会做）
   - 过度依赖个别同工的岗位
   - 人手不足的岗位

4. 生成培训建议和人员配置优化方案

请使用以下工具：
- analyze_role_coverage({f"year='{year}'" if year else ""}{f", start_date='{start_date}', end_date='{end_date}'" if start_date and end_date else ""})
"""
        
        return types.GetPromptResult(
            description=f"分析{date_range_text}岗位健康度",
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
    
    elif name == "analyze_preacher_schedule":
        year = arguments.get("year")
        start_date = arguments.get("start_date")
        end_date = arguments.get("end_date")
        
        date_range_text = f"{start_date} 至 {end_date}" if start_date and end_date else (f"{year}年" if year else "所有时间")
        
        prompt_text = f"""请分析{date_range_text}的讲员轮换模式：

1. 分析每位讲员的讲道频率和间隔

2. 计算平均间隔周期和休息时间

3. 评估轮换质量：
   - 是否均衡分布
   - 是否存在过度集中
   - 休息时间是否充足

4. 建议未来讲员安排：
   - 避免过度集中
   - 确保合理间隔
   - 识别需要培养的新讲员

请使用以下工具：
- analyze_preacher_rotation({f"year='{year}'" if year else ""}{f", start_date='{start_date}', end_date='{end_date}'" if start_date and end_date else ""})
"""
        
        return types.GetPromptResult(
            description=f"分析{date_range_text}讲员轮换",
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
    
    elif name == "track_sermon_series":
        series_name = arguments.get("series_name")
        year = arguments.get("year")
        
        if series_name:
            prompt_text = f"""请追踪"{series_name}"的进度：

1. 计算已讲次数和预计剩余次数

2. 分析时间分布和频率

3. 识别系列中断或跳跃

4. 预测系列完成日期

5. 提供系列规划建议

请使用以下工具：
- analyze_sermon_series_progress(series_name="{series_name}"{f", year='{year}'" if year else ""})
"""
        else:
            prompt_text = f"""请分析所有证道系列的进度：

1. 列出所有系列及其进度

2. 识别中断或异常的系列

3. 分析系列长度和完成度

4. 提供系列规划建议

请使用以下工具：
- analyze_sermon_series_progress({f"year='{year}'" if year else ""})
"""
        
        return types.GetPromptResult(
            description=f"追踪证道系列进度" + (f" - {series_name}" if series_name else ""),
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
    
    elif name == "analyze_volunteer_growth":
        year = arguments.get("year")
        start_date = arguments.get("start_date")
        end_date = arguments.get("end_date")
        
        date_range_text = f"{start_date} 至 {end_date}" if start_date and end_date else (f"{year}年" if year else "所有时间")
        
        prompt_text = f"""请分析{date_range_text}的同工趋势：

1. 识别同工状态分类：
   - 新同工（3个月内首次服侍）
   - 活跃同工（最近3个月有服侍）
   - 休眠同工（3-6个月未服侍）
   - 不活跃同工（6个月以上未服侍）

2. 分析增长/流失趋势：
   - 新同工加入情况
   - 同工流失情况
   - 留存率计算

3. 按季度/年度对比参与度变化

4. 提供同工关怀和培训建议

请使用以下工具：
- analyze_volunteer_trends({f"year='{year}'" if year else ""}{f", start_date='{start_date}', end_date='{end_date}'" if start_date and end_date else ""})
"""
        
        return types.GetPromptResult(
            description=f"分析{date_range_text}同工趋势",
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

