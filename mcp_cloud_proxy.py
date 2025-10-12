#!/usr/bin/env python3
"""
MCP Cloud Proxy - Bridges Claude Desktop (stdio) to Cloud Run MCP Server (SSE)
This is a workaround for Claude Desktop versions that don't support SSE transport.
"""

import sys
import json
import requests
import logging
from typing import Any, Dict

# Configuration
CLOUD_RUN_URL = "https://ministry-data-mcp-wu7uk5rgdq-uc.a.run.app/mcp"
BEARER_TOKEN = "db1d18390fd3f1d632ed66e5216a834d37d03e14d920dd9c94670f274dd0cc30"

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.FileHandler('/tmp/mcp_cloud_proxy.log')]
)
logger = logging.getLogger(__name__)


def send_jsonrpc_request(method: str, params: Dict[str, Any] = None, request_id: int = 1) -> Dict[str, Any]:
    """Send a JSON-RPC request to the cloud MCP server."""
    headers = {
        "Authorization": f"Bearer {BEARER_TOKEN}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "jsonrpc": "2.0",
        "id": request_id,
        "method": method
    }
    
    if params:
        payload["params"] = params
    
    try:
        logger.info(f"Sending request: {method}")
        response = requests.post(CLOUD_RUN_URL, headers=headers, json=payload, timeout=30)
        response.raise_for_status()
        result = response.json()
        logger.info(f"Received response for: {method}")
        return result
    except Exception as e:
        logger.error(f"Error in request {method}: {str(e)}")
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "error": {
                "code": -32603,
                "message": f"Internal error: {str(e)}"
            }
        }


def handle_stdin_message(message: Dict[str, Any]) -> Dict[str, Any]:
    """Handle a JSON-RPC message from Claude Desktop."""
    method = message.get("method")
    params = message.get("params", {})
    request_id = message.get("id", 1)
    
    logger.info(f"Handling method: {method}")
    
    # Forward the request to cloud server
    return send_jsonrpc_request(method, params, request_id)


def main():
    """Main loop - read from stdin, forward to cloud, write to stdout."""
    logger.info("MCP Cloud Proxy started")
    logger.info(f"Connecting to: {CLOUD_RUN_URL}")
    
    try:
        # Read messages from stdin line by line
        for line in sys.stdin:
            line = line.strip()
            if not line:
                continue
            
            try:
                # Parse JSON-RPC message
                message = json.loads(line)
                logger.info(f"Received message: {message.get('method', 'unknown')}")
                
                # Handle the message
                response = handle_stdin_message(message)
                
                # Write response to stdout
                sys.stdout.write(json.dumps(response) + "\n")
                sys.stdout.flush()
                logger.info(f"Sent response: {response.get('result', {}).get('method', 'unknown')}")
                
            except json.JSONDecodeError as e:
                logger.error(f"JSON decode error: {str(e)}")
                error_response = {
                    "jsonrpc": "2.0",
                    "id": 1,
                    "error": {
                        "code": -32700,
                        "message": "Parse error"
                    }
                }
                sys.stdout.write(json.dumps(error_response) + "\n")
                sys.stdout.flush()
            except Exception as e:
                logger.error(f"Error handling message: {str(e)}")
                
    except KeyboardInterrupt:
        logger.info("MCP Cloud Proxy stopped by user")
    except Exception as e:
        logger.error(f"Fatal error: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()

