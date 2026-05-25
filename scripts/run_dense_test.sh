#!/bin/bash
# Run a dense ATP test via API

API_URL="${API_URL:-http://localhost:8000}"

echo "🚀 Starting dense ATP test..."
echo "API URL: $API_URL"

# Start the test
RESPONSE=$(curl -s -X POST "$API_URL/api/atp/dense-test" \
  -H "Content-Type: application/json" \
  -d '{
    "sovereign_ids": ["vexr-ultra", "asim-pilot"],
    "base_intents": [
      {
        "action": "book_appointment",
        "parameters": {"service": "test", "date": "2026-06-01"},
        "sender": "cli-tester",
        "recipient": "vexr-ultra"
      },
      {
        "action": "generate_code", 
        "parameters": {"language": "python", "description": "hello world"},
        "sender": "cli-tester",
        "recipient": "vexr-ultra"
      }
    ],
    "mutation_types": ["expiry", "signature", "parameters"],
    "parallel_tests": 2,
    "timeout_seconds": 30
  }')

TASK_ID=$(echo "$RESPONSE" | grep -o '"task_id":"[^"]*"' | cut -d'"' -f4)

if [ -z "$TASK_ID" ]; then
    echo "❌ Failed to start test"
    echo "$RESPONSE"
    exit 1
fi

echo "✅ Test started: $TASK_ID"

# Poll for status
while true; do
    STATUS=$(curl -s "$API_URL/api/atp/status/$TASK_ID")
    PROGRESS=$(echo "$STATUS" | grep -o '"progress":[0-9.]*' | cut -d':' -f2)
    STATUS_TEXT=$(echo "$STATUS" | grep -o '"status":"[^"]*"' | cut -d'"' -f4)
    
    echo "📊 Progress: ${PROGRESS}% - Status: $STATUS_TEXT"
    
    if [ "$STATUS_TEXT" = "completed" ] || [ "$STATUS_TEXT" = "failed" ]; then
        break
    fi
    
    sleep 3
done

# Get results
echo ""
echo "📋 Test Results:"
curl -s "$API_URL/api/atp/results/$TASK_ID" | python -m json.tool

echo ""
echo "✅ Done"
