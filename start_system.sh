#!/bin/bash

# TeacherAssist V2 - System Startup Script
# Starts both backend (FastAPI) and frontend (React + Vite) servers

set -e  # Exit on error

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Project directories
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$SCRIPT_DIR/backend"
FRONTEND_DIR="$SCRIPT_DIR/frontend"
PID_DIR="$SCRIPT_DIR/.pids"

# PID files
BACKEND_PID_FILE="$PID_DIR/backend.pid"
FRONTEND_PID_FILE="$PID_DIR/frontend.pid"

# Create PID directory if not exists
mkdir -p "$PID_DIR"

# Function to check if process is running
is_running() {
    local pid_file=$1
    if [ -f "$pid_file" ]; then
        local pid=$(cat "$pid_file")
        if ps -p "$pid" > /dev/null 2>&1; then
            return 0  # Process is running
        else
            rm -f "$pid_file"  # Clean up stale PID file
            return 1  # Process not running
        fi
    fi
    return 1  # PID file doesn't exist
}

# Check if servers are already running
echo -e "${YELLOW}Checking existing processes...${NC}"

if is_running "$BACKEND_PID_FILE"; then
    echo -e "${RED}✗ Backend server is already running (PID: $(cat $BACKEND_PID_FILE))${NC}"
    BACKEND_RUNNING=true
else
    BACKEND_RUNNING=false
fi

if is_running "$FRONTEND_PID_FILE"; then
    echo -e "${RED}✗ Frontend server is already running (PID: $(cat $FRONTEND_PID_FILE))${NC}"
    FRONTEND_RUNNING=true
else
    FRONTEND_RUNNING=false
fi

if [ "$BACKEND_RUNNING" = true ] && [ "$FRONTEND_RUNNING" = true ]; then
    echo -e "${YELLOW}Both servers are already running. Use stop_system.sh to stop them first.${NC}"
    exit 1
fi

# Start Backend Server
if [ "$BACKEND_RUNNING" = false ]; then
    echo -e "${YELLOW}Starting backend server...${NC}"

    # Check if virtual environment exists
    if [ ! -d "$BACKEND_DIR/venv" ]; then
        echo -e "${RED}✗ Virtual environment not found at $BACKEND_DIR/venv${NC}"
        echo -e "${YELLOW}Please create it with: cd backend && python3 -m venv venv${NC}"
        exit 1
    fi

    # Start backend in background
    cd "$BACKEND_DIR"
    source venv/bin/activate
    # Load .env file to override system environment variables
    if [ -f .env ]; then
        export $(grep -v '^#' .env | grep OLLAMA_MODEL | xargs)
    fi
    nohup uvicorn app.main:app --reload --port 8000 > "$PID_DIR/backend.log" 2>&1 &
    BACKEND_PID=$!
    echo $BACKEND_PID > "$BACKEND_PID_FILE"
    deactivate
    cd "$SCRIPT_DIR"

    # Wait a moment and check if it started successfully
    sleep 2
    if is_running "$BACKEND_PID_FILE"; then
        echo -e "${GREEN}✓ Backend server started (PID: $BACKEND_PID)${NC}"
        echo -e "  URL: http://localhost:8000"
        echo -e "  Logs: $PID_DIR/backend.log"
    else
        echo -e "${RED}✗ Backend server failed to start${NC}"
        echo -e "  Check logs: $PID_DIR/backend.log"
        exit 1
    fi
else
    echo -e "${YELLOW}Backend server already running, skipping...${NC}"
fi

# Start Frontend Server
if [ "$FRONTEND_RUNNING" = false ]; then
    echo -e "${YELLOW}Starting frontend server...${NC}"

    # Check if node_modules exists
    if [ ! -d "$FRONTEND_DIR/node_modules" ]; then
        echo -e "${RED}✗ node_modules not found at $FRONTEND_DIR/node_modules${NC}"
        echo -e "${YELLOW}Please install dependencies with: cd frontend && npm install${NC}"
        exit 1
    fi

    # Start frontend in background
    cd "$FRONTEND_DIR"
    nohup npm run dev > "$PID_DIR/frontend.log" 2>&1 &
    FRONTEND_PID=$!
    echo $FRONTEND_PID > "$FRONTEND_PID_FILE"
    cd "$SCRIPT_DIR"

    # Wait a moment and check if it started successfully
    sleep 3
    if is_running "$FRONTEND_PID_FILE"; then
        echo -e "${GREEN}✓ Frontend server started (PID: $FRONTEND_PID)${NC}"
        echo -e "  URL: http://localhost:5173"
        echo -e "  Logs: $PID_DIR/frontend.log"
    else
        echo -e "${RED}✗ Frontend server failed to start${NC}"
        echo -e "  Check logs: $PID_DIR/frontend.log"
        exit 1
    fi
else
    echo -e "${YELLOW}Frontend server already running, skipping...${NC}"
fi

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}TeacherAssist V2 System Started${NC}"
echo -e "${GREEN}========================================${NC}"
echo -e "Backend:  http://localhost:8000"
echo -e "Frontend: http://localhost:5173"
echo -e "API Docs: http://localhost:8000/docs"
echo ""
echo -e "To stop the system, run: ${YELLOW}./stop_system.sh${NC}"
echo -e "To view logs:"
echo -e "  Backend:  tail -f .pids/backend.log"
echo -e "  Frontend: tail -f .pids/frontend.log"
