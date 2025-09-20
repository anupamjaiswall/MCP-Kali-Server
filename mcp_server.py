#!/usr/bin/env python3

import sys
import os
import argparse
import logging
from typing import Dict, Any, Optional
import requests

from mcp.server.fastmcp import FastMCP

# Configure logging to stderr (so stdout stays clean for JSON-RPC)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(sys.stderr)
    ]
)
logger = logging.getLogger(__name__)

DEFAULT_KALI_SERVER = "http://192.168.31.72:5000"
DEFAULT_REQUEST_TIMEOUT = 300

class KaliToolsClient:
    def __init__(self, server_url: str, timeout: int = DEFAULT_REQUEST_TIMEOUT):
        self.server_url = server_url.rstrip("/")
        self.timeout = timeout
        logger.info(f"Initialized Kali Tools Client connecting to {server_url}")

    def safe_get(self, endpoint: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        url = f"{self.server_url}/{endpoint}"
        try:
            response = requests.get(url, params=params or {}, timeout=self.timeout)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            return {"error": str(e), "success": False}

    def safe_post(self, endpoint: str, json_data: Dict[str, Any]) -> Dict[str, Any]:
        url = f"{self.server_url}/{endpoint}"
        try:
            response = requests.post(url, json=json_data, timeout=self.timeout)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            return {"error": str(e), "success": False}

    def execute_command(self, command: str) -> Dict[str, Any]:
        return self.safe_post("api/command", {"command": command})

    def check_health(self) -> Dict[str, Any]:
        return self.safe_get("health")

def setup_mcp_server(kali_client: KaliToolsClient) -> FastMCP:
    mcp = FastMCP("kali-mcp")

    @mcp.tool()
    def nmap_scan(target: str, scan_type: str = "-sV", ports: str = "", additional_args: str = "") -> Dict[str, Any]:
        return kali_client.safe_post("api/tools/nmap", {
            "target": target,
            "scan_type": scan_type,
            "ports": ports,
            "additional_args": additional_args
        })

    @mcp.tool()
    def execute_command(command: str) -> Dict[str, Any]:
        return kali_client.execute_command(command)

    @mcp.tool()
    def server_health() -> Dict[str, Any]:
        return kali_client.check_health()

    # Add more tools here (gobuster, dirb, etc.)
    return mcp

def parse_args():
    parser = argparse.ArgumentParser(description="Run the Kali MCP Client")
    parser.add_argument("--server", type=str, default=DEFAULT_KALI_SERVER,
                      help=f"Kali API server URL (default: {DEFAULT_KALI_SERVER})")
    parser.add_argument("--timeout", type=int, default=DEFAULT_REQUEST_TIMEOUT,
                      help=f"Request timeout in seconds (default: {DEFAULT_REQUEST_TIMEOUT})")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    return parser.parse_args()

def main():
    args = parse_args()
    if args.debug:
        logger.setLevel(logging.DEBUG)

    kali_client = KaliToolsClient(args.server, args.timeout)

    health = kali_client.check_health()
    if "error" in health:
        logger.warning(f"Cannot reach Kali API server at {args.server}: {health['error']}")

    mcp = setup_mcp_server(kali_client)
    mcp.run()

if __name__ == "__main__":
    main()
