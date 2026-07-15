#!/bin/bash

# ClaudeVoice Initial Setup Script
# Sets up the development environment

set -e

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT_DIR"

echo "================================"
echo "ClaudeVoice Development Setup"
echo "================================"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "\n${YELLOW}1. Checking uv and Python...${NC}"
if command -v uv >/dev/null && uv python find 3.13 >/dev/null; then
    echo -e "${GREEN}✓ uv and Python 3.13 available${NC}"
else
    echo "❌ uv and Python 3.13 are required"
    exit 1
fi

echo -e "\n${YELLOW}2. Checking Node.js version...${NC}"
node_version=$(node --version | cut -d'v' -f2 | cut -d'.' -f1)
if [[ $node_version -ge 20 ]]; then
    echo -e "${GREEN}✓ Node.js $(node --version) installed${NC}"
else
    echo "❌ Node.js 20+ required. Current: $(node --version)"
    exit 1
fi

echo -e "\n${YELLOW}3. Installing Python dependencies...${NC}"
uv sync --frozen
echo -e "${GREEN}✓ Python dependencies installed${NC}"

echo -e "\n${YELLOW}4. Installing Node.js dependencies...${NC}"
cd webhook
npm ci
echo -e "${GREEN}✓ Node.js dependencies installed${NC}"

echo -e "\n${YELLOW}5. Setting up environment file...${NC}"
cd ..
if [ ! -f .env.local ]; then
    echo "❌ .env.local not found"
    echo "Please create .env.local with your API keys"
    echo "See .env.example for reference"
else
    echo -e "${GREEN}✓ Environment file found${NC}"
fi

echo -e "\n${YELLOW}6. Installing LiveKit CLI...${NC}"
if command -v lk &> /dev/null; then
    echo -e "${GREEN}✓ LiveKit CLI already installed${NC}"
else
    echo "Installing LiveKit CLI..."
    if [[ "$OSTYPE" == "darwin"* ]]; then
        brew install livekit-cli
    else
        curl -sSL https://get.livekit.io/cli | bash
    fi
fi

echo -e "\n${YELLOW}7. Setting up Git hooks...${NC}"
cat > .git/hooks/pre-commit << 'EOF'
#!/bin/bash
# Run tests before commit
uv run --frozen pytest -q
if [ $? -ne 0 ]; then
    echo "Tests failed. Please fix before committing."
    exit 1
fi
EOF
chmod +x .git/hooks/pre-commit
echo -e "${GREEN}✓ Git hooks configured${NC}"

echo -e "\n${YELLOW}8. Creating necessary directories...${NC}"
mkdir -p logs
mkdir -p data
echo -e "${GREEN}✓ Directories created${NC}"

echo -e "\n================================"
echo -e "${GREEN}Setup Complete!${NC}"
echo -e "================================"
echo ""
echo "Next steps:"
echo "1. Add your API keys to .env.local"
echo "2. Run: uv run --frozen python -m agent.main dev"
echo "3. In another terminal: cd webhook && npm run dev"
echo "4. Access LiveKit playground to test"
echo ""
echo "Run tests with: uv run --frozen pytest -v"
echo "Deploy with: ./scripts/deploy.sh"
