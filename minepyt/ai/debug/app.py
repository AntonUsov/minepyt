"""
Flask Debug Server для визуализации AI системы бота в реальном времени.
"""

import asyncio
import logging
import threading
from typing import Optional, Dict, Any
from flask import Flask, render_template
from flask_socketio import SocketIO
from .state_collector import StateCollector
from .socket_handler import WebSocketManager

logger = logging.getLogger(__name__)


class DebugServer:
    """
    Flask сервер для отладки AI системы бота.

    Предоставляет:
    - WebSocket стриминг данных в реальном времени
    - REST API для запросов состояния
    - Веб-интерфейс для визуализации

    Пример использования:
        bot = await SmartBot({
            "host": "localhost",
            "port": 25565,
            "username": "SmartBot",
            "debug_server": True
        })

        # Запустить в отдельном потоке
        import threading
        server_thread = threading.Thread(target=bot.start_debug_server)
        server_thread.daemon = True
        server_thread.start()
    """

    def __init__(self, bot, host: str = "0.0.0.0", port: int = 5000, debug: bool = False):
        """
        Инициализация debug сервера.

        Args:
            bot: Экземпляр SmartBot
            host: Хост для прослушивания
            port: Порт для прослушивания
            debug: Включить debug режим Flask
        """
        self.bot = bot
        self.host = host
        self.port = port
        self.debug = debug

        # Flask приложение
        self.app = Flask(__name__, template_folder="templates", static_folder="static")
        self.app.config["SECRET_KEY"] = "minepyt-debug-secret-key"

        # SocketIO для real-time стриминга
        self.socketio = SocketIO(self.app, cors_allowed_origins="*", async_mode="threading")

        # Компоненты
        self.state_collector = StateCollector(bot)
        self.ws_manager = WebSocketManager(self.socketio, self.state_collector)

        # Настройка
        self._setup_routes()
        self._setup_socketio()

        # Флаг работы
        self.running = False

        logger.info(f"DebugServer initialized on http://{host}:{port}")

    def _setup_routes(self):
        """Настройка HTTP роутов."""

        @self.app.route("/")
        def index():
            """Главная страница с обзором системы."""
            return render_template("index.html")

        @self.app.route("/layers")
        def layers():
            """Визуализация слоёв движения."""
            return render_template("layers.html")

        @self.app.route("/map")
        def map_view():
            """Карта местности."""
            return render_template("map.html")

        @self.app.route("/sensors")
        def sensors():
            """Данные сенсоров."""
            return render_template("sensors.html")

        @self.app.route("/logs")
        def logs():
            """Логи событий."""
            return render_template("logs.html")

        @self.app.route("/performance")
        def performance():
            """Производительность."""
            return render_template("performance.html")

    def _setup_socketio(self):
        """Настройка WebSocket обработчиков."""

        @self.socketio.on("connect")
        def handle_connect():
            """Обработка подключения клиента."""
            logger.info("Client connected")
            # Отправить начальное состояние
            initial_state = self.state_collector.get_full_state()
            self.socketio.emit("initial_state", initial_state)

        @self.socketio.on("disconnect")
        def handle_disconnect():
            """Обработка отключения клиента."""
            logger.info("Client disconnected")

        @self.socketio.on("request_state")
        def handle_request_state():
            """Запрос текущего состояния."""
            state = self.state_collector.get_full_state()
            self.socketio.emit("full_state", state)

        @self.socketio.on("request_layers")
        def handle_request_layers():
            """Запрос состояния слоёв."""
            layers = self.state_collector.get_layers_state()
            self.socketio.emit("layers_state", layers)

        @self.socketio.on("request_sensors")
        def handle_request_sensors():
            """Запрос данных сенсоров."""
            sensors = self.state_collector.get_sensors_data()
            self.socketio.emit("sensors_data", sensors)

    def run(self):
        """Запустить debug сервер (блокирующий вызов)."""
        logger.info(f"Starting Debug Server on http://{self.host}:{self.port}")
        self.running = True

        try:
            self.socketio.run(
                self.app,
                host=self.host,
                port=self.port,
                debug=self.debug,
                use_reloader=False,  # Отключить reloader для избежания проблем с потоками
            )
        except Exception as e:
            logger.error(f"Error running Debug Server: {e}")
            self.running = False
            raise

    def start_background(self):
        """Запустить debug сервер в фоновом потоке."""

        def run_server():
            try:
                self.run()
            except Exception as e:
                logger.error(f"Background server error: {e}")

        thread = threading.Thread(target=run_server, daemon=True)
        thread.start()
        logger.info("Debug Server started in background thread")
        return thread

    def stop(self):
        """Остановить debug сервер."""
        self.running = False
        logger.info("Debug Server stopped")

    def broadcast_event(self, event_type: str, data: Dict[Any, Any]):
        """
        Отправить событие всем подключенным клиентам.

        Args:
            event_type: Тип события
            data: Данные события
        """
        self.ws_manager.broadcast_event(event_type, data)

    def broadcast_position(self, x: float, y: float, z: float, yaw: float, pitch: float):
        """
        Отправить обновление позиции.

        Args:
            x, y, z: Координаты
            yaw: Угол поворота по горизонтали
            pitch: Угол поворота по вертикали
        """
        self.ws_manager.broadcast_position(x, y, z, yaw, pitch)

    def broadcast_layers(self, layer_state: Dict[Any, Any]):
        """
        Отправить обновление слоёв движения.

        Args:
            layer_state: Состояние слоёв
        """
        self.ws_manager.broadcast_layers(layer_state)

    def broadcast_sensors(self, sensors_data: Dict[Any, Any]):
        """
        Отправить данные сенсоров.

        Args:
            sensors_data: Данные сенсоров
        """
        self.ws_manager.broadcast_sensors(sensors_data)
