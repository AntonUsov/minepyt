"""
Play state packet handlers for Minecraft 1.21.4

This is the main game state where most gameplay happens.
Contains handlers for:
- Keep Alive, Disconnect
- Join Game, Respawn
- Player Position, Game State
- Health, Time
- Chat messages
- Chunks, Blocks
- Entities
- Inventory
"""

import json
import math
from typing import TYPE_CHECKING, Any, Dict, Optional, Tuple

from mcproto.buffer import Buffer
from mcproto.protocol.base_io import StructFormat
from mcproto.types.uuid import UUID

if TYPE_CHECKING:
    from ..connection import MinecraftProtocol
from ..models import parse_game_mode

# Import from minepyt package
try:
    from minepyt.chunk_utils import World, ChunkColumn, BufferReader, parse_nbt, parse_chunk_section
    from minepyt.block_registry import Block
    from minepyt.entities import Entity, EntityType, EntityKind
except ImportError:
    # Fallback for relative imports
    from ...chunk_utils import World, ChunkColumn, BufferReader, parse_nbt, parse_chunk_section
    from ...block_registry import Block
    from ...entities import Entity, EntityType, EntityKind


class PlayHandler:
    """Handler for play state packets (clientbound)"""

    async def handle_play_packet(self: "MinecraftProtocol", packet_id: int, buf: Buffer) -> None:
        """Handle play state packets"""
        # Core packets
        if packet_id == 0x27:  # Keep Alive
            await self._handle_keep_alive(buf)

        elif packet_id == 0x2C:  # Login (Join Game)
            await self._handle_join_game(buf)

        elif packet_id == 0x42:  # Synchronize Player Position
            await self._handle_player_position(buf)

        elif packet_id == 0x1A:  # Disconnect
            await self._handle_disconnect(buf)

        elif packet_id == 0x3D:  # Respawn
            await self._handle_respawn(buf)

        elif packet_id == 0x4A:  # Game State Change
            await self._handle_game_state_change(buf)

        elif packet_id == 0x4E:  # Update Time
            await self._handle_update_time(buf)

        elif packet_id == 0x52:  # Update Health
            await self._handle_update_health(buf)

        # Player info
        elif packet_id == 0x3F:  # Player Info Remove
            await self._handle_player_info_remove(buf)

        elif packet_id == 0x40:  # Player Info Update
            await self._handle_player_info_update(buf)

        # Chat
        elif packet_id == 0x73:  # System Chat
            await self._handle_system_chat(buf)

        # World
        elif packet_id == 0x28:  # Level Chunk With Light
            await self._handle_level_chunk(buf)

        elif packet_id == 0x0A:  # Block Update
            await self._handle_block_update(buf)

        # Inventory
        elif packet_id == 0x14:  # Set Slot
            await self._handle_set_slot(buf)

        elif packet_id == 0x11:  # Window Items (Container Content)
            await self._handle_window_items(buf)

        # Entities
        elif packet_id == 0x01:  # Spawn Entity
            await self._handle_spawn_entity(buf)

        elif packet_id == 0x03:  # Entity Destroy
            await self._handle_entity_destroy(buf)

        elif packet_id == 0x1F:  # Set Entity Metadata
            await self._handle_entity_metadata(buf)

        elif packet_id == 0x26:  # Entity Move
            pass  # Too spammy to handle in detail

        elif packet_id == 0x24:  # Merchant Offers (Villager trades)
            await self._handle_merchant_offers(buf)

        else:
            # Many more packets exist - log only unknown ones
            pass

    # === Core packet handlers ===

    async def _handle_keep_alive(self: "MinecraftProtocol", buf: Buffer) -> None:
        """Handle Keep Alive packet (0x27)"""
        keep_alive_id = buf.read_value(StructFormat.LONGLONG)
        await self.send_keep_alive(keep_alive_id)

    async def _handle_join_game(self: "MinecraftProtocol", buf: Buffer) -> None:
        """Handle Join Game packet (0x2C)"""
        print("Received Join Game packet!")
        self.entity_id = buf.read_value(StructFormat.INT)
        is_hardcore = buf.read_value(StructFormat.BOOL)
        self.game.hardcore = is_hardcore

        dim_count = buf.read_varint()
        for _ in range(dim_count):
            buf.read_utf()

        self.game.max_players = buf.read_varint()
        self.game.server_view_distance = buf.read_varint()
        buf.read_varint()  # simulation distance
        buf.read_value(StructFormat.BOOL)  # reduced debug
        self.game.enable_respawn_screen = buf.read_value(StructFormat.BOOL)
        buf.read_value(StructFormat.BOOL)  # do limited crafting

        dimension_type = buf.read_varint()
        dimension_name = buf.read_utf()
        self.game.dimension = dimension_name.replace("minecraft:", "")

        buf.read_value(StructFormat.LONG)  # hashed seed

        game_mode_byte = buf.read_value(StructFormat.BYTE)
        self.game_mode = game_mode_byte
        self.game.game_mode = parse_game_mode(game_mode_byte)

        buf.read_value(StructFormat.BYTE)  # prev game mode
        is_debug = buf.read_value(StructFormat.BOOL)
        is_flat = buf.read_value(StructFormat.BOOL)

        self.game.level_type = "flat" if is_flat else ("debug" if is_debug else "default")

        has_death_loc = buf.read_value(StructFormat.BOOL)
        if has_death_loc:
            buf.read_utf()
            buf.read(8)

        buf.read_varint()  # portal cooldown
        buf.read_varint()  # sea level
        buf.read_value(StructFormat.BOOL)  # enforces secure chat

        print(f"Joined game! Entity ID: {self.entity_id}")
        print(
            f"[GAME] Mode: {self.game.game_mode}, Dimension: {self.game.dimension}, Hardcore: {self.game.hardcore}"
        )

        # Create bot's own entity
        self.entity = {
            "id": self.entity_id,
            "type": "player",
            "username": self.username,
            "uuid": self.uuid,
            "position": self.position,
            "yaw": self.yaw,
            "pitch": self.pitch,
            "on_ground": self.on_ground,
        }
        self.entities[self.entity_id] = self.entity

        self.emit("spawn")
        self.emit("login")
        self.emit("game")
        
        # Start physics after spawning
        self.start_physics()

    async def _handle_player_position(self: "MinecraftProtocol", buf: Buffer) -> None:
        """Handle Synchronize Player Position packet (0x42)"""
        teleport_id = buf.read_varint()
        x = buf.read_value(StructFormat.DOUBLE)
        y = buf.read_value(StructFormat.DOUBLE)
        z = buf.read_value(StructFormat.DOUBLE)
        buf.read_value(StructFormat.DOUBLE)  # vx
        buf.read_value(StructFormat.DOUBLE)  # vy
        buf.read_value(StructFormat.DOUBLE)  # vz
        yaw = buf.read_value(StructFormat.FLOAT)
        pitch = buf.read_value(StructFormat.FLOAT)
        buf.read_value(StructFormat.INT)  # flags

        self.position = (x, y, z)
        self.yaw = yaw
        self.pitch = pitch

        print(f"Position synchronized: {self.position}")

        # Confirm teleportation
        confirm_buf = Buffer()
        confirm_buf.write_varint(teleport_id)
        await self._write_packet(0x00, bytes(confirm_buf))

        # Send player position
        await self.send_player_position()

    async def _handle_disconnect(self: "MinecraftProtocol", buf: Buffer) -> None:
        """Handle Disconnect packet (0x1A)"""
        reason = buf.read_utf()
        print(f"Disconnected: {reason}")
        self.emit("kicked", reason)
        self._running = False

    async def _handle_respawn(self: "MinecraftProtocol", buf: Buffer) -> None:
        """Handle Respawn packet (0x3D)"""
        print("Received Respawn packet!")
        dimension_type = buf.read_varint()
        dimension_name = buf.read_utf()

        self.game.dimension = dimension_name.replace("minecraft:", "")

        buf.read_value(StructFormat.LONG)  # hashed seed
        game_mode_byte = buf.read_value(StructFormat.BYTE)
        self.game.game_mode = parse_game_mode(game_mode_byte)
        self.game.hardcore = bool(game_mode_byte & 0b1000)

        buf.read_value(StructFormat.BYTE)  # prev game mode
        buf.read_value(StructFormat.BOOL)  # is debug
        buf.read_value(StructFormat.BOOL)  # is flat

        has_death_loc = buf.read_value(StructFormat.BOOL)
        if has_death_loc:
            buf.read_utf()
            buf.read(8)

        buf.read_varint()  # portal cooldown
        buf.read_varint()  # sea level

        print(f"[GAME] Respawned in {self.game.dimension}, mode: {self.game.game_mode}")
        self.emit("respawn")
        self.emit("game")

    async def _handle_game_state_change(self: "MinecraftProtocol", buf: Buffer) -> None:
        """Handle Game State Change packet (0x4A)"""
        reason = buf.read_value(StructFormat.UBYTE)
        game_mode_float = buf.read_value(StructFormat.FLOAT)
        game_mode = int(game_mode_float)

        if reason == 3:  # Change game mode
            self.game.game_mode = parse_game_mode(game_mode)
            print(f"[GAME] Game mode changed to: {self.game.game_mode}")
            self.emit("game")
        elif reason == 4:  # Win game (credits)
            if game_mode == 1:
                # Send client command to close credits (respawn)
                cmd_buf = Buffer()
                cmd_buf.write_varint(0)  # Perform respawn
                await self._write_packet(0x0D, bytes(cmd_buf))

    async def _handle_update_time(self: "MinecraftProtocol", buf: Buffer) -> None:
        """Handle Update Time packet (0x4E)"""
        world_age = buf.read_value(StructFormat.LONG)
        time_of_day = buf.read_value(StructFormat.LONG)

        self.game.age = world_age
        self.game.time = time_of_day
        self.emit("time")

    async def _handle_update_health(self: "MinecraftProtocol", buf: Buffer) -> None:
        """Handle Update Health packet (0x52)"""
        health = buf.read_value(StructFormat.FLOAT)
        food = buf.read_varint()
        food_saturation = buf.read_value(StructFormat.FLOAT)

        old_health = self.health
        self.health = health
        self.food = food
        self.food_saturation = food_saturation

        self.emit("health")

        if health <= 0:
            if self.is_alive:
                self.is_alive = False
                print(f"[HEALTH] Death! Health: {health}")
                self.emit("death")
            if self._auto_respawn:
                await self.respawn()
        elif health > 0 and not self.is_alive:
            self.is_alive = True
            print(f"[HEALTH] Spawned! Health: {health}")
            self.emit("spawn")

    # === Player info handlers ===

    async def _handle_player_info_remove(self: "MinecraftProtocol", buf: Buffer) -> None:
        """Handle Player Info Remove packet (0x3F)"""
        count = buf.read_varint()
        for _ in range(count):
            uuid_bytes = buf.read(16)
            uuid_int = int.from_bytes(uuid_bytes, "big")
            uuid = f"{uuid_int:032x}"
            uuid = f"{uuid[:8]}-{uuid[8:12]}-{uuid[12:16]}-{uuid[16:20]}-{uuid[20:]}"
            if uuid in self.players:
                del self.players[uuid]
                print(f"[ENTITIES] Player removed: {uuid}")

    async def _handle_player_info_update(self: "MinecraftProtocol", buf: Buffer) -> None:
        """Handle Player Info Update packet (0x40)"""
        actions_byte = buf.read_value(StructFormat.BYTE)
        count = buf.read_varint()

        for _ in range(count):
            uuid_bytes = buf.read(16)
            uuid_int = int.from_bytes(uuid_bytes, "big")
            uuid = f"{uuid_int:032x}"
            uuid = f"{uuid[:8]}-{uuid[8:12]}-{uuid[12:16]}-{uuid[16:20]}-{uuid[20:]}"

            if uuid not in self.players:
                self.players[uuid] = {"uuid": uuid}

            # Action 0x01: Add Player
            if actions_byte & 0x01:
                name = buf.read_utf()
                self.players[uuid]["username"] = name

                prop_count = buf.read_varint()
                for _ in range(prop_count):
                    buf.read_utf()
                    buf.read_utf()
                    has_sig = buf.read_value(StructFormat.BOOL)
                    if has_sig:
                        buf.read_utf()

                print(f"[ENTITIES] Player added: {name}")
                self.emit("player_joined", self.players[uuid])

            # Action 0x02: Initialize Chat
            if actions_byte & 0x02:
                has_chat = buf.read_value(StructFormat.BOOL)
                if has_chat:
                    buf.read_utf()
                    buf.read_value(StructFormat.LONG)
                    buf.read_value(StructFormat.LONG)

            # Action 0x04: Update Game Mode
            if actions_byte & 0x04:
                game_mode = buf.read_varint()
                self.players[uuid]["game_mode"] = game_mode

            # Action 0x08: Update Listed
            if actions_byte & 0x08:
                listed = buf.read_value(StructFormat.BOOL)
                self.players[uuid]["listed"] = listed

            # Action 0x10: Update Latency
            if actions_byte & 0x10:
                latency = buf.read_varint()
                self.players[uuid]["latency"] = latency

            # Action 0x20: Update Display Name
            if actions_byte & 0x20:
                has_display = buf.read_value(StructFormat.BOOL)
                if has_display:
                    display_name = buf.read_utf()
                    self.players[uuid]["display_name"] = display_name

    # === Chat handler ===

    async def _handle_system_chat(self: "MinecraftProtocol", buf: Buffer) -> None:
        """Handle System Chat packet (0x73)"""
        chat_json = buf.read_utf()
        overlay = buf.read_value(StructFormat.BOOL)

        try:
            data = json.loads(chat_json)
            text = self._extract_text(data)
        except:
            text = chat_json

        print(f"[CHAT] Received: {text}")
        self.emit("chat", text, chat_json, overlay)

    def _extract_text(self: "MinecraftProtocol", data: Any) -> str:
        """Extract plain text from JSON text component"""
        if isinstance(data, str):
            return data
        elif isinstance(data, dict):
            if "text" in data:
                text = data["text"]
            elif "translate" in data:
                text = data["translate"]
                if "with" in data:
                    args = [self._extract_text(arg) for arg in data["with"]]
                    try:
                        text = text % tuple(args)
                    except:
                        text = " ".join([text] + args)
            else:
                text = ""

            if "extra" in data:
                for extra in data["extra"]:
                    text += self._extract_text(extra)

            return text
        elif isinstance(data, list):
            return "".join(self._extract_text(item) for item in data)
        else:
            return str(data)

    # === World handlers ===

    async def _handle_level_chunk(self: "MinecraftProtocol", buf: Buffer) -> None:
        """Handle Level Chunk With Light packet (0x28)"""
        chunk_x = buf.read_value(StructFormat.INT)
        chunk_z = buf.read_value(StructFormat.INT)

        chunk = ChunkColumn(
            x=chunk_x,
            z=chunk_z,
            min_y=self.game.min_y if hasattr(self, "game") else -64,
            max_y=(self.game.min_y + self.game.height - 1) if hasattr(self, "game") else 319,
        )

        chunk_data = bytes(buf.read(buf.remaining))
        reader = BufferReader(chunk_data)

        try:
            heightmaps = parse_nbt(reader)
        except:
            reader.offset = 0

        try:
            data_size = reader.read_varint()
        except:
            data_size = 0

        # Parse chunk sections
        for section_y in range(24):  # -64 to 320 = 24 sections
            try:
                section = parse_chunk_section(reader, section_y)
                if section:
                    chunk.sections[section_y] = section
            except:
                break

        # Store chunk
        self.world.chunks[(chunk_x, chunk_z)] = chunk
        self._chunks_loaded += 1

        if self._chunks_loaded <= 3:
            print(f"[WORLD] Chunk loaded: ({chunk_x}, {chunk_z})")

        self.emit("chunk_loaded", chunk_x, chunk_z)

    async def _handle_block_update(self: "MinecraftProtocol", buf: Buffer) -> None:
        """Handle Block Update packet (0x0A)"""
        # Read position (packed long)
        pos_long = buf.read_value(StructFormat.LONG)
        x = pos_long >> 38
        y = (pos_long >> 26) & 0xFFF
        z = pos_long << 38 >> 38

        # Sign extension
        if x >= 2**25:
            x -= 2**26
        if y >= 2**11:
            y -= 2**12
        if z >= 2**25:
            z -= 2**26

        block_state = buf.read_varint()

        # Update world
        self.world.set_block_state(x, y, z, block_state)

        block = Block(state_id=block_state, position=(x, y, z))
        self.emit("block_update", block)

    # === Inventory handlers ===

    async def _handle_set_slot(self: "MinecraftProtocol", buf: Buffer) -> None:
        """Handle Set Slot packet (0x14)"""
        window_id = buf.read_value(StructFormat.UBYTE)
        state_id = buf.read_varint()
        slot = buf.read_varint()

        item = self._parse_slot(buf)
        item.slot = slot

        if window_id == 0:
            self.inventory[slot] = item

        self.emit("slot_update", window_id, slot, item)

    async def _handle_window_items(self: "MinecraftProtocol", buf: Buffer) -> None:
        """Handle Window Items packet (0x11)"""
        try:
            window_id = buf.read_value(StructFormat.UBYTE)
            state_id = buf.read_varint()

            slot_count = buf.read_varint()
            for slot_idx in range(slot_count):
                try:
                    item = self._parse_slot(buf)
                    item.slot = slot_idx
                    if window_id == 0:
                        self.inventory[slot_idx] = item
                except Exception as e:
                    # Skip malformed slots
                    pass

            # Read cursor item
            try:
                cursor = self._parse_slot(buf)
                self._cursor_item = cursor if not cursor.is_empty else None
            except:
                pass

            self.emit("inventory_update", window_id)
        except Exception as e:
            print(f"[INVENTORY] Error parsing window items: {e}")

    # === Entity handlers ===

    async def _handle_spawn_entity(self: "MinecraftProtocol", buf: Buffer) -> None:
        """Handle Spawn Entity packet (0x01)"""
        entity_id = buf.read_varint()
        uuid_bytes = buf.read(16)
        entity_type_id = buf.read_varint()

        x = buf.read_value(StructFormat.DOUBLE)
        y = buf.read_value(StructFormat.DOUBLE)
        z = buf.read_value(StructFormat.DOUBLE)

        pitch = buf.read_value(StructFormat.BYTE)
        yaw = buf.read_value(StructFormat.BYTE)
        head_yaw = buf.read_value(StructFormat.BYTE)

        data = buf.read_varint()
        vx = buf.read_value(StructFormat.SHORT)
        vy = buf.read_value(StructFormat.SHORT)
        vz = buf.read_value(StructFormat.SHORT)

        # Create entity - use position tuple, not x/y/z
        # EntityType is a string enum, so use OTHER for now
        entity = Entity(
            entity_id=entity_id,
            entity_type=EntityType.OTHER,
            position=(x, y, z),
            yaw=yaw * (360 / 256),
            pitch=pitch * (360 / 256),
            head_yaw=head_yaw * (360 / 256),
            velocity=(vx / 8000.0, vy / 8000.0, vz / 8000.0),
            object_type=entity_type_id,  # Store the numeric type ID
        )

        self.entities[entity_id] = entity
        self.entity_manager.add(entity)

        self.emit("entity_spawn", entity)

    async def _handle_entity_destroy(self: "MinecraftProtocol", buf: Buffer) -> None:
        """Handle Entity Destroy packet (0x03)"""
        count = buf.read_varint()
        for _ in range(count):
            entity_id = buf.read_varint()
            if entity_id in self.entities:
                entity = self.entities[entity_id]
                del self.entities[entity_id]
                self.entity_manager.remove(entity_id)
                self.emit("entity_gone", entity)

    async def _handle_entity_metadata(self: "MinecraftProtocol", buf: Buffer) -> None:
        """Handle Set Entity Metadata packet (0x1F)"""
        entity_id = buf.read_varint()

        if entity_id not in self.entities:
            return

        entity = self.entities[entity_id]

        # Read metadata entries
        while True:
            index = buf.read_value(StructFormat.UBYTE)
            if index == 0xFF:  # End of metadata
                break

            type_id = buf.read_varint()
            value = self._parse_metadata_value(buf, type_id)

            if hasattr(entity, "metadata"):
                entity.metadata[index] = value

        self.emit("entity_metadata", entity)

    async def _handle_merchant_offers(self: "MinecraftProtocol", buf: Buffer) -> None:
        """Handle Merchant Offers packet (0x24) - villager trades"""
        try:
            window_id = buf.read_varint()
            size = buf.read_varint()
            trades = []

            for _ in range(size):
                try:
                    trade = self._parse_merchant_offer(buf)
                    trades.append(trade)
                except Exception as e:
                    print(f"[VILLAGER] Error parsing trade: {e}")
                    continue

            print(f"[VILLAGER] Received {len(trades)} trades for window {window_id}")

            # Forward to villager manager if available
            if hasattr(self, '_villager_mgr'):
                self._villager_mgr.handle_merchant_offers(window_id, trades)

            # Emit event for backward compatibility
            self.emit("merchant_offers", window_id, trades)

        except Exception as e:
            print(f"[VILLAGER] Error parsing merchant offers: {e}")

    def _parse_merchant_offer(self, buf: Buffer) -> Any:
        """Parse a single merchant offer from buffer"""
        try:
            from ..villager import Trade

            # Parse input item 1
            input1 = self._parse_slot(buf)

            # Parse output item
            output = self._parse_slot(buf)

            # Check if there's a second input item
            has_item2 = buf.read_value(StructFormat.BOOL)
            input2 = None
            if has_item2:
                input2 = self._parse_slot(buf)

            # Check if trade is disabled
            trade_disabled = buf.read_value(StructFormat.BOOL)

            # Trade usage counts
            nb_trade_uses = buf.read_varint()
            maximum_nb_trade_uses = buf.read_varint()

            # Optional price modifiers (may not be present)
            try:
                buf.mark()
                special_price = buf.read_varint()
                price_multiplier = buf.read_value(StructFormat.FLOAT)
                buf.unmark()
            except:
                # These fields might not be present in all versions
                buf.reset()
                special_price = 0
                price_multiplier = 0.0

            demand = 0

            # Calculate real price based on demand and special price
            if input1 and not input1.is_empty:
                real_price = input1.item_count
                if special_price != 0 or demand != 0:
                    demand_diff = max(0, int(input1.item_count * demand * price_multiplier))
                    real_price = max(min(input1.item_count + special_price + demand_diff, input1.item_stack_size), 1)
            else:
                real_price = 0

            trade = Trade(
                input_item1=input1 if not input1.is_empty else None,
                input_item2=input2 if input2 and not input2.is_empty else None,
                output_item=output if not output.is_empty else None,
                has_item2=has_item2 and input2 and not input2.is_empty,
                trade_disabled=trade_disabled,
                nb_trade_uses=nb_trade_uses,
                maximum_nb_trade_uses=maximum_nb_trade_uses,
                real_price=real_price,
                demand=demand,
                special_price=special_price,
                price_multiplier=price_multiplier,
            )

            return trade

        except Exception as e:
            print(f"[VILLAGER] Error parsing trade: {e}")
            # Return a default trade to avoid breaking the whole list
            return Trade()
        self.emit("entity_metadata", entity)


__all__ = ["PlayHandler"]
