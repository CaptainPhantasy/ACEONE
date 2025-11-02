#!/bin/bash
# Monitor agent subprocesses and child processes
# Tracks all processes spawned by the main agent

LOG_FILE="/tmp/agent.log"
AGENT_PID=$(pgrep -f "python main.py dev" | head -1)

if [ -z "$AGENT_PID" ]; then
    echo "❌ Agent not running"
    exit 1
fi

echo "🔍 Monitoring Agent Subprocesses"
echo "================================"
echo "Main Agent PID: $AGENT_PID"
echo "Press Ctrl+C to stop"
echo ""

# Function to get child processes
get_children() {
    local pid=$1
    ps -o pid,ppid,command --ppid $pid 2>/dev/null | tail -n +2
}

# Function to get all descendants
get_all_descendants() {
    local pid=$1
    local children=$(ps -o pid --ppid $pid -h 2>/dev/null)
    echo "$pid"
    for child in $children; do
        get_all_descendants $child
    done
}

# Monitor loop
while true; do
    clear
    echo "🔍 Agent Subprocess Monitor - $(date '+%H:%M:%S')"
    echo "=============================================="
    echo ""
    
    # Main process info
    echo "📌 Main Agent Process:"
    ps -p $AGENT_PID -o pid,ppid,user,%cpu,%mem,etime,command 2>/dev/null | tail -n +2
    echo ""
    
    # Direct children
    echo "👶 Direct Child Processes:"
    children=$(get_children $AGENT_PID)
    if [ -z "$children" ]; then
        echo "   (none)"
    else
        ps -p $(echo "$children" | awk '{print $1}') -o pid,ppid,user,%cpu,%mem,etime,command 2>/dev/null | tail -n +2
    fi
    echo ""
    
    # All descendants
    echo "🌳 All Process Tree:"
    all_pids=$(get_all_descendants $AGENT_PID | sort -u)
    if [ -n "$all_pids" ]; then
        ps -p $all_pids -o pid,ppid,user,%cpu,%mem,etime,command 2>/dev/null | tail -n +2 | head -20
    else
        echo "   (no subprocesses)"
    fi
    echo ""
    
    # Resource usage summary
    echo "📊 Resource Summary:"
    total_cpu=$(ps -p $AGENT_PID -o %cpu --no-headers 2>/dev/null | awk '{sum+=$1} END {print sum}')
    total_mem=$(ps -p $AGENT_PID -o %mem --no-headers 2>/dev/null | awk '{sum+=$1} END {print sum}')
    echo "   CPU: ${total_cpu:-0}% | Memory: ${total_mem:-0}%"
    echo ""
    
    echo "Refreshing in 2 seconds... (Ctrl+C to stop)"
    sleep 2
done

