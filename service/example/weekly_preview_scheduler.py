#!/usr/bin/env python3
"""
每周事工预览定时器服务
通过 Cloud Scheduler 触发，调用 MCP Server 生成每周事工预览并发送邮件
"""

import os
import sys
import json
import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, Optional, List
from fastapi import FastAPI, HTTPException, Request, Header
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import uvicorn
from mcp.client.sse import sse_client
from mcp.client.session import ClientSession

# 尝试从 Secret Manager 读取敏感配置
try:
    sys.path.insert(0, str(Path(__file__).parent.parent.parent))
    from core.secret_manager_utils import get_token_from_manager, get_secret_from_manager
    USE_SECRET_MANAGER = True
except ImportError:
    USE_SECRET_MANAGER = False
    logger = logging.getLogger(__name__)

# 配置日志
if 'logger' not in locals():
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    logger = logging.getLogger(__name__)

# FastAPI 应用
app = FastAPI(
    title="Weekly Preview Scheduler",
    description="每周事工预览定时器服务",
    version="1.0.0"
)

# 配置（优先从环境变量读取，如果没有则从 Secret Manager 读取）
MCP_SERVER_URL = os.getenv('MCP_SERVER_URL', 'https://ministry-data-mcp-wu7uk5rgdq-uc.a.run.app')

# MCP Bearer Token - 从 Secret Manager 或环境变量读取
MCP_BEARER_TOKEN = os.getenv('MCP_BEARER_TOKEN')
if not MCP_BEARER_TOKEN and USE_SECRET_MANAGER:
    try:
        MCP_BEARER_TOKEN = get_token_from_manager(
            token_name="mcp-bearer-token",
            fallback_env_var="MCP_BEARER_TOKEN"
        )
        if MCP_BEARER_TOKEN:
            logger.info("✅ MCP Bearer Token loaded from Secret Manager")
    except Exception as e:
        logger.warning(f"Failed to load MCP_BEARER_TOKEN from Secret Manager: {e}")
if not MCP_BEARER_TOKEN:
    MCP_BEARER_TOKEN = os.getenv('MCP_BEARER_TOKEN', 'eb62345c492b2bd0848d7ee4f206be82604f66f938e3e87302e0329d2baf95ff')

# 邮件配置
SMTP_SERVER = os.getenv('SMTP_SERVER', 'smtp.gmail.com')
SMTP_PORT = int(os.getenv('SMTP_PORT', '587'))
SMTP_USER = os.getenv('SMTP_USER', 'jonathanjing@graceirvine.org')

# SMTP Password - 从 Secret Manager 或环境变量读取
SMTP_PASSWORD = os.getenv('SMTP_PASSWORD')
if not SMTP_PASSWORD and USE_SECRET_MANAGER:
    try:
        SMTP_PASSWORD = get_secret_from_manager(
            secret_name="weekly-preview-smtp-password",
            fallback_env_var="SMTP_PASSWORD"
        )
        if SMTP_PASSWORD:
            logger.info("✅ SMTP Password loaded from Secret Manager")
    except Exception as e:
        logger.warning(f"Failed to load SMTP_PASSWORD from Secret Manager: {e}")
if not SMTP_PASSWORD:
    SMTP_PASSWORD = os.getenv('SMTP_PASSWORD', '')

EMAIL_FROM = os.getenv('EMAIL_FROM', 'jonathanjing@graceirvine.org')
EMAIL_TO = os.getenv('EMAIL_TO', '').split(',')  # 支持多个收件人，用逗号分隔
EMAIL_CC = os.getenv('EMAIL_CC', '').split(',') if os.getenv('EMAIL_CC') else []

# Cloud Scheduler 认证 - 从 Secret Manager 或环境变量读取
SCHEDULER_TOKEN = os.getenv('SCHEDULER_TOKEN')
if not SCHEDULER_TOKEN and USE_SECRET_MANAGER:
    try:
        SCHEDULER_TOKEN = get_token_from_manager(
            token_name="weekly-preview-scheduler-token",
            fallback_env_var="SCHEDULER_TOKEN"
        )
        if SCHEDULER_TOKEN:
            logger.info("✅ Scheduler Token loaded from Secret Manager")
    except Exception as e:
        logger.warning(f"Failed to load SCHEDULER_TOKEN from Secret Manager: {e}")
