# Claude Desktop Config Error Fix

## Problem

Claude Desktop shows this error:
```
There was an error reading or parsing claude_desktop_config.json:
"code": "invalid_type",
"expected": "string", 
"received": "undefined",
"path": ["mcpServers", "ministry-data", "command"],
"message": "Required"
```

This occurs when using SSE transport configuration because some versions of Claude Desktop don't fully support SSE transport yet and still require a `command` field.

## Solutions

### Solution 1: Update Claude Desktop (Recommended)

1. **Update Claude Desktop** to the latest version
2. **Restart** Claude Desktop
3. **Use the SSE config** (should work with newer versions):

```json
{
  "mcpServers": {
    "ministry-data": {
      "url": "https://ministry-data-mcp-wu7uk5rgdq-uc.a.run.app/mcp/sse",
      "transport": "sse",
      "headers": {
        "Authorization": "Bearer db1d18390fd3f1d632ed66e5216a834d37d03e14d920dd9c94670f274dd0cc30"
      }
    }
  }
}
```

### Solution 2: Use stdio Proxy (Workaround)

If updating doesn't work or you need it to work right away, use the proxy bridge:

1. **Copy the proxy config** to Claude Desktop's config location:

   **macOS/Linux:**
   ```bash
   cp /Users/jonathan_jing/SynologyDrive/Study/AI/Grace-Irvine-Ministry-Clean/config/claude_desktop_config_cloud_stdio.json \
      ~/.config/Claude/claude_desktop_config.json
   ```

   **Windows:**
   ```powershell
   Copy-Item "C:\path\to\config\claude_desktop_config_cloud_stdio.json" `
      "$env:APPDATA\Claude\claude_desktop_config.json"
   ```

2. **Restart Claude Desktop:**

   **macOS:**
   ```bash
   killall Claude && open -a Claude
   ```

   **Windows:**
   - Close and reopen Claude Desktop

3. **Verify** it's working by checking Claude Desktop shows the "ministry-data" MCP server

## What the Proxy Does

The `mcp_cloud_proxy.py` script:
- Acts as a bridge between Claude Desktop (stdio) and your Cloud Run MCP server (HTTP/SSE)
- Receives JSON-RPC messages from Claude Desktop via stdin
- Forwards them to your cloud server with proper authentication
- Returns responses via stdout

## Configuration Files

### SSE Config (Direct Connection)
**File:** `config/claude_desktop_config_cloud.json`
- Requires Claude Desktop with full SSE support
- Direct connection to cloud server
- Lowest latency

### stdio Proxy Config (Bridge Connection)  
**File:** `config/claude_desktop_config_cloud_stdio.json`
- Works with all Claude Desktop versions
- Uses local proxy script
- Slightly higher latency but more compatible

## Testing

### Test the Proxy Manually
```bash
echo '{"jsonrpc":"2.0","id":1,"method":"tools/list"}' | \
  python3 /Users/jonathan_jing/SynologyDrive/Study/AI/Grace-Irvine-Ministry-Clean/mcp_cloud_proxy.py
```

You should see a list of available tools.

### Check Proxy Logs
```bash
tail -f /tmp/mcp_cloud_proxy.log
```

### Test the Cloud Service Directly
```bash
curl -H "Authorization: Bearer db1d18390fd3f1d632ed66e5216a834d37d03e14d920dd9c94670f274dd0cc30" \
  https://ministry-data-mcp-wu7uk5rgdq-uc.a.run.app/health
```

## Troubleshooting

### Proxy Connection Issues

1. **Check if service is running:**
   ```bash
   curl -H "Authorization: Bearer db1d18390fd3f1d632ed66e5216a834d37d03e14d920dd9c94670f274dd0cc30" \
     https://ministry-data-mcp-wu7uk5rgdq-uc.a.run.app/health
   ```

2. **Check proxy logs:**
   ```bash
   cat /tmp/mcp_cloud_proxy.log
   ```

3. **Verify Python packages:**
   ```bash
   pip3 install requests
   ```

### Claude Desktop Not Showing Server

1. **Check config file location:**
   - macOS/Linux: `~/.config/Claude/claude_desktop_config.json`
   - Windows: `%APPDATA%\Claude\claude_desktop_config.json`

2. **Validate JSON syntax:**
   ```bash
   python3 -m json.tool ~/.config/Claude/claude_desktop_config.json
   ```

3. **Check Claude Desktop logs:**
   - macOS: `~/Library/Logs/Claude/`
   - Windows: `%APPDATA%\Claude\logs\`

### Permission Issues

```bash
chmod +x /Users/jonathan_jing/SynologyDrive/Study/AI/Grace-Irvine-Ministry-Clean/mcp_cloud_proxy.py
```

## Which Solution Should You Use?

| Scenario | Recommended Solution |
|----------|---------------------|
| Latest Claude Desktop version | Solution 1 (SSE direct) |
| Older Claude Desktop version | Solution 2 (stdio proxy) |
| Need it working immediately | Solution 2 (stdio proxy) |
| Want lowest latency | Solution 1 (SSE direct) |
| Maximum compatibility | Solution 2 (stdio proxy) |

## Next Steps

After getting it working:

1. ✅ Verify MCP server shows up in Claude Desktop
2. ✅ Test a simple command (e.g., ask Claude about sermon records)
3. ✅ Check logs for any errors
4. ✅ Enjoy your cloud MCP server!

## Related Files

- **Proxy script:** `mcp_cloud_proxy.py`
- **SSE config:** `config/claude_desktop_config_cloud.json`
- **stdio config:** `config/claude_desktop_config_cloud_stdio.json`
- **Deployment docs:** `docs/MCP_CLOUD_RUN_DEPLOYMENT.md`
- **MCP design:** `docs/MCP_DESIGN.md`

---

**Created:** 2025-10-10  
**Updated:** 2025-10-10  
**Status:** ✅ Tested and working

