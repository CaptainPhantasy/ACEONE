#!/bin/bash
# Comprehensive monitoring script for ACE Voice Agent
# Monitors: logs, metrics, transcripts, processes, latency

LOG_FILE="/tmp/agent_new.log"
AGENT_LOG="/tmp/agent.log"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
MAGENTA='\033[0;35m'
RESET='\033[0m'
BOLD='\033[1m'

echo -e "${BOLD}${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${RESET}"
echo -e "${BOLD}${GREEN}🔍 ACE Voice Agent - Comprehensive Monitoring System${RESET}"
echo -e "${BOLD}${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${RESET}"
echo ""
echo -e "${CYAN}Monitoring:${RESET}"
echo -e "  📝 ${GREEN}Transcripts${RESET} - User and Agent speech"
echo -e "  ⏱️  ${GREEN}Latency Metrics${RESET} - EOU, LLM, TTS, Total latency"
echo -e "  🔍 ${GREEN}RAG Lookups${RESET} - Knowledge base search timing"
echo -e "  📊 ${GREEN}Complete Turn Metrics${RESET} - Full turn analysis"
echo -e "  🔔 ${GREEN}Hook Events${RESET} - on_enter, on_user_turn_completed"
echo -e "  ⚙️  ${GREEN}Process Health${RESET} - Agent process status"
echo ""
echo -e "${YELLOW}Press Ctrl+C to stop monitoring${RESET}"
echo ""

# Check agent process
AGENT_PID=$(pgrep -f "python -m agent.main dev" | head -1)
if [ -n "$AGENT_PID" ]; then
    echo -e "${GREEN}✅ Agent running (PID: $AGENT_PID)${RESET}"
else
    echo -e "${RED}⚠️  Agent process not found${RESET}"
    echo -e "${YELLOW}   Start with: uv run --frozen python -m agent.main dev${RESET}"
fi
echo ""

# Find active log file
ACTIVE_LOG=""
for log in "$LOG_FILE" "$AGENT_LOG" "/tmp/livekit-agent.log"; do
    if [ -f "$log" ]; then
        ACTIVE_LOG="$log"
        echo -e "${GREEN}📄 Using log file: $ACTIVE_LOG${RESET}"
        break
    fi
done

if [ -z "$ACTIVE_LOG" ]; then
    echo -e "${YELLOW}⏳ Waiting for log file to be created...${RESET}"
    while [ -z "$ACTIVE_LOG" ]; do
        for log in "$LOG_FILE" "$AGENT_LOG" "/tmp/livekit-agent.log"; do
            if [ -f "$log" ]; then
                ACTIVE_LOG="$log"
                echo -e "${GREEN}✅ Log file found: $ACTIVE_LOG${RESET}"
                break
            fi
        done
        if [ -z "$ACTIVE_LOG" ]; then
            sleep 1
        fi
    done
fi

echo ""
echo -e "${BOLD}${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${RESET}"
echo ""

# Cleanup function
cleanup() {
    echo ""
    echo -e "${YELLOW}🛑 Stopping monitors...${RESET}"
    kill $LOG_PID 2>/dev/null
    kill $METRICS_PID 2>/dev/null
    kill $PROCESS_PID 2>/dev/null
    exit 0
}
trap cleanup SIGINT SIGTERM

