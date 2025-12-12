#!/usr/bin/env python3
"""
MCP (Model Context Protocol) Server Implementation
提供标准 MCP 协议接口，暴露教会主日事工数据管理工具、资源和提示词

Migrated to FastMCP 2.0
"""

import os
import sys
import json
import logging
import asyncio
from pathlib import Path
from typing import Any, Dict, List, Optional
from datetime import datetime, timedelta

from fastmcp import FastMCP, Context
from fastmcp.types import TextContent, ImageContent, EmbeddedResource
from pydantic import BaseModel

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

# ============================================================
# 配置加载与辅助函数
# ============================================================

def load_config() -> Dict[str, Any]:
    """加载配置文件"""
    try:
        config_file = Path(CONFIG_PATH)
        if not config_file.exists():
            logger.warning(f"Config file not found: {config_file}, using environment variables or defaults")
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
            return default_config
        
        with open(config_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Failed to load config: {e}")
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
if not STORAGE_CONFIG:
    STORAGE_CONFIG = {
        'provider': os.getenv('GCS_PROVIDER', 'gcs'),
        'bucket': os.getenv('GCS_BUCKET', 'grace-irvine-ministry-data'),
        'base_path': os.getenv('GCS_BASE_PATH', 'domains/'),
        'service_account_file': os.getenv('GOOGLE_APPLICATION_CREDENTIALS', '/app/config/service-account.json')
    }

# GCS Client - Lazy Initialization
_GCS_CLIENT = None

def get_gcs_client():
    """Lazily initialize GCS Client to avoid blocking startup"""
    global _GCS_CLIENT
    if _GCS_CLIENT is not None:
        return _GCS_CLIENT
        
    storage_provider = STORAGE_CONFIG.get('provider', 'gcs')
    if storage_provider != 'gcs':
        return None
        
    try:
        sys.path.insert(0, str(PROJECT_ROOT))
        from core.cloud_storage_utils import DomainStorageManager
        
        service_account_file = STORAGE_CONFIG.get('service_account_file')
        if service_account_file:
            if not Path(service_account_file).is_absolute():
                service_account_file = str(PROJECT_ROOT / service_account_file)
            if not Path(service_account_file).exists():
                env_creds = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
                if env_creds and Path(env_creds).exists():
                    service_account_file = env_creds
                else:
                    default_path = '/app/config/service-account.json'
                    if Path(default_path).exists():
                        service_account_file = default_path
                    else:
                        service_account_file = None
        else:
            env_creds = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
            service_account_file = env_creds if env_creds and Path(env_creds).exists() else None
        
        bucket_name = STORAGE_CONFIG.get('bucket') or os.getenv('GCS_BUCKET', 'grace-irvine-ministry-data')
        base_path = STORAGE_CONFIG.get('base_path') or os.getenv('GCS_BASE_PATH', 'domains/')
        
        _GCS_CLIENT = DomainStorageManager(
            bucket_name=bucket_name,
            service_account_file=service_account_file,
            base_path=base_path
        )
        logger.info(f"✅ GCS client initialized successfully: bucket={bucket_name}")
    except Exception as e:
        logger.error(f"❌ Failed to initialize GCS client: {e}", exc_info=True)
        _GCS_CLIENT = False # Mark as failed
        
    return _GCS_CLIENT if _GCS_CLIENT is not False else None


def get_role_display_name(role: str) -> str:
    """获取角色的中文显示名称"""
    columns_mapping = CONFIG.get('columns', {})
    if role in columns_mapping:
        display_name = columns_mapping[role]
        import re
        return re.sub(r'\d+$', '', display_name)
    
    fallback_mapping = {
        'worship': '敬拜部', 'technical': '媒体部', 'education': '儿童部', 'sermon': '讲道部',
        'preacher': '讲员', 'reading': '读经', 'series': '讲道系列', 'sermon_title': '讲道标题',
        'scripture': '经文', 'catechism': '要理问答', 'worship_lead': '敬拜带领',
        'worship_team': '敬拜同工', 'pianist': '司琴', 'songs': '詩歌', 'audio': '音控',
        'video': '导播/摄影', 'propresenter_play': 'ProPresenter 播放+场地布置',
        'propresenter_update': 'ProPresenter 更新', 'video_editor': '视频剪辑',
        'friday_child_ministry': '周五老师', 'sunday_child_assistant': '周日助教',
        'newcomer_reception': '新人接待', 'friday_meal': '周五饭食预备', 'prayer_lead': '祷告会带领'
    }
    
    import re
    base_role = re.sub(r'_?\d+$', '', role)
    if base_role in fallback_mapping:
        return fallback_mapping[base_role]
    return fallback_mapping.get(role, role)

def load_service_layer_data(domain: str, year: Optional[str] = None) -> Dict[str, Any]:
    """加载服务层数据"""
    client = get_gcs_client()
    if client:
        try:
            version = year if year else 'latest'
            data = client.download_domain_data(domain, version)
            data['_data_source'] = 'gcs'
            data['_loaded_at'] = datetime.now().isoformat()
            return data
        except Exception as e:
            logger.warning(f"Failed to load from GCS: {e}")
            
    try:
        data_path = LOGS_DIR / year / f"{domain}_{year}.json" if year else LOGS_DIR / f"{domain}.json"
        if not data_path.exists():
            return {"error": f"Data not found: {domain} (year={year})"}
        with open(data_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        data['_data_source'] = 'local'
        data['_loaded_at'] = datetime.now().isoformat()
        return data
    except Exception as e:
        return {"error": str(e)}

def format_volunteer_record(record: Dict) -> str:
    """格式化同工记录"""
    lines = [f"📅 服侍日期: {record.get('service_date', 'N/A')}"]
    departments = CONFIG.get('departments', {})
    
    # Worship
    worship = record.get('worship', {})
    if worship:
        dept_name = departments.get('worship', {}).get('name', '敬拜团队')
        lines.append(f"\n🎵 {dept_name}:")
        if worship.get('lead', {}).get('name'):
            lines.append(f"  • {get_role_display_name('worship_lead')}: {worship['lead']['name']}")
        
        team = worship.get('team', [])
        names = [m.get('name') for m in team if isinstance(m, dict) and m.get('name')]
        if names:
            lines.append(f"  • {get_role_display_name('worship_team')}: {', '.join(names)}")
            
        if worship.get('pianist', {}).get('name'):
            lines.append(f"  • {get_role_display_name('pianist')}: {worship['pianist']['name']}")

    # Technical
    technical = record.get('technical', {})
    if technical:
        dept_name = departments.get('technical', {}).get('name', '技术团队')
        tech_lines = []
        for role in ['audio', 'video', 'propresenter_play', 'propresenter_update', 'video_editor']:
            p = technical.get(role, {})
            if p and p.get('name'):
                tech_lines.append(f"  • {get_role_display_name(role)}: {p['name']}")
        if tech_lines:
            lines.append(f"\n🔧 {dept_name}:")
            lines.extend(tech_lines)

    # Education
    education = record.get('education', {})
    if education:
        dept_name = departments.get('education', {}).get('name', '儿童部')
        edu_lines = []
        p = education.get('friday_child_ministry', {})
        if p and p.get('name'):
            edu_lines.append(f"  • {get_role_display_name('friday_child_ministry')}: {p['name']}")
        
        assistants = education.get('sunday_child_assistants', [])
        names = [a.get('name') for a in assistants if isinstance(a, dict) and a.get('name')]
        if names:
            edu_lines.append(f"  • {get_role_display_name('sunday_child_assistant')}: {', '.join(names)}")
            
        if edu_lines:
            lines.append(f"\n👶 {dept_name}:")
            lines.extend(edu_lines)

    # Outreach
    outreach = record.get('outreach', {})
    if outreach:
        dept_name = departments.get('outreach', {}).get('name', '外展联络')
        out_lines = []
        for r in ['newcomer_reception_1', 'newcomer_reception_2']:
            p = outreach.get(r, {})
            if p and p.get('name'):
                out_lines.append(f"  • {get_role_display_name(r)}: {p['name']}")
        if out_lines:
            lines.append(f"\n🤝 {dept_name}:")
            lines.extend(out_lines)
            
    return '\n'.join(lines)

def format_sermon_record(record: Dict) -> str:
    """格式化证道记录"""
    lines = [f"📅 服侍日期: {record.get('service_date', 'N/A')}"]
    
    preacher = record.get('preacher', {})
    if preacher.get('name'):
        lines.append(f"  🎤 {get_role_display_name('preacher')}: {preacher['name']}")
        
    reading = record.get('reading', {})
    if reading.get('name'):
        lines.append(f"  📖 {get_role_display_name('reading')}: {reading['name']}")
        
    sermon = record.get('sermon', {})
    if sermon:
        if sermon.get('series'): lines.append(f"  📚 系列: {sermon['series']}")
        if sermon.get('title'): lines.append(f"  📖 标题: {sermon['title']}")
        if sermon.get('scripture'): lines.append(f"  📜 经文: {sermon['scripture']}")
        
    songs = record.get('songs', [])
    if songs:
        lines.append(f"  🎵 诗歌: {', '.join(songs)}")
        
    return '\n'.join(lines)

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
# FastMCP Server Definition
# ============================================================

mcp = FastMCP(
    "ministry-data-mcp",
    dependencies=["pandas", "google-auth", "google-api-python-client"]
)

# ============================================================
# Tools
# ============================================================

@mcp.tool()
def query_volunteers_by_date(date: str, year: str = None) -> str:
    """查询指定日期的同工服侍安排（如：下个主日的服侍人员）
    
    Args:
        date: 日期（格式：YYYY-MM-DD），如 '2025-10-12'
        year: 可选：指定年份（如 '2025'），默认使用 latest
    """
    data = load_service_layer_data("volunteer", year)
    if "error" in data:
        return f"查询失败：{data['error']}"
    
    volunteers = data.get("volunteers", [])
    result = [v for v in volunteers if v.get("service_date", "").startswith(date)]
    
    if result:
        text_lines = [f"✅ 找到 {len(result)} 条同工服侍记录（{date}）\n"]
        for i, record in enumerate(result, 1):
            text_lines.append(f"\n记录 {i}:")
            text_lines.append(format_volunteer_record(record))
        return '\n'.join(text_lines)
    else:
        return f"❌ 未找到 {date} 的同工服侍记录"

@mcp.tool()
def query_sermon_by_date(date: str, year: str = None) -> str:
    """查询指定日期的证道信息（讲员、题目、经文等）
    
    Args:
        date: 日期（格式：YYYY-MM-DD）
        year: 可选：指定年份
    """
    data = load_service_layer_data("sermon", year)
    if "error" in data:
        return f"查询失败：{data['error']}"
        
    sermons = data.get("sermons", [])
    result = [s for s in sermons if s.get("service_date", "").startswith(date)]
    
    if result:
        text_lines = [f"✅ 找到 {len(result)} 条证道记录（{date}）\n"]
        for i, record in enumerate(result, 1):
            text_lines.append(f"\n记录 {i}:")
            text_lines.append(format_sermon_record(record))
        return '\n'.join(text_lines)
    else:
        return f"❌ 未找到 {date} 的证道记录"

@mcp.tool()
def query_date_range(start_date: str, end_date: str, domain: str = "both") -> str:
    """查询一段时间范围内的所有服侍安排
    
    Args:
        start_date: 开始日期（YYYY-MM-DD）
        end_date: 结束日期（YYYY-MM-DD）
        domain: 查询的域，可选 ["volunteer", "sermon", "worship", "both"]
    """
    text_lines = [f"✅ 查询范围: {start_date} 至 {end_date}\n"]
    total_count = 0
    
    # Volunteer
    if domain in ["volunteer", "both"]:
        data = load_service_layer_data("volunteer")
        if "error" not in data:
            filtered = [v for v in data.get("volunteers", []) if start_date <= v.get("service_date", "") <= end_date]
            total_count += len(filtered)
            text_lines.append(f"\n📊 同工服侍记录: {len(filtered)} 条")
            for i, record in enumerate(filtered, 1):
                text_lines.append(f"\n  记录 {i}:")
                text_lines.append("  " + format_volunteer_record(record).replace("\n", "\n  "))

    # Sermon
    if domain in ["sermon", "both"]:
        data = load_service_layer_data("sermon")
        if "error" not in data:
            filtered = [s for s in data.get("sermons", []) if start_date <= s.get("service_date", "") <= end_date]
            total_count += len(filtered)
            text_lines.append(f"\n\n📖 证道记录: {len(filtered)} 条")
            for i, record in enumerate(filtered, 1):
                text_lines.append(f"\n  记录 {i}:")
                text_lines.append("  " + format_sermon_record(record).replace("\n", "\n  "))
                
    text_lines.append(f"\n\n📈 总计: {total_count} 条记录")
    return '\n'.join(text_lines)

@mcp.tool()
def generate_weekly_preview(date: str = None, format: str = "text", year: str = None) -> str:
    """生成指定日期的主日预览报告（证道信息+同工安排），默认生成下一个周日
    
    Args:
        date: 日期（格式：YYYY-MM-DD），可选，默认自动生成下一个周日
        format: 输出格式 ["text", "markdown", "html"]
        year: 可选：指定年份
    """
    if not date:
        today = datetime.now()
        days_until_sunday = (6 - today.weekday()) % 7
        if days_until_sunday == 0: days_until_sunday = 7
        next_sunday = today + timedelta(days=days_until_sunday)
        date = next_sunday.strftime("%Y-%m-%d")
        
    volunteer_data = load_service_layer_data("volunteer", year)
    sermon_data = load_service_layer_data("sermon", year)
    
    if "error" in volunteer_data or "error" in sermon_data:
        return "数据加载失败，请检查数据源"
        
    day_volunteers = [v for v in volunteer_data.get("volunteers", []) if v.get("service_date", "").startswith(date)]
    day_sermons = [s for s in sermon_data.get("sermons", []) if s.get("service_date", "").startswith(date)]
    
    sermon = day_sermons[0] if day_sermons else {}
    volunteer = day_volunteers[0] if day_volunteers else {}

    # Helper to get display name safely
    def get_name(obj):
        if not obj: return ""
        if isinstance(obj, str): return obj
        return obj.get("name", "")

    if format == "html":
        html = [f"<h3>主日预览 {date}</h3>"]
        
        html.append("<h4>📖 证道信息</h4>")
        if sermon:
            html.append("<ul>")
            preacher = get_name(sermon.get('preacher'))
            if preacher: html.append(f"<li>🎤 {get_role_display_name('preacher')}: {preacher}</li>")
            
            reading = get_name(sermon.get('reading'))
            if reading: html.append(f"<li>📖 {get_role_display_name('reading')}: {reading}</li>")
            
            sermon_info = sermon.get('sermon', {})
            if sermon_info.get('series'): html.append(f"<li>📚 系列: {sermon_info['series']}</li>")
            if sermon_info.get('title'): html.append(f"<li>📖 标题: {sermon_info['title']}</li>")
            if sermon_info.get('scripture'): html.append(f"<li>📜 经文: {sermon_info['scripture']}</li>")
            
            songs = sermon.get('songs', [])
            if songs: html.append(f"<li>🎵 诗歌: {', '.join(songs)}</li>")
            html.append("</ul>")
        else:
            html.append("<p>待定</p>")
            
        html.append("<h4>👥 同工安排</h4>")
        if volunteer:
            html.append("<ul>")
            # Reuse logic from format_volunteer_record but output HTML
            departments = CONFIG.get('departments', {})
            
            # Worship
            worship = volunteer.get('worship', {})
            if worship:
                dept_name = departments.get('worship', {}).get('name', '敬拜团队')
                html.append(f"<li><strong>🎵 {dept_name}</strong><ul>")
                lead = get_name(worship.get('lead'))
                if lead: html.append(f"<li>{get_role_display_name('worship_lead')}: {lead}</li>")
                
                team = worship.get('team', [])
                team_names = [get_name(m) for m in team if get_name(m)]
                if team_names: html.append(f"<li>{get_role_display_name('worship_team')}: {', '.join(team_names)}</li>")
                
                pianist = get_name(worship.get('pianist'))
                if pianist: html.append(f"<li>{get_role_display_name('pianist')}: {pianist}</li>")
                html.append("</ul></li>")

            # Technical
            technical = volunteer.get('technical', {})
            if technical:
                dept_name = departments.get('technical', {}).get('name', '技术团队')
                html.append(f"<li><strong>🔧 {dept_name}</strong><ul>")
                for role in ['audio', 'video', 'propresenter_play', 'propresenter_update', 'video_editor']:
                    p_name = get_name(technical.get(role))
                    if p_name: html.append(f"<li>{get_role_display_name(role)}: {p_name}</li>")
                html.append("</ul></li>")
                
            # Education
            education = volunteer.get('education', {})
            if education:
                dept_name = departments.get('education', {}).get('name', '儿童部')
                html.append(f"<li><strong>👶 {dept_name}</strong><ul>")
                friday = get_name(education.get('friday_child_ministry'))
                if friday: html.append(f"<li>{get_role_display_name('friday_child_ministry')}: {friday}</li>")
                
                assistants = education.get('sunday_child_assistants', [])
                asst_names = [get_name(a) for a in assistants if get_name(a)]
                if asst_names: html.append(f"<li>{get_role_display_name('sunday_child_assistant')}: {', '.join(asst_names)}</li>")
                html.append("</ul></li>")
                
            # Outreach
            outreach = volunteer.get('outreach', {})
            if outreach:
                dept_name = departments.get('outreach', {}).get('name', '外展联络')
                html.append(f"<li><strong>🤝 {dept_name}</strong><ul>")
                for r in ['newcomer_reception_1', 'newcomer_reception_2']:
                    p_name = get_name(outreach.get(r))
                    if p_name: html.append(f"<li>{get_role_display_name(r)}: {p_name}</li>")
                html.append("</ul></li>")
            
            html.append("</ul>")
        else:
            html.append("<p>待定</p>")
            
        return "".join(html)

    elif format == "markdown":
        md = [f"### 主日预览 {date}\n"]
        
        md.append("#### 📖 证道信息")
        if sermon:
            preacher = get_name(sermon.get('preacher'))
            if preacher: md.append(f"* **{get_role_display_name('preacher')}**: {preacher}")
            
            reading = get_name(sermon.get('reading'))
            if reading: md.append(f"* **{get_role_display_name('reading')}**: {reading}")
            
            sermon_info = sermon.get('sermon', {})
            if sermon_info.get('series'): md.append(f"* **系列**: {sermon_info['series']}")
            if sermon_info.get('title'): md.append(f"* **标题**: {sermon_info['title']}")
            if sermon_info.get('scripture'): md.append(f"* **经文**: {sermon_info['scripture']}")
            
            songs = sermon.get('songs', [])
            if songs: md.append(f"* **诗歌**: {', '.join(songs)}")
        else:
            md.append("待定")
        md.append("")
            
        md.append("#### 👥 同工安排")
        if volunteer:
            departments = CONFIG.get('departments', {})
            
            # Worship
            worship = volunteer.get('worship', {})
            if worship:
                dept_name = departments.get('worship', {}).get('name', '敬拜团队')
                md.append(f"* **🎵 {dept_name}**")
                lead = get_name(worship.get('lead'))
                if lead: md.append(f"  * {get_role_display_name('worship_lead')}: {lead}")
                
                team = worship.get('team', [])
                team_names = [get_name(m) for m in team if get_name(m)]
                if team_names: md.append(f"  * {get_role_display_name('worship_team')}: {', '.join(team_names)}")
                
                pianist = get_name(worship.get('pianist'))
                if pianist: md.append(f"  * {get_role_display_name('pianist')}: {pianist}")

            # Technical
            technical = volunteer.get('technical', {})
            if technical:
                dept_name = departments.get('technical', {}).get('name', '技术团队')
                md.append(f"* **🔧 {dept_name}**")
                for role in ['audio', 'video', 'propresenter_play', 'propresenter_update', 'video_editor']:
                    p_name = get_name(technical.get(role))
                    if p_name: md.append(f"  * {get_role_display_name(role)}: {p_name}")
                
            # Education
            education = volunteer.get('education', {})
            if education:
                dept_name = departments.get('education', {}).get('name', '儿童部')
                md.append(f"* **👶 {dept_name}**")
                friday = get_name(education.get('friday_child_ministry'))
                if friday: md.append(f"  * {get_role_display_name('friday_child_ministry')}: {friday}")
                
                assistants = education.get('sunday_child_assistants', [])
                asst_names = [get_name(a) for a in assistants if get_name(a)]
                if asst_names: md.append(f"  * {get_role_display_name('sunday_child_assistant')}: {', '.join(asst_names)}")
                
            # Outreach
            outreach = volunteer.get('outreach', {})
            if outreach:
                dept_name = departments.get('outreach', {}).get('name', '外展联络')
                md.append(f"* **🤝 {dept_name}**")
                for r in ['newcomer_reception_1', 'newcomer_reception_2']:
                    p_name = get_name(outreach.get(r))
                    if p_name: md.append(f"  * {get_role_display_name(r)}: {p_name}")
        else:
            md.append("待定")
            
        return "\n".join(md)

    else:
        # Default text format
        lines = [f"=== 主日预览 {date} ==="]
        
        if sermon:
            lines.append("\n📖 证道信息:")
            lines.append(format_sermon_record(sermon))
        else:
            lines.append("\n📖 证道信息: 待定")
            
        if volunteer:
            lines.append("\n👥 同工安排:")
            lines.append(format_volunteer_record(volunteer))
        else:
            lines.append("\n👥 同工安排: 待定")
            
        return '\n'.join(lines)

@mcp.tool()
def get_volunteer_service_counts(year: str = None, sort_by: str = "count", role: str = None, min_count: int = None, max_count: int = None) -> str:
    """根据同工名字生成服侍次数统计
    
    Args:
        year: 可选：指定年份
        sort_by: 排序方式：'count' 按服侍次数降序，'name' 按姓名排序
        role: 可选：按岗位筛选 (如 'worship_lead', 'pianist', 'audio' 等)
        min_count: 可选：最小服侍次数
        max_count: 可选：最大服侍次数
    """
    data = load_service_layer_data("volunteer", year)
    if "error" in data:
        return f"加载数据失败：{data['error']}"
        
    volunteers = data.get("volunteers", [])
    
    counts = {}
    for record in volunteers:
        # Define a helper to process a person object/list for a given role key
        def process_role(role_key, person_obj):
            if not person_obj: return
            
            # Filter if role is specified
            if role and role != role_key:
                return

            if isinstance(person_obj, list):
                for p in person_obj:
                    if isinstance(p, dict) and p.get('name'):
                        name = p['name']
                        counts[name] = counts.get(name, 0) + 1
            elif isinstance(person_obj, dict) and person_obj.get('name'):
                name = person_obj['name']
                counts[name] = counts.get(name, 0) + 1

        # Map JSON structure to role keys
        worship = record.get('worship', {})
        process_role('worship_lead', worship.get('lead'))
        process_role('worship_team', worship.get('team'))
        process_role('pianist', worship.get('pianist'))
        
        technical = record.get('technical', {})
        process_role('audio', technical.get('audio'))
        process_role('video', technical.get('video'))
        process_role('propresenter_play', technical.get('propresenter_play'))
        process_role('propresenter_update', technical.get('propresenter_update'))
        process_role('video_editor', technical.get('video_editor'))

        education = record.get('education', {})
        process_role('friday_child_ministry', education.get('friday_child_ministry'))
        process_role('sunday_child_assistant', education.get('sunday_child_assistants'))
        
        outreach = record.get('outreach', {})
        process_role('newcomer_reception', outreach.get('newcomer_reception_1'))
        process_role('newcomer_reception', outreach.get('newcomer_reception_2'))
        
        meal = record.get('meal', {})
        process_role('friday_meal', meal.get('friday_meal'))
        
        prayer = record.get('prayer', {})
        process_role('prayer_lead', prayer.get('prayer_lead'))
        
    # 过滤与排序
    result = []
    for name, count in counts.items():
        if min_count is not None and count < min_count: continue
        if max_count is not None and count > max_count: continue
        result.append({"name": name, "count": count})
        
    if sort_by == "count":
        result.sort(key=lambda x: x["count"], reverse=True)
    else:
        result.sort(key=lambda x: x["name"])
    
    title_suffix = f" - {role}" if role else ""
    lines = [f"📊 同工服侍统计{title_suffix} (共 {len(result)} 人)"]
    for r in result:
        lines.append(f"{r['name']}: {r['count']} 次")
        
    return '\n'.join(lines)

# ============================================================
# Resources
# ============================================================

@mcp.resource("ministry://sermon/records")
def get_sermon_records() -> str:
    """证道域记录"""
    data = load_service_layer_data("sermon")
    return json.dumps(data, ensure_ascii=False, indent=2)

@mcp.resource("ministry://sermon/by-preacher/{preacher_name}")
def get_sermons_by_preacher(preacher_name: str) -> str:
    """按讲员查询证道"""
    data = load_service_layer_data("sermon")
    sermons = [s for s in data.get("sermons", []) 
               if s.get("preacher", {}).get("name") == preacher_name]
    return json.dumps(sermons, ensure_ascii=False, indent=2)

@mcp.resource("ministry://sermon/series")
def get_sermon_series() -> str:
    """讲道系列信息和进度"""
    data = load_service_layer_data("sermon")
    sermons = data.get("sermons", [])
    series_map = {}
    for sermon in sermons:
        series = sermon.get("sermon", {}).get("series", "未分类")
        if series not in series_map:
            series_map[series] = []
        series_map[series].append(sermon)
    
    series_list = [
        {"name": name, "count": len(sermons), "sermons": sermons}
        for name, sermons in series_map.items()
    ]
    return json.dumps({"total_series": len(series_list), "series": series_list}, ensure_ascii=False, indent=2)

@mcp.resource("ministry://volunteer/assignments")
def get_volunteer_assignments() -> str:
    """同工服侍安排"""
    data = load_service_layer_data("volunteer")
    return json.dumps(data, ensure_ascii=False, indent=2)

@mcp.resource("ministry://volunteer/by-person/{person_id}")
def get_volunteer_by_person(person_id: str) -> str:
    """按人员查询服侍记录"""
    data = load_service_layer_data("volunteer")
    volunteers = data.get("volunteers", [])
    person_records = get_person_records(volunteers, person_id)
    return json.dumps({
        "person_identifier": person_id,
        "records": person_records,
        "total_count": len(person_records)
    }, ensure_ascii=False, indent=2)

@mcp.resource("ministry://volunteer/availability/{year_month}")
def get_volunteer_availability(year_month: str) -> str:
    """查询同工空缺"""
    data = load_service_layer_data("volunteer")
    volunteers = filter_by_date(data.get("volunteers", []), year_month)
    gaps = []
    for record in volunteers:
        service_date = record.get("service_date")
        for role, person in record.items():
            if role != "service_date" and not person:
                gaps.append({"service_date": service_date, "role": role, "status": "vacant"})
    return json.dumps({"year_month": year_month, "gaps": gaps, "total_gaps": len(gaps)}, ensure_ascii=False, indent=2)

@mcp.resource("ministry://stats/summary")
def get_stats_summary() -> str:
    """综合统计"""
    sermon = load_service_layer_data("sermon")
    volunteer = load_service_layer_data("volunteer")
    return json.dumps({
        "sermon_stats": sermon.get("metadata", {}),
        "volunteer_stats": volunteer.get("metadata", {})
    }, ensure_ascii=False, indent=2)

@mcp.resource("ministry://stats/preachers")
def get_stats_preachers() -> str:
    """讲员统计"""
    data = load_service_layer_data("sermon")
    sermons = data.get("sermons", [])
    preacher_map = {}
    for sermon in sermons:
        preacher = sermon.get("preacher", {})
        name = preacher.get("name", "Unknown")
        if name not in preacher_map:
            preacher_map[name] = {"name": name, "count": 0}
        preacher_map[name]["count"] += 1
    return json.dumps({"total_preachers": len(preacher_map), "preachers": list(preacher_map.values())}, ensure_ascii=False, indent=2)

@mcp.resource("ministry://stats/volunteers")
def get_stats_volunteers() -> str:
    """同工统计"""
    data = load_service_layer_data("volunteer")
    volunteers = data.get("volunteers", [])
    person_map = {}
    for record in volunteers:
        for role, person in record.items():
            if role != "service_date" and isinstance(person, dict):
                person_id = person.get("id", "unknown")
                if person_id not in person_map:
                    person_map[person_id] = {"id": person_id, "name": person.get("name"), "count": 0, "roles": []}
                person_map[person_id]["count"] += 1
                person_map[person_id]["roles"].append(role)
    return json.dumps({"total_volunteers": len(person_map), "volunteers": list(person_map.values())}, ensure_ascii=False, indent=2)

@mcp.resource("ministry://config/aliases")
def get_config_aliases() -> str:
    """别名映射配置"""
    try:
        with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
            config = json.load(f)
        return json.dumps({
            "sheets_url": config.get("data_sources", {}).get("aliases_sheet_url", ""),
            "range": config.get("data_sources", {}).get("aliases_range", "Aliases!A:C")
        }, ensure_ascii=False, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)}, ensure_ascii=False, indent=2)

