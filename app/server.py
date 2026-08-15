import asyncio
import base64
import hashlib
import json
import mimetypes
import os
import secrets
import time
import urllib.parse
from app.config import DEFAULT_HOST, DEFAULT_PORT, MASTER_TOKEN
from app.db import (
    init_db, list_nodes, get_node, get_node_by_token, save_node, delete_node,
    update_node_heartbeat, list_tunnels, get_tunnel, save_tunnel,
    set_tunnel_status, delete_tunnel, record_ping, get_latest_pings
)
from app.backhaul import validate_tunnel_ports, generate_server_config, generate_client_config
from app.ping_tool import run_ping, run_tcp_ping

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, "static")
TEMPLATES_DIR = os.path.join(BASE_DIR, "templates")

# Connected WebSocket clients for real-time UI updates
CONNECTED_WS_CLIENTS = set()

# Connected Agent Sockets for real-time dispatch
CONNECTED_AGENTS = {} # node_id -> writer

def make_ws_handshake_response(sec_key):
    guid = "258EAFA5-E914-47DA-95CA-C5AB0DC85B11"
    accept_val = base64.b64encode(hashlib.sha1((sec_key + guid).encode('utf-8')).digest()).decode('utf-8')
    resp = (
        "HTTP/1.1 101 Switching Protocols\r\n"
        "Upgrade: websocket\r\n"
        "Connection: Upgrade\r\n"
        f"Sec-WebSocket-Accept: {accept_val}\r\n\r\n"
    )
    return resp.encode('utf-8')

def encode_ws_frame(payload_bytes, opcode=1):
    length = len(payload_bytes)
    header = bytearray()
    header.append(0x80 | opcode)
    if length <= 125:
        header.append(length)
    elif length <= 65535:
        header.append(126)
        header.extend(length.to_bytes(2, 'big'))
    else:
        header.append(127)
        header.extend(length.to_bytes(8, 'big'))
    return bytes(header + payload_bytes)

async def broadcast_ws(data):
    if not CONNECTED_WS_CLIENTS:
        return
    msg = encode_ws_frame(json.dumps(data).encode('utf-8'))
    dead = []
    for writer in list(CONNECTED_WS_CLIENTS):
        try:
            writer.write(msg)
            await writer.drain()
        except:
            dead.append(writer)
    for w in dead:
        CONNECTED_WS_CLIENTS.discard(w)

