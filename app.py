#!/usr/bin/env python3
"""
FastAPI 应用 - 提供数据清洗 API 和定时任务触发端点
支持 Google Cloud Run 部署和 Cloud Scheduler 定时触发
同时提供 MCP (Model Context Protocol) 兼容的 API 端点
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

# 添加脚本目录到 Python 路径
sys.path.insert(0, str(Path(__file__).parent))

from scripts.clean_pipeline import CleaningPipeline

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# FastAPI 应用
app = FastAPI(
    title="Church Ministry Data Cleaning API",
    description="数据清洗管线 API - 支持 MCP (Model Context Protocol)",
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
    config_path: Optional[str] = None


class CleaningResponse(BaseModel):
    """清洗响应模型"""
    success: bool
    message: str
    total_rows: int
    success_rows: int
    warning_rows: int
    error_rows: int
    timestamp: str
    preview_available: bool = False


class HealthResponse(BaseModel):
    """健康检查响应"""
    status: str
    timestamp: str
    version: str


class DataQueryRequest(BaseModel):
    """数据查询请求（MCP 兼容）"""
    date_from: Optional[str] = None
    date_to: Optional[str] = None
    preacher: Optional[str] = None
    limit: int = 100


# ============================================================
# 工具函数
# ============================================================

def verify_scheduler_token(authorization: Optional[str] = None) -> bool:
    """
    验证 Cloud Scheduler 的认证令牌
    仅允许来自 Cloud Scheduler 的请求触发定时任务
    """
    if not authorization:
        return False
    
    # 从环境变量获取预期的令牌
    expected_token = os.getenv('SCHEDULER_TOKEN')
    if not expected_token:
        logger.warning("未设置 SCHEDULER_TOKEN 环境变量，跳过验证")
        return True
    
    # Bearer token 验证
    if not authorization.startswith('Bearer '):
        return False
    
    token = authorization[7:]
    return token == expected_token


def run_cleaning_pipeline(config_path: str, dry_run: bool = False) -> Dict[str, Any]:
    """
    运行清洗管线
    
    Args:
        config_path: 配置文件路径
        dry_run: 是否为干跑模式
        
    Returns:
        清洗结果摘要
    """
    try:
        pipeline = CleaningPipeline(config_path)
        
        # 读取原始数据
        raw_df = pipeline.read_source_data()
        total_rows = len(raw_df)
        
        # 清洗数据
        clean_df = pipeline.clean_data(raw_df)
        
        # 校验数据
        report = pipeline.validate_data(clean_df)
        
        # 写入输出
        pipeline.write_output(clean_df, dry_run=dry_run)
        
        return {
            'success': True,
            'message': '清洗管线执行成功',
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
        result = run_cleaning_pipeline(CONFIG_PATH, dry_run=False)
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
    
    logger.info(f"收到清洗请求: dry_run={request.dry_run}")
    
    try:
        result = run_cleaning_pipeline(config_path, dry_run=request.dry_run)
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
    获取最近一次清洗的预览数据（MCP 兼容）
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
    查询清洗后的数据（MCP 兼容）
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
    获取数据统计信息（MCP 兼容）
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
# MCP Tools Definition (用于 MCP 客户端)
# ============================================================

@app.get("/mcp/tools")
async def get_mcp_tools():
    """
    返回 MCP 工具定义
    让 MCP 客户端了解可用的 API 工具
    """
    return {
        "tools": [
            {
                "name": "query_ministry_data",
                "description": "查询教会主日事工数据，支持按日期范围、讲员等条件过滤",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "date_from": {
                            "type": "string",
                            "description": "开始日期 (YYYY-MM-DD)"
                        },
                        "date_to": {
                            "type": "string",
                            "description": "结束日期 (YYYY-MM-DD)"
                        },
                        "preacher": {
                            "type": "string",
                            "description": "讲员名称（支持部分匹配）"
                        },
                        "limit": {
                            "type": "integer",
                            "description": "返回记录数上限",
                            "default": 100
                        }
                    }
                }
            },
            {
                "name": "get_ministry_stats",
                "description": "获取教会主日事工数据的统计信息",
                "inputSchema": {
                    "type": "object",
                    "properties": {}
                }
            },
            {
                "name": "trigger_data_cleaning",
                "description": "触发数据清洗任务，更新清洗后的数据",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "dry_run": {
                            "type": "boolean",
                            "description": "是否为测试模式（不写入 Google Sheets）",
                            "default": False
                        }
                    }
                }
            }
        ]
    }


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

