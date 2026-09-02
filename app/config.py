import os
import json
import secrets

DATA_DIR = os.path.expanduser("~/.hawal")
os.makedirs(DATA_DIR, exist_ok=True)

DB_PATH = os.path.join(DATA_DIR, "hawal.db")
CONFIG_PATH = os.path.join(DATA_DIR, "config.json")
LOG_PATH = os.path.join(DATA_DIR, "hawal.log")

DEFAULT_PORT = 9090
DEFAULT_HOST = "0.0.0.0"

# Default dynamic settings that can be customized in the Panel UI
DEFAULT_SETTINGS = {
    "app_name": "Hawal Tunnel (هه‌واڵ)",
    "panel_port": 9090,
    "panel_host": "0.0.0.0",
    "public_panel_url": "",
    "default_transport": "ws",
    "default_mux_con": 8,
    "default_keepalive": 75,
    "default_channel_size": 2048,
    "enable_bbr_auto": True,
    "enable_snappy": True,
    "mtu_clamp": 1360,
    "docker_image": "hawal/node:latest",
    "sync_interval_sec": 3,
    "master_token": ""
}

def load_settings():
    if not os.path.exists(CONFIG_PATH):
        settings = dict(DEFAULT_SETTINGS)
        settings["master_token"] = secrets.token_hex(16)
        save_settings(settings)
        return settings
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
            merged = dict(DEFAULT_SETTINGS)
            merged.update(data)
            return merged
    except:
        return dict(DEFAULT_SETTINGS)

def save_settings(new_settings):
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(new_settings, f, indent=2, ensure_ascii=False)

SETTINGS = load_settings()
MASTER_TOKEN = SETTINGS.get("master_token", secrets.token_hex(16))