class HTTPServer:
    def __init__(self, host=DEFAULT_HOST, port=DEFAULT_PORT):
        self.host = host
        self.port = port
        self.server = None

    async def start(self):
        init_db()
        self.server = await asyncio.start_server(self.handle_client, self.host, self.port)
        print(f"🚀 NexusTunnel Control Panel is listening at http://{self.host}:{self.port}")
        print(f"🔑 Master Admin Token: {MASTER_TOKEN}")

    async def handle_client(self, reader, writer):
        try:
            req_line = await reader.readline()
            if not req_line:
                writer.close()
                return
            
            req_parts = req_line.decode('utf-8', errors='ignore').strip().split()
            if len(req_parts) < 2:
                writer.close()
                return

            method, path = req_parts[0], req_parts[1]
            headers = {}
            while True:
                line = await reader.readline()
                if not line or line == b"\r\n":
                    break
                header_line = line.decode('utf-8', errors='ignore').strip()
                if ":" in header_line:
                    k, v = header_line.split(":", 1)
                    headers[k.strip().lower()] = v.strip()

            parsed_url = urllib.parse.urlparse(path)
            raw_path = parsed_url.path
            query = urllib.parse.parse_qs(parsed_url.query)

            # Check WebSocket Upgrade
            if headers.get("upgrade", "").lower() == "websocket":
                sec_key = headers.get("sec-websocket-key")
                if sec_key:
                    writer.write(make_ws_handshake_response(sec_key))
                    await writer.drain()
                    if raw_path == "/ws":
                        await self.handle_ws_dashboard(reader, writer)
                    return

            # Read Body if POST/PUT
            body = b""
            content_length = int(headers.get("content-length", 0))
            if content_length > 0:
                body = await reader.readexactly(content_length)

            # Route HTTP Requests
            await self.route_request(method, raw_path, query, headers, body, writer)

        except Exception as e:
            try:
                self.send_json(writer, {"error": str(e)}, status=500)
            except:
                pass
        finally:
            try:
                writer.close()
                await writer.wait_closed()
            except:
                pass

    async def route_request(self, method, path, query, headers, body, writer):
        # 1. Static Files & Dashboard UI
        if method == "GET" and path in ["/", "/index.html"]:
            self.serve_template("index.html", writer)
            return

        if method == "GET" and path.startswith("/static/"):
            rel_path = path.replace("/static/", "", 1)
            file_path = os.path.join(STATIC_DIR, rel_path)
            self.serve_static_file(file_path, writer)
            return

        # 2. One-Line Node Installer Script
        if method == "GET" and path == "/install":
            await self.serve_node_installer(query, headers, writer)
            return

        # 3. REST API: Node Management
        if method == "GET" and path == "/api/nodes":
            nodes = list_nodes()
            self.send_json(writer, {"nodes": nodes})
            return

        if method == "POST" and path == "/api/nodes":
            data = json.loads(body.decode('utf-8'))
            node_id = f"node_{secrets.token_hex(4)}"
            name = data.get("name", "New Node")
            ip = data.get("ip", "127.0.0.1")
            role = data.get("role", "kharej")
            token = secrets.token_hex(16)
            
            # Resolve GeoIP location and country flag
            from app.geoip import resolve_geoip
            geo = resolve_geoip(ip)
            if role == "iran":
                geo["flag"] = "🇮🇷"
                geo["country_name"] = "ایران"
                geo["country_code"] = "IR"

            save_node(node_id, name, ip, role, token, 
                      country_code=geo.get("country_code", "GLOBAL"),
                      country_name=geo.get("country_name", "خارج"),
                      flag=geo.get("flag", "🌐"),
                      city=geo.get("city", ""))
            
            self.send_json(writer, {
                "node_id": node_id, 
                "token": token, 
                "name": name, 
                "role": role,
                "flag": geo.get("flag", "🌐"),
                "country_name": geo.get("country_name", "خارج")
            })
            await broadcast_ws({"event": "node_updated"})
            return

        if method == "DELETE" and path.startswith("/api/nodes/"):
            node_id = path.split("/")[-1]
            delete_node(node_id)
            self.send_json(writer, {"success": True, "deleted": node_id})
            await broadcast_ws({"event": "node_updated"})
            return

        # 4. REST API: Tunnel Management
        if method == "GET" and path == "/api/tunnels":
            tunnels = list_tunnels()
            self.send_json(writer, {"tunnels": tunnels})
            return

        if method == "POST" and path == "/api/tunnels":
            data = json.loads(body.decode('utf-8'))
            tunnel_id = data.get("id") or f"tun_{secrets.token_hex(4)}"
            name = data.get("name", "Hawal Tunnel")
            server_node_id = data.get("server_node_id")
            client_node_id = data.get("client_node_id")
            core_port = int(data.get("core_port", 3080))
            transport = data.get("transport", "ws")
            ports = data.get("ports", ["443=127.0.0.1:443"])
            token = data.get("token") or secrets.token_hex(8)
            nodelay = int(data.get("nodelay", 1))
            snappy = int(data.get("snappy", 1))
            mux_con = int(data.get("mux_con", 8))
            channel_size = int(data.get("channel_size", 2048))

            # Validate duplicate port collision on server node
            valid, msg = validate_tunnel_ports(core_port, server_node_id, current_tunnel_id=tunnel_id)
            if not valid:
                self.send_json(writer, {"success": False, "error": msg}, status=400)
                return

            save_tunnel(tunnel_id, name, server_node_id, client_node_id, core_port, transport, ports, token, nodelay, snappy, mux_con, channel_size)
            self.send_json(writer, {"success": True, "tunnel_id": tunnel_id})
            await broadcast_ws({"event": "tunnel_updated"})
            return

        if method == "GET" and "/api/tunnels/" in path and path.endswith("/docker"):
            tunnel_id = path.split("/")[3]
            tunnel = get_tunnel(tunnel_id)
            if not tunnel:
                self.send_json(writer, {"error": "Tunnel not found"}, status=404)
                return
            server_node = get_node(tunnel["server_node_id"])
            s_ip = server_node["ip"] if server_node else "127.0.0.1"
            server_compose, server_toml = generate_docker_compose(tunnel, "server", s_ip)
            client_compose, client_toml = generate_docker_compose(tunnel, "client", s_ip)
            self.send_json(writer, {
                "server_compose": server_compose,
                "server_toml": server_toml,
                "client_compose": client_compose,
                "client_toml": client_toml
            })
            return

        if method == "GET" and path == "/api/settings":
            from app.config import load_settings
            self.send_json(writer, {"settings": load_settings()})
            return

        if method == "POST" and path == "/api/settings":
            from app.config import load_settings, save_settings
            current = load_settings()
            new_data = json.loads(body.decode('utf-8'))
            current.update(new_data)
            save_settings(current)
            self.send_json(writer, {"success": True, "settings": current})
            await broadcast_ws({"event": "settings_updated"})
            return

        if method == "DELETE" and path.startswith("/api/tunnels/"):
            tunnel_id = path.split("/")[-1]
            delete_tunnel(tunnel_id)
            self.send_json(writer, {"success": True, "deleted": tunnel_id})
            await broadcast_ws({"event": "tunnel_updated"})
            return

        if method == "POST" and "/api/tunnels/" in path and path.endswith("/status"):
            tunnel_id = path.split("/")[3]
            data = json.loads(body.decode('utf-8'))
            status = data.get("status", "stopped")
            set_tunnel_status(tunnel_id, status)
            self.send_json(writer, {"success": True, "status": status})
            await broadcast_ws({"event": "tunnel_updated"})
            return

        # 5. REST API: Ping & Quality Diagnostic
        if method == "POST" and path == "/api/ping":
            data = json.loads(body.decode('utf-8'))
            target_ip = data.get("target_ip")
            source_node_id = data.get("source_node_id", "panel")
            target_node_id = data.get("target_node_id", "target")

            res = await run_ping(target_ip, count=4)
            if res.get("success"):
                record_ping(source_node_id, target_node_id, res["avg_ms"], res["min_ms"], res["max_ms"], res["packet_loss"])
            self.send_json(writer, res)
            await broadcast_ws({"event": "ping_completed", "data": res})
            return

        if method == "GET" and path == "/api/pings/latest":
            pings = get_latest_pings()
            self.send_json(writer, {"pings": pings})
            return

        # 6. REST API: Agent Heartbeat & Remote Node Synchronization
        if method == "POST" and path == "/api/agent/heartbeat":
            auth_token = headers.get("x-node-token")
            node = get_node_by_token(auth_token)
            if not node:
                self.send_json(writer, {"error": "Unauthorized node token"}, status=401)
                return
            
            data = json.loads(body.decode('utf-8'))
            client_ip = headers.get("x-forwarded-for") or data.get("public_ip") or writer.get_extra_info('peername')[0]
            update_node_heartbeat(
                node["id"], client_ip,
                data.get("cpu_percent", 0),
                data.get("ram_used_mb", 0),
                data.get("ram_total_mb", 0),
                data.get("uptime_seconds", 0)
            )

            # Return all active tunnel configs for this node
            all_tunnels = list_tunnels()
            assigned_configs = []
            for t in all_tunnels:
                if t["status"] == "running":
                    if t["server_node_id"] == node["id"]:
                        cfg = generate_server_config(t)
                        assigned_configs.append({"tunnel_id": t["id"], "role": "server", "config": cfg})
                    elif t["client_node_id"] == node["id"]:
                        server_node = get_node(t["server_node_id"])
                        server_ip = server_node["ip"] if server_node else "127.0.0.1"
                        cfg = generate_client_config(t, server_ip)
                        assigned_configs.append({"tunnel_id": t["id"], "role": "client", "config": cfg})

            self.send_json(writer, {"status": "ok", "tunnels": assigned_configs})
            await broadcast_ws({"event": "node_heartbeat", "node_id": node["id"]})
            return

        # Not found fallback
        self.send_json(writer, {"error": "Not Found"}, status=404)

    async def handle_ws_dashboard(self, reader, writer):
        CONNECTED_WS_CLIENTS.add(writer)
        try:
            while True:
                hdr = await reader.read(2)
                if not hdr or len(hdr) < 2:
                    break
                length = hdr[1] & 0x7F
                if length == 126:
                    raw_len = await reader.read(2)
                    length = int.from_bytes(raw_len, 'big')
                elif length == 127:
                    raw_len = await reader.read(8)
                    length = int.from_bytes(raw_len, 'big')
                mask = await reader.read(4)
                data = await reader.read(length)
                # Unmask
                unmasked = bytes([b ^ mask[i % 4] for i, b in enumerate(data)])
                # Handle client ping or requests if needed
        except:
            pass
        finally:
            CONNECTED_WS_CLIENTS.discard(writer)

    async def serve_node_installer(self, query, headers, writer):
        token = query.get("token", [""])[0]
        role = query.get("role", ["kharej"])[0]
        name = query.get("name", ["Auto Node"])[0]
        host_header = headers.get("host", f"127.0.0.1:{self.port}")
        panel_url = f"http://{host_header}"

        script = f"""#!/usr/bin/env bash
set -e

echo "🚀 ==============================================="
echo "⚡ Hawal Tunnel (هه‌واڵ) - Automated Node Installer"
echo "🌐 Node Role: {role.upper()} | Panel: {panel_url}"
echo "==============================================="

TOKEN="{token}"
PANEL_URL="{panel_url}"
ROLE="{role}"
NAME="{name}"

if [ -z "$TOKEN" ]; then
  echo "❌ Error: Node token is missing."
  exit 1
fi

mkdir -p /opt/hawal /etc/hawal

echo "📥 Downloading Backhaul High-Performance Tunnel Core..."
ARCH=$(uname -m)
case "$ARCH" in
  x86_64)  BH_URL="https://github.com/Musixal/Backhaul/releases/latest/download/backhaul_linux_amd64.tar.gz" ;;
  aarch64) BH_URL="https://github.com/Musixal/Backhaul/releases/latest/download/backhaul_linux_arm64.tar.gz" ;;
  *) echo "Unsupported architecture: $ARCH"; exit 1 ;;
esac

curl -sL "$BH_URL" -o /tmp/backhaul.tar.gz
tar -xzf /tmp/backhaul.tar.gz -C /usr/local/bin/ backhaul
chmod +x /usr/local/bin/backhaul
rm -f /tmp/backhaul.tar.gz

echo "📥 Installing Hawal Node Agent Daemon..."
curl -sL "${{PANEL_URL}}/static/js/agent.py" -o /opt/hawal/agent.py
chmod +x /opt/hawal/agent.py

# Write agent config
cat > /etc/hawal/agent.json << EOF
{{
  "panel_url": "${{PANEL_URL}}",
  "token": "${{TOKEN}}",
  "role": "${{ROLE}}",
  "name": "${{NAME}}"
}}
EOF

# Write Systemd Service
cat > /etc/systemd/system/hawal-agent.service << EOF
[Unit]
Description=Hawal Tunnel Node Agent Daemon
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/opt/hawal
ExecStart=/usr/bin/python3 /opt/hawal/agent.py
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable hawal-agent
systemctl restart hawal-agent

echo "✅ Hawal Node (هه‌واڵ) successfully connected and active in Panel!"
"""
        resp = (
            "HTTP/1.1 200 OK\r\n"
            "Content-Type: text/x-shellscript; charset=utf-8\r\n"
            f"Content-Length: {len(script.encode('utf-8'))}\r\n"
            "Connection: close\r\n\r\n" + script
        )
        writer.write(resp.encode('utf-8'))
        await writer.drain()

    def serve_template(self, filename, writer):
        filepath = os.path.join(TEMPLATES_DIR, filename)
        if not os.path.exists(filepath):
            self.send_json(writer, {"error": "Template not found"}, status=404)
            return
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()
        resp = (
            "HTTP/1.1 200 OK\r\n"
            "Content-Type: text/html; charset=utf-8\r\n"
            f"Content-Length: {len(content.encode('utf-8'))}\r\n"
            "Connection: close\r\n\r\n" + content
        )
        writer.write(resp.encode('utf-8'))

    def serve_static_file(self, filepath, writer):
        if not os.path.exists(filepath) or os.path.isdir(filepath):
            self.send_json(writer, {"error": "File not found"}, status=404)
            return
        mime_type, _ = mimetypes.guess_type(filepath)
        mime_type = mime_type or "application/octet-stream"
        with open(filepath, "rb") as f:
            content = f.read()
        resp_headers = (
            "HTTP/1.1 200 OK\r\n"
            f"Content-Type: {mime_type}\r\n"
            f"Content-Length: {len(content)}\r\n"
            "Cache-Control: public, max-age=3600\r\n"
            "Connection: close\r\n\r\n"
        )
        writer.write(resp_headers.encode('utf-8') + content)

    def send_json(self, writer, data, status=200):
        body = json.dumps(data).encode('utf-8')
        status_text = "OK" if status == 200 else ("Not Found" if status == 404 else "Error")
        headers = (
            f"HTTP/1.1 {status} {status_text}\r\n"
            "Content-Type: application/json; charset=utf-8\r\n"
            f"Content-Length: {len(body)}\r\n"
            "Access-Control-Allow-Origin: *\r\n"
            "Access-Control-Allow-Methods: GET, POST, DELETE, OPTIONS\r\n"
            "Access-Control-Allow-Headers: Content-Type, X-Node-Token\r\n"
            "Connection: close\r\n\r\n"
        )
        writer.write(headers.encode('utf-8') + body)
