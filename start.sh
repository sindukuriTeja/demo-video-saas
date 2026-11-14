#!/bin/bash
# Demo Video SaaS - Startup Script

cd /opt/sandbox/workspace/demo-video-saas

echo "=============================================="
echo "  Demo Video SaaS Application"
echo "  Starting server..."
echo "=============================================="

# Set Python path to include OpenVoice
export PYTHONPATH="/opt/sandbox/workspace/demo-video-saas/OpenVoice:$PYTHONPATH"

# Start the Flask server
python3 app/server.py
