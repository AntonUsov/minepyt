"""
Visual Debugging System - Flask Web Interface

Система визуальной отладки для AI бота в реальном времени.
Предоставляет:
- Веб-интерфейс для мониторинг бота
- WebSocket стриминг данных в реальном времени
- REST API для запросов состояния
- Визуализация слоёв движения, сенсоров, карты
"""

from .app import DebugServer
from .socket_handler import WebSocketManager
from .api import APIRouter, setup_api_routes
from .state_collector import StateCollector

__all__ = [
    "DebugServer",
 "WebSocketManager",
 "APIRouter",
 "setup_api_routes",
 "StateCollector",
]
