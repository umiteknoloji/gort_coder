"""
Gort FastAPI Server
Provides REST API and WebSocket endpoints for Gort chat
"""

from fastapi import FastAPI, WebSocket, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import asyncio
import json
import os
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv
import httpx
from pydantic import BaseModel
from typing import Optional, List

# Import Gort tools
from mcp_tools import initialize_mcp, get_mcp_manager

# Configuration
load_dotenv()
API_KEY = os.getenv("DEEPSEEK_API_KEY")
BASE_URL = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
MEMORY_FILE = "memory.json"
CONSTITUTION_FILE = "constitution.txt"

# Initialize FastAPI
app = FastAPI(title="Gort API", version="0.1.0")

# CORS middleware for Electron app
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# MCP initialization on startup
@app.on_event("startup")
async def startup_event():
    try:
        await initialize_mcp()
    except Exception as e:
        # Don't block server startup if MCP fails
        print(f"⚠️ MCP initialization failed: {e}")

# Pydantic models
class Message(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None

class ChatResponse(BaseModel):
    response: str
    session_id: str
    tool_used: Optional[str] = None

class SessionData(BaseModel):
    session_id: str
    created_at: str
    messages: List[Message]

# Global state
SESSIONS = {}  # session_id -> conversation


def get_available_tools() -> set:
    """Get all available tool names from MCP manager (if initialized)."""
    try:
        manager = get_mcp_manager()
        return set(manager.tools.keys())
    except Exception:
        return set()


def load_constitution() -> str:
    """Load Gort's constitution from file."""
    if not Path(CONSTITUTION_FILE).exists():
        return "Gort system constitution not found"
    with open(CONSTITUTION_FILE, "r", encoding="utf-8") as f:
        return f.read()


def create_new_session() -> str:
    """Create and return a new session ID"""
    session_id = f"gort-session-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
    SESSIONS[session_id] = {
        "session_id": session_id,
        "created_at": datetime.now().isoformat(),
        "messages": []
    }
    return session_id


def get_chat_completions_url() -> str:
    """Build chat completions URL from base."""
    return f"{BASE_URL.rstrip('/')}/chat/completions"


async def call_deepseek(
    messages: list,
    tools: Optional[list] = None,
    tool_choice: Optional[str] = None
) -> dict:
    """Call DeepSeek Chat Completions API (OpenAI-compatible) via httpx."""
    if not API_KEY:
        raise HTTPException(status_code=500, detail="DEEPSEEK_API_KEY not configured")
    
    payload = {
        "model": "deepseek-chat",
        "messages": messages,
        "temperature": 0.2,
        "max_tokens": 2000,
    }
    if tools:
        payload["tools"] = tools
        if tool_choice:
            payload["tool_choice"] = tool_choice
    
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json",
    }
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(get_chat_completions_url(), headers=headers, json=payload)
    
    if resp.status_code != 200:
        raise HTTPException(status_code=500, detail=f"API Error: {resp.status_code} {resp.text}")
    
    return resp.json()


