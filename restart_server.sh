#!/bin/bash
# Restart chatterbox-inference server

echo "Stopping any existing chatterbox-inference processes..."
pkill -f "chatterbox-inference" 2>/dev/null || true
sleep 2

echo "Starting chatterbox-inference server..."
export CHATTERBOX_API_KEY="test-key-12345"
chatterbox-inference run fastapi > /tmp/server.log 2>&1 &

echo "Server started in background (PID: $!)"
echo "Waiting for server to initialize..."
sleep 8

# Check if server is healthy
if curl -s http://localhost:20480/health > /dev/null 2>&1; then
    echo "✓ Server is healthy and running on port 20480"
    echo "  Log file: /tmp/server.log"
else
    echo "✗ Server health check failed. Check /tmp/server.log for errors"
    exit 1
fi
