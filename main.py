#!/usr/bin/env python3
"""
Gort - AI Assistant CLI
Based on GORT's Constitution v0.1
"""

import os
import json
import sys
import asyncio
from datetime import datetime
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv
import httpx

# Import tools
from mcp_tools import initialize_mcp, get_mcp_manager

# Configuration
load_dotenv()
API_KEY = os.getenv("DEEPSEEK_API_KEY")
BASE_URL = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
MEMORY_FILE = "memory.json"
CONSTITUTION_FILE = "constitution.txt"


def load_constitution():
    """Load Gort's constitution from file."""
    if not Path(CONSTITUTION_FILE).exists():
        print(f"❌ HATA: {CONSTITUTION_FILE} bulunamadı")
        sys.exit(1)
    with open(CONSTITUTION_FILE, "r", encoding="utf-8") as f:
        return f.read()


def load_memory():
    """Load conversation history from memory.json"""
    if Path(MEMORY_FILE).exists():
        try:
            with open(MEMORY_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            print(f"⚠️  Uyarı: Bellek yüklenemedi ({e}), temiz başlat")
            return create_new_session()
    return create_new_session()


def create_new_session():
    """Create a new conversation session."""
    return {
        "session_id": f"gort-session-{datetime.now().strftime('%Y%m%d-%H%M%S')}",
        "created_at": datetime.now().isoformat(),
        "last_updated": datetime.now().isoformat(),
        "messages": []
    }


def save_memory(session):
    """Save conversation history to memory.json"""
    try:
        session["last_updated"] = datetime.now().isoformat()
        with open(MEMORY_FILE, "w", encoding="utf-8") as f:
            json.dump(session, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"\n⚠️  Uyarı: Bellek kaydedilemedi ({e})")


def validate_api_key():
    """Check if API key is configured."""
    if not API_KEY or API_KEY == "your_api_key_here":
        print("\n❌ HATA: DEEPSEEK_API_KEY .env dosyasında ayarlanmamış")
        print("   https://platform.deepseek.com adresinden bir API key alın")
        print("   .env dosyasında DEEPSEEK_API_KEY=sk-... şeklinde kaydedin")
        sys.exit(1)


def get_chat_completions_url() -> str:
    """Build chat completions URL from base."""
    return f"{BASE_URL.rstrip('/')}/chat/completions"


async def call_deepseek(messages: list, tools: Optional[list] = None, tool_choice: Optional[str] = None) -> dict:
    """Call DeepSeek Chat Completions API via httpx."""
    if not API_KEY:
        raise RuntimeError("DEEPSEEK_API_KEY not configured")
    
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
        raise RuntimeError(f"API Error: {resp.status_code} {resp.text}")
    
    return resp.json()


async def chat_with_gort(session: dict, constitution: str, user_message: str) -> Optional[str]:
    """
    Send message to Gort via DeepSeek API with tool support.
    Handles tool calls and executes them.
    """
    # Get MCP tools (if available)
    tools = []
    try:
        manager = get_mcp_manager()
        tools = manager.get_tools_for_llm()
    except Exception:
        manager = None
    
    # Add user message to conversation
    session["messages"].append({
        "role": "user",
        "content": user_message
    })
    
    try:
        # Call DeepSeek API with tools
        response = await call_deepseek(
            messages=[{"role": "system", "content": constitution}, *session["messages"]],
            tools=tools if tools else None,
            tool_choice="auto" if tools else None
        )
        
        # Check if tools were called
        assistant_message = response["choices"][0]["message"]
        
        tool_calls = assistant_message.get("tool_calls")
        if tool_calls:
            # Add assistant tool call message in OpenAI-compatible format
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
            
            for tool_call in tool_calls:
                try:
                    tool_name = tool_call["function"]["name"]
                    raw_args = tool_call["function"].get("arguments", {})
                    arguments = json.loads(raw_args) if isinstance(raw_args, str) else raw_args
                    
                    print(f"\n🔧 Tool çalıştırılıyor: {tool_name}")
                    if manager is None:
                        result = "❌ MCP manager not initialized"
                    else:
                        result = await manager.execute_tool(tool_name, arguments)
                    print(f"✅ {result}\n")

                    session["messages"].append({
                        "role": "tool",
                        "tool_call_id": tool_call.get("id"),
                        "name": tool_name,
                        "content": result,
                    })
                except Exception as e:
                    session["messages"].append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "name": tool_name,
                        "content": f"❌ Tool çalıştırılırken hata: {e}",
                    })
            
            # Get final response from DeepSeek after tools executed
            final_response = await call_deepseek(
                messages=[{"role": "system", "content": constitution}, *session["messages"]]
            )
            
            final_message = final_response["choices"][0]["message"]["content"]
            
            # Add final response to history
            session["messages"].append({
                "role": "assistant",
                "content": final_message
            })
            
            return final_message
        
        else:
            # No tools called, regular response
            response_text = assistant_message.get("content", "")
            
            # Add to history
            session["messages"].append({
                "role": "assistant",
                "content": response_text
            })
            
            return response_text
        
    except Exception as e:
        error_msg = str(e)
        print(f"\n❌ API Hatası: {error_msg}")
        return None


async def main():
    """Main CLI loop for Gort."""
    validate_api_key()
    
    constitution = load_constitution()
    
    # Initialize MCP servers
    try:
        await initialize_mcp()
    except Exception as e:
        print(f"⚠️ MCP initialization failed: {e}")
    session = load_memory()
    
    print("\n" + "="*60)
    print("🤖 GORT - AI Yazılımcı Ortağı")
    print("="*60)
    print(f"📋 Session: {session['session_id']}")
    print("💬 Konuşmaya başla (exit yazarak çık)")
    print("="*60)
    
    try:
        while True:
            # Get user input
            user_input = input("\nYou: ").strip()
            
            if not user_input:
                continue
            
            # Check for exit commands
            if user_input.lower() in ["exit", "quit"]:
                print("\nGort: Hoşça kalın. Konuşma geçmişi kaydedildi.")
                save_memory(session)
                break
            
            # Multiline mode: start with ':' to enter multiline input
            # Type ':' + text, then continue with more lines, finish with '---' on empty line
            if user_input.startswith(':'):
                lines = [user_input[1:].strip()]
                print("  (Multiline mode - type lines, finish with '---' on empty line)")
                while True:
                    try:
                        line = input("  > ").rstrip()
                        if line == '---':
                            break
                        lines.append(line)
                    except EOFError:
                        break
                user_input = '\n'.join(lines)
            
            # Get response from Gort
            response = await chat_with_gort(session, constitution, user_input)
            
            if response is None:
                print("Gort: (Yanıt alınamadı, lütfen tekrar deneyin)")
            else:
                print(f"\nGort: {response}")
                save_memory(session)
            
    except KeyboardInterrupt:
        print("\n\nGort: Program sonlandırıldı. Konuşma geçmişi kaydedildi.")
        save_memory(session)
        sys.exit(0)


if __name__ == "__main__":
    asyncio.run(main())
