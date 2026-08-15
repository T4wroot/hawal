#!/usr/bin/env bash
# Hawal Tunnel Quick Start
cd "$(dirname "$0")"
echo "🚀 Starting Hawal Tunnel Control Panel..."
exec python3 server.py "$@"
