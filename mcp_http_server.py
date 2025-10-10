#!/usr/bin/env python3
"""
MCP HTTP/SSE Server Implementation
提供基于 HTTP 和 Server-Sent Events 的 MCP 传输层
用于远程部署到 Cloud Run
"""

import os
import sys
import json
import logging
import asyncio
from pathlib import Path
from typing import Any, Dict, Optional
from datetime import datetime

from fastapi import FastAPI, Request, HTTPException, Header, Depends
from fastapi.responses import StreamingResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent))

# 导入 MCP Server 处理函数
import mcp_server

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# FastAPI 应用
app = FastAPI(
    title="Ministry Data MCP HTTP Server",
    description="MCP Server with HTTP/SSE Transport for Cloud Run",
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

# 鉴权配置
BEARER_TOKEN = os.getenv("MCP_BEARER_TOKEN", "")
REQUIRE_AUTH = os.getenv("MCP_REQUIRE_AUTH", "true").lower() == "true"


# ============================================================
# 鉴权依赖
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
# Pydantic 模型
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
# MCP 协议处理
# ============================================================

async def handle_mcp_request(request: MCPRequest) -> MCPResponse:
    """处理 MCP JSON-RPC 请求"""
    try:
        method = request.method
        params = request.params or {}
        
        # 路由到对应的 MCP Server 处理器
        if method == "tools/list":
            result = await mcp_server.handle_list_tools()
            return MCPResponse(
                id=request.id,
                result={"tools": [tool.model_dump() for tool in result]}
            )
        
        elif method == "tools/call":
            name = params.get("name")
            arguments = params.get("arguments", {})
            result = await mcp_server.handle_call_tool(name, arguments)
            return MCPResponse(
                id=request.id,
                result={"content": [item.model_dump() for item in result]}
            )
        
        elif method == "resources/list":
            result = await mcp_server.handle_list_resources()
            return MCPResponse(
                id=request.id,
                result={"resources": [res.model_dump() for res in result]}
            )
        
        elif method == "resources/read":
            uri = params.get("uri")
            result = await mcp_server.handle_read_resource(uri)
            return MCPResponse(
                id=request.id,
                result={"contents": [{"uri": uri, "mimeType": "application/json", "text": result}]}
            )
        
        elif method == "prompts/list":
            result = await mcp_server.handle_list_prompts()
            return MCPResponse(
                id=request.id,
                result={"prompts": [prompt.model_dump() for prompt in result]}
            )
        
        elif method == "prompts/get":
            name = params.get("name")
            arguments = params.get("arguments", {})
            result = await mcp_server.handle_get_prompt(name, arguments)
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
# HTTP 端点
# ============================================================

@app.get("/")
async def root():
    """根端点"""
    return {
        "service": "Ministry Data MCP Server",
        "version": "2.0.0",
        "protocol": "MCP (Model Context Protocol)",
        "transport": "HTTP/SSE",
        "endpoints": {
            "mcp": "/mcp",
            "mcp_sse": "/mcp/sse",
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
            "tools": {
                "listChanged": True
            },
            "resources": {
                "subscribe": False,
                "listChanged": True
            },
            "prompts": {
                "listChanged": True
            }
        },
        "serverInfo": {
            "name": "ministry-data",
            "version": "2.0.0",
            "description": "Church Ministry Data Management MCP Server"
        }
    }


@app.get("/mcp")
async def mcp_get_endpoint():
    """MCP 端点 - GET 方法用于验证和发现"""
    return {
        "name": "ministry-data",
        "version": "2.0.0",
        "protocol": "MCP",
        "transport": "HTTP/SSE",
        "description": "Church Ministry Data Management MCP Server",
        "capabilities": {
            "tools": True,
            "resources": True,
            "prompts": True
        },
        "endpoints": {
            "tools": "/mcp/tools",
            "resources": "/mcp/resources",
            "prompts": "/mcp/prompts"
        }
    }


@app.post("/mcp")
async def mcp_endpoint(
    request: MCPRequest,
    authorized: bool = Depends(verify_bearer_token)
) -> MCPResponse:
    """MCP JSON-RPC 端点（HTTP POST）"""
    return await handle_mcp_request(request)


@app.post("/mcp/sse")
async def mcp_sse_endpoint(
    request: Request,
    authorized: bool = Depends(verify_bearer_token)
):
    """MCP SSE (Server-Sent Events) 端点"""
    
    async def event_generator():
        """生成 SSE 事件流"""
        try:
            # 读取请求体
            body = await request.body()
            request_data = json.loads(body) if body else {}
            
            # 处理 MCP 请求
            mcp_request = MCPRequest(**request_data)
            response = await handle_mcp_request(mcp_request)
            
            # 发送 SSE 事件
            yield f"data: {response.model_dump_json()}\n\n"
        
        except Exception as e:
            logger.error(f"Error in SSE endpoint: {e}")
            error_response = MCPResponse(
                error={
                    "code": -32603,
                    "message": f"Internal error: {str(e)}"
                }
            )
            yield f"data: {error_response.model_dump_json()}\n\n"
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"  # 禁用 Nginx 缓冲
        }
    )


# ============================================================
# 便捷端点（直接访问 MCP 功能）
# ============================================================

@app.get("/mcp/tools")
async def list_tools(authorized: bool = Depends(verify_bearer_token)):
    """列出所有工具"""
    request = MCPRequest(method="tools/list")
    response = await handle_mcp_request(request)
    return response.result


@app.post("/mcp/tools/{tool_name}")
async def call_tool(
    tool_name: str,
    arguments: Dict[str, Any],
    authorized: bool = Depends(verify_bearer_token)
):
    """调用指定工具"""
    request = MCPRequest(
        method="tools/call",
        params={"name": tool_name, "arguments": arguments}
    )
    response = await handle_mcp_request(request)
    if response.error:
        raise HTTPException(status_code=500, detail=response.error)
    return response.result


@app.get("/mcp/resources")
async def list_resources(authorized: bool = Depends(verify_bearer_token)):
    """列出所有资源"""
    request = MCPRequest(method="resources/list")
    response = await handle_mcp_request(request)
    return response.result


@app.get("/mcp/resources/read")
async def read_resource(
    uri: str,
    authorized: bool = Depends(verify_bearer_token)
):
    """读取指定资源"""
    request = MCPRequest(
        method="resources/read",
        params={"uri": uri}
    )
    response = await handle_mcp_request(request)
    if response.error:
        raise HTTPException(status_code=500, detail=response.error)
    return response.result


@app.get("/mcp/prompts")
async def list_prompts(authorized: bool = Depends(verify_bearer_token)):
    """列出所有提示词"""
    request = MCPRequest(method="prompts/list")
    response = await handle_mcp_request(request)
    return response.result


@app.get("/mcp/prompts/{prompt_name}")
async def get_prompt(
    prompt_name: str,
    arguments: Optional[Dict[str, Any]] = None,
    authorized: bool = Depends(verify_bearer_token)
):
    """获取指定提示词"""
    request = MCPRequest(
        method="prompts/get",
        params={"name": prompt_name, "arguments": arguments or {}}
    )
    response = await handle_mcp_request(request)
    if response.error:
        raise HTTPException(status_code=500, detail=response.error)
    return response.result


# ============================================================
# 启动服务器
# ============================================================

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8080))
    
    logger.info("=" * 60)
    logger.info("Starting Ministry Data MCP HTTP Server")
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

