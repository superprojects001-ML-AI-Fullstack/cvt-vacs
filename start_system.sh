#!/bin/bash

# CVT-VACS Startup Script
# Computer Vision and Token-Based Vehicle Access Control System
# Developed by: Daria Benjamin Francis (AUPG/24/0033)
# Adeleke University, Ede, Osun State, Nigeria

echo "╔══════════════════════════════════════════════════════════════╗"
echo "║                                                              ║"
echo "║           CVT-VACS - Vehicle Access Control System           ║"
echo "║                                                              ║"
echo "║     Computer Vision and Token-Based Authentication          ║"
echo "║                                                              ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to check if a command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Check prerequisites
echo -e "${BLUE}Checking prerequisites...${NC}"

if ! command_exists python3; then
    echo "Error: Python 3 is not installed"
    exit 1
fi

if ! command_exists node; then
    echo "Error: Node.js is not installed"
    exit 1
fi

echo -e "${GREEN}✓ Prerequisites met${NC}"
echo ""

# Check MongoDB
echo -e "${BLUE}Checking MongoDB connection...${NC}"
if command_exists mongod; then
    echo -e "${GREEN}✓ MongoDB is installed${NC}"
else
    echo -e "${YELLOW}⚠ MongoDB not found locally. Ensure MongoDB Atlas URL is configured${NC}"
fi
echo ""

# Start Backend
echo -e "${BLUE}Starting Backend Server...${NC}"
cd backend

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "Creating Python virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
source venv/bin/activate

# Install dependencies
echo "Installing backend dependencies..."
pip install -q -r requirements.txt

# Start backend in background
echo -e "${GREEN}✓ Starting FastAPI server on http://localhost:8000${NC}"
python main.py &
BACKEND_PID=$!

cd ..
echo ""

# Wait for backend to start
sleep 3

# Start Frontend
echo -e "${BLUE}Starting Frontend...${NC}"
cd app

# Install dependencies if needed
if [ ! -d "node_modules" ]; then
    echo "Installing frontend dependencies..."
    npm install
fi

echo -e "${GREEN}✓ Starting React dev server on http://localhost:5173${NC}"
npm run dev &
FRONTEND_PID=$!

cd ..
echo ""

# Display system information
echo -e "${GREEN}══════════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}  CVT-VACS System is now running!${NC}"
echo -e "${GREEN}══════════════════════════════════════════════════════════════${NC}"
echo ""
echo -e "  ${BLUE}Backend API:${NC}    http://localhost:8000"
echo -e "  ${BLUE}Frontend:${NC}       http://localhost:5173"
echo -e "  ${BLUE}API Docs:${NC}       http://localhost:8000/docs"
echo ""
echo -e "  ${YELLOW}Press Ctrl+C to stop both servers${NC}"
echo ""

# Handle shutdown
cleanup() {
    echo ""
    echo -e "${BLUE}Shutting down CVT-VACS...${NC}"
    kill $BACKEND_PID 2>/dev/null
    kill $FRONTEND_PID 2>/dev/null
    echo -e "${GREEN}✓ System stopped${NC}"
    exit 0
}

trap cleanup SIGINT SIGTERM

# Keep script running
wait