@mcp.resource("ministry://current/week-overview")
def get_current_week_overview() -> str:
    """本周全景概览"""
    today = datetime.now()
    days_since_sunday = (today.weekday() + 1) % 7
    current_sunday = today - timedelta(days=days_since_sunday)
    date_str = current_sunday.strftime("%Y-%m-%d")
    
    s_data = load_service_layer_data("sermon")
    v_data = load_service_layer_data("volunteer")
    
    sermon = next((s for s in s_data.get("sermons", []) if s.get("service_date") == date_str), None)
    volunteer = next((v for v in v_data.get("volunteers", []) if v.get("service_date") == date_str), None)
    
    return json.dumps({
        "date": date_str,
        "sermon": sermon,
        "volunteer": volunteer
    }, ensure_ascii=False, indent=2)

@mcp.resource("ministry://current/next-sunday")
def get_current_next_sunday() -> str:
    """下个主日预览"""
    today = datetime.now()
    days_until = (6 - today.weekday()) % 7
    if days_until == 0: days_until = 7
    next_sunday = today + timedelta(days=days_until)
    date_str = next_sunday.strftime("%Y-%m-%d")
    
    s_data = load_service_layer_data("sermon")
    v_data = load_service_layer_data("volunteer")
    
    sermon = next((s for s in s_data.get("sermons", []) if s.get("service_date") == date_str), None)
    volunteer = next((v for v in v_data.get("volunteers", []) if v.get("service_date") == date_str), None)
    
    return json.dumps({
        "date": date_str,
        "sermon": sermon,
        "volunteer": volunteer
    }, ensure_ascii=False, indent=2)

