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
from openai import OpenAI

# Import tools
from tools import TOOLS_SCHEMA, execute_tool

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


async def chat_with_gort(session: dict, constitution: str, user_message: str) -> Optional[str]:
    """
    Send message to Gort via DeepSeek API with tool support.
    Handles tool calls and executes them.
    """
    client = OpenAI(api_key=API_KEY, base_url=BASE_URL)
    
    # Add user message to conversation
    session["messages"].append({
        "role": "user",
        "content": user_message
    })
    
    try:
        # Call DeepSeek API with tools
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
        
        # Check if tools were called
        assistant_message = response.choices[0].message
        
        if assistant_message.tool_calls:
            # Add assistant's tool decision to history
            session["messages"].append({
                "role": "assistant",
                "content": assistant_message.content or "Tool çağırılıyor..."
            })
            
            # Execute each tool
            tool_results_text = "\n".join([
                f"[Tool Sonucu: {tc.function.name}]"
                for tc in assistant_message.tool_calls
            ])
            
            for tool_call in assistant_message.tool_calls:
                try:
                    tool_name = tool_call.function.name
                    arguments = json.loads(tool_call.function.arguments) if isinstance(tool_call.function.arguments, str) else tool_call.function.arguments
                    
                    print(f"\n🔧 Tool çalıştırılıyor: {tool_name}")
                    result = await execute_tool(tool_name, arguments)
                    print(f"✅ {result}\n")
                    
                    tool_results_text += f"\n\n{result}"
                except Exception as e:
                    tool_results_text += f"\n\n❌ Tool çalıştırılırken hata: {e}"
            
            # Add tool results as assistant message (not tool role)
            session["messages"].append({
                "role": "assistant",
                "content": tool_results_text
            })
            
            # Get final response from DeepSeek after tools executed
            final_response = client.chat.completions.create(
                model="deepseek-chat",
                messages=[
                    {"role": "system", "content": constitution},
                    *session["messages"]
                ],
                temperature=0.5,
                max_tokens=2000
            )
            
            final_message = final_response.choices[0].message.content
            
            # Add final response to history
            session["messages"].append({
                "role": "assistant",
                "content": final_message
            })
            
            return final_message
        
        else:
            # No tools called, regular response
            response_text = assistant_message.content
            
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
