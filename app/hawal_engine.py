import json

def generate_hawal_core_server_config(tunnel_dict):
    """
    Generates JSON configuration dictionary for Hawal Core (Server Mode)
    """
    return {
        "mode": "server",
        "bind_addr": f"0.0.0.0:{tunnel_dict['core_port']}",
        "ports": tunnel_dict.get("ports", []),
        "token": tunnel_dict.get("token", ""),
        "enable_padding": bool(tunnel_dict.get("snappy", 1)),
        "nodelay": bool(tunnel_dict.get("nodelay", 1))
    }

def generate_hawal_core_client_config(tunnel_dict, server_ip):
    """
    Generates JSON configuration dictionary for Hawal Core (Client Mode)
    """
    return {
        "mode": "client",
        "connect_addr": f"{server_ip}:{tunnel_dict['core_port']}",
        "ports": tunnel_dict.get("ports", []),
        "token": tunnel_dict.get("token", ""),
        "enable_padding": bool(tunnel_dict.get("snappy", 1)),
        "nodelay": bool(tunnel_dict.get("nodelay", 1))
    }