# ============================================================
# Prompts
# ============================================================

@mcp.prompt()
def analyze_preaching_schedule(year: str = "2024", focus: str = "全面") -> str:
    """分析讲道安排"""
    return f"""请分析 {year} 年的讲道安排：
1. 列出所有讲道系列及其进度
2. 统计每位讲员的讲道次数
3. 分析涉及的圣经书卷分布
4. 识别可能的排班问题

分析重点：{focus}

请使用以下资源获取数据：
- ministry://sermon/records?year={year}
- ministry://stats/preachers?year={year}
"""

@mcp.prompt()
def analyze_volunteer_balance(year: str = "2024", role: str = "所有岗位") -> str:
    """分析同工服侍均衡性"""
    return f"""请分析 {year} 年 {role} 的同工服侍情况：
1. 统计每位同工的服侍次数
2. 计算服侍频率
3. 识别服侍过多或过少的同工
4. 建议如何更均衡地分配服侍
"""

@mcp.prompt()
def analyze_next_sunday_volunteers(date: str = None) -> str:
    """分析下周日同工服侍"""
    return f"""请分析下周日（{date or '自动计算'}）的同工服侍安排：
1. 列出所有服侍岗位及对应的同工
2. 检查是否有关键岗位空缺
3. 确认是否有人身兼数职
4. 提供调度建议

请使用工具: generate_weekly_preview
"""

