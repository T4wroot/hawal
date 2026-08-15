#!/usr/bin/env bash
# ⚡ Hawal Tunnel (هه‌واڵ) - One-Line Master Panel Installer
# Usage: curl -fsSL https://raw.githubusercontent.com/T4wroot/hawal/master/install-panel.sh | bash

set -e

PORT="9090"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --port) PORT="$2"; shift 2 ;;
    *) shift ;;
  esac
done

echo "🚀 ==============================================="
echo "⚡ Installing Hawal Tunnel Control Panel..."
echo "🌐 Web Port: ${PORT}"
echo "==============================================="

INSTALL_DIR="/opt/hawal-panel"
mkdir -p "$INSTALL_DIR" /etc/hawal

# Check Python 3
if ! command -v python3 &> /dev/null; then
  echo "📦 Installing Python3..."
  apt-get update -y && apt-get install -y python3 curl tar
fi

# Clone or download repository
echo "📥 Fetching Hawal Tunnel source..."
rm -rf /tmp/hawal-temp
curl -fsSL https://github.com/T4wroot/hawal/archive/refs/heads/master.tar.gz -o /tmp/hawal.tar.gz 2>/dev/null || curl -fsSL https://github.com/T4wroot/hawal/archive/refs/heads/main.tar.gz -o /tmp/hawal.tar.gz
mkdir -p /tmp/hawal-temp
tar -xzf /tmp/hawal.tar.gz -C /tmp/hawal-temp --strip-components=1
cp -r /tmp/hawal-temp/* "$INSTALL_DIR/"
rm -rf /tmp/hawal-temp /tmp/hawal.tar.gz

chmod +x "$INSTALL_DIR/server.py" "$INSTALL_DIR/start.sh"

# Create Systemd Service for Panel
cat > /etc/systemd/system/hawal-panel.service << EOF
[Unit]
Description=Hawal Tunnel Master Control Panel
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=${INSTALL_DIR}
ExecStart=/usr/bin/python3 ${INSTALL_DIR}/server.py --port ${PORT}
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable hawal-panel
systemctl restart hawal-panel

SERVER_IP=$(curl -s -4 --connect-timeout 3 ifconfig.me || curl -s -4 --connect-timeout 3 api.ipify.org || hostname -I | awk '{print $1}')

echo "==============================================="
echo "🎉 Hawal Tunnel Panel successfully installed & running!"
echo "👉 Dashboard URL: http://${SERVER_IP}:${PORT}"
echo "==============================================="
