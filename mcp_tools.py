"""
MCP Client & Tool Management for Gort
Handles connection to MCP servers and tool execution
"""

import asyncio
import json
import subprocess
import sys
from typing import Any, Optional
from pathlib import Path

# MCP imports
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

# Environment setup
from dotenv import load_dotenv
import os

load_dotenv()

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
VERCEL_API_KEY = os.getenv("VERCEL_API_KEY")


class MCPToolManager:
    """Manages connections to MCP servers and tool execution"""
    
    def __init__(self):
        self.servers = {}
        self.tools = {}
        self.sessions = {}
    
    async def connect_github_server(self):
        """Connect to GitHub MCP server"""
        try:
            if not GITHUB_TOKEN:
                print("⚠️  GITHUB_TOKEN eksik. GitHub araçları kullanılamayacak.")
                return False
            
            # GitHub MCP server'ı stdio ile çalıştır
            server_params = StdioServerParameters(
                command=sys.executable,
                args=[str(Path(__file__).parent / "github_mcp_server.py")],
                env={"GITHUB_TOKEN": GITHUB_TOKEN}
            )
            
            read, write = await stdio_client(server_params).__aenter__()
            session = ClientSession(read, write)
            await session.__aenter__()
            await session.initialize()
            
            self.servers["github"] = {"read": read, "write": write, "session": session}
            
            # Tools listesini al
            tools_response = await session.list_tools()
            for tool in tools_response.tools:
                self.tools[tool.name] = {
                    "source": "github",
                    "description": tool.description,
                    "inputSchema": tool.inputSchema if hasattr(tool, 'inputSchema') else {}
                }
            
            print(f"✅ GitHub MCP Server bağlandı ({len(tools_response.tools)} tools)")
            return True
            
        except BaseException as e:
            print(f"❌ GitHub MCP Server bağlanamadı: {e}")
            return False
    
    async def connect_vercel_server(self):
        """Connect to custom Vercel MCP server"""
        try:
            if not VERCEL_API_KEY:
                print("⚠️  VERCEL_API_KEY eksik. Vercel araçları kullanılamayacak.")
                return False
            
            # Vercel MCP server'ını stdio ile çalıştır
            server_params = StdioServerParameters(
                command=sys.executable,
                args=[str(Path(__file__).parent / "vercel_mcp_server.py")],
                env={"VERCEL_API_KEY": VERCEL_API_KEY}
            )
            
            read, write = await stdio_client(server_params).__aenter__()
            session = ClientSession(read, write)
            await session.__aenter__()
            await session.initialize()
            
            self.servers["vercel"] = {"read": read, "write": write, "session": session}
            
            # Tools listesini al
            tools_response = await session.list_tools()
            for tool in tools_response.tools:
                self.tools[tool.name] = {
                    "source": "vercel",
                    "description": tool.description,
                    "inputSchema": tool.inputSchema if hasattr(tool, 'inputSchema') else {}
                }
            
            print(f"✅ Vercel MCP Server bağlandı ({len(tools_response.tools)} tools)")
            return True
            
        except BaseException as e:
            print(f"❌ Vercel MCP Server bağlanamadı: {e}")
            return False
    
    async def execute_tool(self, tool_name: str, arguments: dict) -> Optional[str]:
        """Execute a tool via MCP and return result"""
        if tool_name not in self.tools:
            return f"❌ Tool '{tool_name}' bulunamadı"
        
        tool_info = self.tools[tool_name]
        server_name = tool_info["source"]
        
        if server_name not in self.servers:
            return f"❌ '{server_name}' server'ı bağlı değil"
        
        try:
            session = self.servers[server_name]["session"]
            result = await session.call_tool(tool_name, arguments)
            return result.content[0].text if result.content else "No result"
        except Exception as e:
            return f"❌ Tool çalışırken hata: {e}"
    
    def get_tools_for_llm(self) -> list:
        """Return tools in DeepSeek API format"""
        tools_list = []
        for tool_name, tool_info in self.tools.items():
            tools_list.append({
                "type": "function",
                "function": {
                    "name": tool_name,
                    "description": tool_info.get("description", ""),
                    "parameters": tool_info.get("inputSchema", {})
                }
            })
        return tools_list
    
    async def close_all(self):
        """Close all MCP server connections"""
        for server_name, server_info in self.servers.items():
            try:
                await server_info["session"].__aexit__(None, None, None)
                print(f"✅ {server_name} server kapalı")
            except Exception as e:
                print(f"⚠️  {server_name} server kapatılırken hata: {e}")


# Global instance
mcp_manager = None


async def initialize_mcp():
    """Initialize MCP manager and connect servers"""
    global mcp_manager
    mcp_manager = MCPToolManager()
    
    print("\n🔗 MCP Servers bağlanıyor...\n")
    await mcp_manager.connect_github_server()
    await mcp_manager.connect_vercel_server()
    
    print(f"\n📦 Toplam {len(mcp_manager.tools)} tool kullanılabilir\n")
    return mcp_manager


def get_mcp_manager() -> MCPToolManager:
    """Get global MCP manager instance"""
    global mcp_manager
    if mcp_manager is None:
        raise RuntimeError("MCP manager not initialized. Call initialize_mcp() first.")
    return mcp_manager
