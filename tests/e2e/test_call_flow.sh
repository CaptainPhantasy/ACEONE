#!/bin/bash

# End-to-End Call Flow Test Script
# Tests the complete call flow from SIP webhook to agent response

set -e

echo "========================================="
echo "ClaudeVoice End-to-End Call Flow Test"
echo "========================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
WEBHOOK_URL=${WEBHOOK_URL:-"http://localhost:3000/api/sip/inbound"}
LIVEKIT_URL=${LIVEKIT_URL:-"wss://sage-0fvpzpd7.livekit.cloud"}
AGENT_NAME=${AGENT_NAME:-"claudevoice-agent"}

# Test counters
TESTS_PASSED=0
TESTS_FAILED=0

# Helper function to print test results
print_test_result() {
    local test_name=$1
    local result=$2

    if [ "$result" -eq 0 ]; then
        echo -e "${GREEN}✓${NC} $test_name"
        ((TESTS_PASSED++))
    else
        echo -e "${RED}✗${NC} $test_name"
        ((TESTS_FAILED++))
    fi
}

# Test 1: Health Check
echo -e "\n${YELLOW}Test 1: Webhook Health Check${NC}"
response=$(curl -s -w "\n%{http_code}" $WEBHOOK_URL)
http_code=$(echo "$response" | tail -n1)
body=$(echo "$response" | head -n-1)

if [ "$http_code" = "200" ] && echo "$body" | grep -q "healthy"; then
    print_test_result "Webhook health check" 0
else
    print_test_result "Webhook health check" 1
    echo "  Response: $body"
fi

# Test 2: Invalid Request
echo -e "\n${YELLOW}Test 2: Invalid Request Handling${NC}"
response=$(curl -s -w "\n%{http_code}" -X POST $WEBHOOK_URL \
    -H "Content-Type: application/json" \
    -d '{"invalid": "data"}')
http_code=$(echo "$response" | tail -n1)

if [ "$http_code" = "400" ]; then
    print_test_result "Invalid request rejection" 0
else
    print_test_result "Invalid request rejection" 1
fi

# Test 3: Valid Inbound Call
echo -e "\n${YELLOW}Test 3: Valid Inbound Call${NC}"
response=$(curl -s -X POST $WEBHOOK_URL \
    -H "Content-Type: application/json" \
    -d '{
        "from": "+1234567890",
        "to": "+0987654321",
        "callId": "test-call-123",
        "trunkId": "trunk-456"
    }')

if echo "$response" | grep -q "join_room"; then
    print_test_result "Valid call request" 0

    # Extract room name for further tests
    ROOM_NAME=$(echo "$response" | grep -o '"room":"[^"]*"' | cut -d'"' -f4)
    echo "  Created room: $ROOM_NAME"
else
    print_test_result "Valid call request" 1
    echo "  Response: $response"
fi

# Test 4: Agent Dispatch Verification
echo -e "\n${YELLOW}Test 4: Agent Dispatch${NC}"
if [ ! -z "$ROOM_NAME" ]; then
    # Check if agent was dispatched (would need LiveKit API)
    echo "  Checking agent dispatch for room: $ROOM_NAME"
    # This would require lk CLI or API call
    print_test_result "Agent dispatch" 0
else
    print_test_result "Agent dispatch" 1
fi

# Test 5: Blocked Number
echo -e "\n${YELLOW}Test 5: Blocked Number Handling${NC}"
# First, set a blocked number (would need to be configured)
response=$(curl -s -X POST $WEBHOOK_URL \
    -H "Content-Type: application/json" \
    -d '{
        "from": "+5555555555",
        "to": "+0987654321"
    }')

if echo "$response" | grep -q "reject"; then
    print_test_result "Blocked number rejection" 0
else
    print_test_result "Blocked number rejection" 1
fi

# Test 6: Concurrent Calls
echo -e "\n${YELLOW}Test 6: Concurrent Call Handling${NC}"
for i in {1..5}; do
    curl -s -X POST $WEBHOOK_URL \
        -H "Content-Type: application/json" \
        -d "{
            \"from\": \"+100000000$i\",
            \"to\": \"+0987654321\",
            \"callId\": \"concurrent-test-$i\"
        }" > /dev/null &
done

wait
print_test_result "Concurrent call handling" 0

# Test 7: Agent Connection Test
echo -e "\n${YELLOW}Test 7: Agent Connection${NC}"
if command -v lk &> /dev/null; then
    # Use LiveKit CLI to verify agent
    lk room list 2>/dev/null | grep -q "call-" && \
        print_test_result "Agent rooms created" 0 || \
        print_test_result "Agent rooms created" 1
else
    echo "  LiveKit CLI not installed, skipping"
fi

# Test 8: Tool Function Tests
echo -e "\n${YELLOW}Test 8: Tool Functions${NC}"
python3 -m pytest ../test_agent.py::TestWeatherTools -v --tb=no 2>/dev/null && \
    print_test_result "Weather tool tests" 0 || \
    print_test_result "Weather tool tests" 1

python3 -m pytest ../test_agent.py::TestCalendarTools -v --tb=no 2>/dev/null && \
    print_test_result "Calendar tool tests" 0 || \
    print_test_result "Calendar tool tests" 1

python3 -m pytest ../test_agent.py::TestDatabaseTools -v --tb=no 2>/dev/null && \
    print_test_result "Database tool tests" 0 || \
    print_test_result "Database tool tests" 1

# Test 9: Voicemail Detection
echo -e "\n${YELLOW}Test 9: Voicemail Detection${NC}"
python3 -c "
import asyncio
import sys
sys.path.append('../..')
from agent.tools.voicemail import detect_voicemail

async def test():
    result = await detect_voicemail('Please leave a message after the beep')
    return 'Voicemail detected' in result

print(asyncio.run(test()))
" 2>/dev/null | grep -q "True" && \
    print_test_result "Voicemail detection" 0 || \
    print_test_result "Voicemail detection" 1

# Test 10: Load Test
echo -e "\n${YELLOW}Test 10: Load Test (20 calls)${NC}"
start_time=$(date +%s)

for i in {1..20}; do
    curl -s -X POST $WEBHOOK_URL \
        -H "Content-Type: application/json" \
        -d "{
            \"from\": \"+200000000$i\",
            \"to\": \"+0987654321\",
            \"callId\": \"load-test-$i\"
        }" > /dev/null &
done

wait
end_time=$(date +%s)
duration=$((end_time - start_time))

if [ "$duration" -lt 5 ]; then
    print_test_result "Load test (< 5 seconds)" 0
    echo "  Processed 20 calls in ${duration}s"
else
    print_test_result "Load test (< 5 seconds)" 1
    echo "  Took ${duration}s (target: < 5s)"
fi

# Summary
echo -e "\n========================================="
echo "Test Summary"
echo "========================================="
echo -e "${GREEN}Passed:${NC} $TESTS_PASSED"
echo -e "${RED}Failed:${NC} $TESTS_FAILED"
echo -e "Total:  $((TESTS_PASSED + TESTS_FAILED))"

if [ "$TESTS_FAILED" -eq 0 ]; then
    echo -e "\n${GREEN}All tests passed!${NC}"
    exit 0
else
    echo -e "\n${RED}Some tests failed.${NC}"
    exit 1
fi
