
import os
import sys
import asyncio
import logging
from datetime import datetime, timedelta
from mcp.client.sse import sse_client
from mcp.client.session import ClientSession

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Configuration
MCP_SERVER_URL = "https://ministry-data-mcp-wu7uk5rgdq-uc.a.run.app/sse"

async def get_token():
    try:
        # Try to get from environment variable first
        token = os.environ.get("MCP_BEARER_TOKEN")
        if token:
            return token
            
        # Try to get from gcloud if not in env
        logger.info("Fetching token from Secret Manager...")
        process = await asyncio.create_subprocess_shell(
            "gcloud secrets versions access latest --secret='mcp-bearer-token' --project='ai-for-god'",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await process.communicate()
        
        if process.returncode == 0:
            return stdout.decode().strip()
        else:
            logger.error(f"Failed to get token: {stderr.decode()}")
            return None
    except Exception as e:
        logger.error(f"Error getting token: {e}")
        return None

async def test_weekly_preview():
    token = await get_token()
    if not token:
        logger.error("No Bearer Token available. Cannot authenticate.")
        return

    headers = {
        "Authorization": f"Bearer {token}"
    }
    
    # Calculate next Sunday
    today = datetime.now()
    days_until_sunday = (6 - today.weekday()) % 7
    if days_until_sunday == 0:
        days_until_sunday = 7
    next_sunday = today + timedelta(days=days_until_sunday)
    date_str = next_sunday.strftime("%Y-%m-%d")
    
    logger.info(f"Testing generate_weekly_preview for date: {date_str}")
    logger.info(f"Connecting to {MCP_SERVER_URL}...")

    try:
        async with sse_client(MCP_SERVER_URL, headers=headers, timeout=60) as streams:
            async with ClientSession(streams[0], streams[1]) as session:
                logger.info("Session initialized. Calling tool...")
                
                await session.initialize()
                
                result = await session.call_tool(
                    "generate_weekly_preview",
                    arguments={"date": date_str}
                )
                
                print("\n" + "="*50)
                print("TOOL RESULT")
                print("="*50)
                
                if hasattr(result, 'content') and result.content:
                    for content in result.content:
                        if content.type == 'text':
                            print(content.text)
                else:
                    print(result)
                
                print("="*50 + "\n")
                
    except Exception as e:
        logger.error(f"Error calling MCP tool: {e}")

if __name__ == "__main__":
    asyncio.run(test_weekly_preview())