# Monitor 1: Main log with colorized output (filtered for key events)
tail -f "$ACTIVE_LOG" 2>/dev/null | while IFS= read -r line; do
    # Transcripts
    if echo "$line" | grep -qE "USER TRANSCRIPT|📝 USER"; then
        echo -e "${CYAN}${line}${RESET}"
    elif echo "$line" | grep -qE "ASSISTANT RESPONSE|🤖 ASSISTANT"; then
        echo -e "${GREEN}${line}${RESET}"
    # Latency metrics
    elif echo "$line" | grep -qE "COMPLETE TURN METRICS|📊 COMPLETE"; then
        echo -e "${BOLD}${BLUE}${line}${RESET}"
    elif echo "$line" | grep -qE "TOTAL LATENCY|🎯 TOTAL"; then
        echo -e "${BOLD}${MAGENTA}${line}${RESET}"
    elif echo "$line" | grep -qE "EOU|LLM|TTS.*Metrics|⏱️"; then
        echo -e "${BLUE}${line}${RESET}"
    # RAG
    elif echo "$line" | grep -qE "RAG:|🔍 RAG"; then
        echo -e "${YELLOW}${line}${RESET}"
    # Hooks
    elif echo "$line" | grep -qE "HOOK FIRED|🔔"; then
        echo -e "${CYAN}${BOLD}${line}${RESET}"
    # Errors
    elif echo "$line" | grep -qE "ERROR|error|Error|FAILED|Failed|❌"; then
        echo -e "${RED}${line}${RESET}"
    # Important events
    elif echo "$line" | grep -qE "Agent starting|greeting|registered worker|✅|📞"; then
        echo -e "${GREEN}${line}${RESET}"
    # Default
    else
        echo "$line"
    fi
done &
LOG_PID=$!

# Monitor 2: Metrics summary (periodic updates)
(
while true; do
    sleep 15
    if [ -f "$ACTIVE_LOG" ]; then
        echo ""
        echo -e "${BOLD}${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${RESET}"
        echo -e "${BOLD}${YELLOW}📊 METRICS SUMMARY (last 15 seconds)${RESET}"
        echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${RESET}"
        
        # Count recent transcripts
        RECENT_TRANSCRIPTS=$(tail -100 "$ACTIVE_LOG" 2>/dev/null | grep -cE "USER TRANSCRIPT|ASSISTANT RESPONSE")
        echo -e "${CYAN}📝 Recent Transcripts: ${RECENT_TRANSCRIPTS}${RESET}"
        
        # Latest total latency
        LATEST_LATENCY=$(tail -100 "$ACTIVE_LOG" 2>/dev/null | grep "TOTAL LATENCY" | tail -1 | grep -oE "[0-9]+\.[0-9]+ms" | head -1)
        if [ -n "$LATEST_LATENCY" ]; then
            echo -e "${MAGENTA}⏱️  Latest Total Latency: ${LATEST_LATENCY}${RESET}"
        fi
        
        # Latest RAG time
        LATEST_RAG=$(tail -100 "$ACTIVE_LOG" 2>/dev/null | grep "RAG:" | tail -1 | grep -oE "[0-9]+\.[0-9]+ms" | head -1)
        if [ -n "$LATEST_RAG" ]; then
            echo -e "${YELLOW}🔍 Latest RAG: ${LATEST_RAG}${RESET}"
        fi
        
        # Agent process status
        AGENT_PID=$(pgrep -f "python -m agent.main dev" | head -1)
        if [ -n "$AGENT_PID" ]; then
            CPU=$(ps -p "$AGENT_PID" -o %cpu= 2>/dev/null | tr -d ' ')
            MEM=$(ps -p "$AGENT_PID" -o %mem= 2>/dev/null | tr -d ' ')
            echo -e "${GREEN}⚙️  Agent Process: PID ${AGENT_PID} | CPU: ${CPU:-N/A}% | Memory: ${MEM:-N/A}%${RESET}"
        fi
        
        echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${RESET}"
        echo ""
    fi
done
) &
METRICS_PID=$!

# Monitor 3: Process health check
(
while true; do
    sleep 30
    AGENT_PID=$(pgrep -f "python -m agent.main dev" | head -1)
    if [ -z "$AGENT_PID" ]; then
        echo ""
        echo -e "${RED}⚠️  WARNING: Agent process not found!${RESET}"
    else
        # Check if process is still responsive
        if ! ps -p "$AGENT_PID" > /dev/null 2>&1; then
            echo ""
            echo -e "${RED}⚠️  WARNING: Agent process died (was PID: $AGENT_PID)${RESET}"
        fi
    fi
done
) &
PROCESS_PID=$!

# Wait for monitors
wait $LOG_PID
