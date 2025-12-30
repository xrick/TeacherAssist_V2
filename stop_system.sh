#!/bin/bash

# TeacherAssist V2 - System Shutdown Script
# Gracefully stops both backend and frontend servers

set -e  # Exit on error

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Project directories
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PID_DIR="$SCRIPT_DIR/.pids"

# PID files
BACKEND_PID_FILE="$PID_DIR/backend.pid"
FRONTEND_PID_FILE="$PID_DIR/frontend.pid"

# Function to stop a process
stop_process() {
    local name=$1
    local pid_file=$2

    if [ ! -f "$pid_file" ]; then
        echo -e "${YELLOW}✓ $name is not running (no PID file)${NC}"
        return 0
    fi

    local pid=$(cat "$pid_file")

    if ! ps -p "$pid" > /dev/null 2>&1; then
        echo -e "${YELLOW}✓ $name is not running (stale PID)${NC}"
        rm -f "$pid_file"
        return 0
    fi

    echo -e "${YELLOW}Stopping $name (PID: $pid)...${NC}"

    # Try graceful shutdown with SIGTERM
    kill -TERM "$pid" 2>/dev/null || true

    # Wait up to 10 seconds for graceful shutdown
    local count=0
    while ps -p "$pid" > /dev/null 2>&1 && [ $count -lt 10 ]; do
        sleep 1
        count=$((count + 1))
    done

    # If still running, force kill with SIGKILL
    if ps -p "$pid" > /dev/null 2>&1; then
        echo -e "${YELLOW}  Graceful shutdown timeout, forcing...${NC}"
        kill -KILL "$pid" 2>/dev/null || true
        sleep 1
    fi

    # Verify process is stopped
    if ps -p "$pid" > /dev/null 2>&1; then
        echo -e "${RED}✗ Failed to stop $name (PID: $pid)${NC}"
        return 1
    else
        echo -e "${GREEN}✓ $name stopped successfully${NC}"
        rm -f "$pid_file"
        return 0
    fi
}

echo -e "${YELLOW}Shutting down TeacherAssist V2...${NC}"
echo ""

# Stop backend server
stop_process "Backend server" "$BACKEND_PID_FILE"

# Stop frontend server
stop_process "Frontend server" "$FRONTEND_PID_FILE"

# Clean up any orphaned processes
echo ""
echo -e "${YELLOW}Checking for orphaned processes...${NC}"

# Check for uvicorn processes
UVICORN_PIDS=$(pgrep -f "uvicorn app.main:app" || true)
if [ -n "$UVICORN_PIDS" ]; then
    echo -e "${YELLOW}Found orphaned uvicorn processes: $UVICORN_PIDS${NC}"
    echo "$UVICORN_PIDS" | xargs kill -TERM 2>/dev/null || true
    sleep 2
    echo "$UVICORN_PIDS" | xargs kill -KILL 2>/dev/null || true
    echo -e "${GREEN}✓ Cleaned up orphaned uvicorn processes${NC}"
fi

# Check for npm/vite processes
NPM_PIDS=$(pgrep -f "vite.*frontend" || true)
if [ -n "$NPM_PIDS" ]; then
    echo -e "${YELLOW}Found orphaned npm/vite processes: $NPM_PIDS${NC}"
    echo "$NPM_PIDS" | xargs kill -TERM 2>/dev/null || true
    sleep 2
    echo "$NPM_PIDS" | xargs kill -KILL 2>/dev/null || true
    echo -e "${GREEN}✓ Cleaned up orphaned npm/vite processes${NC}"
fi

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}TeacherAssist V2 System Stopped${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo -e "To start the system again, run: ${YELLOW}./start_system.sh${NC}"
