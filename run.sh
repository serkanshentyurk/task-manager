#!/bin/bash

# PhD Task Manager - Start Script
# This starts both backend and frontend with one command

echo "🚀 Starting PhD Task Manager..."

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Function to cleanup on exit
cleanup() {
    echo -e "\n${RED}Shutting down...${NC}"
    kill $BACKEND_PID 2>/dev/null
    exit 0
}

trap cleanup EXIT INT TERM

# Start backend
echo -e "${BLUE}Starting backend...${NC}"
cd backend
source venv/bin/activate
python main.py > ../backend.log 2>&1 &
BACKEND_PID=$!
cd ..

# Wait for backend to start
sleep 2

# Check if backend is running
if ! kill -0 $BACKEND_PID 2>/dev/null; then
    echo -e "${RED}❌ Backend failed to start. Check backend.log${NC}"
    exit 1
fi

echo -e "${GREEN}✓ Backend running on http://localhost:8000${NC}"

# Start frontend
echo -e "${BLUE}Starting frontend...${NC}"
cd frontend
npm run dev

# When frontend stops (Ctrl+C), cleanup will kill backend too
