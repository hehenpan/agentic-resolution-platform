import os
import sys
import json
from pathlib import Path

# Add src and repo_root to sys.path
scripts_dir = Path(__file__).resolve().parent
repo_root = scripts_dir.parent.parent
server_src = scripts_dir.parent / "src"
if str(server_src) not in sys.path:
    sys.path.insert(0, str(server_src))
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

from main import mcp

import asyncio

async def export_metadata():
    # Retrieve FastMCP tools
    mcp_tools = await mcp.list_tools()
    
    tools_list = []
    for t in mcp_tools:
        tools_list.append({
            "type": "function",
            "function": {
                "name": t.name,
                "description": t.description,
                "parameters": t.inputSchema
            }
        })
        
    output_path = repo_root / "shared_common" / "schemas" / "mcp_server" / "tools_metadata.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(tools_list, f, indent=2, ensure_ascii=False)
        
    print(f"Successfully exported {len(tools_list)} tools to {output_path}")

if __name__ == "__main__":
    asyncio.run(export_metadata())
