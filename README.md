# ⚡ Hawal — Multi-Core Tunnel Management Panel

> A lightweight web control plane for creating, monitoring, and managing tunnels between Iranian and global nodes.

[![License: MIT](https://img.shields.io/badge/License-MIT-2563eb.svg)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.8%2B-3776ab?logo=python&logoColor=white)](https://www.python.org/)
[![Docker](https://img.shields.io/badge/Docker-Ready-2496ed?logo=docker&logoColor=white)](docker-compose.yml)
[![Cores](https://img.shields.io/badge/Cores-Hawal%20%7C%20Backhaul%20%7C%20Paqet-0f766e)](#tunnel-cores)

**Hawal** (هه‌واڵ, Kurdish for “friend” or “companion”) keeps tunnel configuration in one panel and synchronizes it to lightweight agents on your servers.

🇮🇷 [مستندات فارسی](README_FA.md)

---

## Highlights

- Web-based creation and editing of multi-port tunnels
- Iran and global node enrollment using panel-generated install commands
- Three selectable cores: **Hawal Stealth Core**, **Backhaul**, and **Paqet**
- Live node health, CPU/RAM, ping, packet-loss, and tunnel status
- Paqet wire-traffic accounting from destination-server raw-table counters
- Systemd services for the panel and agents; Docker Compose for the panel
- Embedded SQLite — no Redis, PostgreSQL, or external control service

## Architecture

```text
 Browser
    │
    ▼
┌──────────────────────┐     configuration sync      ┌──────────────────────┐
│ Hawal panel :9090    │◄───────────────────────────►│ Node agents          │
│ nodes, tunnels, stats│                              │ /opt/hawal/agent.py  │
└──────────────────────┘                              └──────────┬───────────┘
                                                                  │
        Hawal Stealth Core  |  Backhaul multiplexing  |  Paqet raw TCP + KCP
                                                                  │
             entry port on Iran ◄────── tunnel ──────► target service on global node
```

## Tunnel cores

| Core | Best for | Transport | Notes |
|---|---|---|---|
| ⚡ **Hawal Stealth Core** | Simple default deployments | `stealth` | Hawal’s built-in core with padding and `nodelay` |
| 🚀 **Backhaul** | Standard multiplexed tunnels | `ws`, `tcp`, `tcpmux`, `tls` | Keep the core port separate from forwarded ports |
| 🛡️ **Paqet** | Raw-packet/KCP paths | `kcp` | Needs root, a usable NIC, and firewall setup; intended for advanced use |

Start with Hawal Stealth Core. Use Backhaul when its standard transports fit your network. Choose Paqet only if you understand raw sockets and firewall troubleshooting.

> Do not use ports 80 or 443 as a **Paqet core port**. Use a dedicated non-standard port such as `3107` or `9999`.

## Requirements

- Linux with systemd and `root` access
- Python 3, `curl`, and `tar`
- A free panel port (default: `9090`)
- A unique and reachable core port per tunnel
- Connectivity from every node to the panel and between tunnel peers

Protect a public panel with a firewall, VPN, or access-controlled reverse proxy.

## Quick start

### 1. Install the panel

Run this on the server hosting the control panel:

```bash
curl -fsSL https://raw.githubusercontent.com/T4wroot/hawal/master/install-panel.sh | bash
```

Use another panel port when needed:

```bash
curl -fsSL https://raw.githubusercontent.com/T4wroot/hawal/master/install-panel.sh | bash -s -- --port 9090
```

Then open `http://PANEL_IP:9090`.

### 2. Add nodes

1. Add the Iran and global nodes in **Node Management**.
2. Run the generated installation command on each matching node.
3. Wait until the node status becomes `Online`.

Example panel-generated command:

```bash
curl -fsSL "http://PANEL_IP:9090/install?token=NODE_TOKEN&role=kharej&name=Germany" | bash
```

### 3. Create a tunnel

Select nodes, a core, a dedicated core port, and forwarded ports. Use this mapping format:

```text
443=127.0.0.1:443
8443=127.0.0.1:8443
```

Example:

```text
Tunnel name:     iran-to-germany-443
Core:            Hawal Stealth Core
Core port:       3107
Forwarded port:  443=127.0.0.1:443
```

`3107` is the core transport port; `443` is the user-facing forwarded port. They must not collide.

## Paqet notes

Paqet carries traffic through raw TCP packets with KCP, so `ss` and `/proc/PID/io` are not valid traffic sources. Hawal reports the dedicated server-side raw-table counters instead; the result is real wire usage, including KCP overhead.

- Paqet requires root and `iptables`.
- The agent applies `NOTRACK` and TCP-RST protection only to the Paqet server core port.
- Forwarded client ports remain normal, tracked TCP ports.
- Required Paqet rules are restored when the agent starts.

## Operations and troubleshooting

```bash
# Panel status
systemctl status hawal-panel --no-pager

# Agent status and logs (on every node)
systemctl status hawal-agent --no-pager
journalctl -u hawal-agent -n 100 --no-pager

# One Paqet tunnel log
tail -f /opt/hawal/logs/TUNNEL_ID.log

# Listening ports
ss -lntup
```

For an offline node, check panel reachability, token, firewall rules, and `hawal-agent`. For Paqet, verify that the global-node core port is dedicated and its raw-table rules are present.

## Docker Compose

```bash
git clone https://github.com/T4wroot/hawal.git
cd hawal
docker compose up -d --build
docker compose logs -f hawal-panel
```

The Docker deployment uses host networking and listens on port 9090.

## Security and responsible use

- Treat node tokens as secrets; never post them in issues, logs, or screenshots.
- Place a public panel behind TLS and network access control.
- Review firewall rules and target services before opening forwarded ports.
- You are responsible for compliance with applicable law, provider terms, and network policy.

## Contributing

Issues and pull requests are welcome. Good bug reports include the Hawal version, selected core, node roles, sanitized logs, and reproduction steps. Remove tokens and sensitive IP addresses before posting.

## License

Released under the [MIT License](LICENSE) © 2026 [T4wroot](https://github.com/T4wroot) and Hawal contributors.
