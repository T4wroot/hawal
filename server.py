#!/usr/bin/env python3
import asyncio
import sys
import argparse
from app.server import HTTPServer
from app.config import DEFAULT_PORT, DEFAULT_HOST

def main():
    parser = argparse.ArgumentParser(description="Hawal Tunnel Control Panel")
    parser.add_argument("--host", default=DEFAULT_HOST, help="Bind Host (default 0.0.0.0)")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT, help="Bind Port (default 9090)")
    args = parser.parse_args()

    server = HTTPServer(host=args.host, port=args.port)
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(server.start())
        loop.run_forever()
    except KeyboardInterrupt:
        print("\n🛑 Hawal Tunnel Panel stopped gracefully.")

if __name__ == "__main__":
    main()
