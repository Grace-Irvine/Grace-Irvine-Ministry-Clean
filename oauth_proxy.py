#!/usr/bin/env python3
"""
OAuth Proxy for ChatGPT Integration
Converts OAuth requests to Bearer Token requests for MCP server
"""

from flask import Flask, request, jsonify
import requests
import os

app = Flask(__name__)

# MCP Server Configuration
MCP_BASE_URL = "https://ministry-data-mcp-760303847302.us-central1.run.app"
MCP_BEARER_TOKEN = "c577d598601f7b8f01c02053f6db89081321fd3d27fc0cabb5deec1647dbfe42"

# OAuth Configuration (for ChatGPT)
OAUTH_CLIENT_ID = "your-oauth-client-id"
OAUTH_CLIENT_SECRET = "your-oauth-client-secret"

def verify_oauth_token(token):
    """
    Verify OAuth token (implement your OAuth verification logic)
    For now, we'll accept any token for demo purposes
    """
    # In production, verify the OAuth token with your OAuth provider
    return True

@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({"status": "healthy", "service": "oauth-proxy"})

@app.route('/mcp', methods=['POST'])
def mcp_proxy():
    """Proxy MCP requests with OAuth to Bearer Token"""
    
    # Get OAuth token from Authorization header
    auth_header = request.headers.get('Authorization', '')
    if not auth_header.startswith('Bearer '):
        return jsonify({"error": "Invalid authorization header"}), 401
    
    oauth_token = auth_header[7:]  # Remove 'Bearer ' prefix
    
    # Verify OAuth token
    if not verify_oauth_token(oauth_token):
        return jsonify({"error": "Invalid OAuth token"}), 401
    
    # Forward request to MCP server with Bearer Token
    headers = {
        "Authorization": f"Bearer {MCP_BEARER_TOKEN}",
        "Content-Type": "application/json"
    }
    
    try:
        response = requests.post(
            f"{MCP_BASE_URL}/mcp",
            headers=headers,
            json=request.json,
            timeout=30
        )
        
        return jsonify(response.json()), response.status_code
        
    except requests.exceptions.RequestException as e:
        return jsonify({"error": f"Proxy error: {str(e)}"}), 500

@app.route('/mcp/tools', methods=['GET'])
def mcp_tools():
    """Get MCP tools"""
    auth_header = request.headers.get('Authorization', '')
    if not auth_header.startswith('Bearer '):
        return jsonify({"error": "Invalid authorization header"}), 401
    
    oauth_token = auth_header[7:]
    if not verify_oauth_token(oauth_token):
        return jsonify({"error": "Invalid OAuth token"}), 401
    
    headers = {
        "Authorization": f"Bearer {MCP_BEARER_TOKEN}",
        "Content-Type": "application/json"
    }
    
    try:
        response = requests.get(
            f"{MCP_BASE_URL}/mcp/tools",
            headers=headers,
            timeout=30
        )
        
        return jsonify(response.json()), response.status_code
        
    except requests.exceptions.RequestException as e:
        return jsonify({"error": f"Proxy error: {str(e)}"}), 500

@app.route('/mcp/capabilities', methods=['GET'])
def mcp_capabilities():
    """Get MCP capabilities"""
    auth_header = request.headers.get('Authorization', '')
    if not auth_header.startswith('Bearer '):
        return jsonify({"error": "Invalid authorization header"}), 401
    
    oauth_token = auth_header[7:]
    if not verify_oauth_token(oauth_token):
        return jsonify({"error": "Invalid OAuth token"}), 401
    
    headers = {
        "Authorization": f"Bearer {MCP_BEARER_TOKEN}",
        "Content-Type": "application/json"
    }
    
    try:
        response = requests.get(
            f"{MCP_BASE_URL}/mcp/capabilities",
            headers=headers,
            timeout=30
        )
        
        return jsonify(response.json()), response.status_code
        
    except requests.exceptions.RequestException as e:
        return jsonify({"error": f"Proxy error: {str(e)}"}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080, debug=True)
