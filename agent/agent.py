#!/usr/bin/env python3
"""
⚡ Hawal Agent Daemon (هه‌واڵ)
Zero-dependency agent for Linux VPS. Manages Hawal Core (Go) & Backhaul processes,
reports live CPU/RAM metrics, and syncs tunnel configurations automatically.
"""

import os
import sys
import time
import json
import urllib.request
import subprocess
import signal
import shutil

HAWAL_DIR = "/opt/hawal"
BIN_DIR = f"{HAWAL_DIR}/bin"
CONFIG_DIR = f"{HAWAL_DIR}/tunnels"
HAWAL_CORE_BIN = f"{BIN_DIR}/hawal-core"
BACKHAUL_BIN = f"{BIN_DIR}/backhaul"
AGENT_JSON_PATH = "/etc/hawal/agent.json"

class HawalAgent:
    def __init__(self, panel_url, token, role="kharej", node_name=""):
        self.panel_url = panel_url.rstrip("/")
        self.token = token
        self.role = role
        self.node_name = node_name
        self.running_processes = {} # {tunnel_id: subprocess.Popen}
        self.running_configs = {}   # {tunnel_id: hash}

        os.makedirs(BIN_DIR, exist_ok=True)
        os.makedirs(CONFIG_DIR, exist_ok=True)

    def get_system_metrics(self):
        metrics = {
            "cpu_percent": 0.0,
            "ram_used_mb": 0,
            "ram_total_mb": 0,
            "uptime_seconds": 0
        }
        try:
            with open("/proc/stat", "r") as f:
                fields = [float(column) for column in f.readline().strip().split()[1:5]]
            idle, total = fields[3], sum(fields)
            time.sleep(0.1)
            with open("/proc/stat", "r") as f:
                fields = [float(column) for column in f.readline().strip().split()[1:5]]
            idle_delta = fields[3] - idle
            total_delta = sum(fields) - total
            if total_delta > 0:
                metrics["cpu_percent"] = round(100.0 * (1.0 - idle_delta / total_delta), 1)
        except:
            pass

        try:
            with open("/proc/meminfo", "r") as f:
                lines = f.readlines()
            mem = {}
            for line in lines:
                parts = line.split(":")
                if len(parts) == 2:
                    k = parts[0].strip()
                    v = int(parts[1].split()[0])
                    mem[k] = v
            total_mb = mem.get("MemTotal", 0) // 1024
            avail_mb = mem.get("MemAvailable", mem.get("MemFree", 0)) // 1024
            metrics["ram_total_mb"] = total_mb
            metrics["ram_used_mb"] = max(0, total_mb - avail_mb)
        except:
            pass

        try:
            with open("/proc/uptime", "r") as f:
                metrics["uptime_seconds"] = int(float(f.readline().split()[0]))
        except:
            pass

        return metrics

    def ensure_hawal_core_binary(self):
        if os.path.exists(HAWAL_CORE_BIN) and os.path.isfile(HAWAL_CORE_BIN) and os.access(HAWAL_CORE_BIN, os.X_OK):
            return True

        if os.path.exists(HAWAL_CORE_BIN) and os.path.isdir(HAWAL_CORE_BIN):
            shutil.rmtree(HAWAL_CORE_BIN)

        print(f"[Agent] 📥 Installing Hawal Core binary...")
        try:
            local_static_bin = "/opt/hawal-panel/app/static/bin/hawal-core"
            if os.path.exists(local_static_bin) and os.path.isfile(local_static_bin):
                shutil.copy(local_static_bin, HAWAL_CORE_BIN)
                os.chmod(HAWAL_CORE_BIN, 0o755)
                print("[Agent] ✅ Hawal Core binary installed from local panel.")
                return True

            url = f"{self.panel_url}/static/bin/hawal-core"
            req = urllib.request.Request(url, headers={"Authorization": f"Bearer {self.token}"})
            with urllib.request.urlopen(req, timeout=15) as resp, open(HAWAL_CORE_BIN, "wb") as out:
                shutil.copyfileobj(resp, out)
            os.chmod(HAWAL_CORE_BIN, 0o755)
            print("[Agent] ✅ Hawal Core binary downloaded and installed.")
            return True
        except Exception as e:
            print(f"[Agent] ❌ Failed to install Hawal Core binary: {e}")
            return False

    def ensure_backhaul_binary(self):
        if os.path.exists(BACKHAUL_BIN):
            return True
        try:
            if os.path.exists("/usr/local/bin/backhaul"):
                shutil.copy("/usr/local/bin/backhaul", BACKHAUL_BIN)
                os.chmod(BACKHAUL_BIN, 0o755)
                return True
        except:
            pass
        return True

    def send_heartbeat(self):
        metrics = self.get_system_metrics()
        url = f"{self.panel_url}/api/agent/heartbeat"
        req = urllib.request.Request(
            url,
            data=json.dumps(metrics).encode('utf-8'),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.token}"
            },
            method="POST"
        )
        try:
            with urllib.request.urlopen(req, timeout=5) as response:
                return response.status == 200
        except Exception as e:
            return False

    def sync_tunnels(self):
        url = f"{self.panel_url}/api/agent/sync"
        req = urllib.request.Request(
            url,
            headers={"Authorization": f"Bearer {self.token}"},
            method="GET"
        )
        try:
            with urllib.request.urlopen(req, timeout=6) as response:
                data = json.loads(response.read().decode('utf-8'))
                configs = data.get("configs", [])
                self.apply_configs(configs)
        except Exception as e:
            pass

    def apply_configs(self, configs):
        active_ids = set()

        for item in configs:
            tun_id = item["tunnel_id"]
            core_type = item.get("core_type", "hawal")
            active_ids.add(tun_id)

            proc = self.running_processes.get(tun_id)
            is_running = proc is not None and proc.poll() is None

            if core_type == "hawal":
                if not self.ensure_hawal_core_binary():
                    continue

                cfg_path = f"{CONFIG_DIR}/{tun_id}.json"
                cfg_content = json.dumps(item["config"], indent=2)
                
                if not is_running or self.running_configs.get(tun_id) != cfg_content:
                    with open(cfg_path, "w") as f:
                        f.write(cfg_content)
                    self.restart_tunnel_process(tun_id, [HAWAL_CORE_BIN, "-config", cfg_path], cfg_content)

            elif core_type == "backhaul":
                self.ensure_backhaul_binary()
                cfg_path = f"{CONFIG_DIR}/{tun_id}.toml"
                toml_content = item.get("toml", "")
                if not is_running or self.running_configs.get(tun_id) != toml_content:
                    with open(cfg_path, "w") as f:
                        f.write(toml_content)
                    self.restart_tunnel_process(tun_id, [BACKHAUL_BIN, "-c", cfg_path], toml_content)

        # Stop removed tunnels
        for tun_id in list(self.running_processes.keys()):
            if tun_id not in active_ids:
                print(f"[Agent] 🛑 Stopping removed tunnel {tun_id}...")
                self.stop_tunnel_process(tun_id)

    def restart_tunnel_process(self, tun_id, cmd, content_hash):
        self.stop_tunnel_process(tun_id)
        try:
            print(f"[Agent] 🚀 Launching tunnel {tun_id} -> {' '.join(cmd)}")
            proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            self.running_processes[tun_id] = proc
            self.running_configs[tun_id] = content_hash
        except Exception as e:
            print(f"[Agent] ❌ Failed to start tunnel process {tun_id}: {e}")

    def stop_tunnel_process(self, tun_id):
        if tun_id in self.running_processes:
            proc = self.running_processes[tun_id]
            try:
                proc.terminate()
                proc.wait(timeout=2)
            except:
                proc.kill()
            del self.running_processes[tun_id]
            self.running_configs.pop(tun_id, None)

    def run(self):
        print(f"🚀 Hawal Agent started ({self.node_name} - {self.role}). Syncing with {self.panel_url}...")
        while True:
            self.send_heartbeat()
            self.sync_tunnels()
            time.sleep(4)

if __name__ == "__main__":
    p_url = None
    p_token = None
    p_role = "kharej"
    p_name = "Node"

    # 1. First priority: /etc/hawal/agent.json if present
    if os.path.exists(AGENT_JSON_PATH):
        try:
            with open(AGENT_JSON_PATH, "r") as f:
                cfg = json.load(f)
            p_url = cfg.get("panel_url")
            p_token = cfg.get("token")
            p_role = cfg.get("role", "kharej")
            p_name = cfg.get("name", "Node")
        except Exception as e:
            print(f"Error reading {AGENT_JSON_PATH}: {e}")

    # 2. Command line overrides
    if len(sys.argv) >= 3 and sys.argv[1].startswith("http"):
        p_url = sys.argv[1]
        p_token = sys.argv[2]
        if len(sys.argv) > 3: p_role = sys.argv[3]
        if len(sys.argv) > 4: p_name = sys.argv[4]

    if not p_url or not p_token:
        print(f"❌ Could not find valid panel_url or token in {AGENT_JSON_PATH} or arguments.")
        sys.exit(1)

    agent = HawalAgent(p_url, p_token, p_role, p_name)
    agent.run()
