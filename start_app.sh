#!/usr/bin/env bash
# Automatic 1-Click Launcher for Meesho Review Hub
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" >/dev/null 2>&1 && pwd)"
cd "$DIR"

# Check if server is running
if ! pgrep -f "server.py" > /dev/null; then
    echo "Starting Server..."
    python3 "$DIR/server.py" > "$DIR/server.log" 2>&1 &
    sleep 1
fi

# Check if cloudflared is running
if ! pgrep -f "cloudflared tunnel" > /dev/null; then
    echo "Starting Cloudflare Tunnel..."
    "$DIR/cloudflared" tunnel --url http://localhost:8080 > "$DIR/tunnel.log" 2>&1 &
    sleep 3
fi

# Extract URL
URL=$(grep -o 'https://[-a-z0-9]*\.trycloudflare\.com' "$DIR/tunnel.log" | tail -n 1)

if [ -n "$URL" ]; then
    echo "=================================================="
    echo "🚀 MEESHO REVIEW APP IS LIVE!"
    echo "👉 Share this link with Kiran & Anurag:"
    echo "   $URL"
    echo "=================================================="
    echo "$URL" > "$DIR/LIVE_LINK.txt"
    echo "$URL" > /home/harsh/Desktop/MEESHO_REVIEW_LINK.txt 2>/dev/null || true
else
    echo "App running locally at: http://localhost:8080"
fi