@mcp.prompt()
def generate_sunday_preview(date: str, format: str = "text") -> str:
    """生成主日预览报告"""
    return f"""请为 {date} 生成主日预览报告。
格式：{format}

请包含：
1. 证道信息（讲员、经文、题目）
2. 诗歌
3. 所有服侍同工名单

请使用工具: generate_weekly_preview(date='{date}', format='{format}')
"""

# ============================================================
# Main Execution
# ============================================================

# Expose ASGI app for uvicorn workers (Cloud Run)
# Common FastMCP patterns: .fastapi_app, .app, ._app, or the object itself
try:
    app = getattr(mcp, "fastapi_app", None)
    if not app:
        app = getattr(mcp, "app", None)
    if not app:
        app = getattr(mcp, "_app", None)
    if not app and callable(mcp):
        app = mcp
    
    if app:
        logger.info(f"ASGI app exposed for uvicorn: {type(app)}")
    else:
        logger.warning("Could not find ASGI app in mcp object!")
except Exception as e:
    logger.error(f"Error exposing ASGI app: {e}")
    app = None

# ------------------------------------------------------------------
# Cloud Run / client compatibility:
# Some clients (and older deployment scripts) expect the SSE endpoint at /sse.
# FastMCP may expose it at /mcp. We add an ASGI-level alias so streaming works.
# ------------------------------------------------------------------
if app and callable(app):
    try:
        def _wrap_with_path_aliases(asgi_app):
            async def _alias_asgi(scope, receive, send):
                if scope.get("type") == "http":
                    path = scope.get("path") or ""
                    if path == "/sse":
                        new_path = "/mcp"
                    elif path.startswith("/sse/"):
                        new_path = "/mcp/" + path[len("/sse/"):]
                    else:
                        new_path = None

                    if new_path:
                        new_scope = dict(scope)
                        new_scope["path"] = new_path
                        try:
                            new_scope["raw_path"] = new_path.encode("utf-8")
                        except Exception:
                            pass
                        return await asgi_app(new_scope, receive, send)

                return await asgi_app(scope, receive, send)

            return _alias_asgi

        app = _wrap_with_path_aliases(app)
        logger.info("Enabled ASGI path alias: /sse -> /mcp")
    except Exception as e:
        logger.warning(f"Failed to enable /sse alias: {e}")

