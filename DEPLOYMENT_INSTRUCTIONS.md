# Deployment Instructions - SSE Transport Update

## Summary of Changes

The MCP server has been updated with **proper SSE (Server-Sent Events) transport** to enable OpenAI ChatGPT integration.

### Files Created
- `mcp_local/sse_transport.py` - New SSE transport implementation

### Files Modified
- `mcp_local/mcp_server.py` - Added `/sse` endpoint, removed incompatible REST endpoints
- `deploy/deploy-mcp.sh` - Updated deployment script for new endpoints
- `docs/OPENAI_ALIGNMENT.md` - Added SSE implementation documentation
- `docs/OPENAI_SETUP.md` - New OpenAI integration guide (created)

### Key Changes

1. **New SSE Endpoint**: `POST /sse`
   - Replaces old `/mcp` endpoint
   - Proper Server-Sent Events streaming
   - Bearer token authentication
   - Full MCP protocol support

2. **Removed Endpoints**:
   - `/mcp` (POST) - No longer needed
   - `/mcp/tools` (GET) - No longer needed
   - `/mcp/resources` (GET) - No longer needed
   - `/mcp/prompts` (GET) - No longer needed
   - `/mcp/capabilities` (GET) - No longer needed

3. **Kept Endpoints**:
   - `/` - Server info
   - `/health` - Health check
   - `/sse` - Main MCP endpoint (NEW)

## Deployment Steps

### Option 1: Using Deployment Script

```bash
cd /path/to/Grace-Irvine-Ministry-Clean

# Set environment variables
export GCP_PROJECT_ID=<your-actual-project-id>
export MCP_BEARER_TOKEN=c577d598601f7b8f01c02053f6db89081321fd3d27fc0cabb5deec1647dbfe42

# Run deployment script
bash deploy/deploy-mcp.sh
```

### Option 2: Manual Deployment

```bash
cd /path/to/Grace-Irvine-Ministry-Clean/mcp_local

# Deploy to Cloud Run
gcloud run deploy ministry-data-mcp \
  --source . \
  --region=us-central1 \
  --platform=managed \
  --allow-unauthenticated \
  --set-env-vars="MCP_BEARER_TOKEN=c577d598601f7b8f01c02053f6db89081321fd3d27fc0cabb5deec1647dbfe42,MCP_REQUIRE_AUTH=true" \
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

### 2. Test SSE Endpoint (Initialize)

```bash
curl -N \
  -H "Authorization: Bearer c577d598601f7b8f01c02053f6db89081321fd3d27fc0cabb5deec1647dbfe42" \
  -H "Content-Type: application/json" \
  -H "Accept: text/event-stream" \
  -X POST https://ministry-data-mcp-760303847302.us-central1.run.app/sse \
  -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{}}'
```

Expected response (SSE format):
```
event: message
data: {"jsonrpc":"2.0","id":1,"result":{"protocolVersion":"2024-11-05","capabilities":{...}}}
```

### 3. Test SSE Endpoint (List Tools)

```bash
curl -N \
  -H "Authorization: Bearer c577d598601f7b8f01c02053f6db89081321fd3d27fc0cabb5deec1647dbfe42" \
  -H "Content-Type: application/json" \
  -H "Accept: text/event-stream" \
  -X POST https://ministry-data-mcp-760303847302.us-central1.run.app/sse \
  -d '{"jsonrpc":"2.0","id":2,"method":"tools/list","params":{}}'
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
     - **Server URL**: `https://ministry-data-mcp-760303847302.us-central1.run.app/sse`
     - **Authentication**: `Bearer Token`
     - **Token**: `c577d598601f7b8f01c02053f6db89081321fd3d27fc0cabb5deec1647dbfe42`

3. **Verify Connection**
   - Should show "✅ Connected"
   - Should display "11 tools available"

## Troubleshooting

### Error: "This server does not expose any tools"

**Cause**: Server not deployed with latest code, or using wrong URL

**Solution**:
1. Verify you're using `/sse` endpoint (not `/mcp`)
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
mcp_local/
├── mcp_server.py          # Main server (updated)
├── sse_transport.py       # SSE transport (new)
├── Dockerfile             # Container config
├── cloudbuild.yaml        # Build config
└── README.md              # Documentation

docs/
├── OPENAI_SETUP.md        # OpenAI integration guide (new)
└── OPENAI_ALIGNMENT.md    # Alignment report (updated)

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
- [OPENAI_SETUP.md](docs/OPENAI_SETUP.md) - Detailed setup guide
- [OPENAI_ALIGNMENT.md](docs/OPENAI_ALIGNMENT.md) - Technical details
- [MCP_CLOUD_RUN_DEPLOYMENT.md](docs/MCP_CLOUD_RUN_DEPLOYMENT.md) - Deployment guide

---

**Implementation Date**: 2025-10-22
**Protocol Version**: MCP 2024-11-05
**Server Version**: 2.0.0