async def chat_with_gort(message: str, session_id: str) -> tuple[str, Optional[str]]:
    """
    Chat with Gort and return response + tool name (if used)
    """
    constitution = load_constitution()
    
    # Get MCP tools (if available)
    tools = []
    try:
        manager = get_mcp_manager()
        tools = manager.get_tools_for_llm()
    except Exception:
        manager = None
    
    # Get or create session
    if session_id not in SESSIONS:
        session_id = create_new_session()
    
    session = SESSIONS[session_id]
    
    # Add user message to history
    session["messages"].append({
        "role": "user",
        "content": message
    })
    
    try:
        # Call DeepSeek with tools
        response = await call_deepseek(
            messages=[{"role": "system", "content": constitution}, *session["messages"]],
            tools=tools if tools else None,
            tool_choice="auto" if tools else None
        )
        
        assistant_message = response["choices"][0]["message"]
        tool_used = None
        
        # Handle tool calls
        tool_calls = assistant_message.get("tool_calls")
        if tool_calls:
            tool_used = tool_calls[0]["function"]["name"]
            available_tools = get_available_tools()
            
            # Execute tool
            tool_results = []
            for tool_call in tool_calls:
                tool_name = tool_call["function"]["name"]
                
                try:
                    # VALIDATE: Check if tool exists
                    if tool_name not in available_tools:
                        error_msg = f"❌ TOOL HATASI: '{tool_name}' tool'u mevcut değil. Mevcut tool'lar: {', '.join(sorted(available_tools))}"
                        tool_results.append(f"\n[{tool_name}]\n{error_msg}")
                        continue
                    
                    raw_args = tool_call["function"].get("arguments", {})
                    arguments = json.loads(raw_args) if isinstance(raw_args, str) else raw_args
                    
                    if manager is None:
                        tool_results.append(f"\n[{tool_name}]\n❌ MCP manager not initialized")
                        continue
                    
                    result = await manager.execute_tool(tool_name, arguments)
                    tool_results.append(f"\n[{tool_name}]\n{result}")
                except json.JSONDecodeError as e:
                    error_msg = f"❌ ARGUMENT HATASI: {tool_name} tool'unun argümanları parse edilemedi: {e}"
                    tool_results.append(f"\n[{tool_name}]\n{error_msg}")
                except Exception as e:
                    error_msg = f"❌ EXECUTION HATASI: {tool_name} tool'u çalıştırırken hata: {e}"
                    tool_results.append(f"\n[{tool_name}]\n{error_msg}")
            
            # Add assistant tool call in structured format
            session["messages"].append({
                "role": "assistant",
                "content": assistant_message.get("content") or "",
                "tool_calls": [
                    {
                        "id": tc.get("id"),
                        "type": "function",
                        "function": {
                            "name": tc["function"]["name"],
                            "arguments": tc["function"].get("arguments", {}),
                        },
                    }
                    for tc in tool_calls
                ],
            })

            # Add each tool result as role=tool so model can ground follow-up answer
            for tool_call, result in zip(tool_calls, tool_results):
                session["messages"].append({
                    "role": "tool",
                    "tool_call_id": tool_call.get("id"),
                    "name": tool_call["function"]["name"],
                    "content": result,
                })
            
            # Get final response after tool execution
            final_response = await call_deepseek(
                messages=[{"role": "system", "content": constitution}, *session["messages"]]
            )
            
            response_text = final_response["choices"][0]["message"]["content"]
            session["messages"].append({
                "role": "assistant",
                "content": response_text
            })
            
            return response_text, tool_used
        else:
            # Regular response (no tools)
            response_text = assistant_message.get("content", "")
            session["messages"].append({
                "role": "assistant",
                "content": response_text
            })
            
            return response_text, None
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"API Error: {str(e)}")


# Routes

@app.get("/health")
async def health():
    """Health check endpoint"""
    return {"status": "ok", "message": "Gort is running"}


@app.post("/session/create", response_model=dict)
async def create_session():
    """Create a new conversation session"""
    session_id = create_new_session()
    return {"session_id": session_id}


@app.get("/session/{session_id}", response_model=SessionData)
async def get_session(session_id: str):
    """Get conversation history for a session"""
    if session_id not in SESSIONS:
        raise HTTPException(status_code=404, detail="Session not found")
    
    session = SESSIONS[session_id]
    return SessionData(
        session_id=session["session_id"],
        created_at=session["created_at"],
        messages=[Message(**msg) for msg in session["messages"]]
    )


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """Chat endpoint - POST message, get response"""
    session_id = request.session_id or create_new_session()
    
    response_text, tool_used = await chat_with_gort(request.message, session_id)
    
    return ChatResponse(
        response=response_text,
        session_id=session_id,
        tool_used=tool_used
    )


@app.websocket("/ws/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    """WebSocket endpoint for real-time chat"""
    await websocket.accept()
    
    if session_id not in SESSIONS:
        create_new_session_id = create_new_session()
    
    try:
        while True:
            # Receive message from client
            data = await websocket.receive_text()
            message = json.loads(data)
            
            # Chat with Gort
            response_text, tool_used = await chat_with_gort(message.get("message"), session_id)
            
            # Send response back
            await websocket.send_json({
                "response": response_text,
                "tool_used": tool_used,
                "timestamp": datetime.now().isoformat()
            })
    except Exception as e:
        await websocket.send_json({"error": str(e)})
        await websocket.close()


@app.get("/tools")
async def list_tools():
    """Get available tools for the frontend"""
    try:
        manager = get_mcp_manager()
        return {"tools": manager.get_tools_for_llm()}
    except Exception:
        return {"tools": []}


@app.get("/constitution")
async def get_constitution():
    """Get Gort's constitution"""
    return {"constitution": load_constitution()}


# Main app entry
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app,
        host="127.0.0.1",
        port=8000,
        log_level="info"
    )
