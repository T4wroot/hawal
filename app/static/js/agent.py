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
LOG_DIR = f"{HAWAL_DIR}/logs"
HAWAL_CORE_BIN = f"{BIN_DIR}/hawal-core"
BACKHAUL_BIN = f"{BIN_DIR}/backhaul"
PAQET_BIN = f"{BIN_DIR}/paqet"
GOST_BIN = f"{BIN_DIR}/gost"
AGENT_JSON_PATH = "/etc/hawal/agent.json"
AGENT_RESTART_NONCE_PATH = f"{HAWAL_DIR}/agent-restart-nonce"

class HawalAgent:
    def __init__(self, panel_url, token, role="kharej", node_name=""):
        self.panel_url = panel_url.rstrip("/")
        self.token = token
        self.role = role
        self.node_name = node_name
        self.running_processes = {} # {tunnel_id: subprocess.Popen}
        self.running_configs = {}   # {tunnel_id: hash}
        self.running_metadata = {}  # {tunnel_id: runtime details used for cleanup}
        self.shutdown_requested = False
        self.last_log_report = 0
        self.agent_restart_nonce = self._load_agent_restart_nonce()

        os.makedirs(BIN_DIR, exist_ok=True)
        os.makedirs(CONFIG_DIR, exist_ok=True)
        os.makedirs(LOG_DIR, exist_ok=True)

    def _load_agent_restart_nonce(self):
        try:
            with open(AGENT_RESTART_NONCE_PATH, "r") as f:
                return int(f.read().strip() or 0)
        except Exception:
            return 0

    def _save_agent_restart_nonce(self, nonce):
        with open(AGENT_RESTART_NONCE_PATH, "w") as f:
            f.write(str(nonce))

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

    def ensure_paqet_binary(self):
        if os.path.exists(PAQET_BIN) and os.path.isfile(PAQET_BIN) and os.access(PAQET_BIN, os.X_OK):
            return True

        print(f"[Agent] 📥 Installing Paqet binary...")
        try:
            local_static_bin = "/opt/hawal-panel/app/static/bin/paqet"
            if os.path.exists(local_static_bin) and os.path.isfile(local_static_bin):
                shutil.copy(local_static_bin, PAQET_BIN)
                os.chmod(PAQET_BIN, 0o755)
                print("[Agent] ✅ Paqet binary installed from local panel.")
                return True

            import platform
            machine = platform.machine().lower()
            if machine in ("x86_64", "amd64"):
                arch = "amd64"
            elif "arm64" in machine or "aarch64" in machine:
                arch = "arm64"
            elif "arm" in machine:
                arch = "arm32"
            else:
                raise RuntimeError(f"unsupported CPU architecture: {machine}")

            try:
                subprocess.run(["apt-get", "install", "-y", "libpcap0.8"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=20)
            except:
                pass

            import tarfile, io
            url = f"https://github.com/hanselime/paqet/releases/download/v1.0.0-alpha.21/paqet-linux-{arch}-v1.0.0-alpha.21.tar.gz"
            req = urllib.request.Request(url, headers={"User-Agent": "Hawal-Agent"})
            with urllib.request.urlopen(req, timeout=35) as resp:
                tar_bytes = io.BytesIO(resp.read())
                with tarfile.open(fileobj=tar_bytes, mode="r:gz") as tar:
                    for member in tar.getmembers():
                        if member.isfile() and os.path.basename(member.name) in ("paqet", f"paqet_linux_{arch}"):
                            f = tar.extractfile(member)
                            if f:
                                temp_bin = f"{PAQET_BIN}.download"
                                with open(temp_bin, "wb") as out:
                                    out.write(f.read())
                                os.chmod(temp_bin, 0o755)
                                os.replace(temp_bin, PAQET_BIN)
                                print(f"[Agent] ✅ Paqet ({arch}) binary installed successfully.")
                                return True
        except Exception as e:
            print(f"[Agent] ❌ Failed to install Paqet binary: {e}")
            return False
        return os.path.exists(PAQET_BIN)

    def ensure_gost_binary(self):
        if os.path.isfile(GOST_BIN) and os.access(GOST_BIN, os.X_OK):
            return True
        try:
            import platform, tarfile, io
            machine = platform.machine().lower()
            if machine in ("x86_64", "amd64"):
                arch = "amd64"
            elif machine in ("aarch64", "arm64"):
                arch = "arm64"
            else:
                raise RuntimeError(f"unsupported CPU architecture: {machine}")
            version = "3.2.6"
            url = f"https://github.com/go-gost/gost/releases/download/v{version}/gost_{version}_linux_{arch}.tar.gz"
            print(f"[Agent] 📥 Installing GOST v{version} ({arch})...")
            req = urllib.request.Request(url, headers={"User-Agent": "Hawal-Agent"})
            with urllib.request.urlopen(req, timeout=45) as resp:
                with tarfile.open(fileobj=io.BytesIO(resp.read()), mode="r:gz") as tar:
                    member = next((m for m in tar.getmembers() if m.isfile() and os.path.basename(m.name) == "gost"), None)
                    if not member:
                        raise RuntimeError("gost binary was not found in release archive")
                    source = tar.extractfile(member)
                    with open(f"{GOST_BIN}.download", "wb") as out:
                        out.write(source.read())
            os.chmod(f"{GOST_BIN}.download", 0o755)
            os.replace(f"{GOST_BIN}.download", GOST_BIN)
            print("[Agent] ✅ GOST binary installed successfully.")
            return True
        except Exception as e:
            print(f"[Agent] ❌ Failed to install GOST binary: {e}")
            return False

    def get_network_info(self):
        iface = ""
        local_ip = ""
        gateway_ip = ""
        gateway_mac = ""
        try:
            res = subprocess.check_output(["ip", "route"], stderr=subprocess.DEVNULL).decode('utf-8')
            for line in res.splitlines():
                if "default" in line and "dev" in line:
                    parts = line.split()
                    if "dev" in parts:
                        iface = parts[parts.index("dev") + 1]
                    if "via" in parts:
                        gateway_ip = parts[parts.index("via") + 1]
                    break
        except:
            pass
        try:
            res = subprocess.check_output(["ip", "-4", "addr", "show", iface], stderr=subprocess.DEVNULL).decode('utf-8')
            import re
            m = re.search(r'inet\s+(\d+\.\d+\.\d+\.\d+)', res)
            if m:
                local_ip = m.group(1)
        except:
            pass
        try:
            if gateway_ip:
                subprocess.run(["ping", "-c", "1", "-W", "1", gateway_ip], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                res = subprocess.check_output(["ip", "neigh", "show", gateway_ip], stderr=subprocess.DEVNULL).decode('utf-8')
                import re
                m = re.search(r'([0-9a-fA-F]{2}(?::[0-9a-fA-F]{2}){5})', res)
                if m:
                    gateway_mac = m.group(1)
        except:
            pass
        return iface, local_ip, gateway_mac

    def _iptables_rule(self, action, table, chain, rule):
        return subprocess.run(
            ["iptables", "-t", table, action, chain] + rule,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        ).returncode == 0

    def configure_paqet_iptables(self, role, core_port, ports=None):
        if role == "server":
            rules = [
                ("raw", "PREROUTING", ["-p", "tcp", "--dport", str(core_port), "-j", "NOTRACK"]),
                ("raw", "OUTPUT", ["-p", "tcp", "--sport", str(core_port), "-j", "NOTRACK"]),
                ("mangle", "OUTPUT", ["-p", "tcp", "--sport", str(core_port), "--tcp-flags", "RST", "RST", "-j", "DROP"]),
            ]
        else:
            # Paqet's client uses a normal local TCP listener for forwarded ports.
            # The upstream firewall bypass rules are required only on the raw-packet
            # server port; applying NOTRACK to a forwarded port (such as 80/443)
            # can break conntrack for real client traffic.
            rules = []
        try:
            for table, chain, rule in rules:
                if not self._iptables_rule("-C", table, chain, rule):
                    if not self._iptables_rule("-A", table, chain, rule):
                        raise RuntimeError(f"could not add iptables {table}/{chain} rule")
            return True
        except Exception as e:
            print(f"[Agent] ❌ Failed to configure iptables for Paqet: {e}")
            self.cleanup_paqet_iptables(role, core_port, ports)
            return False

    def cleanup_paqet_iptables(self, role, core_port, ports=None):
        if role == "server":
            rules = [
                ("raw", "PREROUTING", ["-p", "tcp", "--dport", str(core_port), "-j", "NOTRACK"]),
                ("raw", "OUTPUT", ["-p", "tcp", "--sport", str(core_port), "-j", "NOTRACK"]),
                ("mangle", "OUTPUT", ["-p", "tcp", "--sport", str(core_port), "--tcp-flags", "RST", "RST", "-j", "DROP"]),
            ]
        else:
            rules = []
        try:
            for table, chain, rule in rules:
                while self._iptables_rule("-D", table, chain, rule):
                    pass
        except Exception as e:
            print(f"[Agent] ⚠️ Failed to clean Paqet iptables rules: {e}")

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
                requested_nonce = int(data.get("agent_restart_nonce", 0) or 0)
                if requested_nonce > self.agent_restart_nonce:
                    self._save_agent_restart_nonce(requested_nonce)
                    self.agent_restart_nonce = requested_nonce
                    print("[Agent] 🔄 Restart requested by panel.")
                    self.shutdown_requested = True
        except Exception as e:
            pass

    def report_logs(self):
        if time.time() - self.last_log_report < 12:
            return
        snapshots = {}
        try:
            result = subprocess.run(["journalctl", "-u", "hawal-agent", "-n", "80", "--no-pager"], capture_output=True, text=True, timeout=4)
            snapshots["agent"] = result.stdout[-12000:]
            for tun_id in self.running_processes:
                path = f"{LOG_DIR}/{tun_id}.log"
                if os.path.exists(path):
                    with open(path, "rb") as f:
                        f.seek(max(0, os.path.getsize(path) - 12000))
                        snapshots[f"tunnel:{tun_id}"] = f.read().decode("utf-8", errors="replace")
            req = urllib.request.Request(
                f"{self.panel_url}/api/agent/logs",
                data=json.dumps({"snapshots": snapshots}).encode("utf-8"),
                headers={"Content-Type": "application/json", "Authorization": f"Bearer {self.token}"}, method="POST"
            )
            with urllib.request.urlopen(req, timeout=5):
                self.last_log_report = time.time()
        except Exception:
            pass

    def apply_configs(self, configs):
        active_ids = set()

        for item in configs:
            tun_id = item["tunnel_id"]
            core_type = item.get("core_type", "hawal")
            restart_marker = f"\x00restart:{item.get('restart_nonce', 0)}"
            active_ids.add(tun_id)

            proc = self.running_processes.get(tun_id)
            is_running = proc is not None and proc.poll() is None

            if core_type == "hawal":
                if not self.ensure_hawal_core_binary():
                    continue

                cfg_path = f"{CONFIG_DIR}/{tun_id}.json"
                cfg_content = json.dumps(item["config"], indent=2)
                
                marker = cfg_content + restart_marker
                if not is_running or self.running_configs.get(tun_id) != marker:
                    with open(cfg_path, "w") as f:
                        f.write(cfg_content)
                    self.restart_tunnel_process(tun_id, [HAWAL_CORE_BIN, "-config", cfg_path], marker)

            elif core_type == "backhaul":
                self.ensure_backhaul_binary()
                cfg_path = f"{CONFIG_DIR}/{tun_id}.toml"
                toml_content = item.get("toml", "")
                marker = toml_content + restart_marker
                if not is_running or self.running_configs.get(tun_id) != marker:
                    with open(cfg_path, "w") as f:
                        f.write(toml_content)
                    self.restart_tunnel_process(tun_id, [BACKHAUL_BIN, "-c", cfg_path], marker)

            elif core_type == "paqet":
                if not self.ensure_paqet_binary():
                    continue
                cfg_path = f"{CONFIG_DIR}/{tun_id}.yaml"
                yaml_template = item.get("yaml", "")
                role = item.get("role", "client")
                core_port = item.get("core_port", 8888)
                ports = item.get("ports", [])

                iface, local_ip, gw_mac = self.get_network_info()
                if not iface or not local_ip or not gw_mac:
                    print(f"[Agent] ❌ Paqet {tun_id} not started: interface, IPv4 address, or gateway MAC could not be detected.")
                    self.stop_tunnel_process(tun_id)
                    continue
                yaml_content = yaml_template.replace("{{INTERFACE}}", iface).replace("{{LOCAL_IP}}", local_ip).replace("{{ROUTER_MAC}}", gw_mac)

                marker = yaml_content + restart_marker
                if not is_running or self.running_configs.get(tun_id) != marker:
                    self.stop_tunnel_process(tun_id)
                    with open(cfg_path, "w") as f:
                        f.write(yaml_content)
                    if not self.configure_paqet_iptables(role, core_port, ports):
                        continue
                    self.restart_tunnel_process(
                        tun_id,
                        [PAQET_BIN, "run", "-c", cfg_path],
                        marker,
                        {"core_type": "paqet", "role": role, "core_port": core_port, "ports": ports}
                    )

            elif core_type == "gost":
                if not self.ensure_gost_binary():
                    continue
                command = item.get("command", [])
                if not command:
                    print(f"[Agent] ❌ GOST {tun_id} not started: empty command.")
                    continue
                command_content = json.dumps(command, separators=(",", ":"))
                marker = command_content + restart_marker
                if not is_running or self.running_configs.get(tun_id) != marker:
                    self.restart_tunnel_process(
                        tun_id, [GOST_BIN] + command, marker,
                        {"core_type": "gost", "role": item.get("role", "client")}
                    )

        # Stop removed tunnels
        for tun_id in list(self.running_processes.keys()):
            if tun_id not in active_ids:
                print(f"[Agent] 🛑 Stopping removed tunnel {tun_id}...")
                self.stop_tunnel_process(tun_id)

    def restart_tunnel_process(self, tun_id, cmd, content_hash, metadata=None):
        self.stop_tunnel_process(tun_id)
        try:
            print(f"[Agent] 🚀 Launching tunnel {tun_id} -> {' '.join(cmd)}")
            log_path = f"{LOG_DIR}/{tun_id}.log"
            log_file = open(log_path, "a")
            proc = subprocess.Popen(cmd, stdout=log_file, stderr=subprocess.STDOUT)
            log_file.close()
            self.running_processes[tun_id] = proc
            self.running_configs[tun_id] = content_hash
            self.running_metadata[tun_id] = metadata or {}
        except Exception as e:
            print(f"[Agent] ❌ Failed to start tunnel process {tun_id}: {e}")

    def stop_tunnel_process(self, tun_id):
        metadata = self.running_metadata.get(tun_id, {})
        if tun_id in self.running_processes:
            proc = self.running_processes[tun_id]
            try:
                proc.terminate()
                proc.wait(timeout=2)
            except:
                proc.kill()
            del self.running_processes[tun_id]
            self.running_configs.pop(tun_id, None)
        if metadata.get("core_type") == "paqet":
            self.cleanup_paqet_iptables(metadata.get("role"), metadata.get("core_port"), metadata.get("ports"))
        self.running_metadata.pop(tun_id, None)

    def track_and_report_traffic(self):
        reports = []
        for tun_id, proc in list(self.running_processes.items()):
            if proc.poll() is None:
                metadata = self.running_metadata.get(tun_id, {})
                # Paqet passes packets through pcap/raw sockets, so /proc/PID/io
                # measures process file I/O rather than transferred traffic. Its
                # server port is dedicated to a tunnel, which gives us exact
                # wire-level byte counters in the raw iptables chains. Report from
                # the server only to avoid counting the same tunnel twice.
                if metadata.get("core_type") == "paqet":
                    if metadata.get("role") != "server":
                        continue
                    try:
                        core_port = int(metadata["core_port"])
                        received = self._iptables_bytes("PREROUTING", "dport", core_port)
                        sent = self._iptables_bytes("OUTPUT", "sport", core_port)
                        last_received, last_sent = getattr(self, "_last_paqet_traffic", {}).get(
                            tun_id, (received, sent)
                        )
                        if not hasattr(self, "_last_paqet_traffic"):
                            self._last_paqet_traffic = {}
                        self._last_paqet_traffic[tun_id] = (received, sent)
                        delta_in = max(0, received - last_received)
                        delta_out = max(0, sent - last_sent)
                        if delta_in or delta_out:
                            reports.append({"tunnel_id": tun_id, "bytes_in": delta_in, "bytes_out": delta_out})
                    except Exception:
                        pass
                    continue
                pid = proc.pid
                io_path = f"/proc/{pid}/io"
                try:
                    if os.path.exists(io_path):
                        with open(io_path, "r") as f:
                            lines = f.readlines()
                        r_bytes = 0
                        w_bytes = 0
                        for l in lines:
                            if l.startswith("read_bytes:"):
                                r_bytes = int(l.split(":")[1].strip())
                            elif l.startswith("write_bytes:"):
                                w_bytes = int(l.split(":")[1].strip())
                            elif l.startswith("rchar:") and r_bytes == 0:
                                r_bytes = int(l.split(":")[1].strip())
                            elif l.startswith("wchar:") and w_bytes == 0:
                                w_bytes = int(l.split(":")[1].strip())
                        
                        last_r, last_w = getattr(self, "_last_io", {}).get(tun_id, (r_bytes, w_bytes))
                        if not hasattr(self, "_last_io"):
                            self._last_io = {}
                        self._last_io[tun_id] = (r_bytes, w_bytes)

                        delta_in = max(0, r_bytes - last_r)
                        delta_out = max(0, w_bytes - last_w)
                        if delta_in > 0 or delta_out > 0:
                            reports.append({"tunnel_id": tun_id, "bytes_in": delta_in, "bytes_out": delta_out})
                except Exception:
                    pass

        if reports:
            try:
                url = f"{self.panel_url}/api/tunnels/traffic"
                req = urllib.request.Request(
                    url,
                    data=json.dumps({"reports": reports}).encode('utf-8'),
                    headers={"Content-Type": "application/json", "Authorization": f"Bearer {self.token}"},
                    method="POST"
                )
                with urllib.request.urlopen(req, timeout=4) as _:
                    pass
            except Exception:
                pass

    def _iptables_bytes(self, chain, port_kind, port):
        """Return the exact byte counter for one Paqet raw-table rule."""
        result = subprocess.run(
            ["iptables", "-t", "raw", "-nvxL", chain],
            capture_output=True, text=True, timeout=3, check=True
        )
        # iptables -L abbreviates these fields in its human-readable output
        # (dport -> dpt and sport -> spt).
        display_kind = {"dport": "dpt", "sport": "spt"}.get(port_kind, port_kind)
        needle = f"{display_kind}:{port}"
        for line in result.stdout.splitlines():
            if needle not in line or "NOTRACK" not in line:
                continue
            columns = line.split()
            if len(columns) >= 2 and columns[0].isdigit() and columns[1].isdigit():
                return int(columns[1])
        raise RuntimeError(f"Paqet raw counter not found: {chain} {needle}")

    def run(self):
        print(f"🚀 Hawal Agent started ({self.node_name} - {self.role}). Syncing with {self.panel_url}...")
        def request_shutdown(signum, _frame):
            print(f"[Agent] 🛑 Shutdown signal {signum} received.")
            self.shutdown_requested = True

        signal.signal(signal.SIGTERM, request_shutdown)
        signal.signal(signal.SIGINT, request_shutdown)
        try:
            while not self.shutdown_requested:
                self.send_heartbeat()
                self.sync_tunnels()
                self.report_logs()
                self.track_and_report_traffic()
                time.sleep(4)
        finally:
            for tun_id in list(self.running_processes.keys()):
                self.stop_tunnel_process(tun_id)

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
