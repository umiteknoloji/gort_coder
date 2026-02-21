#!/bin/bash
# Start both FastAPI server and Electron app

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}🤖 Gort başlatılıyor...${NC}"
echo ""

# Check if Python is available
if ! command -v python3 &> /dev/null; then
    echo -e "${YELLOW}❌ Python3 bulunamadı${NC}"
    exit 1
fi

# Check if Node.js is available
if ! command -v node &> /dev/null; then
    echo -e "${YELLOW}❌ Node.js bulunamadı${NC}"
    exit 1
fi

# Start FastAPI server in background
echo -e "${GREEN}🚀 FastAPI sunucusu başlatılıyor (port 8000)...${NC}"
python3 gort_server.py &
SERVER_PID=$!

# Wait a bit for server to start
sleep 2

# Check if server started successfully
if ! kill -0 $SERVER_PID 2>/dev/null; then
    echo -e "${YELLOW}❌ FastAPI sunucusu başlatılamadı${NC}"
    exit 1
fi

# Start Electron app
echo -e "${GREEN}🖥️  Electron uygulaması başlatılıyor...${NC}"
cd electron-app
npm run dev &
ELECTRON_PID=$!

# Cleanup on exit
trap "kill $SERVER_PID $ELECTRON_PID 2>/dev/null" EXIT

echo -e "${GREEN}✅ Gort başarıyla başlatıldı!${NC}"
echo -e "${YELLOW}FastAPI PID: $SERVER_PID${NC}"
echo -e "${YELLOW}Electron PID: $ELECTRON_PID${NC}"
echo ""
echo "Çıkmak için Ctrl+C tuşlayın..."
echo ""

# Wait for both processes
wait
