# OpenAI Integration Setup Guide

This guide explains how to add the Ministry Data MCP Server to OpenAI ChatGPT.

## Prerequisites

- Deployed MCP server on Cloud Run (see [MCP_CLOUD_RUN_DEPLOYMENT.md](MCP_CLOUD_RUN_DEPLOYMENT.md))
- Bearer token for authentication (`MCP_BEARER_TOKEN`)

## Server URL

```
https://ministry-data-mcp-760303847302.us-central1.run.app/sse
```

## Adding to OpenAI ChatGPT

### Step 1: Open ChatGPT Settings

1. Go to [ChatGPT](https://chat.openai.com/)
2. Click on your profile icon
3. Select **Settings**
4. Navigate to **Model Context Protocol (MCP)**

### Step 2: Add MCP Server

1. Click **Add MCP Server**
2. Enter the following details:

   **Server Name**: `Ministry Data`
   
   **Server URL**: `https://ministry-data-mcp-760303847302.us-central1.run.app/sse`
   
   **Authentication Method**: `Bearer Token`
   
   **Bearer Token**: (Your `MCP_BEARER_TOKEN` from Cloud Run environment)

3. Click **Save**

### Step 3: Verify Connection

1. OpenAI will attempt to connect to the server
2. If successful, you should see:
   - ✅ **Connected**
   - Tools count (e.g., "11 tools available")

3. If connection fails, check:
   - Server is deployed and running
   - Bearer token is correct
   - No typos in the URL

## Using the MCP Server

Once connected, you can use natural language commands:

### Query Examples

```
"Show me next Sunday's volunteer assignments"

"Who is preaching on December 25th?"

"Analyze volunteer frequency for 2024"

"Generate a weekly preview for this Sunday"

"Check which roles need more volunteers"
```

### Available Tools

The server provides 11 tools:

1. **query_volunteers_by_date** - Query volunteer assignments for a specific date
2. **query_sermon_by_date** - Query sermon info for a specific date
3. **query_date_range** - Query all assignments within a date range
4. **check_upcoming_completeness** - Check upcoming schedule completeness
5. **generate_weekly_preview** - Generate Sunday preview report
6. **analyze_role_coverage** - Analyze role coverage and health
7. **analyze_preacher_rotation** - Analyze preacher rotation patterns
8. **analyze_sermon_series_progress** - Track sermon series progress
9. **analyze_volunteer_trends** - Analyze volunteer trends
10. **clean_ministry_data** - Clean and validate ministry data
11. **generate_service_layer** - Generate service layer data

### Available Prompts

The server also provides pre-built prompts for common tasks:

- Analyze preaching schedule
- Analyze volunteer balance
- Find scheduling gaps
- Check next Sunday volunteers
- Analyze volunteer frequency
- Generate Sunday preview
- And more...

## Authentication

The server requires Bearer token authentication:

```bash
Authorization: Bearer <your-token>
```

### Getting Your Token

1. Check Cloud Run environment variables:
   ```bash
   gcloud run services describe ministry-data-mcp \
     --region=us-central1 \
     --format='value(spec.template.spec.containers[0].env[?name=="MCP_BEARER_TOKEN"].value)'
   ```

2. Or check your deployment configuration in `mcp_local/cloudbuild.yaml`

### Security Notes

- **Never share your Bearer token publicly**
- Rotate tokens periodically
- Use environment variables (never hardcode)
- Monitor access logs in Cloud Run

## Troubleshooting

### Error: "This server does not expose any tools"

**Cause**: Server is not responding with proper MCP protocol format

**Solution**: 
1. Ensure you're using the `/sse` endpoint (not `/mcp` or root)
2. Verify server is deployed with latest code
3. Check Cloud Run logs for errors

### Error: "401 Unauthorized"

**Cause**: Bearer token is missing or incorrect

**Solution**:
1. Verify Bearer token matches `MCP_BEARER_TOKEN` in Cloud Run
2. Ensure token is entered correctly (no extra spaces)

### Error: "Connection timeout"

**Cause**: Server is not reachable or slow to respond

**Solution**:
1. Check Cloud Run service is running
2. Verify URL is correct
3. Check Cloud Run logs for startup errors

### Error: "SSL certificate error"

**Cause**: HTTPS certificate issues

**Solution**:
1. Ensure using HTTPS (not HTTP)
2. Cloud Run automatically provides SSL certificates
3. Check for DNS/networking issues

## Deployment Commands

### Deploy to Cloud Run

```bash
cd /path/to/Grace-Irvine-Ministry-Clean

# Deploy with bearer token
gcloud run deploy ministry-data-mcp \
  --source ./mcp_local \
  --region=us-central1 \
  --platform=managed \
  --allow-unauthenticated \
  --set-env-vars="MCP_BEARER_TOKEN=<your-secret-token>,MCP_REQUIRE_AUTH=true"
```

### Update Environment Variables

```bash
# Update bearer token
gcloud run services update ministry-data-mcp \
  --region=us-central1 \
  --update-env-vars="MCP_BEARER_TOKEN=<new-token>"
```

### View Logs

```bash
# Stream logs
gcloud run services logs read ministry-data-mcp \
  --region=us-central1 \
  --follow

# View recent errors
gcloud run services logs read ministry-data-mcp \
  --region=us-central1 \
  --limit=50 \
  | grep ERROR
```

## API Endpoint Reference

### SSE Endpoint

**URL**: `POST /sse`

**Headers**:
```
Authorization: Bearer <token>
Content-Type: application/json
Accept: text/event-stream
```

**Request Body** (JSON-RPC 2.0):
```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "tools/list",
  "params": {}
}
```

**Response** (SSE stream):
```
event: message
data: {"jsonrpc":"2.0","id":1,"result":{"tools":[...]}}
```

### Health Check

**URL**: `GET /health`

**Response**:
```json
{
  "status": "healthy",
  "timestamp": "2025-10-22T12:00:00Z",
  "auth_required": true
}
```

## Testing with curl

### Test health endpoint

```bash
curl https://ministry-data-mcp-760303847302.us-central1.run.app/health
```

### Test SSE endpoint (initialize)

```bash
curl -N \
  -H "Authorization: Bearer <your-token>" \
  -H "Content-Type: application/json" \
  -H "Accept: text/event-stream" \
  -X POST \
  https://ministry-data-mcp-760303847302.us-central1.run.app/sse \
  -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{}}'
```

### Test tools/list

```bash
curl -N \
  -H "Authorization: Bearer <your-token>" \
  -H "Content-Type: application/json" \
  -H "Accept: text/event-stream" \
  -X POST \
  https://ministry-data-mcp-760303847302.us-central1.run.app/sse \
  -d '{"jsonrpc":"2.0","id":2,"method":"tools/list","params":{}}'
```

## Support

For issues or questions:
- Check [TROUBLESHOOTING.md](TROUBLESHOOTING.md)
- Review Cloud Run logs
- Verify bearer token and URL
- Ensure server is deployed with latest code

## Related Documentation

- [MCP Cloud Run Deployment](MCP_CLOUD_RUN_DEPLOYMENT.md)
- [OpenAI Alignment](OPENAI_ALIGNMENT.md)
- [API Endpoints](API_ENDPOINTS.md)
- [Architecture](ARCHITECTURE.md)

---

**Last Updated**: 2025-10-22
**Server Version**: 2.0.0
**Protocol Version**: MCP 2024-11-05

