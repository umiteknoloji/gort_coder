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
from openai import OpenAI
from pydantic import BaseModel
from typing import Optional, List

# Import Gort tools
from tools import TOOLS_SCHEMA, execute_tool

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
    """Get all available tool names from TOOLS_SCHEMA"""
    return {tool["function"]["name"] for tool in TOOLS_SCHEMA}


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


async def chat_with_gort(message: str, session_id: str) -> tuple[str, Optional[str]]:
    """
    Chat with Gort and return response + tool name (if used)
    """
    client = OpenAI(api_key=API_KEY, base_url=BASE_URL)
    constitution = load_constitution()
    
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
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": constitution},
                *session["messages"]
            ],
            tools=TOOLS_SCHEMA,
            tool_choice="auto",
            temperature=0.5,
            max_tokens=2000
        )
        
        assistant_message = response.choices[0].message
        tool_used = None
        
        # Handle tool calls
        if assistant_message.tool_calls:
            tool_used = assistant_message.tool_calls[0].function.name
            available_tools = get_available_tools()
            
            # Execute tool
            tool_results = []
            for tool_call in assistant_message.tool_calls:
                tool_name = tool_call.function.name
                
                try:
                    # VALIDATE: Check if tool exists
                    if tool_name not in available_tools:
                        error_msg = f"❌ TOOL HATASI: '{tool_name}' tool'u mevcut değil. Mevcut tool'lar: {', '.join(sorted(available_tools))}"
                        tool_results.append(f"\n[{tool_name}]\n{error_msg}")
                        continue
                    
                    arguments = json.loads(tool_call.function.arguments) if isinstance(tool_call.function.arguments, str) else tool_call.function.arguments
                    
                    result = await execute_tool(tool_name, arguments)
                    tool_results.append(f"\n[{tool_name}]\n{result}")
                except json.JSONDecodeError as e:
                    error_msg = f"❌ ARGUMENT HATASI: {tool_name} tool'unun argümanları parse edilemedi: {e}"
                    tool_results.append(f"\n[{tool_name}]\n{error_msg}")
                except Exception as e:
                    error_msg = f"❌ EXECUTION HATASI: {tool_name} tool'u çalıştırırken hata: {e}"
                    tool_results.append(f"\n[{tool_name}]\n{error_msg}")
            
            # Add tool execution to history
            session["messages"].append({
                "role": "assistant",
                "content": f"Calling {tool_used}..."
            })
            session["messages"].append({
                "role": "assistant",
                "content": "".join(tool_results)
            })
            
            # Get final response after tool execution
            final_response = client.chat.completions.create(
                model="deepseek-chat",
                messages=[
                    {"role": "system", "content": constitution},
                    *session["messages"]
                ],
                temperature=0.5,
                max_tokens=2000
            )
            
            response_text = final_response.choices[0].message.content
            session["messages"].append({
                "role": "assistant",
                "content": response_text
            })
            
            return response_text, tool_used
        else:
            # Regular response (no tools)
            response_text = assistant_message.content
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
    return {"tools": TOOLS_SCHEMA}


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
