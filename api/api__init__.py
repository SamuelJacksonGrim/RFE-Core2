"""
api — REST and WebSocket interfaces for RFE-Core2.
"""

from api.inference_api import create_app
from api.websocket_server import RFEWebSocketServer

__all__ = [
    "create_app",
    "RFEWebSocketServer",
]