if not SCHEDULER_TOKEN:
    SCHEDULER_TOKEN = os.getenv('SCHEDULER_TOKEN', '')


# ============================================================
# Pydantic 模型
# ============================================================

class SchedulerRequest(BaseModel):
    """定时器请求模型"""
    date: Optional[str] = None  # 可选，格式 YYYY-MM-DD，默认生成下一个周日
    format: str = "text"  # text, markdown, html
    year: Optional[str] = None


class HealthResponse(BaseModel):
    """健康检查响应"""
    status: str
    timestamp: str
    version: str


# ============================================================
# MCP 工具调用
# ============================================================

async def call_mcp_tool(
    tool_name: str,
    arguments: Dict[str, Any],
    timeout: int = 60
) -> Any:
    """
    调用 MCP Server 的工具
    
    Args:
        tool_name: 工具名称
        arguments: 工具参数
        timeout: 超时时间（秒）
    
    Returns:
        工具调用结果
    """
    # MCP Server 使用 /mcp 端点（HTTP/SSE）
    url = f"{MCP_SERVER_URL}/mcp"
    headers = {}
    
    if MCP_BEARER_TOKEN:
        headers["Authorization"] = f"Bearer {MCP_BEARER_TOKEN}"
    
    try:
        logger.info(f"Calling MCP tool: {tool_name} with args: {arguments}")
        logger.info(f"MCP Server URL: {url}")
        
        async with sse_client(url, headers=headers, timeout=timeout) as streams:
            async with ClientSession(streams[0], streams[1]) as session:
                await session.initialize()
                result = await session.call_tool(tool_name, arguments)
                logger.info(f"MCP tool call successful")
                return result
                
    except Exception as e:
        logger.error(f"Error calling MCP tool: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to call MCP tool: {str(e)}"
        )


# ============================================================
# 邮件发送
# ============================================================

def send_email(
    subject: str,
    body: str,
    html_body: Optional[str] = None
) -> bool:
    """
    发送邮件
    
    Args:
        subject: 邮件主题
        body: 邮件正文（纯文本）
        html_body: 邮件正文（HTML格式，可选）
    
    Returns:
        是否发送成功
    """
    if not SMTP_USER or not SMTP_PASSWORD:
        logger.error("SMTP credentials not configured")
        return False
    
    if not EMAIL_TO or not any(EMAIL_TO):
        logger.error("Email recipients not configured")
        return False
    
    try:
        # 创建邮件
        msg = MIMEMultipart('alternative')
        msg['From'] = EMAIL_FROM
        msg['To'] = ', '.join([email for email in EMAIL_TO if email])
        if EMAIL_CC and any(EMAIL_CC):
            msg['Cc'] = ', '.join([email for email in EMAIL_CC if email])
        msg['Subject'] = subject
        
        # 添加纯文本内容
        msg.attach(MIMEText(body, 'plain', 'utf-8'))
        
        # 如果有 HTML 内容，也添加
        if html_body:
            msg.attach(MIMEText(html_body, 'html', 'utf-8'))
        
        # 发送邮件
        recipients = [email for email in EMAIL_TO if email]
        if EMAIL_CC:
            recipients.extend([email for email in EMAIL_CC if email])
        
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_USER, SMTP_PASSWORD)
            server.send_message(msg, to_addrs=recipients)
        
        logger.info(f"Email sent successfully to {', '.join(recipients)}")
        return True
        
    except Exception as e:
        logger.error(f"Error sending email: {e}")
        return False


def convert_text_to_html(text: str) -> str:
    """
    将纯文本转换为 HTML 格式
    
    Args:
        text: 纯文本内容
    
    Returns:
        HTML 格式内容
    """
    # 简单的文本转 HTML
    html = text.replace('\n', '<br>\n')
    html = html.replace('📅', '📅')
    html = html.replace('📖', '📖')
    html = html.replace('👥', '👥')
    html = html.replace('🎵', '🎵')
    html = html.replace('📺', '📺')
    html = html.replace('👶', '👶')
    
    # 添加基本样式
    html_body = f"""
    <html>
    <head>
        <meta charset="UTF-8">
        <style>
            body {{
                font-family: Arial, sans-serif;
                line-height: 1.6;
                color: #333;
                max-width: 600px;
                margin: 0 auto;
                padding: 20px;
            }}
            h1 {{
                color: #2c3e50;
                border-bottom: 2px solid #3498db;
                padding-bottom: 10px;
            }}
            h2 {{
                color: #34495e;
                margin-top: 20px;
            }}
            .section {{
                margin: 15px 0;
                padding: 10px;
                background-color: #f8f9fa;
                border-left: 4px solid #3498db;
            }}
        </style>
    </head>
    <body>
        <div class="section">
            {html}
        </div>
    </body>
    </html>
    """
    return html_body


