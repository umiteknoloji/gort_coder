# 🤖 Gort - Electron + FastAPI Setup Guide

## Project Structure

```
gort/
├── gort_server.py          # FastAPI backend server (port 8000)
├── main.py                 # CLI version (legacy)
├── tools.py                # GitHub & Vercel API integrations
├── constitution.txt        # Gort's system prompt
├── .env                    # API credentials (KEEP SECURE)
├── requirements.txt        # Python dependencies
├── memory.json             # Conversation history
├── start.sh                # Startup script
│
└── electron-app/           # Electron + React frontend
    ├── package.json        # Node dependencies
    ├── tsconfig.json       # TypeScript config
    ├── tsconfig.node.json  # Node TypeScript config
    │
    ├── public/
    │   ├── electron.js     # Electron main process
    │   ├── preload.js      # Electron preload script
    │   └── index.html      # HTML entry point
    │
    └── src/
        ├── App.tsx         # Main React component (Chat UI)
        ├── App.css         # Styling
        ├── index.tsx       # React entry
        └── index.css       # Global styles
```

## Prerequisites

- **Python 3.13+** with pip
- **Node.js 18+** with npm
- **Git**

## Installation

### 1. Backend Setup (Python)

```bash
cd gort/

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install Python dependencies
pip install -r requirements.txt
```

### 2. Frontend Setup (React + Electron)

```bash
cd electron-app

# Install Node dependencies
npm install
```

## Running Gort

### Quick Start (All-in-One)

```bash
# From gort/ root directory
bash start.sh
```

This starts:
- FastAPI server on `http://127.0.0.1:8000`
- React dev server on `http://localhost:3000`
- Electron window with embedded React app

### Manual Start (If start.sh doesn't work)

**Terminal 1 - Backend:**
```bash
# From gort/ root
source .venv/bin/activate
python3 gort_server.py
```

**Terminal 2 - Frontend:**
```bash
# From gort/electron-app
npm run dev
```

## Architecture

```
┌──────────────────────────────────────┐
│      Electron Desktop App            │
│  (Windows, macOS, Linux)             │
│                                      │
│  ┌──────────────────────────────┐   │
│  │  React Components (UI)       │   │
│  │  - Chat interface            │   │
│  │  - Message display           │   │
│  │  - Input handling            │   │
│  └──────────────┬───────────────┘   │
│                 │                    │
│                 │ HTTP POST /chat    │
│                 │ WebSocket /ws      │
│                 ▼                    │
└──────────────────────────────────────┘
              │
              │ (localhost:8000)
              │
┌──────────────▼──────────────────────┐
│     FastAPI Backend Server           │
│  (Python asyncio)                    │
│                                      │
│  ┌──────────────────────────────┐   │
│  │  DeepSeek LLM Integration    │   │
│  │  - Tool choice="auto"        │   │
│  │  - Session management        │   │
│  └──────────────────────────────┘   │
│                                      │
│  ┌──────────────────────────────┐   │
│  │  Tool Executors              │   │
│  │  - GitHub (PyGithub)         │   │
│  │  - Vercel (httpx)            │   │
│  └──────────────────────────────┘   │
└──────────────────────────────────────┘
```

## API Endpoints

### REST API
- `POST /chat` - Send message, get response
  ```json
  Request: { "message": "...", "session_id": "..." }
  Response: { "response": "...", "tool_used": "...", "session_id": "..." }
  ```

### WebSocket
- `WS /ws/{session_id}` - Real-time bidirectional chat

### Utility
- `GET /health` - System health check
- `POST /session/create` - Create new conversation
- `GET /session/{session_id}` - Get conversation history
- `GET /tools` - List available tools
- `GET /constitution` - Get Gort's system prompt

## Features

✅ **Chat Interface**
- Real-time message display
- User/AI message differentiation
- Typing indicators
- Multi-line input support

✅ **Tool Integration**
- GitHub repository creation
- GitHub repository listing
- Vercel project deployment
- Vercel environment variables
- Project listing

✅ **Session Management**
- Persistent conversation history (per-session)
- Session creation & retrieval
- Automatic session handling

✅ **Constitutional AI**
- Gort enforces honesty about capabilities
- System prompt injection
- Dürüstlük (integrity) principle

## Security Notes ⚠️

### Tokens Exposed (URGENT)
The `.env` file contains API tokens. These should be:

1. **Rotate GitHub Token**
   - GitHub Settings → Developer settings → Personal access tokens
   - Delete old token, generate new one
   - Update `.env` with new token

2. **Rotate Vercel Token**
   - Vercel Dashboard → Settings → Tokens
   - Delete old token, generate new one
   - Update `.env` with new token

3. **Never commit `.env`** to git (already in .gitignore, but confirm)

## Troubleshooting

### "FastAPI server not starting"
```bash
# Check if port 8000 is in use
lsof -i :8000
# Kill process if needed: kill -9 <PID>

# Or change port in gort_server.py
```

### "Electron app won't connect to backend"
- Ensure FastAPI server is running on 127.0.0.1:8000
- Check CORS is enabled in gort_server.py
- Verify firewall isn't blocking localhost:8000

### "npm install fails"
```bash
# Clear cache and retry
npm cache clean --force
rm -rf node_modules package-lock.json
npm install
```

### "Python dependencies missing"
```bash
# Reinstall requirements
pip install --upgrade pip
pip install -r requirements.txt
```

## Development Commands

### Backend
```bash
# Run server
python3 gort_server.py

# Run interactive CLI (legacy)
python3 main.py
```

### Frontend
```bash
cd electron-app

# Development (with hot reload)
npm run dev

# Build for production
npm run react-build

# Package into executable
npm run build
```

## Building for Distribution

```bash
cd electron-app

# Build React + Package with Electron
npm run build

# Outputs in dist/
# - macOS: dist/Gort.dmg
# - Windows: dist/Gort Setup.exe
# - Linux: dist/Gort.AppImage
```

## Next Steps

- [ ] Rotate GitHub and Vercel tokens
- [ ] Test full workflow (send message → Gort responds → use tools)
- [ ] Configure electron-builder for platform-specific builds
- [ ] Add persistent database layer (replace in-memory sessions)
- [ ] Implement user settings/preferences UI
- [ ] Add advanced tools (git push, file operations, etc.)

## Support

For issues or questions, check:
1. Terminal error messages
2. Browser DevTools (F12 when Electron window open)
3. Server logs on http://127.0.0.1:8000/docs (FastAPI docs)
