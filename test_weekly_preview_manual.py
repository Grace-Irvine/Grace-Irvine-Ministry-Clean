
import sys
import os
import json
import requests
import threading
import time
from datetime import datetime, timedelta

# Configuration
BASE_URL = "https://ministry-data-mcp-wu7uk5rgdq-uc.a.run.app"
SSE_URL = f"{BASE_URL}/sse"
TOKEN = "eb62345c492b2bd0848d7ee4f206be82604f66f938e3e87302e0329d2baf95ff"

headers = {
    "Authorization": f"Bearer {TOKEN}",
    "Accept": "text/event-stream"
}

def get_next_sunday():
    today = datetime.now()
    days_until_sunday = (6 - today.weekday()) % 7
    if days_until_sunday == 0:
        days_until_sunday = 7
    next_sunday = today + timedelta(days=days_until_sunday)
    return next_sunday.strftime("%Y-%m-%d")

def main():
    print(f"Connecting to {SSE_URL}...")
    
    # Session for persistent connection
    session = requests.Session()
    
    # Start SSE connection
    response = session.get(SSE_URL, headers=headers, stream=True)
    response.raise_for_status()
    
    print("Connected to SSE stream.")
    
    shared_data = {"post_endpoint": None}
    endpoint_event = threading.Event()
    
    def read_stream():
        for line in response.iter_lines():
            if line:
                decoded_line = line.decode('utf-8')
                # print(f"Stream: {decoded_line}")
                
                if decoded_line.startswith("data:"):
                    data_content = decoded_line[5:].strip()
                    
                    # Check for endpoint
                    if not shared_data["post_endpoint"] and ("http" in data_content or data_content.startswith("/")):
                         post_endpoint = data_content
                         if not post_endpoint.startswith("http"):
                             post_endpoint = f"{BASE_URL}{post_endpoint}"
                         print(f"Received POST endpoint: {post_endpoint}")
                         shared_data["post_endpoint"] = post_endpoint
                         endpoint_event.set()
                         continue

                    try:
                        json_data = json.loads(data_content)
                        # print(f"Received JSON: {json.dumps(json_data, indent=2)}")
                        
                        if "result" in json_data:
                            res = json_data["result"]
                            if "content" in res:
                                print("\n" + "="*50)
                                print("TOOL OUTPUT:")
                                for content in res["content"]:
                                    if content.get("type") == "text":
                                        print(content["text"])
                                print("="*50 + "\n")
                                # Exit after receiving result
                                os._exit(0) # Force exit threads
                                
                        if "error" in json_data:
                            print(f"Error: {json_data['error']}")
                            
                    except json.JSONDecodeError:
                        pass

    reader_thread = threading.Thread(target=read_stream)
    reader_thread.daemon = True
    reader_thread.start()
    
    # Wait for endpoint
    if not endpoint_event.wait(timeout=10):
        print("Timeout waiting for endpoint")
        return
    
    post_endpoint = shared_data["post_endpoint"]
        
    # Send Initialize
    rpc_headers = {
        "Authorization": f"Bearer {TOKEN}",
        "Content-Type": "application/json"
    }
    
    init_msg = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "test-client", "version": "1.0"}
        }
    }
    
    print("Sending initialize...")
    requests.post(post_endpoint, headers=rpc_headers, json=init_msg)
    
    time.sleep(1)
    
    # Send Notifications/initialized
    requests.post(post_endpoint, headers=rpc_headers, json={
        "jsonrpc": "2.0",
        "method": "notifications/initialized"
    })
    
    # Call Tool
    date_str = get_next_sunday()
    print(f"Calling generate_weekly_preview for {date_str}...")
    
    call_msg = {
        "jsonrpc": "2.0",
        "id": 2,
        "method": "tools/call",
        "params": {
            "name": "generate_weekly_preview",
            "arguments": {
                "date": date_str
            }
        }
    }
    
    requests.post(post_endpoint, headers=rpc_headers, json=call_msg)
    
    # Wait for response
    time.sleep(60)
    print("Timeout waiting for response")

if __name__ == "__main__":
    main()

