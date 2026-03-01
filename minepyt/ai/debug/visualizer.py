"""
Debug Visualizer

WebSocket сервер для визуализации состояния AI бота в реальном времени.
"""

import asyncio
import json
import time
import logging
from pathlib import Path
from typing import Optional, Set, Callable, Any, Dict, TYPE_CHECKING
from dataclasses import dataclass, field

try:
    import websockets
    from websockets.server import serve, WebSocketServerProtocol

    WEBSOCKETS_AVAILABLE = True
except ImportError:
    WEBSOCKETS_AVAILABLE = False
    WebSocketServerProtocol = Any

from .snapshot import (
    DebugSnapshot,
    PositionInfo,
    HealthInfo,
    InventoryInfo,
    VectorInfo,
    ThreatInfo,
    InterestInfo,
    GoalInfo,
    DecisionRecord,
)

if TYPE_CHECKING:
    from ...protocol.connection import MinecraftProtocol

logger = logging.getLogger(__name__)


@dataclass
class DebugConfig:
    """Конфигурация отладчика"""

    enabled: bool = True
    port: int = 8765
    host: str = "localhost"

    # Частота обновления
    snapshot_interval: float = 0.05  # 20 раз в секунду

    # История
    max_history: int = 10000
    max_decisions: int = 100

    # Фильтрация
    min_threat_danger: float = 0.1  # минимальный уровень угрозы для показа
    min_interest_priority: float = 0.1  # минимальный приоритет интереса

    # Веб-интерфейс
    serve_web_interface: bool = True
    web_interface_port: int = 8080


