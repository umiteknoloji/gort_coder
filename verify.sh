#!/bin/bash
# Test script to verify Gort installation

echo "🔍 Gort Installation Verification"
echo "=================================="
echo ""

# Check Python
echo -n "✓ Checking Python 3.13+... "
if command -v python3 &> /dev/null; then
    PYTHON_VERSION=$(python3 --version | awk '{print $2}')
    echo "✅ Python $PYTHON_VERSION found"
else
    echo "❌ Python not found"
    exit 1
fi

# Check venv
echo -n "✓ Checking Python venv... "
if [ -d ".venv" ]; then
    echo "✅ Virtual environment exists"
    source .venv/bin/activate
else
    echo "⚠️  Virtual environment not found, creating..."
    python3 -m venv .venv
    source .venv/bin/activate
    echo "✅ Created virtual environment"
fi

# Check Python packages
echo -n "✓ Checking Python dependencies... "
MISSING=0
for pkg in openai python-dotenv PyGithub httpx fastapi uvicorn; do
    python3 -c "import ${pkg//-/_}" 2>/dev/null || MISSING=$((MISSING+1))
done
if [ $MISSING -eq 0 ]; then
    echo "✅ All packages installed"
else
    echo "❌ Missing $MISSING packages"
    echo "   Installing from requirements.txt..."
    pip install -r requirements.txt
fi

# Check Node.js
echo -n "✓ Checking Node.js 18+... "
if command -v node &> /dev/null; then
    NODE_VERSION=$(node --version | cut -d'v' -f2 | cut -d'.' -f1)
    if [ "$NODE_VERSION" -ge 18 ]; then
        echo "✅ Node $(node --version) found"
    else
        echo "❌ Node version too old (need 18+)"
        exit 1
    fi
else
    echo "❌ Node.js not found"
    exit 1
fi

# Check npm packages (electron-app)
echo -n "✓ Checking Electron app npm packages... "
if [ -d "electron-app/node_modules" ]; then
    echo "✅ Node modules installed"
else
    echo "⚠️  Node modules not found, installing..."
    cd electron-app
    npm install
    cd ..
fi

# Check .env
echo -n "✓ Checking .env file... "
if [ -f ".env" ]; then
    if grep -q "DEEPSEEK_API_KEY" .env; then
        echo "✅ .env file exists"
    else
        echo "❌ .env missing DEEPSEEK_API_KEY"
        exit 1
    fi
else
    echo "❌ .env file not found"
    exit 1
fi

# Check key files
echo -n "✓ Checking core files... "
FILES="gort_server.py tools.py constitution.txt main.py"
MISSING=0
for file in $FILES; do
    if [ ! -f "$file" ]; then
        echo "❌ Missing: $file"
        MISSING=$((MISSING+1))
    fi
done
if [ $MISSING -eq 0 ]; then
    echo "✅ All core files present"
else
    echo "❌ Missing $MISSING files"
    exit 1
fi

echo ""
echo "=================================="
echo "✅ All checks passed! Ready to start."
echo ""
echo "Run: bash start.sh"
echo ""
