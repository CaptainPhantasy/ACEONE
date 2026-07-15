#!/bin/bash
# Comprehensive monitoring - combines log tailing and subprocess monitoring
# Run in separate terminals or use tmux/screen

LOG_FILE="/tmp/agent.log"

echo "🔍 ACE Agent - Comprehensive Monitoring"
echo "======================================"
echo ""
echo "This script will monitor:"
echo "  1. Real-time logs with colorized output"
echo "  2. Agent subprocesses and resource usage"
echo ""
echo "Press Ctrl+C to stop"
echo ""

# Check if agent is running
AGENT_PID=$(pgrep -f "python -m agent.main dev" | head -1)
if [ -z "$AGENT_PID" ]; then
    echo "⚠️  Warning: Agent process not found"
    echo "   Start agent with: ./run.sh"
    echo ""
fi

# Start log monitoring in background
echo "📝 Starting log monitor..."
tail -f "$LOG_FILE" 2>/dev/null | while IFS= read -r line; do
    # Colorize based on content
    if echo "$line" | grep -q "USER TRANSCRIPT"; then
        echo -e "\033[0;36m📝 $line\033[0m"
    elif echo "$line" | grep -q "ASSISTANT RESPONSE"; then
        echo -e "\033[0;32m🤖 $line\033[0m"
    elif echo "$line" | grep -q "RAG:"; then
        echo -e "\033[1;33m🔍 $line\033[0m"
    elif echo "$line" | grep -q "LATENCY SUMMARY"; then
        echo -e "\033[0;34m📊 $line\033[0m"
    elif echo "$line" | grep -q "ERROR\|error\|Error\|FAILED\|Failed"; then
        echo -e "\033[0;31m❌ $line\033[0m"
    elif echo "$line" | grep -q "greeting\|registered worker\|Agent starting"; then
        echo -e "\033[0;32m✅ $line\033[0m"
    else
        echo "$line"
    fi
done &

LOG_MONITOR_PID=$!

# Function to cleanup on exit
cleanup() {
    echo ""
    echo "🛑 Stopping monitors..."
    kill "$LOG_MONITOR_PID" 2>/dev/null
    exit 0
}

trap cleanup SIGINT SIGTERM

# Wait for log file if it doesn't exist
if [ ! -f "$LOG_FILE" ]; then
    echo "⏳ Waiting for log file..."
    while [ ! -f "$LOG_FILE" ]; do
        sleep 1
    done
fi

# Monitor subprocesses periodically
while true; do
    sleep 10
    if [ -n "$AGENT_PID" ]; then
        # Check if agent is still running
        if ! ps -p "$AGENT_PID" > /dev/null 2>&1; then
            echo ""
            echo "⚠️  Agent process died (PID: $AGENT_PID)"
            AGENT_PID=$(pgrep -f "python -m agent.main dev" | head -1)
            if [ -n "$AGENT_PID" ]; then
                echo "✅ Found new agent process (PID: $AGENT_PID)"
            fi
        fi
    fi
done