class DebugVisualizer:
    """
    Система визуальной отладки AI бота.

    WebSocket сервер для веб-интерфейса, показывающий:
    - Позицию и состояние бота
    - Векторы движения (все слои)
    - Угрозы и интересы
    - Историю решений
    - Метрики производительности
    """

    def __init__(self, bot: "MinecraftProtocol", config: Optional[DebugConfig] = None):
        """
        Инициализация отладчика.

        Args:
            bot: Протокол бота для отслеживания
            config: Конфигурация отладчика
        """
        if not WEBSOCKETS_AVAILABLE:
            raise ImportError(
                "websockets library not installed. Install with: pip install websockets"
            )

        self.bot = bot
        self.config = config or DebugConfig()

        # WebSocket клиенты
        self.clients: Set[WebSocketServerProtocol] = set()

        # История снимков
        self.history: list[DebugSnapshot] = []

        # История решений
        self.decision_history: list[DecisionRecord] = []

        # Сервер
        self._server: Optional[Any] = None
        self._running = False
        self._task: Optional[asyncio.Task] = None

        # Метрики
        self._tick_times: list[float] = []
        self._last_tick_time = time.time()

        # Callbacks для сбора данных
        self._data_collectors: Dict[str, Callable] = {}

        # Регистрируем стандартные коллекторы
        self._register_default_collectors()

    def _register_default_collectors(self):
        """Регистрация стандартных коллекторов данных"""
        self._data_collectors["position"] = self._collect_position
        self._data_collectors["health"] = self._collect_health
        self._data_collectors["inventory"] = self._collect_inventory

    def register_collector(self, name: str, collector: Callable[[], Any]):
        """
        Регистрация кастомного коллектора данных.

        Args:
            name: Имя коллектора
            collector: Функция, возвращающая данные
        """
        self._data_collectors[name] = collector

    # ==================== Коллекторы данных ====================

    def _collect_position(self) -> PositionInfo:
        """Сбор информации о позиции"""
        pos = getattr(self.bot, "position", None)
        if not pos:
            return PositionInfo()

        # Получаем yaw/pitch если доступны
        yaw = getattr(self.bot, "yaw", 0.0) or 0.0
        pitch = getattr(self.bot, "pitch", 0.0) or 0.0

        # Скорость
        velocity = getattr(self.bot, "velocity", (0.0, 0.0, 0.0)) or (0.0, 0.0, 0.0)

        # Состояние
        on_ground = getattr(self.bot, "on_ground", True)
        in_water = getattr(self.bot, "in_water", False)
        in_lava = getattr(self.bot, "in_lava", False)

        return PositionInfo(
            x=pos[0],
            y=pos[1],
            z=pos[2],
            yaw=yaw,
            pitch=pitch,
            velocity=velocity,
            on_ground=on_ground,
            in_water=in_water,
            in_lava=in_lava,
        )

    def _collect_health(self) -> HealthInfo:
        """Сбор информации о здоровье"""
        health = getattr(self.bot, "health", 20.0) or 20.0
        food = getattr(self.bot, "food", 20) or 20
        saturation = getattr(self.bot, "saturation", 5.0) or 5.0

        return HealthInfo(
            health=health,
            food=food,
            saturation=saturation,
        )

    def _collect_inventory(self) -> InventoryInfo:
        """Сбор информации об инвентаре"""
        held_slot = getattr(self.bot, "quick_bar_slot", 0) or 0

        # Получаем предмет в руке
        held_item = None
        held_count = 0

        inventory = getattr(self.bot, "inventory", None)
        if inventory:
            # Пытаемся получить held item
            item = getattr(self.bot, "held_item", None)
            if item:
                held_item = getattr(item, "name", None) or getattr(item, "item_name", None)
                held_count = getattr(item, "item_count", 1) or 1

            # Считаем предметы
            total = 0
            free = 36
            if hasattr(inventory, "items"):
                for slot_item in inventory.items():
                    if slot_item:
                        total += 1
                        free -= 1

        # Броня
        armor = {
            "head": None,
            "chest": None,
            "legs": None,
            "feet": None,
        }
        equipment = getattr(self.bot, "equipment", None)
        if equipment:
            for slot, item in equipment.items():
                if item and slot in armor:
                    armor[slot] = getattr(item, "name", None)

        return InventoryInfo(
            held_slot=held_slot,
            held_item=held_item,
            held_item_count=held_count,
            total_items=total if "total" in dir() else 0,
            free_slots=free if "free" in dir() else 36,
            armor=armor,
        )

    # ==================== AI данные ====================

    def _collect_vectors(self) -> Dict[str, VectorInfo]:
        """Сбор векторов движения от AI"""
        vectors = {}

        # Получаем AI модуль если есть
        ai = getattr(self.bot, "ai", None) or getattr(self.bot, "_ai", None)
        if not ai:
            return vectors

        # Движение
        movement = getattr(ai, "movement", None) or getattr(ai, "_movement", None)
        if movement:
            # Goal vector
            goal_vec = getattr(movement, "goal_vector", None)
            if goal_vec:
                vectors["goal"] = VectorInfo(
                    dx=goal_vec[0],
                    dy=goal_vec[1] if len(goal_vec) > 1 else 0.0,
                    dz=goal_vec[2] if len(goal_vec) > 2 else 0.0,
                    weight=getattr(movement, "goal_weight", 0.5),
                    source="goal",
                )

            # Tactical vector
            tactical_vec = getattr(movement, "tactical_vector", None)
            if tactical_vec:
                vectors["tactical"] = VectorInfo(
                    dx=tactical_vec[0],
                    dy=tactical_vec[1] if len(tactical_vec) > 1 else 0.0,
                    dz=tactical_vec[2] if len(tactical_vec) > 2 else 0.0,
                    weight=getattr(movement, "tactical_weight", 0.8),
                    source="tactical",
                )

            # Avoid vector
            avoid_vec = getattr(movement, "avoid_vector", None)
            if avoid_vec:
                vectors["avoid"] = VectorInfo(
                    dx=avoid_vec[0],
                    dy=avoid_vec[1] if len(avoid_vec) > 1 else 0.0,
                    dz=avoid_vec[2] if len(avoid_vec) > 2 else 0.0,
                    weight=getattr(movement, "avoid_weight", 0.7),
                    source="avoid",
                )

            # Final vector
            final_vec = getattr(movement, "final_vector", None)
            if final_vec:
                vectors["final"] = VectorInfo(
                    dx=final_vec[0],
                    dy=final_vec[1] if len(final_vec) > 1 else 0.0,
                    dz=final_vec[2] if len(final_vec) > 2 else 0.0,
                    weight=1.0,
                    source="final",
                )

        return vectors

    def _collect_threats(self) -> list[ThreatInfo]:
        """Сбор информации об угрозах"""
        threats = []

        ai = getattr(self.bot, "ai", None) or getattr(self.bot, "_ai", None)
        if not ai:
            return threats

        sensors = getattr(ai, "sensors", None) or getattr(ai, "_sensors", None)
        if not sensors:
            return threats

        raw_threats = getattr(sensors, "threats", None) or []

        pos = getattr(self.bot, "position", (0, 0, 0))

        for threat in raw_threats:
            danger = getattr(threat, "danger", 0.0) or 0.0
            if danger < self.config.min_threat_danger:
                continue

            threat_pos = getattr(threat, "position", (0, 0, 0))

            # Вычисляем расстояние
            dx = threat_pos[0] - pos[0]
            dy = threat_pos[1] - pos[1]
            dz = threat_pos[2] - pos[2]
            distance = (dx * dx + dy * dy + dz * dz) ** 0.5

            # Направление (нормализованное)
            if distance > 0:
                direction = (dx / distance, dy / distance, dz / distance)
            else:
                direction = (0, 0, 0)

            threats.append(
                ThreatInfo(
                    threat_type=getattr(threat, "threat_type", "unknown") or "unknown",
                    entity_type=getattr(threat, "entity_type", None),
                    position=threat_pos,
                    distance=distance,
                    danger=danger,
                    direction=direction,
                )
            )

        return threats

    def _collect_interests(self) -> list[InterestInfo]:
        """Сбор информации об интересах"""
        interests = []

        ai = getattr(self.bot, "ai", None) or getattr(self.bot, "_ai", None)
        if not ai:
            return interests

        sensors = getattr(ai, "sensors", None) or getattr(ai, "_sensors", None)
        if not sensors:
            return interests

        raw_interests = getattr(sensors, "interests", None) or []

        pos = getattr(self.bot, "position", (0, 0, 0))

        for interest in raw_interests:
            priority = getattr(interest, "priority", 0.0) or 0.0
            if priority < self.config.min_interest_priority:
                continue

            interest_pos = getattr(interest, "position", (0, 0, 0))

            # Вычисляем расстояние
            dx = interest_pos[0] - pos[0]
            dy = interest_pos[1] - pos[1]
            dz = interest_pos[2] - pos[2]
            distance = (dx * dx + dy * dy + dz * dz) ** 0.5

            interests.append(
                InterestInfo(
                    interest_type=getattr(interest, "interest_type", "unknown") or "unknown",
                    entity_type=getattr(interest, "entity_type", None),
                    position=interest_pos,
                    distance=distance,
                    priority=priority,
                )
            )

        return interests

    def _collect_goal(self) -> GoalInfo:
        """Сбор информации о текущей цели"""
        ai = getattr(self.bot, "ai", None) or getattr(self.bot, "_ai", None)
        if not ai:
            return GoalInfo()

        movement = getattr(ai, "movement", None) or getattr(ai, "_movement", None)
        if not movement:
            return GoalInfo()

        goal_type = getattr(movement, "goal_type", "idle") or "idle"
        target_name = getattr(movement, "goal_entity", None)

        # Целевая позиция
        target_pos = None
        primary_goal = getattr(movement, "primary_goal", None)
        if primary_goal:
            target_pos = primary_goal

        # Прогресс (если идём к точке)
        progress = 0.0
        eta = None
        if target_pos and goal_type in ("goto", "follow"):
            pos = getattr(self.bot, "position", (0, 0, 0))

            dx = target_pos[0] - pos[0]
            dy = target_pos[1] - pos[1]
            dz = target_pos[2] - pos[2]
            distance = (dx * dx + dy * dy + dz * dz) ** 0.5

            # Предполагаем скорость 4.3 блока/сек (нормальная ходьба)
            speed = 4.3
            eta = distance / speed

            # Прогресс на основе начальной дистанции (если сохранена)
            initial_dist = getattr(movement, "initial_distance", None)
            if initial_dist and initial_dist > 0:
                progress = 1.0 - (distance / initial_dist)
                progress = max(0.0, min(1.0, progress))

        return GoalInfo(
            goal_type=goal_type,
            target_name=target_name,
            target_position=target_pos,
            progress=progress,
            eta_seconds=eta,
        )

    # ==================== Создание снимка ====================

    def create_snapshot(self, tick: int = 0) -> DebugSnapshot:
        """
        Создание полного снимка состояния.

        Args:
            tick: Номер тика

        Returns:
            DebugSnapshot с полным состоянием
        """
        # Собираем данные
        position = self._collect_position()
        health = self._collect_health()
        inventory = self._collect_inventory()
        vectors = self._collect_vectors()
        threats = self._collect_threats()
        interests = self._collect_interests()
        goal = self._collect_goal()

        # Метрики FPS
        now = time.time()
        if self._tick_times:
            avg_tick_time = sum(self._tick_times[-20:]) / len(self._tick_times[-20:])
            fps = 1000.0 / avg_tick_time if avg_tick_time > 0 else 20.0
        else:
            fps = 20.0

        return DebugSnapshot(
            timestamp=now,
            bot_name=getattr(self.bot, "username", "Bot") or "Bot",
            tick=tick,
            fps=fps,
            position=position,
            health=health,
            inventory=inventory,
            vectors=vectors,
            threats=threats,
            interests=interests,
            goal=goal,
            recent_decisions=self.decision_history[-20:],
            tick_time_ms=avg_tick_time if self._tick_times else 0.0,
        )

    # ==================== Управление решениями ====================

    def record_decision(
        self,
        action: str,
        reason: str,
        result: str = "pending",
        duration_ms: Optional[float] = None,
    ):
        """
        Записать решение в историю.

        Args:
            action: Выполненное действие
            reason: Причина решения
            result: Результат (success, failed, cancelled, pending)
            duration_ms: Длительность выполнения
        """
        record = DecisionRecord(
            timestamp=time.time(),
            action=action,
            reason=reason,
            result=result,
            duration_ms=duration_ms,
        )

        self.decision_history.append(record)

        # Ограничиваем размер истории
        if len(self.decision_history) > self.config.max_decisions:
            self.decision_history = self.decision_history[-self.config.max_decisions :]

    # ==================== WebSocket сервер ====================

    async def _handle_client(self, websocket: WebSocketServerProtocol, path: str = ""):
        """Обработка подключения клиента"""
        self.clients.add(websocket)
        client_addr = websocket.remote_address
        logger.info(f"Debug client connected: {client_addr}")

        try:
            # Отправляем текущее состояние сразу
            snapshot = self.create_snapshot()
            await websocket.send(snapshot.to_json())

            # Ждём сообщений от клиента (команды)
            async for message in websocket:
                try:
                    data = json.loads(message)
                    await self._handle_client_message(websocket, data)
                except json.JSONDecodeError:
                    logger.warning(f"Invalid JSON from client: {message}")

        except websockets.exceptions.ConnectionClosed:
            pass
        finally:
            self.clients.discard(websocket)
            logger.info(f"Debug client disconnected: {client_addr}")

    async def _handle_client_message(self, websocket: WebSocketServerProtocol, data: dict):
        """Обработка сообщения от клиента"""
        msg_type = data.get("type", "")

        if msg_type == "ping":
            await websocket.send(json.dumps({"type": "pong"}))

        elif msg_type == "get_history":
            # Отправить историю
            count = data.get("count", 100)
            history = [s.to_dict() for s in self.history[-count:]]
            await websocket.send(
                json.dumps(
                    {
                        "type": "history",
                        "data": history,
                    }
                )
            )

        elif msg_type == "set_goal":
            # Установить цель боту (если возможно)
            goal_type = data.get("goalType")
            target = data.get("target")

            ai = getattr(self.bot, "ai", None) or getattr(self.bot, "_ai", None)
            if ai:
                movement = getattr(ai, "movement", None) or getattr(ai, "_movement", None)
                if movement:
                    if goal_type == "follow" and target:
                        movement.set_follow_player(target)
                    elif goal_type == "goto" and target:
                        x, y, z = target.get("x", 0), target.get("y", 64), target.get("z", 0)
                        movement.set_goto(x, y, z)
                    elif goal_type == "idle":
                        movement.clear_goal()

            await websocket.send(json.dumps({"type": "goal_set", "goalType": goal_type}))

        elif msg_type == "command":
            # Выполнить команду бота
            command = data.get("command")
            if command:
                # Можно расширить для выполнения команд
                logger.info(f"Received command: {command}")

    async def broadcast_snapshot(self, snapshot: DebugSnapshot):
        """Рассылка снимка всем клиентам"""
        if not self.clients:
            return

        message = snapshot.to_json()

        # Удаляем отключённых клиентов
        disconnected = set()

        for client in self.clients:
            try:
                await client.send(message)
            except Exception:
                disconnected.add(client)

        self.clients -= disconnected

    # ==================== Главный цикл ====================

    async def _snapshot_loop(self):
        """Цикл создания и рассылки снимков"""
        tick = 0

        while self._running:
            try:
                # Создаём снимок
                snapshot = self.create_snapshot(tick)

                # Сохраняем в историю
                self.history.append(snapshot)
                if len(self.history) > self.config.max_history:
                    self.history.pop(0)

                # Рассылаем клиентам
                await self.broadcast_snapshot(snapshot)

                tick += 1

                # Ждём до следующего снимка
                await asyncio.sleep(self.config.snapshot_interval)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in snapshot loop: {e}")
                await asyncio.sleep(0.1)

    # ==================== Управление сервером ====================

    async def start(self):
        """Запуск сервера отладки"""
        if not self.config.enabled:
            logger.info("Debug visualizer is disabled")
            return

        if self._running:
            return

        self._running = True

        # Запускаем WebSocket сервер
        self._server = await serve(
            self._handle_client,
            self.config.host,
            self.config.port,
        )

        # Запускаем цикл снимков
        self._task = asyncio.create_task(self._snapshot_loop())

        logger.info(f"Debug visualizer started on ws://{self.config.host}:{self.config.port}")

        if self.config.serve_web_interface:
            logger.info(f"Web interface: http://localhost:{self.config.web_interface_port}")

    async def stop(self):
        """Остановка сервера отладки"""
        self._running = False

        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None

        if self._server:
            self._server.close()
            await self._server.wait_closed()
            self._server = None

        # Закрываем клиентов
        for client in list(self.clients):
            await client.close()

        self.clients.clear()

        logger.info("Debug visualizer stopped")

    # ==================== Контекстный менеджер ====================

    async def __aenter__(self):
        await self.start()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.stop()
        return False

    # ==================== Утилиты ====================

    def get_web_interface_html(self) -> str:
        """Получить HTML веб-интерфейса"""
        # HTML файл должен быть в web_interface/ директории
        html_path = Path(__file__).parent / "web_interface" / "index.html"

        if html_path.exists():
            return html_path.read_text(encoding="utf-8")

        # Возвращаем базовый HTML если файл не найден
        return self._get_default_html()

    def _get_default_html(self) -> str:
        """Базовый HTML интерфейс"""
        return """<!DOCTYPE html>
<html>
<head>
    <title>MinePyt Debug</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; background: #1a1a2e; color: #eee; }
        .container { max-width: 1200px; margin: 0 auto; }
        h1 { color: #00d9ff; }
        .panel { background: #16213e; border-radius: 8px; padding: 15px; margin: 10px 0; }
        .status { display: grid; grid-template-columns: repeat(3, 1fr); gap: 10px; }
        .metric { text-align: center; padding: 10px; }
        .metric-value { font-size: 24px; font-weight: bold; color: #00d9ff; }
        .metric-label { font-size: 12px; color: #888; }
        #log { height: 200px; overflow-y: auto; font-family: monospace; font-size: 12px; }
    </style>
</head>
<body>
    <div class="container">
        <h1>MinePyt Debug Visualizer</h1>
        <div class="panel">
            <div class="status">
                <div class="metric">
                    <div class="metric-value" id="health">--</div>
                    <div class="metric-label">Health</div>
                </div>
                <div class="metric">
                    <div class="metric-value" id="food">--</div>
                    <div class="metric-label">Food</div>
                </div>
                <div class="metric">
                    <div class="metric-value" id="fps">--</div>
                    <div class="metric-label">FPS</div>
                </div>
            </div>
        </div>
        <div class="panel">
            <h3>Position</h3>
            <div id="position">--</div>
        </div>
        <div class="panel">
            <h3>Log</h3>
            <div id="log"></div>
        </div>
    </div>
    <script>
        const ws = new WebSocket(`ws://${location.hostname}:8765`);
        ws.onmessage = (event) => {
            const data = JSON.parse(event.data);
            document.getElementById('health').textContent = data.health.health;
            document.getElementById('food').textContent = data.health.food;
            document.getElementById('fps').textContent = data.meta.fps;
            document.getElementById('position').textContent = 
                `X: ${data.position.x.toFixed(1)} Y: ${data.position.y.toFixed(1)} Z: ${data.position.z.toFixed(1)}`;
        };
    </script>
</body>
</html>"""
