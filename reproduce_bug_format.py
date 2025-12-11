
import sys
import os
from pathlib import Path

# Add project root to sys.path
project_root = Path(__file__).parent.absolute()
sys.path.insert(0, str(project_root))

try:
    from mcp.mcp_server import generate_weekly_preview
except ImportError as e:
    print(f"ImportError: {e}")
    print("Please run this script from the project root.")
    sys.exit(1)

def test_format_html():
    print("Testing generate_weekly_preview(format='html')...")
    # Using a date that likely exists or will be defaulted to next Sunday
    # But for deterministic testing, let's use a date we know or let it fail gracefully
    # If data load fails, it returns error string, which is fine for checking format logic if we mock data loading
    # But here we are integration testing.
    
    # Let's try to mock load_service_layer_data to return dummy data
    import mcp.mcp_server
    
    original_load = mcp.mcp_server.load_service_layer_data
    
    def mock_load(domain, year=None):
        if domain == 'volunteer':
            return {
                'volunteers': [{
                    'service_date': '2025-01-05',
                    'worship': {'lead': {'name': 'Test Lead'}}
                }]
            }
        if domain == 'sermon':
            return {
                'sermons': [{
                    'service_date': '2025-01-05',
                    'sermon': {'title': 'Test Sermon'},
                    'preacher': {'name': 'Test Preacher'}
                }]
            }
        return {}
        
    mcp.mcp_server.load_service_layer_data = mock_load
    
    result = generate_weekly_preview(date='2025-01-05', format='html')
    
    print(f"Result:\n{result}")
    
    if "<html>" in result or "<div>" in result or "<b>" in result:
        print("PASS: HTML format detected.")
    else:
        print("FAIL: HTML format NOT detected. Output seems to be plain text.")

    # Restore
    mcp.mcp_server.load_service_layer_data = original_load

if __name__ == "__main__":
    test_format_html()

