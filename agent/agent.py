import json
import os
import subprocess
import time
import urllib.request
import urllib.error

CONFIG_FILE = "/etc/hawal/agent.json"
BACKHAUL_BIN = "/usr/local/bin/backhaul"
RUN_DIR = "/opt/hawal/tunnels"
os.makedirs(RUN_DIR, exist_ok=True)

RUNNING_PROCESSES = {} # tunnel_id -> subprocess.Popen

def get_sys_metrics():
    # 1. CPU & Load
    try:
        load1, _, _ = os.getloadavg()
    except:
        load1 = 0.0

    # 2. RAM
    ram_total_mb = 0
    ram_used_mb = 0
    try:
        with open("/proc/meminfo", "r") as f:
            lines = f.readlines()
        mem = {}
        for l in lines:
            parts = l.split(":")
            if len(parts) == 2:
                mem[parts[0].strip()] = int(parts[1].split()[0])
        ram_total_mb = mem.get("MemTotal", 0) // 1024
        ram_free_mb = mem.get("MemAvailable", mem.get("MemFree", 0)) // 1024
        ram_used_mb = max(0, ram_total_mb - ram_free_mb)
    except:
        pass

    # 3. Uptime
    uptime_sec = 0
    try:
        with open("/proc/uptime", "r") as f:
            uptime_sec = int(float(f.readline().split()[0]))
    except:
        pass

    return {
        "cpu_percent": round(load1 * 10, 1),
        "ram_used_mb": ram_used_mb,
        "ram_total_mb": ram_total_mb,
        "uptime_seconds": uptime_sec
    }

def apply_tunnels(tunnels_data):
    """
    Syncs running Backhaul processes with the assigned configurations from Panel.
    """
    desired_ids = set()
    for item in tunnels_data:
        t_id = item["tunnel_id"]
        desired_ids.add(t_id)
        cfg_content = item["config"]
        cfg_file = os.path.join(RUN_DIR, f"{t_id}.toml")

        # Check if config changed
        existing_cfg = ""
        if os.path.exists(cfg_file):
            with open(cfg_file, "r") as f:
                existing_cfg = f.read()

        if existing_cfg != cfg_content:
            print(f"🔄 Updating configuration for tunnel {t_id}...")
            with open(cfg_file, "w") as f:
                f.write(cfg_content)
            
            # Restart process if already running
            if t_id in RUNNING_PROCESSES:
                try:
                    RUNNING_PROCESSES[t_id].terminate()
                    RUNNING_PROCESSES[t_id].wait(timeout=2)
                except:
                    RUNNING_PROCESSES[t_id].kill()
                del RUNNING_PROCESSES[t_id]

        # Ensure process is running
        if t_id not in RUNNING_PROCESSES or RUNNING_PROCESSES[t_id].poll() is not None:
            print(f"🚀 Starting Backhaul for tunnel {t_id}...")
            proc = subprocess.Popen([BACKHAUL_BIN, "-c", cfg_file], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            RUNNING_PROCESSES[t_id] = proc

    # Kill removed tunnels
    for t_id in list(RUNNING_PROCESSES.keys()):
        if t_id not in desired_ids:
            print(f"🛑 Stopping removed tunnel {t_id}...")
            try:
                RUNNING_PROCESSES[t_id].terminate()
                RUNNING_PROCESSES[t_id].wait(timeout=2)
            except:
                RUNNING_PROCESSES[t_id].kill()
            del RUNNING_PROCESSES[t_id]
            cfg_file = os.path.join(RUN_DIR, f"{t_id}.toml")
            if os.path.exists(cfg_file):
                os.remove(cfg_file)

def main():
    if not os.path.exists(CONFIG_FILE):
        print(f"❌ Config file {CONFIG_FILE} not found!")
        return

    with open(CONFIG_FILE, "r") as f:
        agent_cfg = json.load(f)

    panel_url = agent_cfg.get("panel_url", "http://127.0.0.1:9090")
    token = agent_cfg.get("token", "")
    endpoint = f"{panel_url}/api/agent/heartbeat"

    print(f"⚡ Nexus Node Agent running. Syncing with {panel_url}...")

    while True:
        try:
            metrics = get_sys_metrics()
            req = urllib.request.Request(
                endpoint,
                data=json.dumps(metrics).encode('utf-8'),
                headers={
                    "Content-Type": "application/json",
                    "X-Node-Token": token
                },
                method="POST"
            )
            with urllib.request.urlopen(req, timeout=5) as resp:
                data = json.loads(resp.read().decode('utf-8'))
                if "tunnels" in data:
                    apply_tunnels(data["tunnels"])
        except Exception as e:
            # print(f"Heartbeat notice: {e}")
            pass

        time.sleep(3)

if __name__ == "__main__":
    main()
