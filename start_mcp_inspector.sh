#!/bin/bash
# MCP Inspector Startup Script
# Connects MCP Inspector to the Ministry Data MCP Server

echo "=========================================="
echo "Starting MCP Inspector"
echo "=========================================="
echo ""
echo "MCP Server: Ministry Data"
echo "Mode: stdio"
echo ""
echo "Opening MCP Inspector in your browser..."
echo "Press Ctrl+C to stop"
echo ""
echo "=========================================="

# Set the working directory
cd "$(dirname "$0")"

# Run MCP Inspector with the stdio server
npx @modelcontextprotocol/inspector python3 mcp/mcp_server.py

