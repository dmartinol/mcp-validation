"""JSON-RPC transport layer for MCP communication."""

import json
import asyncio
from typing import Dict, Any, Optional


class JSONRPCTransport:
    """Handles JSON-RPC communication with MCP servers."""
    
    def __init__(self, process: asyncio.subprocess.Process):
        self.process = process
        self.request_id = 0
    
    def _get_next_id(self) -> int:
        """Get next request ID for JSON-RPC."""
        self.request_id += 1
        return self.request_id
    
    def create_request(self, method: str, params: Optional[Dict[str, Any]] = None) -> str:
        """Create a JSON-RPC 2.0 request."""
        request = {
            "jsonrpc": "2.0",
            "id": self._get_next_id(),
            "method": method
        }
        if params:
            request["params"] = params
        return json.dumps(request) + "\n"
    
    def create_notification(self, method: str, params: Optional[Dict[str, Any]] = None) -> str:
        """Create a JSON-RPC 2.0 notification (no response expected)."""
        notification = {
            "jsonrpc": "2.0",
            "method": method
        }
        if params:
            notification["params"] = params
        return json.dumps(notification) + "\n"
    
    def parse_response(self, response_line: str) -> Dict[str, Any]:
        """Parse a JSON-RPC response line."""
        try:
            return json.loads(response_line.strip())
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON response: {e}")
    
    async def send_request(self, method: str, params: Optional[Dict[str, Any]] = None) -> None:
        """Send a JSON-RPC request."""
        request = self.create_request(method, params)
        self.process.stdin.write(request.encode())
        await self.process.stdin.drain()
    
    async def send_notification(self, method: str, params: Optional[Dict[str, Any]] = None) -> None:
        """Send a JSON-RPC notification."""
        notification = self.create_notification(method, params)
        self.process.stdin.write(notification.encode())
        await self.process.stdin.drain()
    
    async def read_response(self, timeout: float = 5.0) -> Dict[str, Any]:
        """Read and parse a JSON-RPC response."""
        response_line = await asyncio.wait_for(
            self.process.stdout.readline(),
            timeout=timeout
        )
        return self.parse_response(response_line.decode())
    
    async def send_and_receive(
        self, 
        method: str, 
        params: Optional[Dict[str, Any]] = None,
        timeout: float = 5.0
    ) -> Dict[str, Any]:
        """Send request and wait for response."""
        await self.send_request(method, params)
        return await self.read_response(timeout)