#!/usr/bin/env python3
"""
FastAPI 应用 - 提供数据清洗 API 和定时任务触发端点
支持 Google Cloud Run 部署和 Cloud Scheduler 定时触发
"""

import os
import sys
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional
from fastapi import FastAPI, HTTPException, Header, BackgroundTasks
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import pandas as pd

# 添加项目根目录到 Python 路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.clean_pipeline import CleaningPipeline
from core.change_detector import ChangeDetector
from core.service_layer import ServiceLayerManager

# 尝试从 Secret Manager 读取敏感配置
try:
    from core.secret_manager_utils import get_token_from_manager
    USE_SECRET_MANAGER = True
except ImportError:
    USE_SECRET_MANAGER = False

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# FastAPI 应用
app = FastAPI(
    title="Church Ministry Data Cleaning API",
    description="数据清洗管线 API",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# 配置文件路径
CONFIG_PATH = os.getenv('CONFIG_PATH', 'config/config.json')


# ============================================================
# Pydantic 模型
# ============================================================

class CleaningRequest(BaseModel):
    """清洗请求模型"""
    dry_run: bool = False
    force: bool = False
    config_path: Optional[str] = None


class CleaningResponse(BaseModel):
    """清洗响应模型"""
    success: bool
    message: str
    changed: bool = True
    change_reason: Optional[str] = None
    change_message: Optional[str] = None
    total_rows: int
    success_rows: int
    warning_rows: int
    error_rows: int
    timestamp: str
    preview_available: bool = False
    last_update_time: Optional[str] = None


class HealthResponse(BaseModel):
    """健康检查响应"""
    status: str
    timestamp: str
    version: str


class DataQueryRequest(BaseModel):
    """数据查询请求"""
    date_from: Optional[str] = None
    date_to: Optional[str] = None
    preacher: Optional[str] = None
    limit: int = 100


class ServiceLayerRequest(BaseModel):
    """服务层生成请求"""
    domains: Optional[List[str]] = None
    force: bool = False
    upload_to_bucket: bool = False
    generate_all_years: bool = True  # 默认生成所有年份


class ServiceLayerResponse(BaseModel):
    """服务层生成响应"""
    success: bool
    message: str
    domains_generated: List[str]
    years_generated: List[str]
    files_saved: Dict[str, Dict[str, str]]  # {year: {domain: path}}
    record_counts: Dict[str, Dict[str, int]]  # {year: {domain: count}}
    uploaded_to_bucket: bool = False
    timestamp: str


class AliasAddRequest(BaseModel):
    """添加别名请求"""
    alias: str
    person_id: str
    display_name: str


class AliasMergeRequest(BaseModel):
    """合并别名请求"""
    source_person_id: str
    target_person_id: str
    keep_display_name: str = "target"  # "source" or "target"


class ValidationRequest(BaseModel):
    """数据验证请求"""
    check_duplicates: bool = True
    generate_report: bool = True


class VolunteerMetadataModel(BaseModel):
    """同工元数据模型"""
    person_id: str
    person_name: str
    family_group: Optional[str] = None
    unavailable_start: Optional[str] = None
    unavailable_end: Optional[str] = None
    unavailable_reason: Optional[str] = None
    notes: Optional[str] = None
    updated_at: Optional[str] = None


class ConflictCheckRequest(BaseModel):
    """冲突检测请求"""
    year_month: Optional[str] = None
    check_family: bool = True
    check_availability: bool = True
    check_overload: bool = True


class SuggestionRequest(BaseModel):
    """排班建议请求"""
    service_date: str
    required_roles: List[str]
    consider_availability: bool = True
    consider_family: bool = True
    consider_balance: bool = True


# ============================================================
# 工具函数
# ============================================================

def get_next_sunday(from_date: Optional[datetime] = None) -> str:
    """
    获取下个周日的日期
    
    Args:
        from_date: 起始日期，默认为今天
        
    Returns:
        下个周日的日期字符串 (YYYY-MM-DD)
    """
    if from_date is None:
        from_date = datetime.now()
    
    # 0 = 周一, 6 = 周日
    days_until_sunday = (6 - from_date.weekday()) % 7
    if days_until_sunday == 0:
        # 如果今天是周日，返回下周日
        days_until_sunday = 7
    
    next_sunday = from_date + pd.Timedelta(days=days_until_sunday)
    return next_sunday.strftime('%Y-%m-%d')


def get_week_range(sunday_date: str) -> tuple:
    """
    获取周日所在周的日期范围（周一到周日）
    
    Args:
        sunday_date: 周日日期 (YYYY-MM-DD)
        
    Returns:
        (week_start, week_end) 元组
    """
    sunday = pd.to_datetime(sunday_date)
    week_start = sunday - pd.Timedelta(days=6)
    return week_start.strftime('%Y-%m-%d'), sunday_date


def is_date_in_range(date_str: str, start_str: Optional[str], end_str: Optional[str]) -> bool:
    """
    检查日期是否在指定范围内
    
    Args:
        date_str: 要检查的日期
        start_str: 开始日期（可选）
        end_str: 结束日期（可选）
        
    Returns:
        是否在范围内
    """
    if not start_str and not end_str:
        return False
    
    date = pd.to_datetime(date_str)
    
    if start_str and end_str:
        start = pd.to_datetime(start_str)
        end = pd.to_datetime(end_str)
        return start <= date <= end
    elif start_str:
        start = pd.to_datetime(start_str)
        return date >= start
    elif end_str:
        end = pd.to_datetime(end_str)
        return date <= end
    
    return False


def verify_scheduler_token(authorization: Optional[str] = None) -> bool:
    """
    验证 Cloud Scheduler 的认证令牌
    仅允许来自 Cloud Scheduler 的请求触发定时任务
    """
    if not authorization:
        return False
    
    # 从环境变量获取预期的令牌（优先），如果没有则从 Secret Manager 读取
    expected_token = os.getenv('SCHEDULER_TOKEN')
    if not expected_token and USE_SECRET_MANAGER:
        try:
            expected_token = get_token_from_manager(
                token_name="api-scheduler-token",
                fallback_env_var="SCHEDULER_TOKEN"
            )
            if expected_token:
                logger.info("✅ Scheduler Token loaded from Secret Manager")
        except Exception as e:
            logger.warning(f"Failed to load SCHEDULER_TOKEN from Secret Manager: {e}")
    
    if not expected_token:
        logger.warning("未设置 SCHEDULER_TOKEN 环境变量或 Secret Manager，跳过验证")
        return True
    
    # Bearer token 验证
    if not authorization.startswith('Bearer '):
        return False
    
    token = authorization[7:]
    return token == expected_token


def run_cleaning_pipeline(
    config_path: str, 
    dry_run: bool = False, 
    force: bool = False
) -> Dict[str, Any]:
    """
    运行清洗管线（支持变化检测）
    
    Args:
        config_path: 配置文件路径
        dry_run: 是否为干跑模式
        force: 是否强制执行（跳过变化检测）
        
    Returns:
        清洗结果摘要
    """
    try:
        pipeline = CleaningPipeline(config_path)
        detector = ChangeDetector()
        
        # 读取原始数据
        raw_df = pipeline.read_source_data()
        total_rows = len(raw_df)
        
        # 检测变化（除非强制执行）
        if not force:
            has_changed, change_details = detector.has_changed(raw_df)
            
            if not has_changed:
                logger.info("数据未发生变化，但仍生成服务层数据")
                state_summary = detector.get_state_summary()

                # 即使数据未变化，也要清洗并生成服务层（用于GCS更新）
                clean_df = pipeline.clean_data(raw_df)
                report = pipeline.validate_data(clean_df)

                # 不写入清洗层Google Sheet（数据未变化），但生成服务层
                pipeline.generate_service_layer(clean_df)

                detector.update_state(raw_df, success=True)

                return {
                    'success': True,
                    'message': '数据未发生变化，但已更新服务层',
                    'changed': False,
                    'change_reason': change_details['reason'],
                    'total_rows': total_rows,
                    'success_rows': report.success_rows,
                    'warning_rows': report.warning_rows,
                    'error_rows': report.error_rows,
                    'timestamp': datetime.utcnow().isoformat() + 'Z',
                    'preview_available': True,
                    'last_update_time': state_summary.get('last_update_time')
                }
            
            logger.info(f"检测到数据变化: {change_details['message']}")
        else:
            logger.info("强制执行模式，跳过变化检测")
            change_details = {
                'reason': 'forced',
                'message': '强制执行',
                'current_rows': total_rows,
                'previous_rows': 0,
                'row_change': 0
            }
        
        # 清洗数据
        clean_df = pipeline.clean_data(raw_df)

        # 校验数据
        report = pipeline.validate_data(clean_df)

        # 写入输出
        pipeline.write_output(clean_df, dry_run=dry_run)

        # 生成服务层数据并上传到 GCS
        pipeline.generate_service_layer(clean_df)

        # 更新状态
        detector.update_state(raw_df, success=True)
        
        return {
            'success': True,
            'message': '清洗管线执行成功',
            'changed': True,
            'change_reason': change_details['reason'],
            'change_message': change_details['message'],
            'total_rows': total_rows,
            'success_rows': report.success_rows,
            'warning_rows': report.warning_rows,
            'error_rows': report.error_rows,
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'preview_available': True
        }
        
    except Exception as e:
        logger.error(f"清洗管线执行失败: {e}", exc_info=True)
        return {
            'success': False,
            'message': f'清洗管线执行失败: {str(e)}',
            'changed': False,
            'total_rows': 0,
            'success_rows': 0,
            'warning_rows': 0,
            'error_rows': 0,
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'preview_available': False
        }


# ============================================================
# API 端点
# ============================================================

@app.get("/", response_model=HealthResponse)
async def root():
    """根端点 - 健康检查"""
    return HealthResponse(
        status="healthy",
        timestamp=datetime.utcnow().isoformat() + 'Z',
        version="1.0.0"
    )


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """健康检查端点"""
    return HealthResponse(
        status="healthy",
        timestamp=datetime.utcnow().isoformat() + 'Z',
        version="1.0.0"
    )


@app.post("/trigger-cleaning")
async def trigger_cleaning(
    background_tasks: BackgroundTasks,
    authorization: Optional[str] = Header(None)
):
    """
    触发清洗任务（用于 Cloud Scheduler）
    需要 Bearer token 认证
    """
    # 验证 token
    if not verify_scheduler_token(authorization):
        raise HTTPException(
            status_code=401,
            detail="Unauthorized: Invalid or missing token"
        )
    
    # 在后台运行清洗任务
    logger.info("收到定时触发请求，启动清洗任务...")
    
    try:
        # 定时任务默认不强制执行，会检测变化
        result = run_cleaning_pipeline(CONFIG_PATH, dry_run=False, force=False)
        return JSONResponse(content=result)
    except Exception as e:
        logger.error(f"清洗任务执行失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"清洗任务执行失败: {str(e)}"
        )


@app.post("/api/v1/clean", response_model=CleaningResponse)
async def clean_data(request: CleaningRequest):
    """
    手动触发数据清洗（公开 API）
    
    Args:
        request: 清洗请求，包含 dry_run 和可选的 config_path
    """
    config_path = request.config_path or CONFIG_PATH
    
    logger.info(f"收到清洗请求: dry_run={request.dry_run}, force={request.force}")
    
    try:
        result = run_cleaning_pipeline(
            config_path, 
            dry_run=request.dry_run, 
            force=request.force
        )
        return CleaningResponse(**result)
    except Exception as e:
        logger.error(f"清洗请求执行失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"清洗请求执行失败: {str(e)}"
        )


@app.get("/api/v1/preview")
async def get_preview():
    """
    获取最近一次清洗的预览数据
    """
    preview_path = Path('logs/clean_preview.json')
    
    if not preview_path.exists():
        raise HTTPException(
            status_code=404,
            detail="预览数据不存在，请先运行清洗任务"
        )
    
    try:
        with open(preview_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        return {
            'success': True,
            'count': len(data),
            'data': data
        }
    except Exception as e:
        logger.error(f"读取预览数据失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"读取预览数据失败: {str(e)}"
        )


@app.post("/api/v1/query")
async def query_data(request: DataQueryRequest):
    """
    查询清洗后的数据
    支持按日期范围、讲员等条件过滤
    """
    preview_path = Path('logs/clean_preview.json')
    
    if not preview_path.exists():
        raise HTTPException(
            status_code=404,
            detail="预览数据不存在，请先运行清洗任务"
        )
    
    try:
        # 读取数据
        with open(preview_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        df = pd.DataFrame(data)
        
        # 应用过滤
        if request.date_from:
            df = df[df['service_date'] >= request.date_from]
        
        if request.date_to:
            df = df[df['service_date'] <= request.date_to]
        
        if request.preacher:
            df = df[df['preacher_name'].str.contains(request.preacher, na=False)]
        
        # 限制返回数量
        df = df.head(request.limit)
        
        return {
            'success': True,
            'count': len(df),
            'data': df.to_dict(orient='records')
        }
    except Exception as e:
        logger.error(f"查询数据失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"查询数据失败: {str(e)}"
        )


@app.get("/api/v1/stats")
async def get_statistics():
    """
    获取数据统计信息
    """
    preview_path = Path('logs/clean_preview.json')
    
    if not preview_path.exists():
        raise HTTPException(
            status_code=404,
            detail="预览数据不存在，请先运行清洗任务"
        )
    
    try:
        with open(preview_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        df = pd.DataFrame(data)
        
        # 统计信息
        stats = {
            'total_records': len(df),
            'date_range': {
                'earliest': df['service_date'].min() if len(df) > 0 else None,
                'latest': df['service_date'].max() if len(df) > 0 else None
            },
            'unique_preachers': df['preacher_name'].nunique() if len(df) > 0 else 0,
            'unique_worship_leaders': df['worship_lead_name'].nunique() if len(df) > 0 else 0,
            'last_updated': data[0].get('updated_at') if len(data) > 0 else None
        }
        
        return {
            'success': True,
            'stats': stats
        }
    except Exception as e:
        logger.error(f"获取统计信息失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"获取统计信息失败: {str(e)}"
        )


# ============================================================
# 服务层端点
# ============================================================

@app.post("/api/v1/service-layer/generate", response_model=ServiceLayerResponse)
async def generate_service_layer(request: ServiceLayerRequest):
    """
    生成服务层数据（sermon 和 volunteer 域）
    支持生成所有年份的数据
    """
    try:
        # 读取清洗后的数据
        preview_path = Path('logs/clean_preview.json')
        
        if not preview_path.exists():
            raise HTTPException(
                status_code=404,
                detail="清洗层数据不存在，请先运行清洗任务"
            )
        
        logger.info(f"读取清洗层数据: {preview_path}")
        with open(preview_path, 'r', encoding='utf-8') as f:
            clean_data = json.load(f)
        
        clean_df = pd.DataFrame(clean_data)
        
        # 初始化服务层管理器
        manager = ServiceLayerManager()
        
        # 确定要生成的域
        domains = request.domains or ['sermon', 'volunteer']
        
        # 输出目录
        output_dir = Path('logs/service_layer')
        
        # 根据参数决定生成方式
        if request.generate_all_years:
            # 生成所有年份
            logger.info(f"生成所有年份的服务层数据: {domains}")
            all_saved_files = manager.generate_all_years(clean_df, output_dir, domains)
            
            # 整理返回数据
            files_saved = {}
            record_counts = {}
            years_generated = []
            
            for year, year_files in all_saved_files.items():
                years_generated.append(year)
                files_saved[year] = {}
                record_counts[year] = {}
                
                for domain, file_path in year_files.items():
                    files_saved[year][domain] = str(file_path)
                    
                    # 读取记录数
                    with open(file_path, 'r', encoding='utf-8') as f:
                        domain_data = json.load(f)
                    record_counts[year][domain] = domain_data['metadata']['record_count']
        else:
            # 只生成 latest
            logger.info(f"生成服务层数据: {domains}")
            domain_data_dict = manager.generate_domain_data(clean_df, domains)
            
            files_saved = {'latest': {}}
            record_counts = {'latest': {}}
            years_generated = ['latest']
            
            for domain, domain_data in domain_data_dict.items():
                file_path = manager.save_domain_data(domain_data, output_dir, domain)
                files_saved['latest'][domain] = str(file_path)
                record_counts['latest'][domain] = domain_data['metadata']['record_count']
        
        # 如果请求上传到 bucket
        uploaded_to_bucket = False
        if request.upload_to_bucket:
            try:
                # 读取配置
                with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                
                storage_config = config.get('service_layer', {}).get('storage', {})
                
                if storage_config.get('provider') == 'gcs':
                    from core.cloud_storage_utils import DomainStorageManager
                    
                    bucket_name = storage_config['bucket']
                    base_path = storage_config.get('base_path', 'domains/')
                    service_account_file = storage_config.get('service_account_file')
                    
                    # 智能处理服务账号文件路径
                    # 如果配置的是绝对路径且不存在，尝试使用容器内的路径
                    if service_account_file and not Path(service_account_file).exists():
                        # 尝试容器内的路径
                        container_path = '/app/config/service-account.json'
                        if Path(container_path).exists():
                            logger.info(f"使用容器内的服务账号文件: {container_path}")
                            service_account_file = container_path
                        else:
                            logger.warning(f"服务账号文件不存在: {service_account_file}")
                    
                    logger.info(f"上传到 Cloud Storage: gs://{bucket_name}/{base_path}")
                    
                    storage_manager = DomainStorageManager(
                        bucket_name=bucket_name,
                        service_account_file=service_account_file,
                        base_path=base_path
                    )
                    
                    # 上传所有年份的数据
                    for year, year_files in files_saved.items():
                        logger.info(f"上传 {year} 数据...")
                        for domain, file_path in year_files.items():
                            with open(file_path, 'r', encoding='utf-8') as f:
                                domain_data = json.load(f)
                            
                            # 根据是否为 latest 决定上传路径
                            if year == 'latest':
                                # 强制上传为 latest.json（避免自动提取年份）
                                uploaded = storage_manager.upload_domain_data(domain, domain_data, force_latest=True)
                            else:
                                # 上传年份文件
                                yearly_path = f"{domain}/{year}/{domain}_{year}.json"
                                gs_path = storage_manager.gcs_client.upload_json(domain_data, yearly_path)
                                uploaded = {f'yearly_{year}': gs_path}
                            
                            logger.info(f"  已上传 {domain} ({year}): {uploaded}")
                    
                    uploaded_to_bucket = True
                else:
                    logger.warning("Cloud Storage 未配置，跳过上传")
            
            except ImportError:
                logger.warning("google-cloud-storage 未安装，跳过上传")
            except Exception as e:
                logger.error(f"上传到 Cloud Storage 失败: {e}")
        
        return ServiceLayerResponse(
            success=True,
            message=f"成功生成 {len(domains)} 个领域 × {len(years_generated)} 个年份的数据",
            domains_generated=domains,
            years_generated=years_generated,
            files_saved=files_saved,
            record_counts=record_counts,
            uploaded_to_bucket=uploaded_to_bucket,
            timestamp=datetime.utcnow().isoformat() + 'Z'
        )
    
    except Exception as e:
        logger.error(f"生成服务层数据失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"生成服务层数据失败: {str(e)}"
        )


@app.get("/api/v1/sermon")
async def get_sermon_data(
    year: Optional[int] = None,
    limit: int = 100,
    offset: int = 0
):
    """
    获取证道域数据
    """
    try:
        sermon_file = Path('logs/service_layer/sermon.json')
        
        if not sermon_file.exists():
            raise HTTPException(
                status_code=404,
                detail="证道域数据不存在，请先生成服务层数据"
            )
        
        with open(sermon_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        sermons = data['sermons']
        
        # 按年份筛选
        if year:
            sermons = [s for s in sermons if s['service_date'].startswith(str(year))]
        
        # 分页
        total = len(sermons)
        sermons = sermons[offset:offset + limit]
        
        return {
            'metadata': {
                'domain': 'sermon',
                'version': data['metadata']['version'],
                'total_count': total,
                'returned_count': len(sermons),
                'offset': offset,
                'limit': limit
            },
            'sermons': sermons
        }
    
    except Exception as e:
        logger.error(f"获取证道数据失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"获取证道数据失败: {str(e)}"
        )


@app.get("/api/v1/volunteer")
async def get_volunteer_data(
    year: Optional[int] = None,
    service_date: Optional[str] = None,
    limit: int = 100,
    offset: int = 0
):
    """
    获取同工域数据
    """
    try:
        volunteer_file = Path('logs/service_layer/volunteer.json')
        
        if not volunteer_file.exists():
            raise HTTPException(
                status_code=404,
                detail="同工域数据不存在，请先生成服务层数据"
            )
        
        with open(volunteer_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        volunteers = data['volunteers']
        
        # 按年份筛选
        if year:
            volunteers = [v for v in volunteers if v['service_date'].startswith(str(year))]
        
        # 按日期筛选
        if service_date:
            volunteers = [v for v in volunteers if v['service_date'] == service_date]
        
        # 分页
        total = len(volunteers)
        volunteers = volunteers[offset:offset + limit]
        
        return {
            'metadata': {
                'domain': 'volunteer',
                'version': data['metadata']['version'],
                'total_count': total,
                'returned_count': len(volunteers),
                'offset': offset,
                'limit': limit
            },
            'volunteers': volunteers
        }
    
    except Exception as e:
        logger.error(f"获取同工数据失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"获取同工数据失败: {str(e)}"
        )


# ============================================================
# 高级查询端点
# ============================================================

@app.get("/api/v1/sermon/by-preacher/{preacher_name}")
async def get_sermons_by_preacher(
    preacher_name: str,
    year: Optional[int] = None,
    limit: int = 100,
    offset: int = 0
):
    """
    按讲员查询证道记录 (Resource: sermon-by-preacher)
    """
    try:
        sermon_file = Path('logs/service_layer/sermon.json')
        
        if not sermon_file.exists():
            raise HTTPException(
                status_code=404,
                detail="证道域数据不存在，请先生成服务层数据"
            )
        
        with open(sermon_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        sermons = data['sermons']
        
        # 按讲员名称筛选（支持部分匹配）
        sermons = [
            s for s in sermons 
            if preacher_name.lower() in s['preacher']['name'].lower()
        ]
        
        # 按年份筛选
        if year:
            sermons = [s for s in sermons if s['service_date'].startswith(str(year))]
        
        # 分页
        total = len(sermons)
        sermons = sermons[offset:offset + limit]
        
        return {
            'metadata': {
                'domain': 'sermon',
                'version': data['metadata']['version'],
                'preacher_name': preacher_name,
                'total_count': total,
                'returned_count': len(sermons),
                'offset': offset,
                'limit': limit
            },
            'sermons': sermons
        }
    
    except Exception as e:
        logger.error(f"按讲员查询证道数据失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"按讲员查询证道数据失败: {str(e)}"
        )


@app.get("/api/v1/sermon/series")
async def get_sermon_series(year: Optional[int] = None):
    """
    获取讲道系列信息和进度 (Resource: sermon-series)
    """
    try:
        sermon_file = Path('logs/service_layer/sermon.json')
        
        if not sermon_file.exists():
            raise HTTPException(
                status_code=404,
                detail="证道域数据不存在，请先生成服务层数据"
            )
        
        with open(sermon_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        sermons = data['sermons']
        
        # 按年份筛选
        if year:
            sermons = [s for s in sermons if s['service_date'].startswith(str(year))]
        
        # 统计系列
        series_dict = {}
        for sermon in sermons:
            series_name = sermon['sermon']['series']
            if not series_name or series_name == '':
                series_name = '未分类'
            
            if series_name not in series_dict:
                series_dict[series_name] = {
                    'series_name': series_name,
                    'sermon_count': 0,
                    'sermons': [],
                    'date_range': {'start': None, 'end': None},
                    'preachers': set()
                }
            
            series_info = series_dict[series_name]
            series_info['sermon_count'] += 1
            series_info['sermons'].append({
                'service_date': sermon['service_date'],
                'title': sermon['sermon']['title'],
                'scripture': sermon['sermon']['scripture'],
                'preacher': sermon['preacher']['name']
            })
            series_info['preachers'].add(sermon['preacher']['name'])
            
            # 更新日期范围
            service_date = sermon['service_date']
            if series_info['date_range']['start'] is None or service_date < series_info['date_range']['start']:
                series_info['date_range']['start'] = service_date
            if series_info['date_range']['end'] is None or service_date > series_info['date_range']['end']:
                series_info['date_range']['end'] = service_date
        
        # 转换为列表并排序
        series_list = []
        for series_name, series_info in series_dict.items():
            series_info['preachers'] = list(series_info['preachers'])
            series_info['sermons'].sort(key=lambda x: x['service_date'])
            series_list.append(series_info)
        
        # 按讲道数量降序排序
        series_list.sort(key=lambda x: x['sermon_count'], reverse=True)
        
        return {
            'metadata': {
                'domain': 'sermon',
                'version': data['metadata']['version'],
                'total_series': len(series_list),
                'year': year
            },
            'series': series_list
        }
    
    except Exception as e:
        logger.error(f"获取讲道系列失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"获取讲道系列失败: {str(e)}"
        )


@app.get("/api/v1/volunteer/by-person/{person_identifier}")
async def get_volunteer_by_person(
    person_identifier: str,
    year: Optional[int] = None,
    limit: int = 100,
    offset: int = 0
):
    """
    查询某人的所有服侍记录 (Resource: volunteer-by-person)
    person_identifier 可以是 person_id 或姓名
    """
    try:
        volunteer_file = Path('logs/service_layer/volunteer.json')
        
        if not volunteer_file.exists():
            raise HTTPException(
                status_code=404,
                detail="同工域数据不存在，请先生成服务层数据"
            )
        
        with open(volunteer_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        volunteers = data['volunteers']
        
        # 筛选该人员的服侍记录
        person_records = []
        for record in volunteers:
            # 检查所有岗位
            roles_served = []
            
            # 敬拜主领
            if (person_identifier.lower() in record['worship']['lead']['id'].lower() or
                person_identifier.lower() in record['worship']['lead']['name'].lower()):
                roles_served.append('敬拜主领')
            
            # 敬拜团队
            for member in record['worship']['team']:
                if (person_identifier.lower() in member['id'].lower() or
                    person_identifier.lower() in member['name'].lower()):
                    roles_served.append('敬拜同工')
                    break
            
            # 司琴
            if (person_identifier.lower() in record['worship']['pianist']['id'].lower() or
                person_identifier.lower() in record['worship']['pianist']['name'].lower()):
                roles_served.append('司琴')
            
            # 技术岗位
            for tech_role, tech_field in [
                ('音控', 'audio'),
                ('导播/摄影', 'video'),
                ('ProPresenter播放', 'propresenter_play'),
                ('ProPresenter更新', 'propresenter_update')
            ]:
                tech_person = record['technical'][tech_field]
                if (person_identifier.lower() in tech_person['id'].lower() or
                    person_identifier.lower() in tech_person['name'].lower()):
                    roles_served.append(tech_role)
            
            if roles_served:
                person_records.append({
                    'service_date': record['service_date'],
                    'service_week': record['service_week'],
                    'service_slot': record['service_slot'],
                    'roles': roles_served,
                    'full_record': record
                })
        
        # 按年份筛选
        if year:
            person_records = [r for r in person_records if r['service_date'].startswith(str(year))]
        
        # 分页
        total = len(person_records)
        person_records = person_records[offset:offset + limit]
        
        # 统计信息
        role_counts = {}
        for record in person_records:
            for role in record['roles']:
                role_counts[role] = role_counts.get(role, 0) + 1
        
        return {
            'metadata': {
                'domain': 'volunteer',
                'version': data['metadata']['version'],
                'person_identifier': person_identifier,
                'total_count': total,
                'returned_count': len(person_records),
                'offset': offset,
                'limit': limit,
                'role_statistics': role_counts
            },
            'records': person_records
        }
    
    except Exception as e:
        logger.error(f"按人员查询同工数据失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"按人员查询同工数据失败: {str(e)}"
        )


@app.get("/api/v1/volunteer/availability/{year_month}")
async def get_volunteer_availability(year_month: str):
    """
    查询某时间范围内的空缺岗位 (Resource: volunteer-availability)
    year_month 格式: YYYY-MM
    """
    try:
        volunteer_file = Path('logs/service_layer/volunteer.json')
        
        if not volunteer_file.exists():
            raise HTTPException(
                status_code=404,
                detail="同工域数据不存在，请先生成服务层数据"
            )
        
        with open(volunteer_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        volunteers = data['volunteers']
        
        # 筛选指定月份的记录
        month_records = [
            v for v in volunteers 
            if v['service_date'].startswith(year_month)
        ]
        
        # 检查每条记录的空缺
        availability_report = []
        for record in month_records:
            gaps = []
            
            # 检查敬拜主领
            if not record['worship']['lead']['name'] or record['worship']['lead']['name'] == '':
                gaps.append('敬拜主领')
            
            # 检查敬拜团队
            if not record['worship']['team'] or len(record['worship']['team']) == 0:
                gaps.append('敬拜同工')
            
            # 检查司琴
            if not record['worship']['pianist']['name'] or record['worship']['pianist']['name'] == '':
                gaps.append('司琴')
            
            # 检查技术岗位
            tech_roles = {
                'audio': '音控',
                'video': '导播/摄影',
                'propresenter_play': 'ProPresenter播放',
                'propresenter_update': 'ProPresenter更新'
            }
            for tech_field, tech_name in tech_roles.items():
                if not record['technical'][tech_field]['name'] or record['technical'][tech_field]['name'] == '':
                    gaps.append(tech_name)
            
            if gaps:
                availability_report.append({
                    'service_date': record['service_date'],
                    'service_week': record['service_week'],
                    'service_slot': record['service_slot'],
                    'vacant_positions': gaps,
                    'urgency': 'high' if len(gaps) >= 3 else 'medium' if len(gaps) >= 2 else 'low'
                })
        
        # 按日期排序（越近越紧急）
        availability_report.sort(key=lambda x: x['service_date'])
        
        # 统计汇总
        total_gaps = sum(len(r['vacant_positions']) for r in availability_report)
        gap_by_position = {}
        for report in availability_report:
            for position in report['vacant_positions']:
                gap_by_position[position] = gap_by_position.get(position, 0) + 1
        
        return {
            'metadata': {
                'domain': 'volunteer',
                'version': data['metadata']['version'],
                'year_month': year_month,
                'total_services': len(month_records),
                'services_with_gaps': len(availability_report),
                'total_gaps': total_gaps
            },
            'summary': {
                'gap_by_position': gap_by_position
            },
            'availability': availability_report
        }
    
    except Exception as e:
        logger.error(f"查询排班空缺失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"查询排班空缺失败: {str(e)}"
        )


# ============================================================
# 统计分析端点
# ============================================================

@app.get("/api/v1/stats/preachers")
async def get_preacher_stats(year: Optional[int] = None):
    """
    讲员统计 (Resource: preacher-stats)
    """
    try:
        sermon_file = Path('logs/service_layer/sermon.json')
        
        if not sermon_file.exists():
            raise HTTPException(
                status_code=404,
                detail="证道域数据不存在，请先生成服务层数据"
            )
        
        with open(sermon_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        sermons = data['sermons']
        
        # 按年份筛选
        if year:
            sermons = [s for s in sermons if s['service_date'].startswith(str(year))]
        
        # 统计每位讲员
        preacher_stats = {}
        for sermon in sermons:
            preacher_id = sermon['preacher']['id']
            preacher_name = sermon['preacher']['name']
            
            if preacher_id not in preacher_stats:
                preacher_stats[preacher_id] = {
                    'preacher_id': preacher_id,
                    'preacher_name': preacher_name,
                    'sermon_count': 0,
                    'series': set(),
                    'scriptures': [],
                    'dates': []
                }
            
            stats = preacher_stats[preacher_id]
            stats['sermon_count'] += 1
            if sermon['sermon']['series']:
                stats['series'].add(sermon['sermon']['series'])
            if sermon['sermon']['scripture']:
                stats['scriptures'].append(sermon['sermon']['scripture'])
            stats['dates'].append(sermon['service_date'])
        
        # 转换为列表
        preacher_list = []
        for preacher_id, stats in preacher_stats.items():
            stats['series'] = list(stats['series'])
            stats['dates'].sort()
            stats['date_range'] = {
                'first': stats['dates'][0] if stats['dates'] else None,
                'last': stats['dates'][-1] if stats['dates'] else None
            }
            del stats['dates']  # 不返回完整日期列表
            preacher_list.append(stats)
        
        # 按讲道次数降序排序
        preacher_list.sort(key=lambda x: x['sermon_count'], reverse=True)
        
        return {
            'metadata': {
                'domain': 'sermon',
                'version': data['metadata']['version'],
                'year': year,
                'total_preachers': len(preacher_list),
                'total_sermons': len(sermons)
            },
            'preachers': preacher_list
        }
    
    except Exception as e:
        logger.error(f"获取讲员统计失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"获取讲员统计失败: {str(e)}"
        )


@app.get("/api/v1/stats/volunteers")
async def get_volunteer_stats(year: Optional[int] = None):
    """
    同工统计 (Resource: volunteer-stats)
    """
    try:
        volunteer_file = Path('logs/service_layer/volunteer.json')
        
        if not volunteer_file.exists():
            raise HTTPException(
                status_code=404,
                detail="同工域数据不存在，请先生成服务层数据"
            )
        
        with open(volunteer_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        volunteers = data['volunteers']
        
        # 按年份筛选
        if year:
            volunteers = [v for v in volunteers if v['service_date'].startswith(str(year))]
        
        # 统计每位同工
        volunteer_stats = {}
        
        def add_person_stat(person_id, person_name, role, service_date):
            if not person_name or person_name == '':
                return
            
            if person_id not in volunteer_stats:
                volunteer_stats[person_id] = {
                    'person_id': person_id,
                    'person_name': person_name,
                    'total_services': 0,
                    'roles': {},
                    'dates': []
                }
            
            stats = volunteer_stats[person_id]
            stats['total_services'] += 1
            stats['roles'][role] = stats['roles'].get(role, 0) + 1
            if service_date not in stats['dates']:
                stats['dates'].append(service_date)
        
        for record in volunteers:
            service_date = record['service_date']
            
            # 敬拜主领
            add_person_stat(
                record['worship']['lead']['id'],
                record['worship']['lead']['name'],
                '敬拜主领',
                service_date
            )
            
            # 敬拜团队
            for member in record['worship']['team']:
                add_person_stat(member['id'], member['name'], '敬拜同工', service_date)
            
            # 司琴
            add_person_stat(
                record['worship']['pianist']['id'],
                record['worship']['pianist']['name'],
                '司琴',
                service_date
            )
            
            # 技术岗位
            tech_roles = {
                'audio': '音控',
                'video': '导播/摄影',
                'propresenter_play': 'ProPresenter播放',
                'propresenter_update': 'ProPresenter更新'
            }
            for tech_field, tech_name in tech_roles.items():
                add_person_stat(
                    record['technical'][tech_field]['id'],
                    record['technical'][tech_field]['name'],
                    tech_name,
                    service_date
                )
        
        # 转换为列表
        volunteer_list = []
        for person_id, stats in volunteer_stats.items():
            stats['dates'].sort()
            stats['date_range'] = {
                'first': stats['dates'][0] if stats['dates'] else None,
                'last': stats['dates'][-1] if stats['dates'] else None
            }
            stats['unique_dates'] = len(set(stats['dates']))
            del stats['dates']  # 不返回完整日期列表
            volunteer_list.append(stats)
        
        # 按服侍次数降序排序
        volunteer_list.sort(key=lambda x: x['total_services'], reverse=True)
        
        return {
            'metadata': {
                'domain': 'volunteer',
                'version': data['metadata']['version'],
                'year': year,
                'total_volunteers': len(volunteer_list),
                'total_services': len(volunteers)
            },
            'volunteers': volunteer_list
        }
    
    except Exception as e:
        logger.error(f"获取同工统计失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"获取同工统计失败: {str(e)}"
        )


# ============================================================
# 别名管理端点
# ============================================================

@app.get("/api/v1/config/aliases")
async def get_alias_mappings():
    """
    获取人员别名映射表 (Resource: alias-mappings)
    """
    try:
        # 读取配置文件获取别名表信息
        with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        alias_sources = config.get('alias_sources', {})
        
        if not alias_sources or 'people_alias_sheet' not in alias_sources:
            return {
                'success': False,
                'message': '别名数据源未配置',
                'aliases': []
            }
        
        # 读取别名表
        from scripts.gsheet_utils import GSheetClient
        
        alias_config = alias_sources['people_alias_sheet']
        client = GSheetClient()
        alias_df = client.read_range(alias_config['url'], alias_config['range'])
        
        # 转换为标准格式
        aliases = []
        for _, row in alias_df.iterrows():
            aliases.append({
                'alias': str(row.get('alias', '')),
                'person_id': str(row.get('person_id', '')),
                'display_name': str(row.get('display_name', ''))
            })
        
        return {
            'success': True,
            'metadata': {
                'total_count': len(aliases),
                'source': 'Google Sheets'
            },
            'aliases': aliases
        }
    
    except Exception as e:
        logger.error(f"获取别名映射失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"获取别名映射失败: {str(e)}"
        )


@app.post("/api/v1/config/aliases")
async def add_alias(request: AliasAddRequest):
    """
    添加人员别名映射 (Tool: add_person_alias)
    """
    try:
        # 读取配置文件获取别名表信息
        with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        alias_sources = config.get('alias_sources', {})
        
        if not alias_sources or 'people_alias_sheet' not in alias_sources:
            raise HTTPException(
                status_code=400,
                detail='别名数据源未配置'
            )
        
        # 读取现有别名
        from scripts.gsheet_utils import GSheetClient
        
        alias_config = alias_sources['people_alias_sheet']
        client = GSheetClient()
        alias_df = client.read_range(alias_config['url'], alias_config['range'])
        
        # 检查别名是否已存在
        existing_alias = alias_df[alias_df['alias'] == request.alias]
        if not existing_alias.empty:
            return {
                'success': False,
                'message': f"别名 '{request.alias}' 已存在",
                'existing_mapping': {
                    'alias': request.alias,
                    'person_id': str(existing_alias.iloc[0]['person_id']),
                    'display_name': str(existing_alias.iloc[0]['display_name'])
                }
            }
        
        # 添加新别名
        new_row = pd.DataFrame([{
            'alias': request.alias,
            'person_id': request.person_id,
            'display_name': request.display_name
        }])
        
        updated_df = pd.concat([alias_df, new_row], ignore_index=True)
        
        # 写回Google Sheets
        sheet_range = alias_config['range'].split('!')[0]  # 只取sheet名称
        client.write_range(alias_config['url'], f"{sheet_range}!A1", updated_df)
        
        logger.info(f"成功添加别名: {request.alias} -> {request.person_id}")
        
        return {
            'success': True,
            'message': f"成功添加别名 '{request.alias}'",
            'alias': {
                'alias': request.alias,
                'person_id': request.person_id,
                'display_name': request.display_name
            },
            'timestamp': datetime.utcnow().isoformat() + 'Z'
        }
    
    except Exception as e:
        logger.error(f"添加别名失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"添加别名失败: {str(e)}"
        )


@app.post("/api/v1/config/aliases/merge")
async def merge_aliases(request: AliasMergeRequest):
    """
    合并两个人员ID的所有别名 (Tool: merge_person_aliases)
    """
    try:
        # 读取配置文件获取别名表信息
        with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        alias_sources = config.get('alias_sources', {})
        
        if not alias_sources or 'people_alias_sheet' not in alias_sources:
            raise HTTPException(
                status_code=400,
                detail='别名数据源未配置'
            )
        
        # 读取现有别名
        from scripts.gsheet_utils import GSheetClient
        
        alias_config = alias_sources['people_alias_sheet']
        client = GSheetClient()
        alias_df = client.read_range(alias_config['url'], alias_config['range'])
        
        # 查找源和目标person_id
        source_aliases = alias_df[alias_df['person_id'] == request.source_person_id]
        target_aliases = alias_df[alias_df['person_id'] == request.target_person_id]
        
        if source_aliases.empty:
            raise HTTPException(
                status_code=404,
                detail=f"未找到源person_id: {request.source_person_id}"
            )
        
        if target_aliases.empty:
            raise HTTPException(
                status_code=404,
                detail=f"未找到目标person_id: {request.target_person_id}"
            )
        
        # 确定保留的显示名称
        if request.keep_display_name == "source":
            keep_display_name = str(source_aliases.iloc[0]['display_name'])
        else:
            keep_display_name = str(target_aliases.iloc[0]['display_name'])
        
        # 合并：将源person_id的所有别名改为目标person_id
        alias_df.loc[alias_df['person_id'] == request.source_person_id, 'person_id'] = request.target_person_id
        alias_df.loc[alias_df['person_id'] == request.target_person_id, 'display_name'] = keep_display_name
        
        # 去除可能的重复项
        alias_df = alias_df.drop_duplicates(subset=['alias'], keep='first')
        
        # 写回Google Sheets
        sheet_range = alias_config['range'].split('!')[0]
        client.write_range(alias_config['url'], f"{sheet_range}!A1", alias_df)
        
        merged_count = len(source_aliases)
        
        logger.info(f"成功合并别名: {request.source_person_id} -> {request.target_person_id}, 合并了{merged_count}个别名")
        
        return {
            'success': True,
            'message': f"成功合并 {merged_count} 个别名",
            'details': {
                'source_person_id': request.source_person_id,
                'target_person_id': request.target_person_id,
                'merged_aliases': source_aliases['alias'].tolist(),
                'display_name': keep_display_name
            },
            'timestamp': datetime.utcnow().isoformat() + 'Z'
        }
    
    except Exception as e:
        logger.error(f"合并别名失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"合并别名失败: {str(e)}"
        )


# ============================================================
# 数据验证和管线状态端点
# ============================================================

@app.post("/api/v1/validate")
async def validate_data(request: ValidationRequest):
    """
    校验原始数据质量 (Tool: validate_raw_data)
    """
    try:
        pipeline = CleaningPipeline(CONFIG_PATH)
        
        # 读取原始数据
        raw_df = pipeline.read_source_data()
        total_rows = len(raw_df)
        
        logger.info(f"开始验证数据，共 {total_rows} 行")
        
        # 清洗数据（用于验证）
        clean_df = pipeline.clean_data(raw_df)
        
        # 校验数据
        report = pipeline.validate_data(clean_df)
        
        # 检查重复
        duplicates = []
        if request.check_duplicates:
            # 检查重复的服务记录
            duplicate_mask = clean_df.duplicated(subset=['service_date', 'service_slot'], keep=False)
            if duplicate_mask.any():
                dup_df = clean_df[duplicate_mask][['service_date', 'service_slot', 'source_row']]
                for _, row in dup_df.iterrows():
                    duplicates.append({
                        'service_date': str(row['service_date']),
                        'service_slot': str(row['service_slot']),
                        'source_row': int(row['source_row'])
                    })
        
        # 生成验证报告
        validation_summary = {
            'total_rows': total_rows,
            'success_rows': report.success_rows,
            'warning_rows': report.warning_rows,
            'error_rows': report.error_rows,
            'duplicate_records': len(duplicates),
            'issues_by_severity': {
                'error': len([i for i in report.issues if i.severity == 'error']),
                'warning': len([i for i in report.issues if i.severity == 'warning'])
            }
        }
        
        # 分组问题
        issues_by_field = {}
        for issue in report.issues:
            field = issue.field
            if field not in issues_by_field:
                issues_by_field[field] = []
            issues_by_field[field].append({
                'row': issue.row_number,
                'severity': issue.severity,
                'message': issue.message,
                'value': issue.value
            })
        
        # 生成报告文件（如果请求）
        report_file = None
        if request.generate_report:
            report_file = pipeline.save_validation_report(report)
            logger.info(f"验证报告已保存: {report_file}")
        
        return {
            'success': True,
            'message': '数据验证完成',
            'summary': validation_summary,
            'duplicates': duplicates[:20] if duplicates else [],  # 最多返回20个
            'issues_by_field': {k: v[:10] for k, v in issues_by_field.items()},  # 每个字段最多10个问题
            'report_file': str(report_file) if report_file else None,
            'timestamp': datetime.utcnow().isoformat() + 'Z'
        }
    
    except Exception as e:
        logger.error(f"数据验证失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"数据验证失败: {str(e)}"
        )


@app.get("/api/v1/pipeline/status")
async def get_pipeline_status(last_n_runs: int = 10):
    """
    获取数据清洗管线的运行状态和历史记录 (Tool: get_pipeline_status)
    """
    try:
        detector = ChangeDetector()
        
        # 获取当前状态
        state_summary = detector.get_state_summary()
        
        # 查找最近的验证报告
        logs_dir = Path('logs')
        validation_reports = sorted(
            logs_dir.glob('validation_report_*.txt'),
            key=lambda p: p.stat().st_mtime,
            reverse=True
        )[:last_n_runs]
        
        recent_reports = []
        for report_path in validation_reports:
            # 从文件名提取时间戳
            filename = report_path.stem  # validation_report_20251006_162602
            timestamp_str = filename.replace('validation_report_', '')
            
            # 读取报告内容（前几行）
            with open(report_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()[:20]  # 只读前20行
                summary_text = ''.join(lines)
            
            # 解析统计信息
            stats = {}
            for line in lines:
                if '总行数:' in line:
                    stats['total_rows'] = int(line.split(':')[1].strip())
                elif '成功行数:' in line:
                    stats['success_rows'] = int(line.split(':')[1].strip())
                elif '警告行数:' in line:
                    stats['warning_rows'] = int(line.split(':')[1].strip())
                elif '错误行数:' in line:
                    stats['error_rows'] = int(line.split(':')[1].strip())
            
            recent_reports.append({
                'timestamp': timestamp_str,
                'file': str(report_path),
                'stats': stats,
                'preview': summary_text
            })
        
        # 检查服务层文件状态
        service_layer_status = {}
        for domain in ['sermon', 'volunteer']:
            domain_file = Path(f'logs/service_layer/{domain}.json')
            if domain_file.exists():
                stat = domain_file.stat()
                with open(domain_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                service_layer_status[domain] = {
                    'exists': True,
                    'record_count': data['metadata']['record_count'],
                    'last_modified': datetime.fromtimestamp(stat.st_mtime).isoformat(),
                    'file_size': stat.st_size
                }
            else:
                service_layer_status[domain] = {'exists': False}
        
        return {
            'success': True,
            'pipeline_status': {
                'last_run': state_summary.get('last_update_time'),
                'last_row_count': state_summary.get('last_row_count', 0),
                'last_hash': state_summary.get('last_hash', '')[:16] + '...' if state_summary.get('last_hash') else None,
                'is_healthy': state_summary.get('last_row_count', 0) > 0
            },
            'service_layer': service_layer_status,
            'recent_runs': recent_reports,
            'timestamp': datetime.utcnow().isoformat() + 'Z'
        }
    
    except Exception as e:
        logger.error(f"获取管线状态失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"获取管线状态失败: {str(e)}"
        )


# ============================================================
# 同工元数据端点
# ============================================================

@app.get("/api/v1/volunteer/metadata")
async def get_volunteer_metadata(person_id: Optional[str] = None):
    """
    获取同工元数据 (Resource: volunteer-metadata)
    """
    try:
        # 读取配置
        with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        metadata_config = config.get('volunteer_metadata_sheet')
        if not metadata_config:
            return {
                'success': False,
                'message': '同工元数据表未配置',
                'metadata': []
            }
        
        # 读取元数据表
        from scripts.gsheet_utils import GSheetClient
        
        client = GSheetClient()
        metadata_df = client.read_range(
            metadata_config['url'],
            metadata_config['range']
        )
        
        # 如果指定了person_id，只返回该人的数据
        if person_id:
            metadata_df = metadata_df[metadata_df['person_id'] == person_id]
        
        # 转换为标准格式
        metadata_list = []
        for _, row in metadata_df.iterrows():
            # 检查当前日期是否在不可用时间段
            is_available = True
            unavailable_start = str(row.get('unavailable_start', '')) if pd.notna(row.get('unavailable_start')) else None
            unavailable_end = str(row.get('unavailable_end', '')) if pd.notna(row.get('unavailable_end')) else None
            
            if unavailable_start and unavailable_end:
                today = datetime.now().strftime('%Y-%m-%d')
                is_available = not is_date_in_range(today, unavailable_start, unavailable_end)
            
            metadata_item = {
                'person_id': str(row.get('person_id', '')),
                'person_name': str(row.get('person_name', '')),
                'family_group': str(row.get('family_group', '')) if pd.notna(row.get('family_group')) else None,
                'unavailable_start': unavailable_start,
                'unavailable_end': unavailable_end,
                'unavailable_reason': str(row.get('unavailable_reason', '')) if pd.notna(row.get('unavailable_reason')) else None,
                'notes': str(row.get('notes', '')) if pd.notna(row.get('notes')) else None,
                'updated_at': str(row.get('updated_at', '')) if pd.notna(row.get('updated_at')) else None,
                'is_available': is_available
            }
            metadata_list.append(metadata_item)
        
        # 按family_group分组
        family_groups = {}
        for item in metadata_list:
            if item['family_group']:
                if item['family_group'] not in family_groups:
                    family_groups[item['family_group']] = []
                family_groups[item['family_group']].append(item['person_id'])
        
        return {
            'success': True,
            'metadata': {
                'total_count': len(metadata_list),
                'available_count': sum(1 for m in metadata_list if m['is_available']),
                'unavailable_count': sum(1 for m in metadata_list if not m['is_available']),
                'family_groups': family_groups,
                'source': 'Google Sheets'
            },
            'volunteers': metadata_list
        }
    
    except Exception as e:
        logger.error(f"获取同工元数据失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"获取同工元数据失败: {str(e)}"
        )


@app.post("/api/v1/volunteer/metadata")
async def add_volunteer_metadata(request: VolunteerMetadataModel):
    """
    添加或更新同工元数据 (Tool: add_volunteer_metadata)
    """
    try:
        # 读取配置
        with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        metadata_config = config.get('volunteer_metadata_sheet')
        if not metadata_config:
            raise HTTPException(
                status_code=400,
                detail='同工元数据表未配置'
            )
        
        # 读取现有数据
        from scripts.gsheet_utils import GSheetClient
        
        client = GSheetClient()
        metadata_df = client.read_range(
            metadata_config['url'],
            metadata_config['range']
        )
        
        # 检查是否已存在
        existing = metadata_df[metadata_df['person_id'] == request.person_id]
        
        # 准备新数据
        new_data = {
            'person_id': request.person_id,
            'person_name': request.person_name,
            'family_group': request.family_group or '',
            'unavailable_start': request.unavailable_start or '',
            'unavailable_end': request.unavailable_end or '',
            'unavailable_reason': request.unavailable_reason or '',
            'notes': request.notes or '',
            'updated_at': request.updated_at or datetime.now().strftime('%Y-%m-%d')
        }
        
        if not existing.empty:
            # 更新现有记录
            for col, val in new_data.items():
                if val:  # 只更新非空值
                    metadata_df.loc[metadata_df['person_id'] == request.person_id, col] = val
            message = f"成功更新同工元数据: {request.person_name}"
        else:
            # 添加新记录
            new_row = pd.DataFrame([new_data])
            metadata_df = pd.concat([metadata_df, new_row], ignore_index=True)
            message = f"成功添加同工元数据: {request.person_name}"
        
        # 写回Google Sheets
        sheet_range = metadata_config['range'].split('!')[0]
        client.write_range(metadata_config['url'], f"{sheet_range}!A1", metadata_df)
        
        logger.info(message)
        
        return {
            'success': True,
            'message': message,
            'metadata': new_data,
            'timestamp': datetime.utcnow().isoformat() + 'Z'
        }
    
    except Exception as e:
        logger.error(f"添加同工元数据失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"添加同工元数据失败: {str(e)}"
        )


@app.get("/api/v1/volunteer/next-week")
async def get_next_week_volunteers():
    """
    获取下周同工安排 (Resource: next-week-volunteers)
    """
    try:
        # 计算下周日
        next_sunday = get_next_sunday()
        week_start, week_end = get_week_range(next_sunday)
        
        # 读取下周的同工安排
        volunteer_file = Path('logs/service_layer/volunteer.json')
        
        if not volunteer_file.exists():
            raise HTTPException(
                status_code=404,
                detail="同工域数据不存在，请先生成服务层数据"
            )
        
        with open(volunteer_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        volunteers = data['volunteers']
        
        # 筛选下周的记录
        next_week_records = [
            v for v in volunteers
            if v['service_date'] == next_sunday
        ]
        
        if not next_week_records:
            return {
                'success': True,
                'message': f'下周（{next_sunday}）暂无安排',
                'week_info': {
                    'week_start': week_start,
                    'week_end': week_end,
                    'sunday_date': next_sunday,
                    'is_next_week': True
                },
                'services': [],
                'summary': {
                    'total_volunteers': 0,
                    'unique_volunteers': 0
                }
            }
        
        # 获取元数据
        metadata_response = await get_volunteer_metadata()
        metadata_dict = {}
        if metadata_response['success']:
            for vol in metadata_response['volunteers']:
                metadata_dict[vol['person_id']] = vol
        
        # 收集所有服侍的人
        all_volunteers = []
        unique_volunteers = set()
        
        for record in next_week_records:
            # 敬拜主领
            if record['worship']['lead']['name']:
                person_id = record['worship']['lead']['id']
                all_volunteers.append({
                    'person_id': person_id,
                    'person_name': record['worship']['lead']['name'],
                    'role': '敬拜主领',
                    'is_available': metadata_dict.get(person_id, {}).get('is_available', True),
                    'metadata': metadata_dict.get(person_id, {})
                })
                unique_volunteers.add(person_id)
            
            # 敬拜团队
            for member in record['worship']['team']:
                if member['name']:
                    person_id = member['id']
                    all_volunteers.append({
                        'person_id': person_id,
                        'person_name': member['name'],
                        'role': '敬拜同工',
                        'is_available': metadata_dict.get(person_id, {}).get('is_available', True),
                        'metadata': metadata_dict.get(person_id, {})
                    })
                    unique_volunteers.add(person_id)
            
            # 司琴
            if record['worship']['pianist']['name']:
                person_id = record['worship']['pianist']['id']
                all_volunteers.append({
                    'person_id': person_id,
                    'person_name': record['worship']['pianist']['name'],
                    'role': '司琴',
                    'is_available': metadata_dict.get(person_id, {}).get('is_available', True),
                    'metadata': metadata_dict.get(person_id, {})
                })
                unique_volunteers.add(person_id)
            
            # 技术岗位
            tech_roles = {
                'audio': '音控',
                'video': '导播/摄影',
                'propresenter_play': 'ProPresenter播放',
                'propresenter_update': 'ProPresenter更新'
            }
            for tech_field, tech_name in tech_roles.items():
                if record['technical'][tech_field]['name']:
                    person_id = record['technical'][tech_field]['id']
                    all_volunteers.append({
                        'person_id': person_id,
                        'person_name': record['technical'][tech_field]['name'],
                        'role': tech_name,
                        'is_available': metadata_dict.get(person_id, {}).get('is_available', True),
                        'metadata': metadata_dict.get(person_id, {})
                    })
                    unique_volunteers.add(person_id)
        
        # 统计不可用的同工
        unavailable_volunteers = [v for v in all_volunteers if not v['is_available']]
        
        return {
            'success': True,
            'week_info': {
                'week_start': week_start,
                'week_end': week_end,
                'sunday_date': next_sunday,
                'is_next_week': True
            },
            'services': next_week_records,
            'volunteers': all_volunteers,
            'summary': {
                'total_volunteers': len(all_volunteers),
                'unique_volunteers': len(unique_volunteers),
                'unavailable_count': len(unavailable_volunteers),
                'unavailable_list': unavailable_volunteers
            },
            'timestamp': datetime.utcnow().isoformat() + 'Z'
        }
    
    except Exception as e:
        logger.error(f"获取下周同工安排失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"获取下周同工安排失败: {str(e)}"
        )


@app.post("/api/v1/volunteer/conflicts")
async def check_volunteer_conflicts(request: ConflictCheckRequest):
    """
    检测排班冲突 (Tool: check_conflicts)
    """
    try:
        volunteer_file = Path('logs/service_layer/volunteer.json')
        
        if not volunteer_file.exists():
            raise HTTPException(
                status_code=404,
                detail="同工域数据不存在，请先生成服务层数据"
            )
        
        with open(volunteer_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        volunteers = data['volunteers']
        
        # 按年月筛选
        if request.year_month:
            volunteers = [v for v in volunteers if v['service_date'].startswith(request.year_month)]
        
        # 获取元数据
        metadata_response = await get_volunteer_metadata()
        metadata_dict = {}
        family_groups = {}
        
        if metadata_response['success']:
            for vol in metadata_response['volunteers']:
                metadata_dict[vol['person_id']] = vol
                if vol['family_group']:
                    if vol['family_group'] not in family_groups:
                        family_groups[vol['family_group']] = []
                    family_groups[vol['family_group']].append(vol['person_id'])
        
        conflicts = []
        
        # 按周分组检查
        weekly_assignments = {}
        for record in volunteers:
            service_date = record['service_date']
            week_start, week_end = get_week_range(service_date)
            week_key = f"{week_start}_to_{week_end}"
            
            if week_key not in weekly_assignments:
                weekly_assignments[week_key] = {
                    'week_start': week_start,
                    'week_end': week_end,
                    'sunday_date': service_date,
                    'volunteers': []
                }
            
            # 收集该周所有服侍的人
            volunteers_this_service = []
            
            # 敬拜主领
            if record['worship']['lead']['name']:
                volunteers_this_service.append({
                    'person_id': record['worship']['lead']['id'],
                    'person_name': record['worship']['lead']['name'],
                    'role': '敬拜主领',
                    'service_date': service_date
                })
            
            # 敬拜团队
            for member in record['worship']['team']:
                if member['name']:
                    volunteers_this_service.append({
                        'person_id': member['id'],
                        'person_name': member['name'],
                        'role': '敬拜同工',
                        'service_date': service_date
                    })
            
            # 司琴
            if record['worship']['pianist']['name']:
                volunteers_this_service.append({
                    'person_id': record['worship']['pianist']['id'],
                    'person_name': record['worship']['pianist']['name'],
                    'role': '司琴',
                    'service_date': service_date
                })
            
            # 技术岗位
            tech_roles = {
                'audio': '音控',
                'video': '导播/摄影',
                'propresenter_play': 'ProPresenter播放',
                'propresenter_update': 'ProPresenter更新'
            }
            for tech_field, tech_name in tech_roles.items():
                if record['technical'][tech_field]['name']:
                    volunteers_this_service.append({
                        'person_id': record['technical'][tech_field]['id'],
                        'person_name': record['technical'][tech_field]['name'],
                        'role': tech_name,
                        'service_date': service_date
                    })
            
            weekly_assignments[week_key]['volunteers'].extend(volunteers_this_service)
        
        # 检查1: 家庭成员冲突
        if request.check_family:
            for week_key, week_data in weekly_assignments.items():
                person_ids_this_week = set([v['person_id'] for v in week_data['volunteers']])
                
                for family_group, members in family_groups.items():
                    # 检查该周是否有多个家庭成员服侍
                    members_serving = [m for m in members if m in person_ids_this_week]
                    
                    if len(members_serving) > 1:
                        affected_persons = []
                        for person_id in members_serving:
                            # 找到该人的服侍记录
                            person_records = [v for v in week_data['volunteers'] if v['person_id'] == person_id]
                            if person_records:
                                affected_persons.extend(person_records)
                        
                        conflicts.append({
                            'type': 'family_conflict',
                            'severity': 'warning',
                            'week': week_data['sunday_date'],
                            'week_range': f"{week_data['week_start']} 到 {week_data['week_end']}",
                            'description': f"{', '.join([p['person_name'] for p in affected_persons])} 是家庭成员，在同一周服侍",
                            'affected_persons': affected_persons,
                            'family_group': family_group,
                            'suggestion': "建议将其中一人调整到其他周"
                        })
        
        # 检查2: 不可用时间段冲突
        if request.check_availability:
            for week_key, week_data in weekly_assignments.items():
                for volunteer in week_data['volunteers']:
                    person_id = volunteer['person_id']
                    service_date = volunteer['service_date']
                    
                    if person_id in metadata_dict:
                        metadata = metadata_dict[person_id]
                        unavailable_start = metadata.get('unavailable_start')
                        unavailable_end = metadata.get('unavailable_end')
                        
                        if unavailable_start and unavailable_end:
                            if is_date_in_range(service_date, unavailable_start, unavailable_end):
                                conflicts.append({
                                    'type': 'unavailability_conflict',
                                    'severity': 'error',
                                    'week': service_date,
                                    'description': f"{volunteer['person_name']} 在 {unavailable_start} 到 {unavailable_end} 期间不可用，但被安排服侍",
                                    'affected_persons': [volunteer],
                                    'unavailable_reason': metadata.get('unavailable_reason', ''),
                                    'suggestion': "需要重新安排其他人"
                                })
        
        # 统计摘要
        summary = {
            'total_conflicts': len(conflicts),
            'by_severity': {
                'error': len([c for c in conflicts if c['severity'] == 'error']),
                'warning': len([c for c in conflicts if c['severity'] == 'warning'])
            },
            'by_type': {}
        }
        
        for conflict in conflicts:
            conflict_type = conflict['type']
            summary['by_type'][conflict_type] = summary['by_type'].get(conflict_type, 0) + 1
        
        return {
            'success': True,
            'conflicts': conflicts,
            'summary': summary,
            'timestamp': datetime.utcnow().isoformat() + 'Z'
        }
    
    except Exception as e:
        logger.error(f"检测冲突失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"检测冲突失败: {str(e)}"
        )


@app.post("/api/v1/volunteer/suggestions")
async def get_volunteer_suggestions(request: SuggestionRequest):
    """
    获取排班建议 (Tool: get_suggestions)
    
    基于同工的可用性、家庭关系、服侍频率等因素，为指定日期和岗位提供排班建议。
    """
    try:
        # 读取同工统计数据
        stats_response = await get_volunteer_stats()
        if not stats_response['metadata']['total_volunteers']:
            raise HTTPException(
                status_code=404,
                detail="同工统计数据不存在"
            )
        
        volunteer_stats = {v['person_id']: v for v in stats_response['volunteers']}
        
        # 获取元数据
        metadata_response = await get_volunteer_metadata()
        metadata_dict = {}
        family_groups = {}
        
        if metadata_response['success']:
            for vol in metadata_response['volunteers']:
                metadata_dict[vol['person_id']] = vol
                if vol['family_group']:
                    if vol['family_group'] not in family_groups:
                        family_groups[vol['family_group']] = []
                    family_groups[vol['family_group']].append(vol['person_id'])
        
        # 获取该周已有的安排
        service_date = request.service_date
        week_start, week_end = get_week_range(service_date)
        
        volunteer_file = Path('logs/service_layer/volunteer.json')
        existing_volunteers_this_week = set()
        
        if volunteer_file.exists():
            with open(volunteer_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # 找出该周已服侍的人
            for record in data['volunteers']:
                if week_start <= record['service_date'] <= week_end:
                    # 收集所有人员ID
                    if record['worship']['lead']['name']:
                        existing_volunteers_this_week.add(record['worship']['lead']['id'])
                    for member in record['worship']['team']:
                        if member['name']:
                            existing_volunteers_this_week.add(member['id'])
                    if record['worship']['pianist']['name']:
                        existing_volunteers_this_week.add(record['worship']['pianist']['id'])
                    for tech_field in ['audio', 'video', 'propresenter_play', 'propresenter_update']:
                        if record['technical'][tech_field]['name']:
                            existing_volunteers_this_week.add(record['technical'][tech_field]['id'])
        
        # 为每个岗位生成建议
        suggestions = []
        
        for role in request.required_roles:
            candidates = []
            
            # 遍历所有同工，计算推荐分数
            for person_id, stats in volunteer_stats.items():
                person_metadata = metadata_dict.get(person_id, {})
                
                # 基础分数
                score = 50
                reasons = []
                concerns = []
                
                # 检查1: 时间可用性
                if request.consider_availability:
                    unavailable_start = person_metadata.get('unavailable_start')
                    unavailable_end = person_metadata.get('unavailable_end')
                    
                    if unavailable_start and unavailable_end:
                        if is_date_in_range(service_date, unavailable_start, unavailable_end):
                            score -= 100  # 不可用，直接排除
                            concerns.append(f"时间不可用（{person_metadata.get('unavailable_reason', '不可用')}）")
                        else:
                            score += 10
                            reasons.append("时间可用")
                    else:
                        score += 10
                        reasons.append("时间可用")
                
                # 检查2: 家庭成员冲突
                if request.consider_family:
                    family_group = person_metadata.get('family_group')
                    if family_group and family_group in family_groups:
                        family_members = family_groups[family_group]
                        # 检查是否有家庭成员已在该周服侍
                        family_conflict = any(m in existing_volunteers_this_week for m in family_members)
                        if family_conflict:
                            score -= 30
                            concerns.append("家庭成员本周已服侍")
                        else:
                            score += 10
                            reasons.append("无家庭成员冲突")
                
                # 检查3: 服侍均衡度
                if request.consider_balance:
                    total_services = stats.get('total_services', 0)
                    unique_dates = stats.get('unique_dates', 0)
                    
                    # 服侍较少的同工加分
                    if unique_dates < 5:
                        score += 20
                        reasons.append(f"服侍次数较少（{unique_dates}次）")
                    elif unique_dates < 10:
                        score += 10
                        reasons.append(f"服侍次数适中（{unique_dates}次）")
                    else:
                        score -= 10
                        concerns.append(f"服侍较频繁（{unique_dates}次）")
                    
                    # 检查近期是否服侍
                    date_range = stats.get('date_range', {})
                    if date_range.get('last'):
                        last_service = pd.to_datetime(date_range['last'])
                        target_date = pd.to_datetime(service_date)
                        days_since_last = (target_date - last_service).days
                        
                        if days_since_last < 7:
                            score -= 20
                            concerns.append(f"上周刚服侍过（{date_range['last']}）")
                        elif days_since_last < 14:
                            score -= 10
                            concerns.append(f"近期服侍过（{date_range['last']}）")
                        else:
                            score += 10
                            reasons.append("距离上次服侍已有一段时间")
                
                # 检查4: 岗位匹配（根据备注）
                notes = person_metadata.get('notes', '')
                if notes:
                    if role in notes or '优先' in notes:
                        score += 15
                        reasons.append(f"备注：{notes}")
                
                # 检查5: 该周是否已服侍
                if person_id in existing_volunteers_this_week:
                    score -= 30
                    concerns.append("本周已在其他日期服侍")
                
                # 只保留分数>0的候选人
                if score > 0:
                    candidates.append({
                        'person_id': person_id,
                        'person_name': stats['person_name'],
                        'score': score,
                        'reasons': reasons,
                        'concerns': concerns,
                        'statistics': {
                            'total_services': stats.get('total_services', 0),
                            'unique_dates': stats.get('unique_dates', 0),
                            'roles': stats.get('roles', {})
                        }
                    })
            
            # 按分数排序
            candidates.sort(key=lambda x: x['score'], reverse=True)
            
            # 只返回前5名
            suggestions.append({
                'role': role,
                'candidates': candidates[:5]
            })
        
        return {
            'success': True,
            'service_date': service_date,
            'week_range': f"{week_start} 到 {week_end}",
            'suggestions': suggestions,
            'timestamp': datetime.utcnow().isoformat() + 'Z'
        }
    
    except Exception as e:
        logger.error(f"获取排班建议失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"获取排班建议失败: {str(e)}"
        )


# ============================================================
# 启动配置
# ============================================================

if __name__ == "__main__":
    import uvicorn
    
    # 从环境变量获取端口，默认 8080（Cloud Run 标准端口）
    port = int(os.getenv('PORT', 8080))
    
    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=port,
        log_level="info"
    )

