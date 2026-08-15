import asyncio
import re
import socket
import time
from app.db import record_ping

async def run_ping(target_ip, count=4):
    """
    Executes ICMP ping to target_ip and extracts latency metrics and packet loss.
    """
    try:
        proc = await asyncio.create_subprocess_exec(
            "ping", "-c", str(count), "-W", "2", target_ip,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await proc.communicate()
        output = stdout.decode("utf-8", errors="ignore")

        # Parse packet loss: "0% packet loss"
        loss_match = re.search(r"(\d+(?:\.\d+)?)%\s+packet\s+loss", output)
        packet_loss = float(loss_match.group(1)) if loss_match else 100.0

        # Parse rtt: "rtt min/avg/max/mdev = 96.438/96.517/96.613/0.072 ms"
        rtt_match = re.search(r"rtt\s+min/avg/max/mdev\s*=\s*([\d\.]+)/([\d\.]+)/([\d\.]+)/([\d\.]+)", output)
        if rtt_match:
            min_ms = float(rtt_match.group(1))
            avg_ms = float(rtt_match.group(2))
            max_ms = float(rtt_match.group(3))
        else:
            min_ms = avg_ms = max_ms = 0.0

        return {
            "success": proc.returncode == 0 or packet_loss < 100,
            "target": target_ip,
            "min_ms": min_ms,
            "avg_ms": avg_ms,
            "max_ms": max_ms,
            "packet_loss": packet_loss,
            "raw": output
        }
    except Exception as e:
        return {
            "success": False,
            "target": target_ip,
            "min_ms": 0,
            "avg_ms": 0,
            "max_ms": 0,
            "packet_loss": 100.0,
            "error": str(e)
        }

async def run_tcp_ping(target_ip, port, timeout=2.0):
    """
    Executes a TCP SYN connect to target_ip:port and measures RTT in milliseconds.
    """
    start = time.perf_counter()
    try:
        reader, writer = await asyncio.wait_for(
            asyncio.open_connection(target_ip, port), timeout=timeout
        )
        latency_ms = (time.perf_counter() - start) * 1000.0
        writer.close()
        await writer.wait_closed()
        return {
            "success": True,
            "target": f"{target_ip}:{port}",
            "latency_ms": round(latency_ms, 2)
        }
    except Exception as e:
        return {
            "success": False,
            "target": f"{target_ip}:{port}",
            "error": str(e)
        }
