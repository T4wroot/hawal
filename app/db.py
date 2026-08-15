import sqlite3
import json
import time
from app.config import DB_PATH

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_db() as conn:
        cursor = conn.cursor()
        
        # Nodes table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS nodes (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            ip TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'kharej', -- 'iran' or 'kharej'
            country_code TEXT DEFAULT 'GLOBAL',
            country_name TEXT DEFAULT 'خارج',
            flag TEXT DEFAULT '🌐',
            city TEXT DEFAULT '',
            token TEXT NOT NULL UNIQUE,
            status TEXT NOT NULL DEFAULT 'offline',
            last_seen REAL DEFAULT 0,
            cpu_percent REAL DEFAULT 0,
            ram_used_mb INTEGER DEFAULT 0,
            ram_total_mb INTEGER DEFAULT 0,
            uptime_seconds INTEGER DEFAULT 0,
            created_at REAL NOT NULL
        )
        """)
        
        # Tunnels table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS tunnels (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            server_node_id TEXT NOT NULL,
            client_node_id TEXT NOT NULL,
            core_port INTEGER NOT NULL,
            transport TEXT NOT NULL DEFAULT 'ws', -- 'tcp', 'ws', 'tcpmux', 'tls'
            ports_json TEXT NOT NULL DEFAULT '[]', -- JSON array of "443=127.0.0.1:443"
            token TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'stopped', -- 'running', 'stopped', 'error'
            nodelay INTEGER DEFAULT 1,
            snappy INTEGER DEFAULT 1,
            mux_con INTEGER DEFAULT 8,
            keepalive INTEGER DEFAULT 75,
            channel_size INTEGER DEFAULT 2048,
            created_at REAL NOT NULL,
            FOREIGN KEY (server_node_id) REFERENCES nodes (id) ON DELETE CASCADE,
            FOREIGN KEY (client_node_id) REFERENCES nodes (id) ON DELETE CASCADE
        )
        """)
        
        # Ping latency history
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS ping_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source_node_id TEXT NOT NULL,
            target_node_id TEXT NOT NULL,
            latency_avg_ms REAL NOT NULL,
            latency_min_ms REAL NOT NULL,
            latency_max_ms REAL NOT NULL,
            packet_loss REAL NOT NULL,
            created_at REAL NOT NULL
        )
        """)
        
        conn.commit()

# --- Node Operations ---
def list_nodes():
    with get_db() as conn:
        rows = conn.execute("SELECT * FROM nodes ORDER BY created_at ASC").fetchall()
        nodes = []
        now = time.time()
        for r in rows:
            d = dict(r)
            # consider offline if last_seen > 15s ago
            if now - d.get("last_seen", 0) > 15:
                d["status"] = "offline"
            nodes.append(d)
        return nodes

def get_node(node_id):
    with get_db() as conn:
        row = conn.execute("SELECT * FROM nodes WHERE id = ?", (node_id,)).fetchone()
        return dict(row) if row else None

def get_node_by_token(token):
    with get_db() as conn:
        row = conn.execute("SELECT * FROM nodes WHERE token = ?", (token,)).fetchone()
        return dict(row) if row else None

def save_node(node_id, name, ip, role, token, country_code="GLOBAL", country_name="خارج", flag="🌐", city=""):
    now = time.time()
    with get_db() as conn:
        conn.execute("""
        INSERT INTO nodes (id, name, ip, role, country_code, country_name, flag, city, token, status, last_seen, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'online', ?, ?)
        ON CONFLICT(id) DO UPDATE SET
            name=excluded.name,
            ip=excluded.ip,
            role=excluded.role,
            country_code=excluded.country_code,
            country_name=excluded.country_name,
            flag=excluded.flag,
            city=excluded.city,
            last_seen=excluded.last_seen,
            status='online'
        """, (node_id, name, ip, role, country_code, country_name, flag, city, token, now, now))
        conn.commit()

def update_node_heartbeat(node_id, ip, cpu, ram_used, ram_total, uptime, country_code=None, country_name=None, flag=None, city=None):
    now = time.time()
    with get_db() as conn:
        if country_code and country_name:
            conn.execute("""
            UPDATE nodes SET
                ip = ?,
                cpu_percent = ?,
                ram_used_mb = ?,
                ram_total_mb = ?,
                uptime_seconds = ?,
                country_code = ?,
                country_name = ?,
                flag = ?,
                city = ?,
                last_seen = ?,
                status = 'online'
            WHERE id = ?
            """, (ip, cpu, ram_used, ram_total, uptime, country_code, country_name, flag, city, now, node_id))
        else:
            conn.execute("""
            UPDATE nodes SET
                ip = ?,
                cpu_percent = ?,
                ram_used_mb = ?,
                ram_total_mb = ?,
                uptime_seconds = ?,
                last_seen = ?,
                status = 'online'
            WHERE id = ?
            """, (ip, cpu, ram_used, ram_total, uptime, now, node_id))
        conn.commit()

def delete_node(node_id):
    with get_db() as conn:
        conn.execute("DELETE FROM nodes WHERE id = ?", (node_id,))
        conn.commit()

# --- Tunnel Operations ---
def list_tunnels():
    with get_db() as conn:
        rows = conn.execute("""
        SELECT t.*, 
               sn.name as server_node_name, sn.ip as server_node_ip, sn.role as server_node_role,
               cn.name as client_node_name, cn.ip as client_node_ip, cn.role as client_node_role
        FROM tunnels t
        LEFT JOIN nodes sn ON t.server_node_id = sn.id
        LEFT JOIN nodes cn ON t.client_node_id = cn.id
        ORDER BY t.created_at ASC
        """).fetchall()
        tunnels = []
        for r in rows:
            d = dict(r)
            try:
                d["ports"] = json.loads(d["ports_json"])
            except:
                d["ports"] = []
            tunnels.append(d)
        return tunnels

def get_tunnel(tunnel_id):
    with get_db() as conn:
        row = conn.execute("SELECT * FROM tunnels WHERE id = ?", (tunnel_id,)).fetchone()
        if not row:
            return None
        d = dict(row)
        try:
            d["ports"] = json.loads(d["ports_json"])
        except:
            d["ports"] = []
        return d

def save_tunnel(tunnel_id, name, server_node_id, client_node_id, core_port, transport, ports, token, nodelay=1, snappy=1, mux_con=8, channel_size=2048):
    now = time.time()
    ports_json = json.dumps(ports)
    with get_db() as conn:
        conn.execute("""
        INSERT INTO tunnels (id, name, server_node_id, client_node_id, core_port, transport, ports_json, token, status, nodelay, snappy, mux_con, channel_size, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'stopped', ?, ?, ?, ?, ?)
        ON CONFLICT(id) DO UPDATE SET
            name=excluded.name,
            server_node_id=excluded.server_node_id,
            client_node_id=excluded.client_node_id,
            core_port=excluded.core_port,
            transport=excluded.transport,
            ports_json=excluded.ports_json,
            token=excluded.token,
            nodelay=excluded.nodelay,
            snappy=excluded.snappy,
            mux_con=excluded.mux_con,
            channel_size=excluded.channel_size
        """, (tunnel_id, name, server_node_id, client_node_id, core_port, transport, ports_json, token, nodelay, snappy, mux_con, channel_size, now))
        conn.commit()

def set_tunnel_status(tunnel_id, status):
    with get_db() as conn:
        conn.execute("UPDATE tunnels SET status = ? WHERE id = ?", (status, tunnel_id))
        conn.commit()

def delete_tunnel(tunnel_id):
    with get_db() as conn:
        conn.execute("DELETE FROM tunnels WHERE id = ?", (tunnel_id,))
        conn.commit()

# --- Ping History ---
def record_ping(source_id, target_id, avg_ms, min_ms, max_ms, loss_pct):
    now = time.time()
    with get_db() as conn:
        conn.execute("""
        INSERT INTO ping_history (source_node_id, target_node_id, latency_avg_ms, latency_min_ms, latency_max_ms, packet_loss, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (source_id, target_id, avg_ms, min_ms, max_ms, loss_pct, now))
        conn.commit()

def get_latest_pings():
    with get_db() as conn:
        rows = conn.execute("""
        SELECT ph.*, 
               sn.name as source_name, sn.role as source_role,
               tn.name as target_name, tn.role as target_role
        FROM ping_history ph
        JOIN nodes sn ON ph.source_node_id = sn.id
        JOIN nodes tn ON ph.target_node_id = tn.id
        ORDER BY ph.created_at DESC LIMIT 20
        """).fetchall()
        return [dict(r) for r in rows]
