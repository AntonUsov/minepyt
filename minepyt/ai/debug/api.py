"""
REST API для запросов состояния бота.
"""

from flask import jsonify, request
from functools import wraps
from typing import Dict, Any, Optional, Callable
import logging

logger = logging.getLogger(__name__)


def handle_errors(f: Callable) -> Callable:
    """
    Декоратор для обработки ошибок в API эндпоинтах.

    Args:
        f: Функция-обработчик

    Returns:
        Обернутая функция с обработкой ошибок
    """

    @wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except Exception as e:
            logger.error(f"API Error: {e}", exc_info=True)
            return jsonify({"error": str(e), "status": "error"}), 500

    return decorated_function


class APIRouter:
    """
    REST API роутер для запросов состояния бота.

    Предоставляет эндпоинты:
    - GET /api/state - Полное состояние бота
    - GET /api/layers - Состояние слоёв движения
    - GET /api/sensors - Данные сенсоров
    - GET /api/logs - Логи событий
    - GET /api/perf - Производительность
    - GET /api/health - Здоровье и голод
    - GET /api/inventory - Инвентарь
    """

    def __init__(self, app, state_collector):
        """
        Инициализация API роутера.

        Args:
            app: Flask приложение
            state_collector: StateCollector для сбора данных
        """
        self.app = app
        self.state_collector = state_collector
        self._setup_routes()

    def _setup_routes(self):
        """Настройка всех API роутов."""

        @self.app.route("/api/state")
        @handle_errors
        def get_state():
            """
            Получить полное состояние бота.

            Returns:
                JSON с полным состоянием бота
            """
            state = self.state_collector.get_full_state()
            return jsonify(state)

        @self.app.route("/api/layers")
        @handle_errors
        def get_layers():
            """
            Получить состояние слоёв движения.

            Returns:
                JSON с состоянием слоёв
            """
            layers = self.state_collector.get_layers_state()
            return jsonify(layers)

        @self.app.route("/api/sensors")
        @handle_errors
        def get_sensors():
            """
            Получить данные сенсоров.

            Query params:
                detailed: bool - Вернуть детальные данные (default: false)

            Returns:
                JSON с данными сенсоров
            """
            detailed = request.args.get("detailed", "false").lower() == "true"
            sensors = self.state_collector.get_sensors_data(detailed=detailed)
            return jsonify(sensors)

        @self.app.route("/api/logs")
        @handle_errors
        def get_logs():
            """
            Получить логи событий.

            Query params:
                limit: int - Максимальное количество логов (default: 100)
                level: str - Фильтр по уровню (info, warning, error)

            Returns:
                JSON с логами событий
            """
            limit = request.args.get("limit", 100, type=int)
            level = request.args.get("level", None)

            logs = self.state_collector.get_logs(limit=limit, level=level)
            return jsonify({"logs": logs, "count": len(logs)})

        @self.app.route("/api/perf")
        @handle_errors
        def get_performance():
            """
            Получить данные производительности.

            Returns:
                JSON с данными производительности
            """
            perf = self.state_collector.get_performance_stats()
            return jsonify(perf)

        @self.app.route("/api/health")
        @handle_errors
        def get_health():
            """
            Получить состояние здоровья и голода.

            Returns:
                JSON с состоянием здоровья
            """
            health = self.state_collector.get_health_state()
            return jsonify(health)

        @self.app.route("/api/inventory")
        @handle_errors
        def get_inventory():
            """
            Получить данные инвентаря.

            Query params:
                slots: str - Какие слоты показать (all, hotbar, armor)

            Returns:
                JSON с данными инвентаря
            """
            slots = request.args.get("slots", "all")
            inventory = self.state_collector.get_inventory_data(slots=slots)
            return jsonify(inventory)

        @self.app.route("/api/position")
        @handle_errors
        def get_position():
            """
            Получить текущую позицию бота.

            Returns:
                JSON с позицией бота
            """
            position = self.state_collector.get_position_data()
            return jsonify(position)

        @self.app.route("/api/task")
        @handle_errors
        def get_task():
            """
            Получить текущую задачу бота.

            Returns:
                JSON с информацией о текущей задаче
            """
            task = self.state_collector.get_current_task()
            return jsonify(task)

        @self.app.route("/api/config")
        @handle_errors
        def get_config():
            """
            Получить конфигурацию debug сервера.

            Returns:
                JSON с конфигурацией
            """
            config = {
                "min_broadcast_interval": 0.05,
                "max_log_size": 1000,
                "supported_endpoints": [
                    "/api/state",
                    "/api/layers",
                    "/api/sensors",
                    "/api/logs",
                    "/api/perf",
                    "/api/health",
                    "/api/inventory",
                    "/api/position",
                    "/api/task",
                    "/api/config",
                ],
            }
            return jsonify(config)


def setup_api_routes(app, state_collector):
    """
    Настроить все API роуты.

    Args:
        app: Flask приложение
        state_collector: StateCollector для сбора данных

    Returns:
        APIRouter экземпляр
    """
    return APIRouter(app, state_collector)
