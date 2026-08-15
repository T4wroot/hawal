import json
from app.db import list_tunnels

def validate_tunnel_ports(core_port, server_node_id, current_tunnel_id=None):
    """
    Validates that core_port is not duplicated across active tunnels on the same server node.
    """
    all_tunnels = list_tunnels()
    for t in all_tunnels:
        if current_tunnel_id and t["id"] == current_tunnel_id:
            continue
        if t["server_node_id"] == server_node_id and int(t["core_port"]) == int(core_port):
            return False, f"پورت ترانسپورت {core_port} در حال حاضر توسط تانل '{t['name']}' روی همین نود در حال استفاده است."
    return True, ""

def generate_server_config(tunnel, bind_ip="0.0.0.0"):
    """
    Generates Backhaul server TOML configuration with modern options.
    """
    ports = tunnel.get("ports", [])
    ports_toml = "[\n" + ",\n".join([f'  "{p}"' for p in ports]) + "\n]"
    
    transport = tunnel.get("transport", "ws")
    token = tunnel.get("token", "")
    core_port = tunnel.get("core_port", 3080)
    nodelay = "true" if tunnel.get("nodelay", 1) else "false"
    snappy = "true" if tunnel.get("snappy", 1) else "false"
    mux_con = tunnel.get("mux_con", 8)
    keepalive = tunnel.get("keepalive", 75)
    channel_size = tunnel.get("channel_size", 2048)

    config = f"""[server]
bind_addr = "{bind_ip}:{core_port}"
transport = "{transport}"
token = "{token}"
ports = {ports_toml}
nodelay = {nodelay}
snappy = {snappy}
keepalive_period = {keepalive}
channel_size = {channel_size}
log_level = "info"
heartbeat = 40
mux_con = {mux_con}
"""
    return config

def generate_client_config(tunnel, server_public_ip):
    """
    Generates Backhaul client TOML configuration.
    """
    transport = tunnel.get("transport", "ws")
    token = tunnel.get("token", "")
    core_port = tunnel.get("core_port", 3080)
    nodelay = "true" if tunnel.get("nodelay", 1) else "false"
    snappy = "true" if tunnel.get("snappy", 1) else "false"
    mux_con = tunnel.get("mux_con", 8)
    keepalive = tunnel.get("keepalive", 75)

    config = f"""[client]
remote_addr = "{server_public_ip}:{core_port}"
transport = "{transport}"
token = "{token}"
connection_pool = 4
retry_interval = 3
nodelay = {nodelay}
snappy = {snappy}
keepalive_period = {keepalive}
log_level = "info"
dial_timeout = 10
mux_con = {mux_con}
"""
    return config

def generate_docker_compose(tunnel, role="server", server_ip="127.0.0.1"):
    """
    Generates a ready-to-use docker-compose.yml for this specific tunnel.
    """
    if role == "server":
        cfg = generate_server_config(tunnel)
    else:
        cfg = generate_client_config(tunnel, server_ip)

    compose = f"""version: '3.8'

services:
  hawal-backhaul:
    image: musixal/backhaul:latest
    container_name: hawal_{tunnel['id']}_{role}
    restart: always
    network_mode: host
    volumes:
      - ./config.toml:/root/config.toml
    command: ["-c", "/root/config.toml"]
"""
    return compose, cfg
