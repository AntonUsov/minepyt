"""
State Collector для сбора состояния бота и отправки в debug сервер.
"""

import time
import asyncio
import logging
from typing import Dict, Any, List, Optional
from collections import deque
import threading

logger = logging.getLogger(__name__)


class StateCollector:
    """
    Сбор состояния бота для визуализации.

    Отвечает за:
    - Сбор данных о слоях движения
    - Сбор данных сенсоров
    - Сбор позиции и здоровья
    - Логирование событий
    - Управление буфером логов
    """

    def __init__(self, bot, max_log_size: int = 1000):
        """
        Инициализация сборщика состояния.

        Args:
            bot: Экземпляр SmartBot
            max_log_size: Максимальный размер буфера логов
        """
        self.bot = bot
        self.max_log_size = max_log_size

        # WebSocket менеджер (устанавливается позже)
        self.ws_manager = None

        # Буферы данных
        self.log_buffer: deque = deque(maxlen=max_log_size)
        self.position_history: deque = deque(maxlen=100)
        self.performance_history: deque = deque(maxlen=60)

        # Кэш состояния
        self._layers_cache: Dict[Any, Any] = {}
        self._sensors_cache: Dict[Any, Any] = {}
        self._last_update_time = 0

        # Потокобезопасность
        self._lock = threading.Lock()

        # Перформанс метрики
        self._tick_times: deque = deque(maxlen=100)
        self._last_tick_time = time.time()

    def set_websocket_manager(self, ws_manager):
        """
        Установить WebSocket менеджер.

        Args:
            ws_manager: WebSocketManager экземпляр
        """
        self.ws_manager = ws_manager

    def get_full_state(self) -> Dict[Any, Any]:
        """
        Получить полное состояние бота.

        Returns:
            Словарь с полным состоянием
        """
        with self._lock:
            return {
                "position": self.get_position_data(),
                "health": self.get_health_state(),
                "layers": self.get_layers_state(),
                "sensors": self.get_sensors_data(),
                "task": self.get_current_task(),
                "inventory": self.get_inventory_data(),
                "performance": self.get_performance_stats(),
                "timestamp": time.time(),
            }

    def get_position_data(self) -> Dict[str, Any]:
        """
        Получить данные о позиции бота.

        Returns:
            Словарь с координатами и углами
        """
        try:
            if hasattr(self.bot, "position") and self.bot.position:
                x, y, z = self.bot.position
                yaw = getattr(self.bot, "yaw", 0.0)
                pitch = getattr(self.bot, "pitch", 0.0)

                return {
                    "x": float(x),
                    "y": float(y),
                    "z": float(z),
                    "yaw": float(yaw),
                    "pitch": float(pitch),
                    "dimension": getattr(self.bot, "dimension", "overworld"),
                }
        except Exception as e:
            logger.error(f"Error getting position: {e}")

        return {"x": 0.0, "y": 0.0, "z": 0.0, "yaw": 0.0, "pitch": 0.0, "dimension": "unknown"}

    def get_health_state(self) -> Dict[str, Any]:
        """
        Получить состояние здоровья и голода.

        Returns:
            Словарь с данными здоровья
        """
        try:
            health = getattr(self.bot, "health", 20.0)
            max_health = 20.0
            food = getattr(self.bot, "food", 20)
            max_food = 20

            return {
                "health": float(health),
                "max_health": float(max_health),
                "health_percent": (health / max_health) * 100 if max_health > 0 else 0,
                "food": int(food),
                "max_food": int(max_food),
                "food_percent": (food / max_food) * 100 if max_food > 0 else 0,
                "is_alive": health > 0,
            }
        except Exception as e:
            logger.error(f"Error getting health: {e}")
            return {
                "health": 20.0,
                "max_health": 20.0,
                "health_percent": 100.0,
                "food": 20,
                "max_food": 20,
                "food_percent": 100.0,
                "is_alive": True,
            }

    def get_layers_state(self) -> Dict[Any, Any]:
        """
        Получить состояние слоёв движения.

        Returns:
            Словарь с состоянием слоёв
        """
        with self._lock:
            # Возвращаем кэшированные данные или пустое состояние
            return (
                self._layers_cache.copy()
                if self._layers_cache
                else {
                    "layer4_goal": None,
                    "layer3_tactical": [],
                    "layer2_avoid": [],
                    "layer1_physics": None,
                    "final_vector": None,
                    "goal_type": "idle",
                    "goal_target": None,
                }
            )

    def get_sensors_data(self, detailed: bool = False) -> Dict[Any, Any]:
        """
        Получить данные сенсоров.

        Args:
            detailed: Вернуть детальные данные

        Returns:
            Словарь с данными сенсоров
        """
        with self._lock:
            data = (
                self._sensors_cache.copy()
                if self._sensors_cache
                else {"threats": [], "interests": [], "terrain": {}, "players": []}
            )

            if not detailed:
                # Сокращенные данные для WebSocket
                data["threats"] = [
                    {"type": t.get("type"), "distance": t.get("distance")}
                    for t in data.get("threats", [])[:5]  # Только первые 5
                ]

            return data

    def get_current_task(self) -> Dict[str, Any]:
        """
        Получить информацию о текущей задаче.

        Returns:
            Словарь с информацией о задаче
        """
        try:
            # Пытаемся получить текущую задачу из бота
            if hasattr(self.bot, "current_task"):
                task = self.bot.current_task
                if task:
                    return {
                        "name": getattr(task, "name", "Unknown"),
                        "status": getattr(task, "status", "running"),
                        "progress": getattr(task, "progress", 0.0),
                        "started_at": getattr(task, "started_at", None),
                    }
        except Exception as e:
            logger.error(f"Error getting task: {e}")

        return {"name": "idle", "status": "idle", "progress": 0.0, "started_at": None}

    def get_inventory_data(self, slots: str = "all") -> Dict[Any, Any]:
        """
        Получить данные инвентаря.

        Args:
            slots: Какие слоты показать (all, hotbar, armor)

        Returns:
            Словарь с данными инвентаря
        """
        try:
            inventory = {
                "slots": [],
                "hotbar": [],
                "armor": {},
                "held_item": None,
                "total_items": 0,
            }

            # Получаем инвентарь из бота
            if hasattr(self.bot, "inventory"):
                bot_inventory = self.bot.inventory

                # Считаем общее количество предметов
                total = 0
                for slot_id, item in bot_inventory.items():
                    if item:
                        total += item.get("count", 1)

                inventory["total_items"] = total

            # Получаем текущий предмет в руке
            if hasattr(self.bot, "held_item"):
                held = self.bot.held_item
                if held:
                    inventory["held_item"] = {
                        "name": getattr(held, "name", "Unknown"),
                        "count": getattr(held, "count", 1),
                    }

            return inventory

        except Exception as e:
            logger.error(f"Error getting inventory: {e}")
            return {"slots": [], "hotbar": [], "armor": {}, "held_item": None, "total_items": 0}

    def get_logs(self, limit: int = 100, level: Optional[str] = None) -> List[Dict[Any, Any]]:
        """
        Получить логи событий.

        Args:
            limit: Максимальное количество логов
            level: Фильтр по уровню (опционально)

        Returns:
            Список логов
        """
        with self._lock:
            logs = list(self.log_buffer)

            if level:
                logs = [log for log in logs if log.get("level") == level]

            return logs[-limit:]

    def get_performance_stats(self) -> Dict[str, Any]:
        """
        Получить статистику производительности.

        Returns:
            Словарь со статистикой
        """
        with self._lock:
            if not self._tick_times:
                return {
                    "avg_tick_time_ms": 0.0,
                    "max_tick_time_ms": 0.0,
                    "min_tick_time_ms": 0.0,
                    "ticks_per_second": 0.0,
                }

            tick_times = list(self._tick_times)
            avg_time = sum(tick_times) / len(tick_times)

            return {
                "avg_tick_time_ms": avg_time * 1000,
                "max_tick_time_ms": max(tick_times) * 1000,
                "min_tick_time_ms": min(tick_times) * 1000,
                "ticks_per_second": 1.0 / avg_time if avg_time > 0 else 0.0,
                "history": list(self.performance_history),
            }

    # === Callbacks для обновления данных ===

    def on_layers_update(self, layer_state: Dict[Any, Any]):
        """
        Вызывается при обновлении слоёв движения.

        Args:
            layer_state: Новое состояние слоёв
        """
        with self._lock:
            self._layers_cache = layer_state

        # Отправить по WebSocket
        if self.ws_manager:
            try:
                self.ws_manager.broadcast_layers(layer_state)
            except Exception as e:
                logger.error(f"Error broadcasting layers: {e}")

    def on_sensors_update(self, sensors_data: Dict[Any, Any]):
        """
        Вызывается при обновлении данных сенсоров.

        Args:
            sensors_data: Новые данные сенсоров
        """
        with self._lock:
            self._sensors_cache = sensors_data

        # Отправить по WebSocket
        if self.ws_manager:
            try:
                self.ws_manager.broadcast_sensors(sensors_data)
            except Exception as e:
                logger.error(f"Error broadcasting sensors: {e}")

    def on_position_update(self, x: float, y: float, z: float, yaw: float, pitch: float):
        """
        Вызывается при изменении позиции.

        Args:
            x, y, z: Координаты
            yaw: Угол поворота
            pitch: Наклон
        """
        # Добавляем в историю
        with self._lock:
            self.position_history.append(
                {"x": x, "y": y, "z": z, "yaw": yaw, "pitch": pitch, "timestamp": time.time()}
            )

        # Отправить по WebSocket
        if self.ws_manager:
            try:
                self.ws_manager.broadcast_position(x, y, z, yaw, pitch)
            except Exception as e:
                logger.error(f"Error broadcasting position: {e}")

    def log_event(self, event_type: str, data: Dict[Any, Any], level: str = "info"):
        """
        Записать событие в лог.

        Args:
            event_type: Тип события
            data: Данные события
            level: Уровень лога (info, warning, error, debug)
        """
        entry = {"type": event_type, "level": level, "data": data, "timestamp": time.time()}

        with self._lock:
            self.log_buffer.append(entry)

        # Отправить по WebSocket
        if self.ws_manager:
            try:
                self.ws_manager.broadcast_log(level, event_type, data)
            except Exception as e:
                logger.error(f"Error broadcasting log: {e}")

    def on_tick_complete(self, tick_time: float):
        """
        Вызывается при завершении тика.

        Args:
            tick_time: Время выполнения тика в секундах
        """
        with self._lock:
            self._tick_times.append(tick_time)

            # Обновляем историю производительности (раз в секунду)
            now = time.time()
            if now - self._last_update_time >= 1.0:
                self.performance_history.append(
                    {"tick_time_ms": tick_time * 1000, "timestamp": now}
                )
                self._last_update_time = now
