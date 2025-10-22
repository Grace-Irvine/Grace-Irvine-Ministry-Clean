#!/usr/bin/env python3
"""
SSE Transport for MCP Server
Implements Server-Sent Events transport for OpenAI and other HTTP clients
"""

import json
import logging
import asyncio
from typing import Any, Dict, AsyncIterator, TYPE_CHECKING
from fastapi import Request
from sse_starlette.sse import EventSourceResponse

if TYPE_CHECKING:
    from mcp.server import Server

logger = logging.getLogger(__name__)


async def handle_sse_session(server, request: Request, handlers: Dict[str, Any]) -> EventSourceResponse:
    """
    Handle an SSE session for MCP communication
    
    Args:
        server: MCP Server instance
        request: FastAPI Request object
        handlers: Dict of handler functions (list_tools, call_tool, etc.)
    
    Returns:
        EventSourceResponse for streaming MCP messages
    """
    logger.info("New SSE session started")
    
    async def event_generator() -> AsyncIterator[Dict[str, Any]]:
        """Generate SSE events from MCP server responses"""
        try:
            # Read the request body (JSON-RPC messages)
            body = await request.body()
            
            if not body:
                # For initial connection, send endpoint info
                yield {
                    "event": "endpoint",
                    "data": json.dumps({
                        "type": "endpoint",
                        "endpoint": "/sse"
                    })
                }
                return
            
            # Parse JSON-RPC request
            try:
                message = json.loads(body)
                logger.info(f"Received MCP message: {message.get('method', 'unknown')}")
            except json.JSONDecodeError as e:
                logger.error(f"Invalid JSON in request: {e}")
                yield {
                    "event": "error",
                    "data": json.dumps({
                        "jsonrpc": "2.0",
                        "id": None,
                        "error": {
                            "code": -32700,
                            "message": "Parse error"
                        }
                    })
                }
                return
            
            # Route the message to appropriate handler
            method = message.get("method")
            params = message.get("params", {})
            msg_id = message.get("id")
            
            try:
                if method == "initialize":
                    # Handle initialization
                    response = {
                        "jsonrpc": "2.0",
                        "id": msg_id,
                        "result": {
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
                    }
                    
                elif method == "tools/list":
                    # List available tools
                    tools = await handlers["list_tools"]()
                    response = {
                        "jsonrpc": "2.0",
                        "id": msg_id,
                        "result": {
                            "tools": [tool.model_dump() for tool in tools]
                        }
                    }
                    
                elif method == "tools/call":
                    # Call a tool
                    tool_name = params.get("name")
                    arguments = params.get("arguments", {})
                    result = await handlers["call_tool"](tool_name, arguments)
                    response = {
                        "jsonrpc": "2.0",
                        "id": msg_id,
                        "result": {
                            "content": [item.model_dump() for item in result]
                        }
                    }
                    
                elif method == "resources/list":
                    # List available resources
                    resources = await handlers["list_resources"]()
                    response = {
                        "jsonrpc": "2.0",
                        "id": msg_id,
                        "result": {
                            "resources": [res.model_dump() for res in resources]
                        }
                    }
                    
                elif method == "resources/read":
                    # Read a resource
                    uri = params.get("uri")
                    content = await handlers["read_resource"](uri)
                    response = {
                        "jsonrpc": "2.0",
                        "id": msg_id,
                        "result": {
                            "contents": [{
                                "uri": uri,
                                "mimeType": "application/json",
                                "text": content
                            }]
                        }
                    }
                    
                elif method == "prompts/list":
                    # List available prompts
                    prompts = await handlers["list_prompts"]()
                    response = {
                        "jsonrpc": "2.0",
                        "id": msg_id,
                        "result": {
                            "prompts": [prompt.model_dump() for prompt in prompts]
                        }
                    }
                    
                elif method == "prompts/get":
                    # Get a specific prompt
                    prompt_name = params.get("name")
                    prompt_args = params.get("arguments", {})
                    result = await handlers["get_prompt"](prompt_name, prompt_args)
                    response = {
                        "jsonrpc": "2.0",
                        "id": msg_id,
                        "result": result.model_dump()
                    }
                    
                else:
                    # Method not found
                    response = {
                        "jsonrpc": "2.0",
                        "id": msg_id,
                        "error": {
                            "code": -32601,
                            "message": f"Method not found: {method}"
                        }
                    }
                
                # Yield the response as SSE event
                logger.info(f"Sending response for method: {method}")
                yield {
                    "event": "message",
                    "data": json.dumps(response)
                }
                
            except Exception as e:
                logger.error(f"Error handling MCP method {method}: {e}", exc_info=True)
                yield {
                    "event": "error",
                    "data": json.dumps({
                        "jsonrpc": "2.0",
                        "id": msg_id,
                        "error": {
                            "code": -32603,
                            "message": f"Internal error: {str(e)}"
                        }
                    })
                }
                
        except Exception as e:
            logger.error(f"SSE session error: {e}", exc_info=True)
            yield {
                "event": "error",
                "data": json.dumps({
                    "error": str(e)
                })
            }
    
    return EventSourceResponse(event_generator())

