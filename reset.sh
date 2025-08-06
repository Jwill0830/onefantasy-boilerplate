#!/bin/bash

echo "�� OneFantasy Reset Script"
echo "========================="

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${YELLOW}⚠️  This will reset your development environment!${NC}"
echo "Continue? (y/N)"
read -r response

if [[ ! "$response" =~ ^[Yy]$ ]]; then
    echo "Reset cancelled."
    exit 0
fi

echo -e "\n${YELLOW}🛑 Stopping processes...${NC}"
if command -v lsof >/dev/null 2>&1; then
    lsof -ti:3000 | xargs kill -9 2>/dev/null || true
    lsof -ti:5000 | xargs kill -9 2>/dev/null || true
fi

echo -e "\n${YELLOW}🧹 Cleaning up...${NC}"
rm -rf node_modules package-lock.json
rm -rf frontend/node_modules frontend/package-lock.json
npm cache clean --force 2>/dev/null || true

echo -e "\n${YELLOW}📦 Reinstalling...${NC}"
npm install
if [ -d "frontend" ]; then
    cd frontend && npm install && cd ..
fi

echo -e "\n${GREEN}✅ Reset complete!${NC}"
