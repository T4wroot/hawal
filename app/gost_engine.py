"""Configuration helpers for the GOST v3 relay core.

GOST is deliberately kept as a normal socket-based tunnel core.  Unlike
Paqet it does not need raw socket/firewall manipulation, which makes it a
useful encrypted fallback transport.
"""

from urllib.parse import quote


_TRANSPORTS = {"tls", "ws", "kcp", "quic"}


def gost_transport(tunnel):
    """Return a supported GOST relay carrier, with a safe default."""
    transport = str(tunnel.get("transport", "tls")).lower()
    return transport if transport in _TRANSPORTS else "tls"


def relay_url(tunnel, host):
    """Build a GOST Relay URL for both client and server commands."""
    transport = gost_transport(tunnel)
    token = quote(str(tunnel.get("token", "")), safe="")
    core_port = int(tunnel.get("core_port", 8443))
    # Relay authentication requires a user and password.  The tunnel token is
    # the password; the fixed username only identifies Hawal-managed sessions.
    return f"relay+{transport}://hawal:{token}@{host}:{core_port}"


def generate_gost_server_command(tunnel):
    """The foreign node accepts authenticated Relay connections."""
    return ["-L", relay_url(tunnel, "")]


def generate_gost_client_command(tunnel, server_ip):
    """Expose each entry port for both TCP and UDP through GOST Relay.

    A single Hawal port mapping is protocol-agnostic.  Creating only a TCP
    listener breaks QUIC applications such as Hysteria2, even though Relay can
    carry UDP.  GOST keeps the two listeners independent, so an unused UDP
    listener has no effect on a TCP-only target.
    """
    args = []
    for rule in tunnel.get("ports", []):
        try:
            listen_port, target = str(rule).split("=", 1)
            listen_port = int(listen_port.strip().split(":")[-1])
            target = target.strip()
            if not target or not 1 <= listen_port <= 65535:
                continue
            args.extend([
                "-L", f"tcp://:{listen_port}/{target}",
                "-L", f"udp://:{listen_port}/{target}",
            ])
        except (TypeError, ValueError):
            continue
    args.extend(["-F", relay_url(tunnel, server_ip)])
    return args
