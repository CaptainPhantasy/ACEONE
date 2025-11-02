#!/bin/bash
# Real-time monitoring script for ACE Voice Agent
# Monitors logs, transcripts, and latency metrics

LOG_FILE="/tmp/agent.log"
COLOR_RED='\033[0;31m'
COLOR_GREEN='\033[0;32m'
COLOR_YELLOW='\033[1;33m'
COLOR_BLUE='\033[0;34m'
COLOR_CYAN='\033[0;36m'
COLOR_RESET='\033[0m'

echo "🔍 ACE Voice Agent Monitor"
echo "=========================="
echo "Monitoring: $LOG_FILE"
echo "Press Ctrl+C to stop"
echo ""

# Function to highlight key metrics
highlight() {
    local pattern="$1"
    local color="$2"
    
    tail -f "$LOG_FILE" 2>/dev/null | while IFS= read -r line; do
        # Check for different log types and colorize
        if echo "$line" | grep -q "USER TRANSCRIPT"; then
            echo -e "${COLOR_CYAN}📝 $line${COLOR_RESET}"
        elif echo "$line" | grep -q "ASSISTANT RESPONSE"; then
            echo -e "${COLOR_GREEN}🤖 $line${COLOR_RESET}"
        elif echo "$line" | grep -q "RAG:"; then
            echo -e "${COLOR_YELLOW}🔍 $line${COLOR_RESET}"
        elif echo "$line" | grep -q "LATENCY SUMMARY"; then
            echo -e "${COLOR_BLUE}📊 $line${COLOR_RESET}"
        elif echo "$line" | grep -q "ERROR\|error\|Error\|FAILED\|Failed"; then
            echo -e "${COLOR_RED}❌ $line${COLOR_RESET}"
        elif echo "$line" | grep -q "greeting\|registered worker\|Agent starting"; then
            echo -e "${COLOR_GREEN}✅ $line${COLOR_RESET}"
        else
            echo "$line"
        fi
    done
}

# Start monitoring
if [ -f "$LOG_FILE" ]; then
    highlight
else
    echo "Waiting for log file to be created..."
    while [ ! -f "$LOG_FILE" ]; do
        sleep 1
    done
    highlight
fi

