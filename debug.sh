#!/bin/bash

echo "�� OneFantasy Debug Script"
echo "=========================="

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

print_status() {
    local status=$1
    local message=$2
    case $status in
        "success") echo -e "${GREEN}✅ $message${NC}" ;;
        "error") echo -e "${RED}❌ $message${NC}" ;;
        "warning") echo -e "${YELLOW}⚠️  $message${NC}" ;;
        "info") echo -e "${BLUE}ℹ️  $message${NC}" ;;
    esac
}

echo -e "\n${BLUE}📁 Checking Environment Files...${NC}"
if [ -f ".env" ]; then
    print_status "success" ".env file found"
else
    print_status "error" ".env file not found - copy .env.example to .env"
fi

echo -e "\n${BLUE}📦 Checking Node.js Environment...${NC}"
if command -v node >/dev/null 2>&1; then
    node_version=$(node --version)
    print_status "success" "Node.js version: $node_version"
else
    print_status "error" "Node.js not found"
fi

if command -v npm >/dev/null 2>&1; then
    npm_version=$(npm --version)
    print_status "success" "npm version: $npm_version"
else
    print_status "error" "npm not found"
fi

echo -e "\n${BLUE}🔌 Checking Ports...${NC}"
if command -v lsof >/dev/null 2>&1; then
    if lsof -ti:3000 >/dev/null 2>&1; then
        print_status "warning" "Port 3000 is in use"
    else
        print_status "success" "Port 3000 is available"
    fi
    
    if lsof -ti:5000 >/dev/null 2>&1; then
        print_status "warning" "Port 5000 is in use"
    else
        print_status "success" "Port 5000 is available"
    fi
fi

echo -e "\n${BLUE}📚 Checking Dependencies...${NC}"
if [ -d "node_modules" ]; then
    print_status "success" "Root node_modules exists"
else
    print_status "warning" "Root node_modules not found - run 'npm install'"
fi

if [ -d "frontend/node_modules" ]; then
    print_status "success" "Frontend node_modules exists"
else
    print_status "warning" "Frontend node_modules not found - run 'cd frontend && npm install'"
fi

echo -e "\n${GREEN}Debug check complete!${NC}"