# ============================================================
# API 端点
# ============================================================

def verify_scheduler_token(authorization: Optional[str] = Header(None)) -> bool:
    """验证 Cloud Scheduler 的认证令牌"""
    if not SCHEDULER_TOKEN:
        logger.warning("SCHEDULER_TOKEN not configured, skipping authentication")
        return True
    
    if not authorization:
        return False
    
    if authorization.startswith('Bearer '):
        token = authorization[7:]
        return token == SCHEDULER_TOKEN
    return False


@app.get("/", response_model=HealthResponse)
async def root():
    """根端点 - 健康检查"""
    return HealthResponse(
        status="healthy",
        timestamp=datetime.now().isoformat(),
        version="1.0.0"
    )


@app.get("/health", response_model=HealthResponse)
async def health():
    """健康检查端点"""
    return HealthResponse(
        status="healthy",
        timestamp=datetime.now().isoformat(),
        version="1.0.0"
    )


@app.post("/trigger")
async def trigger_weekly_preview(
    request: Request,
    scheduler_request: Optional[SchedulerRequest] = None,
    authorization: Optional[str] = Header(None)
):
    """
    触发每周事工预览生成和邮件发送
    
    此端点由 Cloud Scheduler 定时调用（每周一早上9点）
    """
    # 验证认证令牌
    if not verify_scheduler_token(authorization):
        raise HTTPException(status_code=401, detail="Invalid or missing authorization token")
    
    try:
        # 如果没有提供日期，自动计算下一个周日
        if scheduler_request is None:
            scheduler_request = SchedulerRequest()
        
        date = scheduler_request.date
        if not date:
            # 计算下一个周日
            today = datetime.now()
            days_until_sunday = (6 - today.weekday()) % 7
            if days_until_sunday == 0:
                days_until_sunday = 7
            next_sunday = today + timedelta(days=days_until_sunday)
            date = next_sunday.strftime("%Y-%m-%d")
        
        # 调用 MCP Server 的 generate_weekly_preview 工具
        logger.info(f"Generating weekly preview for date: {date}")
        
        arguments = {
            "date": date,
            "format": scheduler_request.format or "text"
        }
        if scheduler_request.year:
            arguments["year"] = scheduler_request.year
        
        mcp_result = await call_mcp_tool("generate_weekly_preview", arguments)
        
        # 提取预览文本
        preview_text = ""
        if hasattr(mcp_result, 'content') and mcp_result.content:
            for content in mcp_result.content:
                if content.type == 'text':
                    preview_text += content.text
        
        if not preview_text:
             raise HTTPException(status_code=500, detail="Empty preview generated")
        
        logger.info("Weekly preview generated successfully")
        
        # 生成邮件主题和内容
        email_subject = f"主日预览 - {date}"
        
        # 发送邮件
        html_content = None
        if scheduler_request.format == "html" or scheduler_request.format == "markdown":
            html_content = convert_text_to_html(preview_text)
        
        email_sent = send_email(email_subject, preview_text, html_content)
        
        if not email_sent:
            raise HTTPException(status_code=500, detail="Failed to send email")
        
        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "message": "Weekly preview generated and email sent successfully",
                "date": date,
                "preview_length": len(preview_text),
                "email_sent": email_sent,
                "timestamp": datetime.now().isoformat()
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in trigger_weekly_preview: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )


# ============================================================
# 主函数
# ============================================================

def main():
    """启动 FastAPI 服务器"""
    port = int(os.getenv('PORT', '8080'))
    logger.info(f"Starting Weekly Preview Scheduler on port {port}")
    logger.info(f"MCP Server URL: {MCP_SERVER_URL}")
    logger.info(f"Email From: {EMAIL_FROM}")
    logger.info(f"Email To: {', '.join(EMAIL_TO) if EMAIL_TO else 'Not configured'}")
    
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=port,
        log_level="info"
    )


if __name__ == "__main__":
    main()
