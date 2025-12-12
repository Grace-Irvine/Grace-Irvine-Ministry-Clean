# Deployment Instructions - MCP HTTP/SSE Endpoint Standardization

## Summary of Changes

The MCP server is exposed over HTTP using **MCP over SSE**. The canonical endpoint is now **`/mcp`**.

### Files Modified
- `mcp/mcp_server.py` / `service/mcp_server.py` - MCP server (stdio + HTTP/SSE) with `/sse -> /mcp` compat alias
- `deploy/deploy-mcp.sh` - Deployment script updated to use `/mcp`
- `deploy/deploy-all.sh` - Deployment summary updated to show `/mcp`
- Docs & examples updated to reference `/mcp`

### Key Changes

1. **Canonical MCP Endpoint**: `POST /mcp` (HTTP/SSE)
   - MCP over Server-Sent Events (SSE)
   - Bearer token authentication
   - Full MCP protocol support
   - Requires correct `Accept` header: `application/json, text/event-stream`

2. **Compatibility Alias**: `/sse`
   - Kept for older clients / scripts
   - Internally rewritten to `/mcp` on the server

## Deployment Steps

### Option 1: Using Deployment Script

```bash
cd /path/to/Grace-Irvine-Ministry-Clean

# Set environment variables
export GCP_PROJECT_ID=<your-actual-project-id>
export MCP_BEARER_TOKEN=<your-bearer-token>

# Run deployment script
bash deploy/deploy-mcp.sh
```

### Option 2: Manual Deployment

```bash
cd /path/to/Grace-Irvine-Ministry-Clean/mcp

# Deploy to Cloud Run
gcloud run deploy ministry-data-mcp \
  --source . \
  --region=us-central1 \
  --platform=managed \
  --allow-unauthenticated \
  --set-env-vars="MCP_BEARER_TOKEN=<your-bearer-token>,MCP_REQUIRE_AUTH=true" \
  --project=<your-project-id>
```

### Finding Your Project ID

```bash
# List all projects
gcloud projects list

# Or check the current deployed service
gcloud run services describe ministry-data-mcp \
  --region=us-central1 \
  --format='value(metadata.namespace)'
```

## Testing After Deployment

### 1. Test Health Endpoint

```bash
curl https://ministry-data-mcp-760303847302.us-central1.run.app/health
```

Expected response:
```json
{
  "status": "healthy",
  "timestamp": "2025-10-22T...",
  "auth_required": true
}
```

### 2. Test MCP Endpoint (Initialize)

```bash
curl -N -X POST \
  -H "Authorization: Bearer <your-bearer-token>" \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"curl-test","version":"0.0.0"}}}' \
  "https://ministry-data-mcp-760303847302.us-central1.run.app/mcp"
```

Expected response (SSE format):
```
event: message
data: {"jsonrpc":"2.0","id":1,"result":{"protocolVersion":"2024-11-05","capabilities":{...}}}
```

### 3. Test MCP Endpoint (List Tools)

```bash
curl -N -X POST \
  -H "Authorization: Bearer <your-bearer-token>" \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -d '{"jsonrpc":"2.0","id":2,"method":"tools/list","params":{}}' \
  "https://ministry-data-mcp-760303847302.us-central1.run.app/mcp"
```

Expected response should include 11 tools.

## Adding to OpenAI ChatGPT

Once deployed, add the MCP server to OpenAI:

1. **Open ChatGPT Settings**
   - Go to https://chat.openai.com/
   - Click profile icon → Settings
   - Navigate to "Model Context Protocol (MCP)"

2. **Add MCP Server**
   - Click "Add MCP Server"
   - Enter:
     - **Server Name**: `Ministry Data`
     - **Server URL**: `https://ministry-data-mcp-760303847302.us-central1.run.app/mcp`
     - **Authentication**: `Bearer Token`
     - **Token**: `<your-bearer-token>`

3. **Verify Connection**
   - Should show "✅ Connected"
   - Should display "11 tools available"

## Troubleshooting

### Error: "This server does not expose any tools"

**Cause**: Server not deployed with latest code, or using wrong URL

**Solution**:
1. Verify you're using the `/mcp` endpoint
2. Ensure the request sets: `Accept: application/json, text/event-stream`
2. Deploy the latest code
3. Check Cloud Run logs:
   ```bash
   gcloud run services logs read ministry-data-mcp --region=us-central1 --limit=50
   ```

### Error: "401 Unauthorized"

**Cause**: Bearer token mismatch

**Solution**:
1. Verify token in OpenAI matches deployment token
2. Check Cloud Run environment variables:
   ```bash
   gcloud run services describe ministry-data-mcp \
     --region=us-central1 \
     --format='value(spec.template.spec.containers[0].env)'
   ```

### Error: "Connection timeout"

**Cause**: Server not running or slow response

**Solution**:
1. Check service is running:
   ```bash
   gcloud run services describe ministry-data-mcp --region=us-central1
   ```
2. Check logs for startup errors
3. Verify service URL is correct

## Project Structure

```
mcp/
├── mcp_server.py          # Main server (updated)
├── Dockerfile             # Container config
├── cloudbuild.yaml        # Build config
└── README.md              # Documentation

文档已整合到主 README

deploy/
└── deploy-mcp.sh          # Deployment script (updated)
```

## Next Steps

1. ✅ **Code changes complete** - All files updated
2. ⏳ **Deploy to Cloud Run** - Run deployment command above
3. ⏳ **Test endpoints** - Verify health and SSE endpoints work
4. ⏳ **Add to OpenAI** - Configure in ChatGPT settings
5. ⏳ **Verify connection** - Check tools are exposed

## Support

For more information:
- [主README](README.md) - 完整项目文档
- [MCP服务器文档](service/README.md) - MCP 集成指南

---

**Protocol Version**: MCP 2024-11-05