if __name__ == "__main__":
    import uvicorn
    
    print("Starting mcp_server.py...", file=sys.stderr)
    
    # 检查是否运行在 HTTP 模式 (Cloud Run 会设置 PORT)
    port = os.getenv("PORT")
    
    try:
        if port:
            # HTTP/SSE 模式
            logger.info(f"Starting FastMCP Server in SSE mode on port {port}")
            
            # Try to find the ASGI app to run with uvicorn directly
            asgi_app = getattr(mcp, "fastapi_app", None) or getattr(mcp, "app", None) or getattr(mcp, "_app", None)
            
            if asgi_app:
                logger.info(f"Found underlying ASGI app: {type(asgi_app)}, running with uvicorn directly")
                uvicorn.run(asgi_app, host="0.0.0.0", port=int(port))
            else:
                logger.info("Could not find ASGI app on mcp object, using mcp.run() with safe fallback")
                try:
                    # Ensure host is "0.0.0.0" to listen on all interfaces
                    mcp.run(transport="sse", port=int(port), host="0.0.0.0")
                except TypeError as te:
                    if "host" in str(te):
                        logger.warning("mcp.run does not accept 'host' argument. Trying without it.")
                        # Warning: This might bind to localhost only!
                        mcp.run(transport="sse", port=int(port))
                    else:
                        raise te
        else:
            # stdio 模式 (默认)
            logger.info("Starting FastMCP Server in stdio mode")
            mcp.run()
    except Exception as e:
        logger.error(f"Failed to start FastMCP Server: {e}", exc_info=True)
        # 确保错误信息输出到 stderr，以便 Cloud Run 捕获
        print(f"CRITICAL ERROR: Failed to start server: {e}", file=sys.stderr)
        sys.exit(1)
