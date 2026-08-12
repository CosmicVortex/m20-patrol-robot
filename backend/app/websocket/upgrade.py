"""WebSocket upgrade handler for M20 Pro patrol robot.

Provides WebSocket endpoint integration with the HTTP server.
"""

from __future__ import annotations

import asyncio
import base64
import hashlib
import json
import logging
import socket
from http.cookies import SimpleCookie
from typing import Any, Optional

logger = logging.getLogger(__name__)

_WEBSOCKET_GUID = "258EAFA5-E914-47DA-95CA-5AB5DC99A3BE"


class WebSocketUpgradeHandler:
    """Handles WebSocket upgrade requests in the main HTTP server."""
    
    def __init__(self, video_handler: Any = None, nav_handler: Any = None, auth_middleware: Any = None) -> None:
        self._video_handler = video_handler
        self._nav_handler = nav_handler
        self._auth_middleware = auth_middleware
        self._connections: list[tuple[str, Any]] = []
    
    def set_handlers(self, video: Any = None, nav: Any = None) -> None:
        """Set WebSocket handlers."""
        if video:
            self._video_handler = video
        if nav:
            self._nav_handler = nav
    
    def handle_request(self, conn: socket.socket) -> None:
        """Handle a WebSocket upgrade request."""
        try:
            conn.settimeout(10.0)
            request = b""
            while b"\r\n\r\n" not in request:
                chunk = conn.recv(4096)
                if not chunk:
                    return
                request += chunk
            
            request_text = request.decode("utf-8", errors="replace")
            lines = request_text.split("\r\n")
            
            if not lines or "GET /ws/" not in lines[0]:
                return
            
            headers: dict[str, str] = {}
            for line in lines[1:]:
                if line == "":
                    break
                if ":" in line:
                    key, value = line.split(":", 1)
                    headers[key.strip().lower()] = value.strip()
            
            if headers.get("upgrade", "").lower() != "websocket":
                return
            if "upgrade" not in {item.strip().lower() for item in headers.get("connection", "").split(",")}:
                return
            
            key = headers.get("sec-websocket-key", "")
            if not key:
                return
            
            accept_key = base64.b64encode(
                hashlib.sha1((key + _WEBSOCKET_GUID).encode()).digest()
            ).decode()
            
            ws_path = lines[0].split(" ")[1]
            if self._auth_middleware is not None:
                token = headers.get("x-m20-token", "")
                bearer = headers.get("authorization", "")
                if not token and bearer.lower().startswith("bearer "):
                    token = bearer[7:].strip()
                if not token:
                    cookie = SimpleCookie()
                    cookie.load(headers.get("cookie", ""))
                    morsel = cookie.get("m20_session")
                    token = morsel.value if morsel is not None else ""
                session = self._auth_middleware.store.resolve_session(token) if token else None
                if session is None:
                    conn.sendall(b"HTTP/1.1 401 Unauthorized\r\nConnection: close\r\nContent-Length: 0\r\n\r\n")
                    conn.close()
                    return
            response = (
                b"HTTP/1.1 101 Switching Protocols\r\n"
                b"Upgrade: websocket\r\n"
                b"Connection: Upgrade\r\n"
                b"Sec-WebSocket-Accept: " + accept_key.encode() + b"\r\n"
                b"\r\n"
            )
            conn.sendall(response)
            
            handler = self._get_handler(ws_path)
            
            if handler:
                logger.info("WebSocket connection established: %s", ws_path)
                conn.settimeout(60.0)
                self._handle_client(conn, ws_path, handler)
            else:
                logger.warning("No handler for WebSocket path: %s", ws_path)
                conn.close()
                
        except Exception as e:
            logger.error("WebSocket handshake failed: %s", e)
            try:
                conn.close()
            except Exception:
                pass
    
    def _get_handler(self, path: str) -> Any:
        """Get the appropriate handler for the WebSocket path."""
        if path.startswith("/ws/video"):
            return self._video_handler
        elif path.startswith("/ws/navigation"):
            return self._nav_handler
        return None
    
    def _handle_client(self, conn: socket.socket, path: str, handler: Any) -> None:
        """Handle a WebSocket client connection."""
        try:
            while True:
                frame = self._read_frame(conn)
                if frame is None:
                    break
                
                if frame == b"":
                    break
                
                try:
                    message = frame.decode("utf-8")
                    data = json.loads(message)
                except (json.JSONDecodeError, UnicodeDecodeError):
                    self._send_text(conn, json.dumps({
                        "type": "error",
                        "message": "Invalid JSON"
                    }))
                    continue
                
                result = handler.handle_message(message)
                
                if asyncio.iscoroutine(result):
                    loop = asyncio.new_event_loop()
                    try:
                        result = loop.run_until_complete(result)
                    finally:
                        loop.close()
                
                if result:
                    self._send_text(conn, json.dumps(result))
                    
        except Exception as e:
            logger.warning("WebSocket client disconnected: %s", e)
        finally:
            try:
                conn.close()
            except Exception:
                pass
    
    def _read_frame(self, conn: socket.socket) -> Optional[bytes]:
        """Read a WebSocket frame."""
        try:
            header = conn.recv(2)
            if len(header) < 2:
                return None
            
            opcode = header[0] & 0x0F
            masked = header[1] & 0x80
            length = header[1] & 0x7F
            
            if length == 126:
                length_bytes = conn.recv(2)
                if len(length_bytes) < 2:
                    return None
                length = int.from_bytes(length_bytes, 'big')
            elif length == 127:
                length_bytes = conn.recv(8)
                if len(length_bytes) < 8:
                    return None
                length = int.from_bytes(length_bytes, 'big')
            
            if length > 1024 * 1024:
                logger.warning("WebSocket frame exceeds 1 MiB limit")
                return None
            if opcode >= 0x8 and (header[0] & 0x80) == 0 or opcode >= 0x8 and length > 125:
                logger.warning("WebSocket control frame is invalid")
                return None
            if not masked:
                logger.warning("WebSocket client frame is not masked")
                return None

            mask_key = None
            if masked:
                mask_key = conn.recv(4)
                if len(mask_key) < 4:
                    return None
            
            if length > 0:
                payload = b""
                while len(payload) < length:
                    chunk = conn.recv(min(4096, length - len(payload)))
                    if not chunk:
                        break
                    payload += chunk
            else:
                payload = b""
            
            if mask_key and payload:
                payload = bytes([b ^ mask_key[i % 4] for i, b in enumerate(payload)])
            
            if opcode == 0x8:
                return b""
            elif opcode == 0x9:
                pong_header = bytes([0x8A, len(payload)])
                conn.sendall(pong_header + payload)
                return None
            elif opcode == 0xA:
                return None
            
            if opcode == 0x1:
                return payload
            
            return None
            
        except Exception as e:
            logger.debug("WebSocket frame read error: %s", e)
            return None
    
    def _send_text(self, conn: socket.socket, data: str) -> None:
        """Send a text frame."""
        try:
            body = data.encode("utf-8")
            length = len(body)
            
            if length < 126:
                header = bytes([0x81, length])
            elif length < 65536:
                header = bytes([0x81, 0x7E, (length >> 8) & 0xFF, length & 0xFF])
            else:
                header = bytes([0x81, 0x7F]) + length.to_bytes(8, 'big')
            
            conn.sendall(header + body)
        except Exception as e:
            logger.warning("WebSocket send error: %s", e)


def create_upgrade_handler(video_handler: Any = None, nav_handler: Any = None) -> WebSocketUpgradeHandler:
    """Create and return a WebSocket upgrade handler."""
    return WebSocketUpgradeHandler(video_handler, nav_handler)
