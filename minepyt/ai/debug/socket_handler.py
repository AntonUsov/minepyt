"""
WebSocket менеджер для real-time стриминга данных.
"""

import time
import logging
from typing import Dict, Any, List, Optional
from flask_socketio import SocketIO

logger = logging.getLogger(__name__)


class WebSocketManager:
    """
    Управление WebSocket подключениями и стриминг данных.

    Отвечает за:
    - Отправку данных о слоях движения
    - Отправку данных сенсоров
    - Отправку позиции бота
    - Отправку событий
    """

    def __init__(self, socketio: Optional[SocketIO] = None):
        """
        Инициализация WebSocket менеджера.

        Args:
            socketio: Экземпляр Flask-SocketIO (опционально)
        """
        self.socketio = socketio
        self.connected_clients = 0
        self.last_broadcast_time = {}
        self.min_broadcast_interval = 0.05  # 50ms между обновлениями

    def set_socketio(self, socketio: SocketIO):
        """
        Установить экземпляр Flask-SocketIO.

        Args:
            socketio: Экземпляр Flask-SocketIO
        """
        self.socketio = socketio

    def _can_broadcast(self, channel: str) -> bool:
        """
        Проверить, можно ли отправить данные в канал (rate limiting).

        Args:
            channel: Имя канала

        Returns:
            True если можно отправить
        """
        now = time.time()
        last_time = self.last_broadcast_time.get(channel, 0)

        if now - last_time < self.min_broadcast_interval:
            return False

        self.last_broadcast_time[channel] = now
        return True

    def broadcast_layers(self, layer_state: Dict[Any, Any]):
        """
        Отправка состояния слоёв движения.

        Args:
            layer_state: Состояние слоёв с векторами
        """
        if not self.socketio:
            logger.warning("SocketIO not initialized")
            return

        if not self._can_broadcast("layers"):
            return

        try:
            self.socketio.emit(
                "layers_update",
                {
                    "type": "layers_update",
                    "data": {
                        "layer4_goal": layer_state.get("goal_vector"),
                        "layer3_tactical": layer_state.get("tactical_vectors", []),
                        "layer2_avoid": layer_state.get("avoid_vectors", []),
                        "layer1_physics": layer_state.get("physics_vector"),
                        "final_vector": layer_state.get("final_vector"),
                        "timestamp": time.time(),
                    },
                },
            )
        except Exception as e:
            logger.error(f"Error broadcasting layers: {e}")

    def broadcast_sensors(self, sensors_data: Dict[Any, Any]):
        """
        Отправка данных сенсоров.

        Args:
            sensors_data: Данные сенсоров (угрозы, интересы, местность)
        """
        if not self.socketio:
            logger.warning("SocketIO not initialized")
            return

        if not self._can_broadcast("sensors"):
            return

        try:
            self.socketio.emit(
                "sensors_update",
                {
                    "type": "sensors_update",
                    "data": {
                        "threats": sensors_data.get("threats", []),
                        "interests": sensors_data.get("interests", []),
                        "terrain": sensors_data.get("terrain", {}),
                        "players": sensors_data.get("players", []),
                        "timestamp": time.time(),
                    },
                },
            )
        except Exception as e:
            logger.error(f"Error broadcasting sensors: {e}")

    def broadcast_position(self, x: float, y: float, z: float, yaw: float, pitch: float):
        """
        Отправка позиции бота.

        Args:
            x, y, z: Координаты
            yaw: Угол поворота по горизонтали (градусы)
            pitch: Угол поворота по вертикали (градусы)
        """
        if not self.socketio:
            logger.warning("SocketIO not initialized")
            return

        if not self._can_broadcast("position"):
            return

        try:
            self.socketio.emit(
                "position_update",
                {
                    "type": "position_update",
                    "data": {
                        "x": x,
                        "y": y,
                        "z": z,
                        "yaw": yaw,
                        "pitch": pitch,
                        "timestamp": time.time(),
                    },
                },
            )
        except Exception as e:
            logger.error(f"Error broadcasting position: {e}")

    def broadcast_event(self, event_type: str, data: Dict[Any, Any]):
        """
        Отправка события.

        Args:
            event_type: Тип события (threat_detected, goal_changed, etc.)
            data: Данные события
        """
        if not self.socketio:
            logger.warning("SocketIO not initialized")
            return

        try:
            self.socketio.emit(
                "event",
                {"type": "event", "event_type": event_type, "data": data, "timestamp": time.time()},
            )
        except Exception as e:
            logger.error(f"Error broadcasting event: {e}")

    def broadcast_health(self, health: float, max_health: float, food: int, max_food: int):
        """
        Отправка состояния здоровья и голода.

        Args:
            health: Текущее здоровье
            max_health: Максимальное здоровье
            food: Текущий голод
            max_food: Максимальный голод
        """
        if not self.socketio:
            return

        if not self._can_broadcast("health"):
            return

        try:
            self.socketio.emit(
                "health_update",
                {
                    "type": "health_update",
                    "data": {
                        "health": health,
                        "max_health": max_health,
                        "food": food,
                        "max_food": max_food,
                        "timestamp": time.time(),
                    },
                },
            )
        except Exception as e:
            logger.error(f"Error broadcasting health: {e}")

    def broadcast_inventory(self, inventory_data: Dict[Any, Any]):
        """
        Отправка данных инвентаря.

        Args:
            inventory_data: Данные инвентаря
        """
        if not self.socketio:
            return

        if not self._can_broadcast("inventory"):
            return

        try:
            self.socketio.emit(
                "inventory_update",
                {"type": "inventory_update", "data": inventory_data, "timestamp": time.time()},
            )
        except Exception as e:
            logger.error(f"Error broadcasting inventory: {e}")

    def broadcast_performance(self, perf_data: Dict[Any, Any]):
        """
        Отправка данных производительности.

        Args:
            perf_data: Данные производительности (CPU, память, время тика)
        """
        if not self.socketio:
            return

        if not self._can_broadcast("performance"):
            return

        try:
            self.socketio.emit(
                "performance_update",
                {"type": "performance_update", "data": perf_data, "timestamp": time.time()},
            )
        except Exception as e:
            logger.error(f"Error broadcasting performance: {e}")

    def broadcast_log(self, log_level: str, message: str, metadata: Optional[Dict] = None):
        """
        Отправка лог-сообщения.

        Args:
            log_level: Уровень лога (info, warning, error, debug)
            message: Сообщение
            metadata: Дополнительные метаданные
        """
        if not self.socketio:
            return

        try:
            self.socketio.emit(
                "log",
                {
                    "type": "log",
                    "level": log_level,
                    "message": message,
                    "metadata": metadata or {},
                    "timestamp": time.time(),
                },
            )
        except Exception as e:
            logger.error(f"Error broadcasting log: {e}")

    def on_client_connect(self):
        """Обработка подключения клиента."""
        self.connected_clients += 1
        logger.info(f"Client connected. Total clients: {self.connected_clients}")

    def on_client_disconnect(self):
        """Обработка отключения клиента."""
        self.connected_clients -= 1
        logger.info(f"Client disconnected. Total clients: {self.connected_clients}")
