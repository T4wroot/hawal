"""
⚡ Hawal Tunnel - Paqet Engine (هه‌واڵ)
Generates client and server YAML configurations for Paqet (Raw Packet + KCP anti-DPI core).
"""

def parse_ports_list(ports):
    """
    Parses ports list which may be in formats:
    - ["443=127.0.0.1:443", "2083=127.0.0.1:2083"]
    - ["443", "2083"]
    - ["443:443"]
    Returns list of dicts: [{"listen": "443", "target": "127.0.0.1:443"}]
    """
    parsed = []
    for p in ports:
        p = str(p).strip()
        if not p:
            continue
        if "=" in p:
            parts = p.split("=", 1)
            listen_p = parts[0].strip()
            target_addr = parts[1].strip()
            if ":" not in target_addr:
                target_addr = f"127.0.0.1:{target_addr}"
            parsed.append({"listen": listen_p, "target": target_addr})
        elif ":" in p:
            parts = p.split(":", 1)
            parsed.append({"listen": parts[0].strip(), "target": f"127.0.0.1:{parts[1].strip()}"})
        else:
            parsed.append({"listen": p, "target": f"127.0.0.1:{p}"})
    return parsed

def generate_paqet_server_config(tunnel):
    """
    Generates Paqet server YAML config template.
    Template markers {{INTERFACE}}, {{LOCAL_IP}}, {{ROUTER_MAC}} are dynamically
    injected by the node's agent based on local network topology.
    """
    core_port = int(tunnel.get("core_port", 8888))
    token = tunnel.get("token", "hawal-secret-key")
    conn = int(tunnel.get("mux_con", 4))
    raw_chan = int(tunnel.get("channel_size", 1150))
    mtu = raw_chan if raw_chan <= 1400 else 1150
    kcp_mode = "fast"
    block_cipher = "aes-128-gcm"

    yaml_content = f"""# Hawal Paqet Server Config (Auto-Generated)
role: "server"

log:
  level: "info"

listen:
  addr: ":{core_port}"

network:
  interface: "{{{{INTERFACE}}}}"
  ipv4:
    addr: "{{{{LOCAL_IP}}}}:{core_port}"
    router_mac: "{{{{ROUTER_MAC}}}}"
  tcp:
    local_flag: ["PA"]
  pcap:
    sockbuf: 8388608

transport:
  protocol: "kcp"
  conn: {conn}
  tcpbuf: 8192
  udpbuf: 4096
  kcp:
    key: "{token}"
    mode: "{kcp_mode}"
    block: "{block_cipher}"
    mtu: {mtu}
"""
    return yaml_content

def generate_paqet_client_config(tunnel, server_ip):
    """
    Generates Paqet client YAML config template with port forwarding rules.
    Template markers {{INTERFACE}}, {{LOCAL_IP}}, {{ROUTER_MAC}} are dynamically
    injected by the node's agent based on local network topology.
    """
    core_port = int(tunnel.get("core_port", 8888))
    token = tunnel.get("token", "hawal-secret-key")
    conn = int(tunnel.get("mux_con", 4))
    raw_chan = int(tunnel.get("channel_size", 1150))
    mtu = raw_chan if raw_chan <= 1400 else 1150
    kcp_mode = "fast"
    block_cipher = "aes-128-gcm"

    ports = parse_ports_list(tunnel.get("ports", []))
    forward_lines = []
    for p in ports:
        listen_port = p["listen"]
        target = p["target"]
        forward_lines.append(f"""  - listen: "0.0.0.0:{listen_port}"
    target: "{target}"
    protocol: "tcp"
  - listen: "0.0.0.0:{listen_port}"
    target: "{target}"
    protocol: "udp" """)

    forward_block = "\n".join(forward_lines) if forward_lines else """  - listen: "0.0.0.0:443"
    target: "127.0.0.1:443"
    protocol: "tcp" """

    yaml_content = f"""# Hawal Paqet Client Config (Auto-Generated)
role: "client"

log:
  level: "info"

forward:
{forward_block}

network:
  interface: "{{{{INTERFACE}}}}"
  ipv4:
    addr: "{{{{LOCAL_IP}}}}:0"
    router_mac: "{{{{ROUTER_MAC}}}}"
  tcp:
    local_flag: ["PA"]
    remote_flag: ["PA"]
  pcap:
    sockbuf: 4194304

server:
  addr: "{server_ip}:{core_port}"

transport:
  protocol: "kcp"
  conn: {conn}
  tcpbuf: 8192
  udpbuf: 4096
  kcp:
    key: "{token}"
    mode: "{kcp_mode}"
    block: "{block_cipher}"
    mtu: {mtu}
"""
    return yaml_content
