
import os
import asyncio
import logging
from datetime import datetime, timedelta

from mcp.client.sse import sse_client
from mcp.client.session import ClientSession

# Manual test using the official MCP Python client against the canonical /mcp endpoint.
# (The older raw-SSE parsing approach was tied to a legacy /sse transport shape.)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

BASE_URL = os.getenv("MCP_BASE_URL", "https://ministry-data-mcp-wu7uk5rgdq-uc.a.run.app")
MCP_URL = f"{BASE_URL}/mcp"

def get_next_sunday() -> str:
    today = datetime.now()
    days_until_sunday = (6 - today.weekday()) % 7
    if days_until_sunday == 0:
        days_until_sunday = 7
    next_sunday = today + timedelta(days=days_until_sunday)
    return next_sunday.strftime("%Y-%m-%d")

async def main():
    token = os.getenv("MCP_BEARER_TOKEN", "")
    headers = {"Authorization": f"Bearer {token}"} if token else {}

    date_str = get_next_sunday()
    logger.info(f"Connecting to {MCP_URL}")
    logger.info(f"Calling generate_weekly_preview for {date_str}")

    async with sse_client(MCP_URL, headers=headers, timeout=60) as streams:
        async with ClientSession(streams[0], streams[1]) as session:
            await session.initialize()
            result = await session.call_tool("generate_weekly_preview", arguments={"date": date_str})

            print("\n" + "=" * 50)
            print("TOOL RESULT")
            print("=" * 50)

            if hasattr(result, "content") and result.content:
                for content in result.content:
                    if getattr(content, "type", None) == "text":
                        print(content.text)
            else:
                print(result)
            print("=" * 50 + "\n")

if __name__ == "__main__":
    asyncio.run(main())

