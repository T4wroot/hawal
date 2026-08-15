# ⚡ Hawal Tunnel (هه‌واڵ)

> **Modern, Zero-Dependency Tunnel Management Panel & Lightning-Fast Multiplexing Core for Censorship Circumvention.**

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.8%2B-blue?logo=python&logoColor=white)](https://python.org)
[![Docker](https://img.shields.io/badge/Docker-Ready-2496ED?logo=docker&logoColor=white)](Dockerfile)
[![Core: Backhaul](https://img.shields.io/badge/Core-Backhaul%20Multiplex-emerald)](https://github.com/Musixal/Backhaul)

*«Hawal» (هه‌واڵ) is a Kurdish word meaning **Friend / Companion / Comrade**.*

🇮🇷 **راهنمای فارسی:** برای مطالعه کامل مستندات به زبان فارسی، به فایل [README_FA.md](README_FA.md) مراجعه کنید.

---

## 🌟 Why Hawal Tunnel?

Unlike legacy tunnel managers that suffer from port collision bugs, zombie processes, heavy docker bloat, or brittle file synchronizations, **Hawal Tunnel** provides a sleek, lightweight, zero-dependency control plane designed specifically for multi-server tunneling between Iran and global datacenters.

```
┌─────────────────────────────────────────────────────────────┐
│                 🖥️ Hawal Master Web Panel                   │
│   - Live Visual Topology & Real-time Metrics                │
│   - Interactive Tag-Based Port Forwarding (443, 2083, ...)  │
│   - GeoIP Country & Flag Auto-Detection                     │
│   - Inter-Server Ping & Packet-Loss Matrix                  │
└──────────────────────────────▲──────────────────────────────┘
                               │ (Secure WebSocket Heartbeat & Sync)
            ┌──────────────────┴──────────────────┐
            ▼                                     ▼
┌─────────────────────────┐             ┌─────────────────────────┐
│  🇮🇷 Iran Hub (Node)     │ ◄─────────► │  🇩🇪 Global Core (Node)  │
│   - Backhaul Server MUX │  ⚡ WS MUX   │   - Backhaul Client MUX │
│   - Ports: 443, 2083    │   (Sub-2ms) │   - Zero Port Collision │
└─────────────────────────┘             └─────────────────────────┘
```

---

## ✨ Key Features

* 🚀 **Zero Dependencies:** Pure standard library. Runs out of the box on any Linux VPS without needing Python `pip` packages, NodeJS builds, or database setups.
* ⚡ **One-Line Instant Installer:**
  * Install Panel in 5 seconds on any VPS.
  * Connect Nodes instantly with a one-line command (`curl ... | bash` or `docker run`).
* 🏷️ **Interactive Port Tag Builder:** Add forwarding ports (`443`, `2083`, `8080`, `8443`) with Enter key or 1-click preset badges.
* 🌍 **Smart GeoIP & Country Flags:** Automatically resolves public IPs to real country names and emoji flags (🇩🇪 Germany, 🇫🇮 Finland, 🇳🇱 Netherlands, 🇮🇷 Iran, 🇺🇸 USA, 🇹🇷 Turkey, etc.).
* 📊 **Live Topology & Inter-Node Ping:** Real-time visual route animation and millisecond ping/packet loss testing between servers.
* 🛡️ **Anti-DPI Transport Support:** Toggle between `WebSocket`, `TCP`, `TCPMux`, and `TLS` to prevent throttling and DPI packet drops.
* 🐳 **Native & Docker Ready:** Full support for both Linux Systemd services and Docker Compose containers.

---

## 🚀 Quick Start & Installation

### 1. Install Master Panel (on Iran or Global VPS)

Run this single command on your main server:

```bash
curl -fsSL https://raw.githubusercontent.com/T4wroot/hawal/master/install-panel.sh | bash
```

Once installed, open your browser at:
👉 `http://YOUR_SERVER_IP:9090`

---

### 2. Connect Nodes (Iran & Global Servers)

1. Open the Hawal Dashboard and go to **مدیریت نودها (Nodes)**.
2. Click **+ افزودن نود جدید (Add Node)**, enter the server name and IP.
3. Copy the generated **One-Line Command** and run it on the remote server:

```bash
# Example generated command:
curl -fsSL "http://YOUR_PANEL_IP:9090/install?token=YOUR_TOKEN&role=kharej&name=Germany-Core" | bash
```

The node will connect, perform GeoIP self-discovery, and appear **Online** within 2 seconds!

---

### 3. Docker Deployment (Optional)

You can also run Hawal via Docker Compose:

```bash
git clone https://github.com/T4wroot/hawal.git
cd hawal
docker compose up -d
```

---

## ⚙️ REST API Endpoints

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/api/nodes` | List all registered nodes and live metrics |
| `POST` | `/api/nodes` | Register a new node definition and generate token |
| `DELETE` | `/api/nodes/<id>` | Remove a node |
| `GET` | `/api/tunnels` | List all configured Backhaul tunnels |
| `POST` | `/api/tunnels` | Create or update a tunnel with port validation |
| `POST` | `/api/tunnels/<id>/status` | Start or stop a tunnel |
| `POST` | `/api/ping` | Execute live ICMP ping and packet loss test |
| `GET` | `/api/settings` | Get panel configuration variables |
| `GET` | `/ws` | WebSocket stream for real-time live events |

---

## 📄 License

Released under the [MIT License](LICENSE) © 2026 [T4wroot](https://github.com/T4wroot) & Hawal Tunnel Contributors.
