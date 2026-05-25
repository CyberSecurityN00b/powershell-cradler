#! /usr/bin/env python3
import sys
import threading
import logging
import argparse
import time

logging.getLogger("wrkzeug").setLevel(logging.ERROR)

def _start_flask(app, host: str, port: int):
    app.run(host=host, port=port, use_reloader=False, threaded=True)

def main():
    from core.plugin_loader import discover_plugins
    from core.endpoint_registry import EndpointRegistry
    from core.terminal import PowerShellCradleTerminal
    from server.app import app as flask_app, init_app

    parser = argparse.ArgumentParser(description="PowerShell Payload Cradle Delivery Framework")
    parser.add_argument("-i", "--interface", "--host", type=str, default="0.0.0.0", help="IP of interface to host cradle server on.")
    parser.add_argument("-p", "--port", type=int, default=8888, help="Port to host cradle server on.")
    args = parser.parse_args()

    plugin_map        = discover_plugins()
    server_config     = {"host": args.interface, "port": args.port, "domain": f"{args.interface}:{args.port}"}
    endpoint_registry = EndpointRegistry(plugin_map,server_config)

    terminal = PowerShellCradleTerminal(endpoint_registry,plugin_map,server_config)

    init_app(endpoint_registry,terminal)
    flask_thread = threading.Thread(
        target=_start_flask,
        args=(flask_app, server_config["host"], server_config["port"]),
        daemon=True
    )
    flask_thread.start()

    try:
        terminal.run()
    except Exception as exc:
        print(f"\nFatal error: {exc}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()