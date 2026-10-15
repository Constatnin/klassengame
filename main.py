import ipaddress
import math
import json
import queue
import random
import socket
import sys
import threading
import time

import pygame


SCREEN_W, SCREEN_H = 960, 680
WORLD_W, WORLD_H = 2200, 1600
LAN_PORT = 50505
MAX_PLAYERS = 5
MAX_CLIENTS = MAX_PLAYERS - 1
PLAYER_SPEED = 270
BOT_COLORS = ((255, 104, 112), (255, 170, 70), (195, 118, 255), (255, 215, 85))
BRAWLERS = (
    {
        "name": "NOVA",
        "color": (68, 181, 239),
        "hp": 100,
        "speed": 270,
        "damage": 24,
        "fire_rate": 0.24,
        "bullet_speed": 660,
        "ammo_capacity": 8,
        "reload_time": 1.1,
        "description": "Ausgewogen - schneller Energieschuss",
        "super_name": "Nova-Impuls",
        "super_description": "Impulswelle: trifft Gegner in der Naehe",
    },
    {
        "name": "VOLT",
        "color": (255, 204, 73),
        "hp": 80,
        "speed": 330,
        "damage": 15,
        "fire_rate": 0.15,
        "bullet_speed": 730,
        "ammo_capacity": 12,
        "reload_time": 1.35,
        "description": "Flink - schnelle Doppelschuesse",
        "super_name": "Blitzsalve",
        "super_description": "Salve: fuenf schnelle Schuesse nach vorn",
    },
    {
        "name": "BRUTUS",
        "color": (238, 105, 127),
        "hp": 145,
        "speed": 215,
        "damage": 38,
        "fire_rate": 0.48,
        "bullet_speed": 540,
        "ammo_capacity": 5,
        "reload_time": 1.6,
        "description": "Tank - langsam, aber maechtig",
        "super_name": "Bodenbrecher",
        "super_description": "Schmetterschlag: hoher Nahbereichsschaden",
    },
    {
        "name": "LYNX",
        "color": (94, 224, 167),
        "hp": 90,
        "speed": 300,
        "damage": 20,
        "fire_rate": 0.22,
        "bullet_speed": 690,
        "ammo_capacity": 7,
        "reload_time": 1.2,
        "description": "Wendig - praezise Energiesalven",
        "super_name": "Phasensprung",
        "super_description": "Sprung: stuerme vor und ramme Gegner",
    },
    {
        "name": "ORBIT",
        "color": (181, 139, 255),
        "hp": 115,
        "speed": 245,
        "damage": 29,
        "fire_rate": 0.36,
        "bullet_speed": 610,
        "ammo_capacity": 6,
        "reload_time": 1.4,
        "description": "Kontrolle - starke Plasmakugeln",
        "super_name": "Gravitationsfeld",
        "super_description": "Sog: zieht nahe Gegner heran und verletzt sie",
    },
)

WALLS = (
    pygame.Rect(270, 200, 250, 56),
    pygame.Rect(720, 180, 60, 250),
    pygame.Rect(1110, 240, 320, 56),
    pygame.Rect(1460, 360, 64, 250),
    pygame.Rect(280, 510, 64, 280),
    pygame.Rect(500, 670, 280, 58),
    pygame.Rect(940, 530, 70, 310),
    pygame.Rect(1190, 700, 310, 58),
    pygame.Rect(610, 980, 290, 58),
    pygame.Rect(1320, 1010, 66, 190),
    pygame.Rect(80, 900, 210, 60),
    pygame.Rect(1560, 770, 170, 60),
    pygame.Rect(1820, 180, 70, 270),
    pygame.Rect(1760, 560, 290, 58),
    pygame.Rect(1900, 880, 70, 290),
    pygame.Rect(1520, 1240, 310, 58),
    pygame.Rect(1050, 1330, 70, 190),
    pygame.Rect(480, 1230, 260, 58),
    pygame.Rect(340, 1080, 64, 190),
    pygame.Rect(780, 360, 250, 52),
)
CRATE_POSITIONS = (
    (650, 410), (1150, 390), (430, 720), (1600, 1000),
    (950, 1040), (1650, 650), (1850, 650), (500, 1380),
)
MAPS = (
    {
        "name": "NEON-ARENA",
        "description": "Offene Wege mit versetzten Deckungen",
        "walls": WALLS,
        "crates": CRATE_POSITIONS,
        "background": (27, 51, 58),
        "grid": (31, 57, 63),
        "wall": (67, 91, 94),
        "wall_edge": (89, 119, 116),
    },
    {
        "name": "KRISTALL-LABOR",
        "description": "Enge Korridore und geschuetzte Seitenwege",
        "walls": (
            pygame.Rect(360, 280, 460, 54), pygame.Rect(1380, 280, 460, 54),
            pygame.Rect(360, 1266, 460, 54), pygame.Rect(1380, 1266, 460, 54),
            pygame.Rect(360, 400, 60, 300), pygame.Rect(1780, 400, 60, 300),
            pygame.Rect(360, 900, 60, 300), pygame.Rect(1780, 900, 60, 300),
            pygame.Rect(700, 570, 260, 54), pygame.Rect(1240, 570, 260, 54),
            pygame.Rect(700, 976, 260, 54), pygame.Rect(1240, 976, 260, 54),
            pygame.Rect(1035, 300, 64, 185), pygame.Rect(1035, 1115, 64, 185),
            pygame.Rect(540, 820, 230, 54), pygame.Rect(1430, 820, 230, 54),
            pygame.Rect(860, 430, 54, 100), pygame.Rect(1286, 1070, 54, 100),
            pygame.Rect(860, 1070, 54, 100), pygame.Rect(1286, 430, 54, 100),
        ),
        "crates": (
            (540, 400), (1660, 400), (540, 1200), (1660, 1200),
            (900, 720), (1300, 720), (900, 880), (1300, 880),
        ),
        "background": (44, 42, 63),
        "grid": (57, 51, 79),
        "wall": (87, 74, 112),
        "wall_edge": (145, 125, 181),
    },
)
CRATE_SIZE = 48
CRATE_HP = 70


def circle_rect_collision(x, y, radius, rect):
    closest_x = max(rect.left, min(x, rect.right))
    closest_y = max(rect.top, min(y, rect.bottom))
    return (x - closest_x) ** 2 + (y - closest_y) ** 2 < radius**2


def move_circle(x, y, dx, dy, radius, obstacles=(), walls=None):
    walls = tuple(WALLS if walls is None else walls) + tuple(obstacles)
    next_x = max(radius, min(WORLD_W - radius, x + dx))
    if not any(circle_rect_collision(next_x, y, radius, wall) for wall in walls):
        x = next_x
    next_y = max(radius, min(WORLD_H - radius, y + dy))
    if not any(circle_rect_collision(x, next_y, radius, wall) for wall in walls):
        y = next_y
    return x, y


def line_hits_wall(start, end, obstacles=(), walls=None):
    walls = tuple(WALLS if walls is None else walls) + tuple(obstacles)
    return any(wall.clipline(start, end) for wall in walls)


class LanConnection:
    def __init__(self):
        self.messages = queue.Queue()
        self.connection = None
        self.listener = None
        self.connections = {}
        self.connection_lock = threading.Lock()
        self.next_peer_id = 1
        self.send_lock = threading.Lock()
        self.closed = False

    def host(self):
        self.listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.listener.bind(("", LAN_PORT))
        self.listener.listen(MAX_CLIENTS)
        self.listener.settimeout(0.5)
        threading.Thread(target=self._accept, daemon=True).start()

    def _accept(self):
        while not self.closed:
            try:
                connection, address = self.listener.accept()
            except socket.timeout:
                continue
            except OSError as error:
                if not self.closed:
                    self.messages.put({"type": "error", "message": str(error)})
                return
            connection.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
            with self.connection_lock:
                if len(self.connections) >= MAX_CLIENTS:
                    peer_id = None
                else:
                    peer_id = f"client_{self.next_peer_id}"
                    self.next_peer_id += 1
                    self.connections[peer_id] = connection
            if peer_id is None:
                self._send_socket(connection, {"type": "error", "message": "Der Host ist bereits voll (maximal 5 Spieler)."})
                connection.close()
                continue
            self.messages.put({"type": "connected", "address": address[0], "peer_id": peer_id})
            threading.Thread(target=self._receive, args=(connection, peer_id), daemon=True).start()

    def join(self, address):
        def connect():
            connection = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            connection.settimeout(6)
            try:
                connection.connect((address, LAN_PORT))
                connection.settimeout(None)
                connection.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
                self.connection = connection
                self.messages.put({"type": "connected", "address": address, "peer_id": None})
                threading.Thread(target=self._receive, args=(connection, None), daemon=True).start()
            except OSError as error:
                connection.close()
                self.messages.put({"type": "error", "message": str(error)})
        threading.Thread(target=connect, daemon=True).start()

    def _receive(self, connection, peer_id):
        buffer = b""
        try:
            while not self.closed:
                data = connection.recv(4096)
                if not data:
                    break
                buffer += data
                while b"\n" in buffer:
                    line, buffer = buffer.split(b"\n", 1)
                    message = json.loads(line.decode("utf-8"))
                    if peer_id is not None:
                        message["peer_id"] = peer_id
                    self.messages.put(message)
        except (OSError, json.JSONDecodeError, UnicodeDecodeError) as error:
            if not self.closed:
                self.messages.put({"type": "error", "message": str(error), "peer_id": peer_id})
        finally:
            if not self.closed:
                self.messages.put({"type": "disconnected", "peer_id": peer_id})
            if peer_id is not None:
                with self.connection_lock:
                    if self.connections.get(peer_id) is connection:
                        self.connections.pop(peer_id, None)

    def _send_socket(self, connection, message, peer_id=None):
        if connection is None:
            return
        payload = (json.dumps(message, separators=(",", ":")) + "\n").encode("utf-8")
        try:
            with self.send_lock:
                connection.sendall(payload)
        except OSError as error:
            if not self.closed:
                self.messages.put({"type": "error", "message": str(error), "peer_id": peer_id})

    def send(self, message, peer_id=None):
        if self.listener is None:
            self._send_socket(self.connection, message)
            return
        if peer_id is None:
            with self.connection_lock:
                connections = list(self.connections.items())
            for connected_peer, connection in connections:
                self._send_socket(connection, message, connected_peer)
            return
        with self.connection_lock:
            connection = self.connections.get(peer_id)
        self._send_socket(connection, message, peer_id)

    def close_peer(self, peer_id):
        with self.connection_lock:
            connection = self.connections.pop(peer_id, None)
        if connection is not None:
            try:
                connection.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass
            connection.close()

    def close(self):
        self.closed = True
        with self.connection_lock:
            connections = list(self.connections.values())
            self.connections.clear()
        for connection in connections + [self.connection, self.listener]:
            if connection is not None:
                try:
                    connection.shutdown(socket.SHUT_RDWR)
                except OSError:
                    pass
                connection.close()


class Brawler:
    def __init__(self):
        pygame.init()
        pygame.display.set_caption("Neon Arena")
        self.window = pygame.display.set_mode((SCREEN_W, SCREEN_H), pygame.RESIZABLE)
        self.screen = pygame.Surface((SCREEN_W, SCREEN_H))
        self.fullscreen = False
        self.windowed_size = (SCREEN_W, SCREEN_H)
        self.clock = pygame.time.Clock()
        self.font = pygame.font.Font(None, 29)
        self.small_font = pygame.font.Font(None, 22)
        self.title_font = pygame.font.Font(None, 62)
        self.selected_brawler = 0
        self.selected_map = 0
        self.animation_time = 0
        self.network = None
        self.network_role = None
        self.network_status = ""
        self.network_error = ""
        self.ip_address = "127.0.0.1"
        self.editing_ip = False
        self.ip_input_selected = False
        self.last_network_send = 0
        self.remote_input = {}
        self.remote_dash_cooldown = 0
        self.remote_players = {}
        self.client_id = None
        self.winner_id = None
        self.player = None
        self.powerup_spawn_timer = 0
        self.arena_event = None
        self.arena_event_timer = 0
        self.damage_flash = 0
        self.screen_shake = 0
        self.reset()

    def stop_network(self):
        if self.network is not None:
            self.network.close()
            self.network = None
        self.network_role = None
        self.network_status = ""
        self.network_error = ""
        self.remote_input = {}
        self.remote_players = {}
        self.client_id = None
        self.last_network_send = 0

    @property
    def map_data(self):
        return MAPS[self.selected_map]

    @property
    def walls(self):
        return self.map_data["walls"]

    def reset(self):
        self.stop_network()
        self.game_state = "menu"
        self.player = None
        self.bots = []
        self.projectiles = []
        self.particles = []
        self.cubes = []
        self.crates = []
        self.powerups = []
        self.kills = 0

    def start_game(self):
        if not 0 <= self.selected_brawler < len(BRAWLERS):
            self.selected_brawler = 0
        if not 0 <= self.selected_map < len(MAPS):
            self.selected_map = 0
        connected_players = {}
        if self.network_role == "host":
            connected_players = {
                player_id: fighter["brawler"]
                for player_id, fighter in self.remote_players.items()
            }
        self.winner_id = None
        self.player = self.make_fighter(self.selected_brawler, "host")
        self.player["x"], self.player["y"] = self.player_spawn(0)
        self.remote_players = {}
        for position, (player_id, brawler_index) in enumerate(connected_players.items(), 1):
            fighter = self.make_fighter(brawler_index, player_id)
            fighter["spawn_slot"] = position
            fighter["x"], fighter["y"] = self.player_spawn(position)
            self.remote_players[player_id] = fighter
        if self.network_role == "client":
            self.player = self.make_fighter(self.selected_brawler, self.client_id or "client")
        self.bots = []
        self.projectiles = []
        self.particles = []
        self.cubes = []
        self.crates = []
        self.powerups = []
        self.kills = 0
        self.spawn_timer = 0
        self.powerup_spawn_timer = 8
        self.arena_event = None
        self.arena_event_timer = 18
        self.damage_flash = 0
        self.screen_shake = 0
        self.game_state = "playing"
        self.state_send_timer = 0
        self.dash_pending = False
        self.super_pending = False
        if self.network_role in (None, "host"):
            self.spawn_crates()
        if self.network_role == "host":
            self.remote_input = {}
            return
        if self.network_role == "client":
            self.remote_input = {}
            return
        self.remote_players = {}
        for _ in range(4):
            self.spawn_bot()

    @staticmethod
    def player_spawn(index):
        center_x, center_y = WORLD_W / 2, WORLD_H / 2
        if index == 0:
            return center_x, center_y
        angle = -math.pi / 2 + (index - 1) * math.tau / MAX_CLIENTS
        return center_x + math.cos(angle) * 300, center_y + math.sin(angle) * 300

    @staticmethod
    def make_fighter(brawler_index, player_id):
        brawler = BRAWLERS[brawler_index]
        return {
            "x": WORLD_W / 2,
            "y": WORLD_H / 2,
            "hp": brawler["hp"],
            "max_hp": brawler["hp"],
            "radius": 19,
            "cooldown": 0,
            "ammo": brawler["ammo_capacity"],
            "reload_timer": 0,
            "shield_timer": 0,
            "rapid_timer": 0,
            "hurt_timer": 0,
            "super": 0,
            "dash_timer": 0,
            "dash_dir": (0, 0),
            "dash_cooldown": 0,
            "move_phase": 0,
            "move_amount": 0,
            "flash": 0,
            "brawler": brawler_index,
            "cubes": 0,
            "kills": 0,
            "color": brawler["color"],
            "player_id": player_id,
            "spawn_slot": 0,
        }

    def start_host(self):
        if self.network is not None:
            self.stop_network()
        connection = LanConnection()
        try:
            connection.host()
        except OSError as error:
            connection.close()
            self.network_error = f"Host konnte nicht gestartet werden: {error}"
            return
        self.network = connection
        self.network_role = "host"
        self.network_status = f"Warte auf Mitspieler auf Port {LAN_PORT} ..."
        self.network_error = ""
        self.game_state = "lobby"

    def start_join(self):
        address = self.ip_address.strip()
        if not address:
            self.network_error = "Bitte die IP-Adresse des Hosts eingeben."
            return
        try:
            parsed_address = ipaddress.ip_address(address)
        except ValueError:
            self.network_error = "Bitte eine gueltige IPv4-Adresse eingeben."
            return
        if parsed_address.version != 4:
            self.network_error = "Der LAN-Host erwartet eine IPv4-Adresse."
            return
        if self.network is not None:
            self.stop_network()
        connection = LanConnection()
        connection.join(address)
        self.network = connection
        self.network_role = "client"
        self.network_status = f"Verbinde mit {address} ..."
        self.game_state = "connecting"
        self.network_error = ""

    def process_network(self):
        connection = self.network
        if connection is None:
            return
        while True:
            try:
                message = connection.messages.get_nowait()
            except queue.Empty:
                break
            kind = message.get("type")
            peer_id = message.get("peer_id")
            if kind == "connected":
                if self.network_role == "client":
                    self.network_status = f"Verbunden mit {message.get('address', 'Host')}"
                    connection.send({
                        "type": "hello",
                        "brawler": self.selected_brawler,
                    })
                else:
                    self.network_status = f"{len(self.remote_players)} von {MAX_CLIENTS} Mitspielern verbunden"
            elif kind == "hello":
                brawler = message.get("brawler")
                if self.network_role != "host" or peer_id is None:
                    continue
                if not isinstance(brawler, int) or not 0 <= brawler < len(BRAWLERS):
                    connection.send({"type": "error", "message": "Ungueltiger Brawler."}, peer_id)
                    connection.close_peer(peer_id)
                    continue
                if peer_id not in self.remote_players:
                    if len(self.remote_players) >= MAX_CLIENTS:
                        connection.send({"type": "error", "message": "Der Host ist bereits voll."}, peer_id)
                        connection.close_peer(peer_id)
                        continue
                    fighter = self.make_fighter(brawler, peer_id)
                    occupied_slots = {
                        existing.get("spawn_slot", 0)
                        for existing in self.remote_players.values()
                    }
                    spawn_slot = next(slot for slot in range(1, MAX_PLAYERS) if slot not in occupied_slots)
                    fighter["spawn_slot"] = spawn_slot
                    fighter["x"], fighter["y"] = self.player_spawn(spawn_slot)
                    self.remote_players[peer_id] = fighter
                    self.remote_input[peer_id] = {}
                    if self.game_state in ("lobby", "won", "lost"):
                        self.start_game()
                    self.network_status = f"{len(self.remote_players)} von {MAX_CLIENTS} Mitspielern verbunden"
                connection.send({
                    "type": "welcome",
                    "client_id": peer_id,
                    "players": len(self.remote_players) + 1,
                }, peer_id)
                self.send_network_state(0, force=True)
            elif kind == "input" and self.network_role == "host":
                if peer_id in self.remote_players:
                    self.remote_input[peer_id] = message
            elif kind == "restart" and self.network_role == "host":
                self.start_game()
            elif kind == "welcome" and self.network_role == "client":
                client_id = message.get("client_id")
                if not isinstance(client_id, str) or not client_id.startswith("client_"):
                    self.handle_network_failure("Ungueltige Spieler-ID vom Host.", connection)
                    break
                self.client_id = client_id
                self.start_game()
                self.network_status = f"Verbunden: {message.get('players', 2)} Spieler"
            elif kind == "state" and self.network_role == "client":
                self.apply_network_state(message)
            elif kind == "error":
                if self.network_role == "host" and peer_id is not None:
                    connection.close_peer(peer_id)
                    self.remote_players.pop(peer_id, None)
                    self.remote_input.pop(peer_id, None)
                    self.network_status = str(message.get("message", "Mitspieler getrennt"))
                    continue
                self.handle_network_failure(
                    f"Netzwerkfehler: {message.get('message', 'Unbekannter Fehler')}",
                    connection,
                )
                break
            elif kind == "disconnected":
                if self.network_role == "host" and peer_id is not None:
                    self.remote_players.pop(peer_id, None)
                    self.remote_input.pop(peer_id, None)
                    self.network_status = f"{len(self.remote_players)} von {MAX_CLIENTS} Mitspielern verbunden"
                    continue
                self.handle_network_failure(
                    "Verbindung zum Mitspieler verloren.",
                    connection,
                )
                break

    def handle_network_failure(self, status, connection):
        connection.close()
        if self.network is connection:
            self.network = None
        self.network_status = status
        self.network_error = status
        if self.game_state in ("connecting", "lobby"):
            self.network_role = None
            self.game_state = "menu"
        elif self.game_state in ("playing", "won", "lost"):
            self.game_state = "disconnected"

    def collect_network_input(self):
        keys = pygame.key.get_pressed()
        mx = float(keys[pygame.K_d] or keys[pygame.K_RIGHT]) - float(keys[pygame.K_a] or keys[pygame.K_LEFT])
        my = float(keys[pygame.K_s] or keys[pygame.K_DOWN]) - float(keys[pygame.K_w] or keys[pygame.K_UP])
        length = math.hypot(mx, my)
        if length:
            mx, my = mx / length, my / length
        return {
            "type": "input",
            "move": [mx, my],
            "aim": list(self.screen_to_world(self.logical_mouse_pos())),
            "fire": bool(pygame.mouse.get_pressed()[0]),
            "dash": self.dash_pending,
            "super": self.super_pending,
        }

    def send_network_input(self, now):
        if self.network_role != "client" or self.network is None or self.game_state != "playing":
            return
        if now - self.last_network_send < 1 / 30:
            return
        self.last_network_send = now
        self.network.send(self.collect_network_input())
        self.dash_pending = False
        self.super_pending = False

    def send_network_state(self, dt, force=False):
        if self.network_role != "host" or self.network is None:
            return
        self.state_send_timer += dt
        if self.state_send_timer < 1 / 20 and not force:
            return
        self.state_send_timer = 0
        state = {
            "type": "state",
            "players": {
                "host": self.serialize_fighter(self.player),
                **{
                    player_id: self.serialize_fighter(fighter)
                    for player_id, fighter in self.remote_players.items()
                },
            },
            "cubes": [[cube["x"], cube["y"], cube["phase"]] for cube in self.cubes],
            "projectiles": [
                [p["x"], p["y"], p["vx"], p["vy"], p["owner"], p["color"]]
                for p in self.projectiles if p["owner"] != "bot"
            ],
            "crates": [
                [crate["x"], crate["y"], crate["hp"], crate["max_hp"]]
                for crate in self.crates
            ],
            "powerups": [
                [item["x"], item["y"], item["type"], item["timer"], item["phase"]]
                for item in self.powerups
            ],
            "arena_event": self.arena_event,
            "kills": self.kills,
            "game_state": self.game_state,
            "winner_id": self.winner_id,
            "map_index": self.selected_map,
        }
        for player_id in self.remote_players:
            self.network.send(state, player_id)

    @staticmethod
    def serialize_fighter(fighter):
        return {
            key: fighter[key]
            for key in ("x", "y", "hp", "max_hp", "super", "brawler", "cubes", "kills", "move_phase", "move_amount", "hurt_timer", "flash", "dash_timer", "ammo", "reload_timer", "shield_timer", "rapid_timer")
        }

    def apply_network_state(self, message):
        map_index = message.get("map_index", 0)
        if not isinstance(map_index, int) or not 0 <= map_index < len(MAPS):
            self.network_error = "Ungueltige Arena in den Spieldaten."
            return
        players = message.get("players")
        if not isinstance(players, dict) or self.client_id not in players or "host" not in players:
            self.network_error = "Ungueltige Spieldaten vom Host empfangen."
            return
        for player_id, state in players.items():
            if not isinstance(state, dict):
                self.network_error = "Ungueltige Spielerdaten vom Host empfangen."
                return
            brawler_index = state.get("brawler")
            if not isinstance(brawler_index, int) or not 0 <= brawler_index < len(BRAWLERS):
                self.network_error = "Ungueltiger Brawler in den Spieldaten."
                return
            if player_id == self.client_id:
                fighter = self.player or self.make_fighter(brawler_index, player_id)
                self.player = fighter
            else:
                fighter = self.remote_players.get(player_id)
                if fighter is None:
                    fighter = self.make_fighter(brawler_index, player_id)
                    self.remote_players[player_id] = fighter
            previous_hp = fighter["hp"]
            fighter.update(state)
            fighter["color"] = BRAWLERS[brawler_index]["color"]
            if player_id == self.client_id and fighter["hp"] < previous_hp:
                self.trigger_damage_feedback()
        self.remote_players = {
            player_id: fighter
            for player_id, fighter in self.remote_players.items()
            if player_id in players and player_id != self.client_id
        }
        self.network_error = ""
        self.selected_map = map_index
        self.cubes = [
            {"x": item[0], "y": item[1], "phase": item[2], "pickup": 0}
            for item in message.get("cubes", [])
            if isinstance(item, list) and len(item) == 3
        ]
        self.crates = [
            {"x": item[0], "y": item[1], "hp": item[2], "max_hp": item[3]}
            for item in message.get("crates", [])
            if isinstance(item, list) and len(item) == 4
        ]
        self.powerups = [
            {"x": item[0], "y": item[1], "type": item[2], "timer": item[3], "phase": item[4]}
            for item in message.get("powerups", [])
            if isinstance(item, list) and len(item) == 5
            and item[2] in ("heal", "shield", "rapid")
        ]
        event = message.get("arena_event")
        self.arena_event = event if isinstance(event, dict) else None
        self.projectiles = [
            {
                "x": item[0], "y": item[1], "vx": item[2], "vy": item[3],
                "owner": item[4], "color": tuple(item[5]), "radius": 6,
                "trail": [], "damage": 0, "life": 1,
            }
            for item in message.get("projectiles", [])
            if isinstance(item, list) and len(item) == 6
        ]
        self.kills = self.player.get("kills", 0)
        self.winner_id = message.get("winner_id")
        if message.get("game_state") == "playing":
            self.game_state = "playing"
        else:
            self.game_state = "won" if self.winner_id == self.client_id else "lost"

    def spawn_bot(self):
        for _ in range(50):
            x = random.randint(65, WORLD_W - 65)
            y = random.randint(65, WORLD_H - 65)
            if math.hypot(x - self.player["x"], y - self.player["y"]) > 370 and not any(
                circle_rect_collision(x, y, 22, wall)
                for wall in self.walls + self.crate_obstacles()
            ):
                max_hp = random.choice((62, 76, 90))
                brawler_index = random.randrange(len(BRAWLERS))
                self.bots.append({
                    "x": float(x),
                    "y": float(y),
                    "hp": max_hp,
                    "max_hp": max_hp,
                    "radius": 17,
                    "color": random.choice(BOT_COLORS),
                    "brawler": brawler_index,
                    "ammo": BRAWLERS[brawler_index]["ammo_capacity"],
                    "reload_timer": 0,
                    "cooldown": random.uniform(0.5, 1.5),
                    "hurt_timer": 0,
                    "phase": random.random() * math.tau,
                    "move_amount": 0,
                })
                return

    def player_screen_pos(self):
        camera_x = max(0, min(WORLD_W - SCREEN_W, self.player["x"] - SCREEN_W / 2))
        camera_y = max(0, min(WORLD_H - SCREEN_H, self.player["y"] - SCREEN_H / 2))
        return camera_x, camera_y

    def logical_mouse_pos(self, position=None):
        if position is None:
            position = pygame.mouse.get_pos()
        window_width, window_height = self.window.get_size()
        scale = min(window_width / SCREEN_W, window_height / SCREEN_H)
        rendered_width, rendered_height = int(SCREEN_W * scale), int(SCREEN_H * scale)
        offset_x = (window_width - rendered_width) // 2
        offset_y = (window_height - rendered_height) // 2
        x = (position[0] - offset_x) / max(scale, 0.001)
        y = (position[1] - offset_y) / max(scale, 0.001)
        return max(0, min(SCREEN_W - 1, int(x))), max(0, min(SCREEN_H - 1, int(y)))

    def toggle_fullscreen(self):
        self.fullscreen = not self.fullscreen
        if self.fullscreen:
            self.windowed_size = self.window.get_size()
            self.window = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
        else:
            width = max(SCREEN_W, self.windowed_size[0])
            height = max(SCREEN_H, self.windowed_size[1])
            self.window = pygame.display.set_mode((width, height), pygame.RESIZABLE)

    def resize_window(self, width, height):
        if self.fullscreen:
            return
        self.windowed_size = (max(640, width), max(480, height))
        self.window = pygame.display.set_mode(self.windowed_size, pygame.RESIZABLE)

    def present(self):
        window_width, window_height = self.window.get_size()
        scale = min(window_width / SCREEN_W, window_height / SCREEN_H)
        rendered_size = (max(1, int(SCREEN_W * scale)), max(1, int(SCREEN_H * scale)))
        rendered = pygame.transform.smoothscale(self.screen, rendered_size)
        self.window.fill((5, 10, 16))
        self.window.blit(rendered, rendered.get_rect(center=self.window.get_rect().center))
        pygame.display.flip()

    def screen_to_world(self, pos):
        camera_x, camera_y = self.player_screen_pos()
        return pos[0] + camera_x, pos[1] + camera_y

    def shoot(self, source, target, owner, speed, damage, color):
        dx, dy = target[0] - source["x"], target[1] - source["y"]
        length = math.hypot(dx, dy)
        if length == 0:
            return
        dx, dy = dx / length, dy / length
        source["flash"] = 0.09
        self.projectiles.append({
            "x": source["x"] + dx * (source["radius"] + 6),
            "y": source["y"] + dy * (source["radius"] + 6),
            "vx": dx * speed,
            "vy": dy * speed,
            "owner": owner,
            "damage": damage,
            "color": color,
            "life": 1.5,
            "radius": 6 if owner == "player" else 5,
            "trail": [],
        })

    @staticmethod
    def crate_rect(crate):
        half_size = CRATE_SIZE // 2
        return pygame.Rect(
            round(crate["x"] - half_size),
            round(crate["y"] - half_size),
            CRATE_SIZE,
            CRATE_SIZE,
        )

    def crate_obstacles(self):
        return tuple(self.crate_rect(crate) for crate in self.crates)

    def spawn_crates(self):
        self.crates = [
            {"x": x, "y": y, "hp": CRATE_HP, "max_hp": CRATE_HP}
            for x, y in self.map_data["crates"]
        ]

    def spawn_powerup(self):
        occupied = self.crate_obstacles()
        fighters = [self.player, *self.remote_players.values()]
        for _ in range(80):
            x = random.randint(80, WORLD_W - 80)
            y = random.randint(80, WORLD_H - 80)
            if any(circle_rect_collision(x, y, 24, wall) for wall in self.walls + occupied):
                continue
            if any(
                fighter and fighter["hp"] > 0
                and math.hypot(x - fighter["x"], y - fighter["y"]) < 100
                for fighter in fighters
            ):
                continue
            if any(math.hypot(x - item["x"], y - item["y"]) < 70 for item in self.powerups):
                continue
            powerup_type = random.choices(
                ("heal", "shield", "rapid"), weights=(4, 3, 3), k=1
            )[0]
            self.powerups.append({
                "x": float(x),
                "y": float(y),
                "type": powerup_type,
                "timer": 18,
                "phase": random.random() * math.tau,
            })
            self.add_burst_particles(x, y, count=12, colors=((126, 230, 255), (255, 240, 130)))
            return

    def collect_powerups(self, fighter):
        if fighter["hp"] <= 0:
            return
        for powerup in self.powerups[:]:
            if math.hypot(powerup["x"] - fighter["x"], powerup["y"] - fighter["y"]) > fighter["radius"] + 22:
                continue
            self.powerups.remove(powerup)
            if powerup["type"] == "heal":
                fighter["hp"] = min(fighter["max_hp"], fighter["hp"] + 35)
                color = (105, 255, 151)
            elif powerup["type"] == "shield":
                fighter["shield_timer"] = max(fighter["shield_timer"], 7)
                color = (103, 204, 255)
            else:
                fighter["rapid_timer"] = max(fighter["rapid_timer"], 8)
                color = (255, 220, 93)
            self.add_burst_particles(powerup["x"], powerup["y"], count=20, colors=(color, (255, 255, 255)))

    def trigger_damage_feedback(self):
        self.damage_flash = max(self.damage_flash, 0.22)
        self.screen_shake = max(self.screen_shake, 0.16)

    @staticmethod
    def take_damage(fighter, damage):
        damage_multiplier = 0.45 if fighter.get("shield_timer", 0) > 0 else 1
        applied_damage = max(1, round(damage * damage_multiplier))
        fighter["hp"] = max(0, fighter["hp"] - applied_damage)
        fighter["hurt_timer"] = 0.55
        fighter["flash"] = 0.18
        return applied_damage

    def update_arena_event(self, dt):
        if self.arena_event is None:
            self.arena_event_timer -= dt
            if self.arena_event_timer <= 0:
                self.arena_event = {
                    "x": random.randint(230, WORLD_W - 230),
                    "y": random.randint(230, WORLD_H - 230),
                    "radius": 190,
                    "phase": "warning",
                    "timer": 3,
                    "damage_timer": 0,
                }
            return

        event = self.arena_event
        event["timer"] -= dt
        if event["phase"] == "warning":
            if event["timer"] <= 0:
                event["phase"] = "active"
                event["timer"] = 7
                event["damage_timer"] = 0
            return

        event["damage_timer"] -= dt
        if event["damage_timer"] <= 0:
            targets = []
            if self.network_role == "host":
                targets.extend((self.player, *self.remote_players.values()))
            else:
                targets.append(self.player)
                targets.extend(self.bots)
            for target in targets:
                if target["hp"] <= 0:
                    continue
                if math.hypot(target["x"] - event["x"], target["y"] - event["y"]) > event["radius"]:
                    continue
                was_alive = target["hp"] > 0
                self.take_damage(target, 16)
                if target is self.player:
                    self.trigger_damage_feedback()
                    if target["hp"] == 0 and self.network_role is None:
                        self.game_state = "lost"
                elif self.network_role is None and target in self.bots and was_alive and target["hp"] == 0:
                    self.defeat_bot(target)
            event["damage_timer"] = 1.2
            self.check_match_winner()
        if event["timer"] <= 0:
            self.arena_event = None
            self.arena_event_timer = 22

    @staticmethod
    def update_ammo(fighter, dt):
        if fighter["ammo"] == 0 and fighter["reload_timer"] > 0:
            fighter["reload_timer"] = max(0, fighter["reload_timer"] - dt)
            if fighter["reload_timer"] == 0:
                fighter["ammo"] = BRAWLERS[fighter["brawler"]]["ammo_capacity"]

    @staticmethod
    def consume_ammo(fighter, amount=1):
        if fighter["ammo"] < amount:
            return False
        fighter["ammo"] -= amount
        if fighter["ammo"] == 0:
            fighter["reload_timer"] = BRAWLERS[fighter["brawler"]]["reload_time"]
        return True

    def spawn_cube(self, x, y):
        self.cubes.append({
            "x": float(x),
            "y": float(y),
            "phase": random.random() * math.tau,
            "pickup": 0,
        })
        self.add_burst_particles(x, y, count=10, colors=((104, 255, 159), (230, 255, 120)))

    def add_burst_particles(self, x, y, count=28, colors=None):
        colors = colors or ((100, 225, 255), (255, 240, 130), (255, 255, 255))
        for _ in range(count):
            angle = random.random() * math.tau
            speed = random.uniform(90, 300)
            self.particles.append({
                "x": x,
                "y": y,
                "vx": math.cos(angle) * speed,
                "vy": math.sin(angle) * speed,
                "life": random.uniform(0.25, 0.55),
                "max_life": 0.55,
                "color": random.choice(colors),
            })

    def burst(self):
        if self.player is None:
            return
        self.activate_super(
            "host" if self.network_role == "host" else "player",
            self.player,
            self.screen_to_world(self.logical_mouse_pos()),
        )

    def activate_super(self, attacker_id, attacker, aim):
        if attacker["hp"] <= 0 or attacker["super"] < 100:
            return
        attacker["super"] = 0
        brawler_index = attacker["brawler"]
        if brawler_index == 1:
            stats = BRAWLERS[brawler_index]
            base_angle = math.atan2(aim[1] - attacker["y"], aim[0] - attacker["x"])
            for offset in (-0.28, -0.14, 0, 0.14, 0.28):
                target = (
                    attacker["x"] + math.cos(base_angle + offset) * 500,
                    attacker["y"] + math.sin(base_angle + offset) * 500,
                )
                self.shoot(
                    attacker, target, attacker_id,
                    stats["bullet_speed"] * 1.3,
                    stats["damage"] * 1.5,
                    stats["color"],
                )
        elif brawler_index == 3:
            self.activate_lynx_dash(attacker_id, attacker, aim)
        else:
            radius, damage, movement = {
                0: (190, 38, 45),
                2: (240, 55, 78),
                4: (350, 28, -100),
            }[brawler_index]
            self.apply_area_super(attacker_id, attacker, radius, damage, movement)
        self.add_burst_particles(attacker["x"], attacker["y"])
        self.check_match_winner()
        self.send_network_state(0, force=True)

    def apply_area_super(self, attacker_id, attacker, radius, damage, movement):
        targets = [
            (f"bot_{index}", bot)
            for index, bot in enumerate(self.bots)
        ]
        if self.network_role == "host":
            targets.extend(
                (player_id, fighter)
                for player_id, fighter in (("host", self.player), *self.remote_players.items())
            )
        defeated_bots = []
        for target_id, target in targets:
            if target_id == attacker_id or target["hp"] <= 0:
                continue
            dx, dy = target["x"] - attacker["x"], target["y"] - attacker["y"]
            distance = math.hypot(dx, dy)
            if distance > radius or line_hits_wall(
                (int(attacker["x"]), int(attacker["y"])),
                (int(target["x"]), int(target["y"])),
                self.crate_obstacles(),
                self.walls,
            ):
                continue
            target["hp"] = max(0, target["hp"] - damage)
            target["hurt_timer"] = 0.25
            target["flash"] = 0.2
            if distance:
                movement_amount = movement
                if movement < 0:
                    movement_amount = -min(
                        -movement,
                        max(0, distance - attacker["radius"] - target["radius"]),
                    )
                target["x"], target["y"] = move_circle(
                    target["x"], target["y"],
                    dx / distance * movement_amount,
                    dy / distance * movement_amount,
                    target["radius"],
                    self.crate_obstacles(),
                    self.walls,
                )
            if target["hp"] == 0:
                if target_id.startswith("bot_"):
                    defeated_bots.append(target)
                else:
                    attacker["kills"] += 1
        for bot in defeated_bots:
            self.defeat_bot(bot)

    def activate_lynx_dash(self, attacker_id, attacker, aim):
        dx, dy = aim[0] - attacker["x"], aim[1] - attacker["y"]
        distance = max(1, math.hypot(dx, dy))
        dx, dy = dx / distance, dy / distance
        start = (attacker["x"], attacker["y"])
        attacker["x"], attacker["y"] = move_circle(
            attacker["x"], attacker["y"], dx * 300, dy * 300,
            attacker["radius"], self.crate_obstacles(), self.walls,
        )
        attacker["dash_timer"] = 0.16
        attacker["dash_dir"] = (dx, dy)
        attacker["dash_cooldown"] = 1.2
        end = (attacker["x"], attacker["y"])
        defeated_bots = []
        for bot in self.bots:
            if math.hypot(bot["x"] - attacker["x"], bot["y"] - attacker["y"]) <= 78:
                bot["hp"] = max(0, bot["hp"] - 42)
                bot["hurt_timer"] = 0.25
                if bot["hp"] == 0:
                    defeated_bots.append(bot)
        if self.network_role == "host":
            for target_id, target in (("host", self.player), *self.remote_players.items()):
                if target_id == attacker_id or target["hp"] <= 0:
                    continue
                if math.hypot(target["x"] - attacker["x"], target["y"] - attacker["y"]) <= 78:
                    target["hp"] = max(0, target["hp"] - 42)
                    target["hurt_timer"] = 0.25
                    target["flash"] = 0.2
                    if target["hp"] == 0:
                        attacker["kills"] += 1
        for bot in defeated_bots:
            self.defeat_bot(bot)
        self.add_burst_particles(*start, count=12, colors=(BRAWLERS[3]["color"], (255, 255, 255)))
        self.add_burst_particles(*end, count=20, colors=(BRAWLERS[3]["color"], (255, 255, 255)))

    def defeat_bot(self, bot):
        if bot not in self.bots:
            return
        self.bots.remove(bot)
        self.kills += 1
        self.spawn_cube(bot["x"], bot["y"])
        self.add_burst_particles(
            bot["x"], bot["y"], count=20, colors=(bot["color"], (255, 255, 255))
        )
        self.player["hp"] = min(
            self.player["max_hp"], self.player["hp"] + 8
        )
        if self.kills >= 10:
            self.game_state = "won"

    def update(self, dt):
        self.animation_time += dt
        self.damage_flash = max(0, self.damage_flash - dt)
        self.screen_shake = max(0, self.screen_shake - dt)
        if self.game_state != "playing":
            return
        if self.network_role == "client":
            return
        player = self.player
        obstacles = self.crate_obstacles()
        self.update_ammo(player, dt)
        player["shield_timer"] = max(0, player["shield_timer"] - dt)
        player["rapid_timer"] = max(0, player["rapid_timer"] - dt)
        player["cooldown"] = max(0, player["cooldown"] - dt)
        player["hurt_timer"] = max(0, player["hurt_timer"] - dt)
        player["dash_timer"] = max(0, player["dash_timer"] - dt)
        player["dash_cooldown"] = max(0, player["dash_cooldown"] - dt)
        player["flash"] = max(0, player["flash"] - dt)

        keys = pygame.key.get_pressed()
        mx = float(keys[pygame.K_d] or keys[pygame.K_RIGHT]) - float(keys[pygame.K_a] or keys[pygame.K_LEFT])
        my = float(keys[pygame.K_s] or keys[pygame.K_DOWN]) - float(keys[pygame.K_w] or keys[pygame.K_UP])
        magnitude = math.hypot(mx, my)
        if player["hp"] <= 0:
            mx, my, magnitude = 0, 0, 0
            player["dash_timer"] = 0
        player["move_amount"] = min(1, magnitude)
        player["move_phase"] += dt * (13 if magnitude else 3)
        if magnitude:
            mx, my = mx / magnitude, my / magnitude

        if player["dash_timer"] > 0:
            dx, dy = player["dash_dir"]
            player["x"], player["y"] = move_circle(
                player["x"], player["y"], dx * 700 * dt, dy * 700 * dt,
                player["radius"], obstacles, self.walls,
            )
        else:
            player["x"], player["y"] = move_circle(
                player["x"], player["y"],
                mx * (BRAWLERS[player["brawler"]]["speed"] + player["cubes"] * 2) * dt,
                my * (BRAWLERS[player["brawler"]]["speed"] + player["cubes"] * 2) * dt,
                player["radius"], obstacles, self.walls,
            )

        brawler = BRAWLERS[player["brawler"]]
        ammo_cost = 2 if player["brawler"] == 1 else 1
        if (
            player["hp"] > 0 and pygame.mouse.get_pressed()[0]
            and player["cooldown"] <= 0 and player["ammo"] >= ammo_cost
        ):
            target = self.screen_to_world(self.logical_mouse_pos())
            damage = brawler["damage"] * (1 + player["cubes"] * 0.08)
            owner = "host" if self.network_role == "host" else "player"
            self.shoot(player, target, owner, brawler["bullet_speed"], damage, brawler["color"])
            if player["brawler"] == 1:
                dx, dy = target[0] - player["x"], target[1] - player["y"]
                length = max(1, math.hypot(dx, dy))
                offset = 9
                side_target = (
                    target[0] - dy / length * offset,
                    target[1] + dx / length * offset,
                )
                self.shoot(player, side_target, owner, brawler["bullet_speed"], damage, brawler["color"])
            self.consume_ammo(player, ammo_cost)
            fire_rate = brawler["fire_rate"] * (0.62 if player["rapid_timer"] > 0 else 1)
            player["cooldown"] = fire_rate

        if self.network_role == "host":
            for player_id, fighter in list(self.remote_players.items()):
                self.update_remote_player(player_id, fighter, self.remote_input.get(player_id, {}), dt)
                fighter["shield_timer"] = max(0, fighter["shield_timer"] - dt)
                fighter["rapid_timer"] = max(0, fighter["rapid_timer"] - dt)

        for bot in self.bots:
            self.update_ammo(bot, dt)
            bot["shield_timer"] = max(0, bot.get("shield_timer", 0) - dt)
            bot["rapid_timer"] = max(0, bot.get("rapid_timer", 0) - dt)
            bot["cooldown"] = max(0, bot["cooldown"] - dt)
            bot["hurt_timer"] = max(0, bot["hurt_timer"] - dt)
            bot["flash"] = max(0, bot.get("flash", 0) - dt)
            dx, dy = player["x"] - bot["x"], player["y"] - bot["y"]
            distance = max(1, math.hypot(dx, dy))
            direction_x, direction_y = dx / distance, dy / distance
            bot["phase"] += dt * 1.7
            strafe = math.sin(bot["phase"]) * 0.34
            if distance > 270:
                vx = direction_x + -direction_y * strafe
                vy = direction_y + direction_x * strafe
            elif distance < 170:
                vx = -direction_x + -direction_y * strafe
                vy = -direction_y + direction_x * strafe
            else:
                vx, vy = -direction_y * strafe, direction_x * strafe
            length = max(1, math.hypot(vx, vy))
            bot["x"], bot["y"] = move_circle(
                bot["x"], bot["y"], vx / length * 105 * dt,
                vy / length * 105 * dt, bot["radius"], obstacles, self.walls,
            )
            bot["move_amount"] = min(1, abs(vx) + abs(vy))
            if bot["cooldown"] <= 0 and distance < 540 and not line_hits_wall(
                (int(bot["x"]), int(bot["y"])),
                (int(player["x"]), int(player["y"])),
                obstacles,
                self.walls,
            ) and bot["ammo"] > 0:
                self.shoot(bot, (player["x"], player["y"]), "bot", 380, 12, (255, 115, 125))
                self.consume_ammo(bot)
                bot["cooldown"] = random.uniform(1.05, 1.45)

        for projectile in self.projectiles[:]:
            if self.game_state != "playing":
                break
            projectile["x"] += projectile["vx"] * dt
            projectile["y"] += projectile["vy"] * dt
            projectile["life"] -= dt
            projectile["trail"].append((projectile["x"], projectile["y"]))
            if len(projectile["trail"]) > 5:
                projectile["trail"].pop(0)
            hit_wall = any(wall.collidepoint(projectile["x"], projectile["y"]) for wall in self.walls)
            if (
                projectile["life"] <= 0
                or hit_wall
                or not (0 <= projectile["x"] <= WORLD_W and 0 <= projectile["y"] <= WORLD_H)
            ):
                self.projectiles.remove(projectile)
                continue
            crate = next((
                crate for crate in self.crates
                if self.crate_rect(crate).inflate(
                    projectile["radius"] * 2, projectile["radius"] * 2
                ).collidepoint(projectile["x"], projectile["y"])
            ), None)
            if crate is not None:
                crate["hp"] = max(0, crate["hp"] - projectile["damage"])
                self.add_burst_particles(
                    projectile["x"], projectile["y"], count=5,
                    colors=((194, 124, 67), (255, 208, 123)),
                )
                self.projectiles.remove(projectile)
                if crate["hp"] == 0:
                    self.crates.remove(crate)
                    self.spawn_cube(crate["x"], crate["y"])
                continue
            player_owner = projectile["owner"] in ("player", "host") or projectile["owner"] in self.remote_players
            if projectile["owner"] in ("player", "host") and self.network_role is None:
                target = next((
                    bot for bot in self.bots
                    if math.hypot(projectile["x"] - bot["x"], projectile["y"] - bot["y"])
                    < bot["radius"] + projectile["radius"]
                ), None)
                if target is not None:
                    self.take_damage(target, projectile["damage"])
                    self.add_burst_particles(projectile["x"], projectile["y"], count=5)
                    player["super"] = min(100, player["super"] + 18)
                    self.projectiles.remove(projectile)
                    if target["hp"] <= 0:
                        self.defeat_bot(target)
            elif player_owner and self.network_role == "host":
                attacker = self.player if projectile["owner"] == "host" else self.remote_players[projectile["owner"]]
                target = next((
                    (target_id, fighter)
                    for target_id, fighter in (("host", self.player), *self.remote_players.items())
                    if target_id != projectile["owner"]
                    and fighter["hp"] > 0
                    and math.hypot(projectile["x"] - fighter["x"], projectile["y"] - fighter["y"])
                    < fighter["radius"] + projectile["radius"]
                ), None)
                if target is not None:
                    target_id, fighter = target
                    self.take_damage(fighter, projectile["damage"])
                    if fighter is self.player:
                        self.trigger_damage_feedback()
                    attacker["super"] = min(100, attacker["super"] + 18)
                    if fighter["hp"] <= 0:
                        attacker["kills"] += 1
                    self.add_burst_particles(projectile["x"], projectile["y"], count=7, colors=((255, 108, 122), (255, 230, 230)))
                    self.projectiles.remove(projectile)
            elif projectile["owner"] == "bot" and math.hypot(
                projectile["x"] - player["x"], projectile["y"] - player["y"]
            ) < player["radius"] + projectile["radius"]:
                self.take_damage(player, projectile["damage"])
                self.trigger_damage_feedback()
                self.add_burst_particles(projectile["x"], projectile["y"], count=7, colors=((255, 108, 122), (255, 230, 230)))
                self.projectiles.remove(projectile)
                if player["hp"] <= 0:
                    self.game_state = "lost"
        self.check_match_winner()

        for powerup in self.powerups[:]:
            powerup["timer"] -= dt
            powerup["phase"] += dt * 3
            if powerup["timer"] <= 0:
                self.powerups.remove(powerup)
        if self.network_role in (None, "host"):
            self.powerup_spawn_timer -= dt
            if self.powerup_spawn_timer <= 0 and len(self.powerups) < 3:
                self.spawn_powerup()
                self.powerup_spawn_timer = 13

        for cube in self.cubes[:]:
            cube["phase"] += dt * 3
            cube["pickup"] = max(0, cube["pickup"] - dt)
            if math.hypot(cube["x"] - player["x"], cube["y"] - player["y"]) < player["radius"] + 25:
                self.cubes.remove(cube)
                player["cubes"] += 1
                player["max_hp"] = BRAWLERS[player["brawler"]]["hp"] + player["cubes"] * 10
                player["hp"] = min(player["max_hp"], player["hp"] + 15)
                self.add_burst_particles(cube["x"], cube["y"], count=18)

        self.collect_powerups(player)
        if self.network_role == "host":
            for fighter in self.remote_players.values():
                self.collect_powerups(fighter)

        self.update_arena_event(dt)

        if self.network_role == "host" and self.game_state == "playing":
            for player_id, fighter in (("host", self.player), *self.remote_players.items()):
                if player_id == "host":
                    continue
                for cube in self.cubes[:]:
                    if fighter["hp"] > 0 and math.hypot(cube["x"] - fighter["x"], cube["y"] - fighter["y"]) < fighter["radius"] + 25:
                        self.cubes.remove(cube)
                        fighter["cubes"] += 1
                        fighter["max_hp"] = BRAWLERS[fighter["brawler"]]["hp"] + fighter["cubes"] * 10
                        fighter["hp"] = min(fighter["max_hp"], fighter["hp"] + 15)
                        self.add_burst_particles(cube["x"], cube["y"], count=18)

        if self.network_role is None and len(self.bots) < 4 and self.game_state == "playing":
            self.spawn_timer += dt
            if self.spawn_timer >= 1.5:
                self.spawn_timer = 0
                self.spawn_bot()

        if player["hp"] > 0 and player["hurt_timer"] <= 0 and player["hp"] < player["max_hp"]:
            player["hp"] = min(player["max_hp"], player["hp"] + 5 * dt)
        if self.network_role == "host":
            for fighter in self.remote_players.values():
                if fighter["hp"] > 0 and fighter["hurt_timer"] <= 0 and fighter["hp"] < fighter["max_hp"]:
                    fighter["hp"] = min(fighter["max_hp"], fighter["hp"] + 5 * dt)

        for particle in self.particles[:]:
            particle["x"] += particle["vx"] * dt
            particle["y"] += particle["vy"] * dt
            particle["life"] -= dt
            if particle["life"] <= 0:
                self.particles.remove(particle)
        self.send_network_state(dt, force=self.game_state != "playing")

    def check_match_winner(self):
        if self.network_role != "host" or self.game_state != "playing":
            return
        alive = [
            player_id
            for player_id, fighter in (("host", self.player), *self.remote_players.items())
            if fighter["hp"] > 0
        ]
        if len(alive) <= 1:
            self.winner_id = alive[0] if alive else None
            self.game_state = "won" if self.winner_id == "host" else "lost"

    def update_remote_player(self, player_id, opponent, controls, dt):
        if opponent["hp"] <= 0:
            return
        self.update_ammo(opponent, dt)
        obstacles = self.crate_obstacles()
        opponent["cooldown"] = max(0, opponent["cooldown"] - dt)
        opponent["hurt_timer"] = max(0, opponent["hurt_timer"] - dt)
        opponent["flash"] = max(0, opponent["flash"] - dt)
        opponent["dash_timer"] = max(0, opponent["dash_timer"] - dt)
        opponent["dash_cooldown"] = max(0, opponent["dash_cooldown"] - dt)

        movement = controls.get("move", (0, 0))
        if not isinstance(movement, (tuple, list)) or len(movement) != 2:
            movement = (0, 0)
        try:
            mx, my = max(-1, min(1, float(movement[0]))), max(-1, min(1, float(movement[1])))
        except (TypeError, ValueError):
            mx, my = 0, 0
        length = math.hypot(mx, my)
        if length > 1:
            mx, my = mx / length, my / length
            length = 1
        opponent["move_amount"] = min(1, math.hypot(mx, my))
        opponent["move_phase"] += dt * (13 if opponent["move_amount"] else 3)

        if controls.get("dash") and opponent["dash_cooldown"] <= 0:
            if length:
                direction = (mx / max(length, 1), my / max(length, 1))
            else:
                targets = [
                    fighter for other_id, fighter in (("host", self.player), *self.remote_players.items())
                    if other_id != player_id and fighter["hp"] > 0
                ]
                target = min(targets, key=lambda fighter: math.hypot(fighter["x"] - opponent["x"], fighter["y"] - opponent["y"]), default=self.player)
                direction = (target["x"] - opponent["x"], target["y"] - opponent["y"])
                distance = max(1, math.hypot(*direction))
                direction = (direction[0] / distance, direction[1] / distance)
            opponent["dash_dir"] = direction
            opponent["dash_timer"] = 0.16
            opponent["dash_cooldown"] = 1.2

        if opponent["dash_timer"] > 0:
            dx, dy = opponent["dash_dir"]
            opponent["x"], opponent["y"] = move_circle(
                opponent["x"], opponent["y"], dx * 700 * dt,
                dy * 700 * dt, opponent["radius"], obstacles, self.walls,
            )
        else:
            speed = BRAWLERS[opponent["brawler"]]["speed"] + opponent["cubes"] * 2
            opponent["x"], opponent["y"] = move_circle(
                opponent["x"], opponent["y"], mx * speed * dt,
                my * speed * dt, opponent["radius"], obstacles, self.walls,
            )

        aim = controls.get("aim", [self.player["x"], self.player["y"]])
        if not isinstance(aim, (tuple, list)) or len(aim) != 2:
            aim = [self.player["x"], self.player["y"]]
        try:
            aim = [max(0, min(WORLD_W, float(aim[0]))), max(0, min(WORLD_H, float(aim[1])))]
        except (TypeError, ValueError):
            aim = [self.player["x"], self.player["y"]]
        stats = BRAWLERS[opponent["brawler"]]
        ammo_cost = 2 if opponent["brawler"] == 1 else 1
        if (
            controls.get("fire") and opponent["cooldown"] <= 0
            and opponent["ammo"] >= ammo_cost
        ):
            damage = stats["damage"] * (1 + opponent["cubes"] * 0.08)
            self.shoot(opponent, aim, player_id, stats["bullet_speed"], damage, stats["color"])
            if opponent["brawler"] == 1:
                dx, dy = aim[0] - opponent["x"], aim[1] - opponent["y"]
                length = max(1, math.hypot(dx, dy))
                side_target = (
                    aim[0] - dy / length * 9,
                    aim[1] + dx / length * 9,
                )
                self.shoot(opponent, side_target, player_id, stats["bullet_speed"], damage, stats["color"])
            self.consume_ammo(opponent, ammo_cost)
            opponent["cooldown"] = stats["fire_rate"] * (
                0.62 if opponent["rapid_timer"] > 0 else 1
            )

        if controls.get("super") and opponent["super"] >= 100:
            self.activate_super(player_id, opponent, aim)

    def return_to_menu(self):
        self.stop_network()
        self.player = None
        self.bots = []
        self.projectiles = []
        self.particles = []
        self.cubes = []
        self.crates = []
        self.powerups = []
        self.kills = 0
        self.game_state = "menu"

    def handle_event(self, event):
        if event.type == pygame.QUIT:
            return False
        if event.type == pygame.VIDEORESIZE:
            self.resize_window(event.w, event.h)
            return True
        if event.type == pygame.KEYDOWN and event.key == pygame.K_F11:
            self.toggle_fullscreen()
            return True
        if event.type == pygame.TEXTINPUT and self.game_state == "menu" and self.editing_ip:
            current_address = "" if self.ip_input_selected else self.ip_address
            if len(current_address) + len(event.text) <= 15:
                self.ip_address = current_address + event.text
            self.ip_input_selected = False
            return True
        if event.type == pygame.KEYDOWN:
            if self.game_state == "menu" and self.editing_ip and event.key == pygame.K_ESCAPE:
                self.editing_ip = False
                self.ip_input_selected = False
                pygame.key.stop_text_input()
                return True
            if event.key == pygame.K_ESCAPE:
                if self.game_state == "menu":
                    return False
                self.return_to_menu()
                return True
            if event.key == pygame.K_r and self.game_state == "disconnected":
                self.return_to_menu()
                return True
            if event.key == pygame.K_r and self.game_state in ("won", "lost"):
                if self.network_role == "client" and self.network is not None:
                    self.network.send({"type": "restart"})
                    self.game_state = "connecting"
                    self.network_status = "Warte auf Neustart durch den Host ..."
                elif self.network_role == "host":
                    self.start_game()
                else:
                    self.start_game()
                return True
            if self.game_state == "menu":
                if self.editing_ip and event.key == pygame.K_BACKSPACE:
                    self.ip_address = "" if self.ip_input_selected else self.ip_address[:-1]
                    self.ip_input_selected = False
                elif self.editing_ip and event.key == pygame.K_RETURN:
                    self.editing_ip = False
                    self.ip_input_selected = False
                    pygame.key.stop_text_input()
                elif not self.editing_ip and event.key in (
                    pygame.K_1, pygame.K_2, pygame.K_3, pygame.K_4, pygame.K_5
                ):
                    self.selected_brawler = event.key - pygame.K_1
                elif not self.editing_ip and event.key in (pygame.K_LEFT, pygame.K_a):
                    self.selected_brawler = (self.selected_brawler - 1) % len(BRAWLERS)
                elif not self.editing_ip and event.key in (pygame.K_RIGHT, pygame.K_d):
                    self.selected_brawler = (self.selected_brawler + 1) % len(BRAWLERS)
                elif not self.editing_ip and event.key in (pygame.K_q, pygame.K_e):
                    step = -1 if event.key == pygame.K_q else 1
                    self.selected_map = (self.selected_map + step) % len(MAPS)
                elif not self.editing_ip and event.key in (pygame.K_RETURN, pygame.K_SPACE):
                    self.network_role = None
                    self.start_game()
                return True
            if event.key == pygame.K_SPACE and self.game_state == "playing" and self.player["hp"] > 0:
                if self.network_role == "client":
                    if self.player["super"] >= 100:
                        self.super_pending = True
                    else:
                        self.dash_pending = True
                    return True
                if self.player["super"] >= 100:
                    self.burst()
                else:
                    keys = pygame.key.get_pressed()
                    dx = float(keys[pygame.K_d] or keys[pygame.K_RIGHT]) - float(keys[pygame.K_a] or keys[pygame.K_LEFT])
                    dy = float(keys[pygame.K_s] or keys[pygame.K_DOWN]) - float(keys[pygame.K_w] or keys[pygame.K_UP])
                    length = math.hypot(dx, dy)
                    if length == 0:
                        target = self.screen_to_world(self.logical_mouse_pos())
                        dx, dy = target[0] - self.player["x"], target[1] - self.player["y"]
                        length = max(1, math.hypot(dx, dy))
                    if self.player["dash_cooldown"] <= 0:
                        self.player["dash_dir"] = (dx / length, dy / length)
                        self.player["dash_timer"] = 0.16
                        self.player["dash_cooldown"] = 1.2
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 and self.game_state == "menu":
            mouse_pos = self.logical_mouse_pos(event.pos)
            for index in range(len(BRAWLERS)):
                if self.character_card_rect(index).collidepoint(mouse_pos):
                    self.selected_brawler = index
                    return True
            if self.map_previous_rect().collidepoint(mouse_pos):
                self.selected_map = (self.selected_map - 1) % len(MAPS)
            elif self.map_next_rect().collidepoint(mouse_pos):
                self.selected_map = (self.selected_map + 1) % len(MAPS)
            elif self.host_button_rect().collidepoint(mouse_pos):
                self.editing_ip = False
                self.ip_input_selected = False
                pygame.key.stop_text_input()
                self.start_host()
            elif self.join_button_rect().collidepoint(mouse_pos):
                self.editing_ip = False
                self.ip_input_selected = False
                pygame.key.stop_text_input()
                self.start_join()
            elif self.local_button_rect().collidepoint(mouse_pos):
                self.network_role = None
                self.editing_ip = False
                self.ip_input_selected = False
                pygame.key.stop_text_input()
                self.start_game()
            elif self.ip_field_rect().collidepoint(mouse_pos):
                self.editing_ip = True
                self.ip_input_selected = True
                pygame.key.start_text_input()
            else:
                self.editing_ip = False
                self.ip_input_selected = False
                pygame.key.stop_text_input()
        return True

    @staticmethod
    def local_button_rect():
        return pygame.Rect(75, 535, 250, 54)

    @staticmethod
    def host_button_rect():
        return pygame.Rect(355, 535, 250, 54)

    @staticmethod
    def join_button_rect():
        return pygame.Rect(635, 535, 250, 54)

    @staticmethod
    def ip_field_rect():
        return pygame.Rect(300, 607, 360, 38)

    @staticmethod
    def map_previous_rect():
        return pygame.Rect(350, 204, 46, 38)

    @staticmethod
    def map_next_rect():
        return pygame.Rect(564, 204, 46, 38)

    @staticmethod
    def character_card_rect(index):
        return pygame.Rect(31 + index * 183, 285, 166, 215)

    def draw_bar(self, x, y, width, height, ratio, color, background=(43, 47, 59)):
        pygame.draw.rect(self.screen, background, (x, y, width, height), border_radius=height // 2)
        if ratio > 0:
            pygame.draw.rect(
                self.screen, color,
                (x, y, max(height, int(width * min(1, ratio))), height),
                border_radius=height // 2,
            )

    @staticmethod
    def wrap_text(font, text, max_width, max_lines):
        max_width = max(1, int(max_width))
        max_lines = max(1, int(max_lines))
        lines = []
        current = ""
        for word in str(text).split():
            while word:
                candidate = f"{current} {word}".strip()
                if font.size(candidate)[0] <= max_width:
                    current = candidate
                    break
                if current:
                    lines.append(current)
                    current = ""
                    continue
                if font.size(word[0])[0] > max_width:
                    word = word[1:]
                    continue
                split_at = 1
                while split_at < len(word) and font.size(word[:split_at + 1])[0] <= max_width:
                    split_at += 1
                lines.append(word[:split_at])
                word = word[split_at:]
        if current:
            lines.append(current)
        if len(lines) > max_lines:
            lines = lines[:max_lines]
            last = lines[-1]
            marker = "..."
            while marker and font.size(marker)[0] > max_width:
                marker = marker[:-1]
            while last and font.size(last + marker)[0] > max_width:
                last = last[:-1]
            lines[-1] = last.rstrip() + marker
        return lines

    def draw_text_box(self, text, font, color, rect, max_lines=1, centered=False, line_spacing=0):
        rect = pygame.Rect(rect)
        if rect.width <= 0 or rect.height <= 0:
            return
        line_height = max(1, font.get_linesize() + line_spacing)
        visible_lines = max(1, (rect.height + line_spacing) // line_height)
        lines = self.wrap_text(font, text, rect.width, min(max_lines, visible_lines))
        if not lines:
            return
        previous_clip = self.screen.get_clip()
        self.screen.set_clip(previous_clip.clip(rect))
        row_height = max(1, (rect.height - line_spacing * (len(lines) - 1)) // len(lines))
        line_height = row_height + line_spacing
        total_height = len(lines) * row_height + (len(lines) - 1) * line_spacing
        y = rect.y + max(0, (rect.height - total_height) // 2)
        for line in lines:
            surface = font.render(line, True, color)
            if surface.get_width() > rect.width or surface.get_height() > row_height:
                scale = min(
                    rect.width / surface.get_width(),
                    row_height / surface.get_height(),
                )
                size = (
                    max(1, int(surface.get_width() * scale)),
                    max(1, int(surface.get_height() * scale)),
                )
                surface = pygame.transform.smoothscale(surface, size)
            x = rect.centerx - surface.get_width() // 2 if centered else rect.x
            self.screen.blit(surface, (x, y))
            y += line_height
        self.screen.set_clip(previous_clip)

    def draw_menu(self):
        mouse_x, mouse_y = self.logical_mouse_pos()
        self.screen.fill((10, 18, 28))

        glow = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
        for radius in range(360, 10, -26):
            alpha = max(18, 120 - (360 - radius) * 2)
            pygame.draw.circle(
                glow,
                (30, 97, 150, alpha),
                (SCREEN_W // 2, 220), radius,
            )
        self.screen.blit(glow, (0, 0))

        for y in range(0, SCREEN_H, 52):
            pygame.draw.line(self.screen, self.map_data["grid"], (0, y), (SCREEN_W, y))

        panel = pygame.Surface((SCREEN_W - 110, 635), pygame.SRCALPHA)
        panel.fill((17, 28, 39, 160))
        panel_rect = panel.get_rect(center=(SCREEN_W // 2, SCREEN_H // 2 + 18))
        self.screen.blit(panel, panel_rect)
        pygame.draw.rect(self.screen, (76, 112, 142), panel_rect, 1, border_radius=24)

        self.draw_text_box("NEON BRAWL", self.title_font, (239, 247, 255), (80, 62, 800, 62), centered=True)
        self.draw_text_box(
            "FUENF HELDEN. ZWEI ARENEN. WIE LANGE HAELTST DU DURCH?",
            self.font, (166, 204, 222), (80, 126, 800, 32), centered=True,
        )

        for rect, label in (
            (self.map_previous_rect(), "<"),
            (self.map_next_rect(), ">"),
        ):
            hovered = rect.collidepoint(mouse_x, mouse_y)
            color = (91, 150, 190) if hovered else (59, 97, 126)
            pygame.draw.rect(self.screen, (26, 47, 64), rect, border_radius=10)
            pygame.draw.rect(self.screen, color, rect, 2, border_radius=10)
            self.draw_text_box(label, self.font, (238, 247, 255), rect, centered=True)
        self.draw_text_box(
            self.map_data["name"], self.font, (222, 238, 249),
            (402, 197, 156, 28), centered=True,
        )
        self.draw_text_box(
            self.map_data["description"], self.small_font, (158, 188, 205),
            (270, 240, 420, 26), centered=True,
        )
        self.draw_text_box(
            "ARENA AUSWAEHLEN  (< / > oder Q / E)",
            self.small_font, (145, 173, 190), (300, 174, 360, 22), centered=True,
        )

        for index, brawler in enumerate(BRAWLERS):
            rect = self.character_card_rect(index)
            selected = index == self.selected_brawler
            hovered = rect.collidepoint(mouse_x, mouse_y)
            card_color = (28, 48, 67) if not selected else (39, 66, 88)
            if hovered and not selected:
                card_color = (35, 59, 80)
            pygame.draw.rect(self.screen, card_color, rect, border_radius=22)
            glow_color = brawler["color"] if selected else (72, 94, 118)
            glow_width = 4 if selected else 2
            pygame.draw.rect(self.screen, glow_color, rect, glow_width, border_radius=22)

            cx = rect.centerx
            cy = rect.y + 60 + int(math.sin(self.animation_time * 3 + index) * 5)
            preview = {
                "x": cx, "y": cy, "radius": 25, "brawler": index,
                "color": brawler["color"], "phase": self.animation_time * 3 + index,
                "move_phase": self.animation_time * 3 + index, "move_amount": 0.4,
                "flash": 0, "hurt_timer": 0, "super": 0,
            }
            self.draw_brawler(preview, 0, 0, is_player=True, menu_preview=True)

            self.draw_text_box(
                brawler["name"], self.font, (244, 249, 255),
                (rect.x + 8, rect.y + 102, rect.width - 16, 26), centered=True,
            )
            self.draw_text_box(
                brawler["super_name"], self.small_font, brawler["color"],
                (rect.x + 7, rect.y + 129, rect.width - 14, 22), centered=True,
            )
            self.draw_text_box(
                brawler["super_description"], self.small_font, (180, 205, 220),
                (rect.x + 8, rect.y + 151, rect.width - 16, 36), max_lines=2, centered=True,
            )

            self.draw_text_box("HP", self.small_font, (166, 192, 207), (rect.x + 9, rect.y + 185, 27, 20))
            self.draw_bar(rect.x + 38, rect.y + 191, 116, 8, brawler["hp"] / 145, brawler["color"])
            self.draw_text_box("DMG", self.small_font, (166, 192, 207), (rect.x + 4, rect.y + 203, 34, 12))
            self.draw_bar(rect.x + 38, rect.y + 207, 116, 8, brawler["damage"] / 38, (255, 194, 111))

            number_surface = self.small_font.render(str(index + 1), True, (151, 180, 196))
            self.screen.blit(number_surface, (rect.x + 16, rect.y + 14))

        buttons = (
            (self.local_button_rect(), "SOLO SPIELEN", (76, 190, 149)),
            (self.host_button_rect(), "LAN-MATCH HOSTEN", (97, 164, 233)),
            (self.join_button_rect(), "LAN-MATCH BEITRETEN", (170, 122, 239)),
        )
        for rect, label, color in buttons:
            hovered = rect.collidepoint(mouse_x, mouse_y)
            button_back = tuple(max(0, min(255, c + (20 if hovered else 0))) for c in color)
            pygame.draw.rect(self.screen, (button_back[0] // 3, button_back[1] // 3, button_back[2] // 3), rect.move(0, 6), border_radius=16)
            pygame.draw.rect(self.screen, button_back, rect, border_radius=16)
            if hovered:
                pygame.draw.rect(self.screen, (255, 255, 255), rect, 2, border_radius=16)
            else:
                pygame.draw.rect(self.screen, color, rect, 2, border_radius=16)
            self.draw_text_box(
                label, self.small_font, (241, 247, 254),
                rect.inflate(-10, -8), centered=True,
            )

        field = self.ip_field_rect()
        field_color = (51, 74, 96) if self.editing_ip else (31, 46, 62)
        pygame.draw.rect(self.screen, field_color, field, border_radius=12)
        pygame.draw.rect(self.screen, (110, 156, 192), field, 2, border_radius=12)
        self.draw_text_box(
            "HOST-IP:", self.small_font, (176, 204, 221),
            (field.x - 86, field.y + 4, 78, field.height - 8),
        )
        visible_ip = self.ip_address or "IPv4 des Hosts eingeben"
        ip_surface = self.font.render(visible_ip, True, (238, 246, 252))
        if ip_surface.get_width() > field.width - 26:
            ip_surface = self.small_font.render(visible_ip, True, (238, 246, 252))
        if self.editing_ip and self.ip_input_selected and self.ip_address:
            selection = pygame.Rect(
                field.x + 10, field.y + 5,
                min(ip_surface.get_width() + 6, field.width - 20),
                min(ip_surface.get_height() + 6, field.height - 10),
            )
            pygame.draw.rect(self.screen, (73, 112, 145), selection, border_radius=4)
        self.draw_text_box(
            visible_ip, self.small_font if ip_surface.get_width() > field.width - 26 else self.font,
            (238, 246, 252), field.inflate(-20, -8),
        )
        if self.editing_ip and int(self.animation_time * 2) % 2 == 0:
            cursor_x = min(field.right - 8, field.x + 13 + ip_surface.get_width() + 2)
            pygame.draw.line(self.screen, (242, 247, 255), (cursor_x, field.y + 8), (cursor_x, field.bottom - 8), 2)

        if self.game_state in ("lobby", "connecting"):
            status = self.network_status
            if self.network_role == "host":
                status = f"{self.network_status}  (IP: {self.get_local_ip()})"
            self.draw_text_box(
                status, self.small_font, (255, 219, 138),
                (70, 644, 820, 30), centered=True,
            )
        elif self.network_error:
            self.draw_text_box(
                self.network_error, self.small_font, (255, 135, 143),
                (70, 644, 820, 30), centered=True,
            )
        else:
            self.draw_text_box(
                "WASD: bewegen   Maus: zielen & schiessen   Leertaste: Dash/Super   F11: Vollbild",
                self.small_font, (160, 189, 205),
                (45, 644, 870, 30), centered=True,
            )
        self.present()

    @staticmethod
    def get_local_ip():
        try:
            # A UDP connect selects the active route without sending a packet.
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as route_socket:
                route_socket.connect(("192.0.2.1", 9))
                address = route_socket.getsockname()[0]
                if address and not address.startswith(("127.", "169.254.")):
                    return address
        except OSError:
            pass
        try:
            addresses = socket.getaddrinfo(socket.gethostname(), None, socket.AF_INET)
            for address in addresses:
                ip = address[4][0]
                if not ip.startswith(("127.", "169.254.")):
                    return ip
            return "Keine LAN-IP gefunden"
        except OSError:
            return "IP nicht verfuegbar"

    def draw_brawler(self, entity, camera_x, camera_y, is_player=False, menu_preview=False):
        x, y = entity["x"] - camera_x, entity["y"] - camera_y
        if not (-55 < x < SCREEN_W + 55 and -55 < y < SCREEN_H + 55):
            return
        phase = entity.get("move_phase", entity.get("phase", 0))
        moving = entity.get("move_amount", 0)
        bob = math.sin(phase) * 3 * moving
        sx, sy = int(x), int(y + bob)
        radius = entity["radius"]
        body_color = BRAWLERS[entity["brawler"]]["color"] if is_player else entity["color"]
        if entity.get("hurt_timer", 0) > 0 or entity.get("flash", 0) > 0:
            body_color = (255, 255, 255)

        leg_swing = int(math.sin(phase) * 7 * moving)
        pygame.draw.ellipse(
            self.screen, (12, 25, 33),
            (sx - radius, int(y + radius * 0.55), radius * 2, radius // 2 + 5),
        )
        for side in (-1, 1):
            hip = (sx + side * 7, sy + radius - 3)
            foot = (sx + side * 9 + leg_swing * side, sy + radius + 9)
            pygame.draw.line(self.screen, (29, 44, 57), hip, foot, 8)
            pygame.draw.line(self.screen, body_color, hip, foot, 5)
            pygame.draw.ellipse(
                self.screen, (239, 244, 244),
                (foot[0] - 5, foot[1] - 3, 12, 7),
            )

        if is_player:
            if menu_preview:
                angle = -math.pi / 4
            else:
                aim_x, aim_y = self.logical_mouse_pos()
                angle = math.atan2(aim_y - sy, aim_x - sx)
        else:
            dx, dy = self.player["x"] - entity["x"], self.player["y"] - entity["y"]
            angle = math.atan2(dy, dx)
        direction = (math.cos(angle), math.sin(angle))
        if entity.get("shield_timer", 0) > 0:
            shield_pulse = int(math.sin(self.animation_time * 8) * 2)
            pygame.draw.circle(
                self.screen, (94, 205, 255), (sx, sy),
                radius + 7 + shield_pulse, 2,
            )
        if entity.get("rapid_timer", 0) > 0:
            pygame.draw.circle(self.screen, (255, 220, 95), (sx, sy), radius + 4, 2)
        if is_player and entity.get("dash_timer", 0) > 0:
            dash_radius = radius + int((0.16 - entity["dash_timer"]) * 100)
            pygame.draw.circle(self.screen, (145, 231, 255), (sx, sy), dash_radius, 3)
        if entity.get("super", 0) >= 100:
            pulse = int(math.sin(self.animation_time * 7) * 2)
            pygame.draw.circle(self.screen, (255, 217, 90), (sx, sy), radius + 8 + pulse, 2)

        start = (sx + int(direction[0] * radius * 0.5), sy + int(direction[1] * radius * 0.5))
        end_distance = radius + 13 + (7 if entity.get("flash", 0) > 0 else 0)
        end = (sx + int(direction[0] * end_distance), sy + int(direction[1] * end_distance))
        pygame.draw.line(self.screen, (22, 35, 48), start, end, 13)
        pygame.draw.line(self.screen, (36, 68, 86), start, end, 9)
        pygame.draw.line(self.screen, body_color, start, end, 5)
        if entity.get("flash", 0) > 0:
            pygame.draw.circle(self.screen, (255, 247, 177), end, 9 + int(entity["flash"] * 35))

        kind = entity["brawler"]
        if kind == 0:
            shell = pygame.Rect(sx - radius, sy - radius + 2, radius * 2, radius * 2)
            pygame.draw.rect(self.screen, (19, 35, 54), shell, border_radius=12)
            pygame.draw.rect(self.screen, body_color, shell.inflate(-4, -3), border_radius=10)
            pygame.draw.arc(self.screen, (207, 244, 255), shell.inflate(-8, -8), math.pi, math.tau, 3)
            visor = pygame.Rect(sx - 12, sy - 7, 24, 10)
            pygame.draw.rect(self.screen, (20, 48, 68), visor, border_radius=5)
            pygame.draw.line(self.screen, (207, 250, 255), (sx - 7, sy - 4), (sx + 5, sy - 4), 2)
            pygame.draw.circle(self.screen, (255, 231, 126), (sx + 10, sy + 11), 3)
        elif kind == 1:
            points = [(sx, sy - radius - 3), (sx + radius, sy), (sx, sy + radius + 2), (sx - radius, sy)]
            pygame.draw.polygon(self.screen, (50, 39, 20), [(px, py + 5) for px, py in points])
            pygame.draw.polygon(self.screen, body_color, points)
            pygame.draw.polygon(self.screen, (255, 246, 198), points, 2)
            pygame.draw.polygon(
                self.screen, (255, 240, 180),
                [(sx, sy - radius - 3), (sx + 7, sy - radius + 5), (sx, sy - radius + 11), (sx - 7, sy - radius + 5)],
            )
            pygame.draw.rect(self.screen, (95, 58, 23), (sx - 13, sy - 3, 26, 10), border_radius=5)
            pygame.draw.line(self.screen, (255, 255, 224), (sx - 7, sy + 1), (sx + 7, sy + 1), 2)
        elif kind == 2:
            armor = pygame.Rect(sx - radius - 2, sy - radius, radius * 2 + 4, radius * 2 + 5)
            pygame.draw.rect(self.screen, (47, 38, 51), armor, border_radius=9)
            pygame.draw.rect(self.screen, body_color, armor.inflate(-5, -5), border_radius=7)
            pygame.draw.rect(self.screen, (255, 208, 187), (sx - 11, sy - 6, 22, 12), border_radius=4)
            pygame.draw.line(self.screen, (85, 41, 51), (sx - 6, sy), (sx - 2, sy + 2), 2)
            pygame.draw.line(self.screen, (85, 41, 51), (sx + 2, sy + 2), (sx + 6, sy), 2)
            pygame.draw.circle(self.screen, (255, 223, 112), (sx - radius - 1, sy + 2), 5)
            pygame.draw.circle(self.screen, (255, 223, 112), (sx + radius + 1, sy + 2), 5)
        elif kind == 3:
            pygame.draw.circle(self.screen, (24, 49, 48), (sx, sy), radius + 3)
            pygame.draw.circle(self.screen, body_color, (sx, sy), radius)
            pygame.draw.circle(self.screen, (211, 255, 231), (sx, sy), radius, 2)
            pygame.draw.polygon(self.screen, (230, 255, 242), [
                (sx - 12, sy - 11), (sx - 21, sy - 24), (sx - 5, sy - 17),
            ])
            pygame.draw.polygon(self.screen, (230, 255, 242), [
                (sx + 12, sy - 11), (sx + 21, sy - 24), (sx + 5, sy - 17),
            ])
            pygame.draw.circle(self.screen, (244, 255, 248), (sx, sy + 2), 5)
        else:
            pygame.draw.circle(self.screen, (43, 35, 67), (sx, sy), radius + 4)
            pygame.draw.circle(self.screen, body_color, (sx, sy), radius)
            pygame.draw.circle(self.screen, (236, 222, 255), (sx, sy), radius, 2)
            pygame.draw.circle(self.screen, (247, 242, 255), (sx, sy), 8, 2)
            pygame.draw.ellipse(self.screen, (247, 242, 255), (sx - 20, sy - 7, 40, 14), 2)

        if not menu_preview:
            self.draw_text_box(
                BRAWLERS[entity["brawler"]]["name"], self.small_font, (243, 247, 248),
                (sx - 55, sy - radius - 30, 110, 20), centered=True,
            )

    def draw_power_cube(self, cube, camera_x, camera_y):
        x = int(cube["x"] - camera_x)
        y = int(cube["y"] - camera_y + math.sin(cube["phase"]) * 5)
        if not (-30 < x < SCREEN_W + 30 and -30 < y < SCREEN_H + 30):
            return
        rotation = cube["phase"]
        size = 12
        points = []
        for index in range(4):
            angle = rotation + math.pi / 4 + index * math.pi / 2
            points.append((x + int(math.cos(angle) * size), y + int(math.sin(angle) * size)))
        glow = pygame.Surface((54, 54), pygame.SRCALPHA)
        pygame.draw.circle(glow, (77, 255, 120, 38), (27, 27), 24)
        self.screen.blit(glow, (x - 27, y - 27))
        pygame.draw.circle(self.screen, (57, 155, 83), (x, y), 19)
        pygame.draw.polygon(self.screen, (117, 255, 139), points)
        pygame.draw.polygon(self.screen, (233, 255, 208), points, 2)
        pygame.draw.circle(self.screen, (255, 255, 255), (x - 3, y - 4), 2)

    def draw_powerup(self, powerup, camera_x, camera_y):
        x = int(powerup["x"] - camera_x)
        y = int(powerup["y"] - camera_y + math.sin(powerup["phase"]) * 4)
        if not (-30 < x < SCREEN_W + 30 and -30 < y < SCREEN_H + 30):
            return
        colors = {
            "heal": ((70, 235, 132), "+"),
            "shield": ((83, 190, 255), "S"),
            "rapid": ((255, 205, 74), ">>"),
        }
        color, symbol = colors[powerup["type"]]
        pulse = int(math.sin(powerup["phase"] * 2) * 2)
        pygame.draw.circle(self.screen, (18, 30, 43), (x, y), 17 + pulse)
        pygame.draw.circle(self.screen, color, (x, y), 14 + pulse)
        pygame.draw.circle(self.screen, (238, 250, 255), (x, y), 14 + pulse, 2)
        label = self.small_font.render(symbol, True, (19, 34, 44))
        self.screen.blit(label, label.get_rect(center=(x, y)))

    def draw_arena_event(self, camera_x, camera_y):
        if self.arena_event is None:
            return
        event = self.arena_event
        x, y = int(event["x"] - camera_x), int(event["y"] - camera_y)
        radius = int(event["radius"])
        if event["phase"] == "warning":
            pulse = int(math.sin(self.animation_time * 9) * 8)
            pygame.draw.circle(self.screen, (255, 203, 91), (x, y), radius + pulse, 4)
            label = f"STURMZONE IN {max(1, math.ceil(event['timer']))}s"
            color = (255, 219, 140)
        else:
            diameter = radius * 2
            danger = pygame.Surface((diameter, diameter), pygame.SRCALPHA)
            pygame.draw.circle(danger, (255, 65, 78, 44), (radius, radius), radius)
            self.screen.blit(danger, (x - radius, y - radius))
            pygame.draw.circle(self.screen, (255, 86, 96), (x, y), radius, 4)
            label = "STURMZONE AKTIV - VERLASSE DEN ROTEN BEREICH!"
            color = (255, 125, 132)
        self.draw_text_box(
            label, self.small_font, color,
            (SCREEN_W // 2 - 230, 108, 460, 26), centered=True,
        )

    def draw_crate(self, crate, camera_x, camera_y):
        rect = self.crate_rect(crate).move(-camera_x, -camera_y)
        if not rect.colliderect(self.screen.get_rect()):
            return
        pygame.draw.rect(self.screen, (28, 30, 34), rect.move(0, 5), border_radius=5)
        pygame.draw.rect(self.screen, (112, 69, 43), rect, border_radius=5)
        pygame.draw.rect(self.screen, (183, 119, 69), rect.inflate(-7, -7), border_radius=3)
        pygame.draw.line(self.screen, (111, 65, 42), (rect.left + 8, rect.top + 8), (rect.right - 8, rect.bottom - 8), 5)
        pygame.draw.line(self.screen, (111, 65, 42), (rect.right - 8, rect.top + 8), (rect.left + 8, rect.bottom - 8), 5)
        pygame.draw.rect(self.screen, (221, 167, 103), rect, width=3, border_radius=5)
        if crate["hp"] < crate["max_hp"]:
            self.draw_bar(
                rect.x, rect.y - 9, rect.width, 5,
                crate["hp"] / crate["max_hp"], (255, 185, 94),
            )

    def draw(self):
        if self.game_state in ("menu", "lobby", "connecting"):
            self.draw_menu()
            return
        camera_x, camera_y = self.player_screen_pos()
        if self.screen_shake > 0:
            shake = max(1, int(self.screen_shake * 24))
            camera_x += random.randint(-shake, shake)
            camera_y += random.randint(-shake, shake)
        self.screen.fill(self.map_data["background"])
        grid = 48
        for x in range(-int(camera_x) % grid, SCREEN_W, grid):
            pygame.draw.line(self.screen, self.map_data["grid"], (x, 0), (x, SCREEN_H))
        for y in range(-int(camera_y) % grid, SCREEN_H, grid):
            pygame.draw.line(self.screen, self.map_data["grid"], (0, y), (SCREEN_W, y))

        for index in range(32):
            world_x = (index * 263 + 117) % WORLD_W
            world_y = (index * 397 + 83) % WORLD_H
            sx, sy = int(world_x - camera_x), int(world_y - camera_y)
            if 0 <= sx < SCREEN_W and 0 <= sy < SCREEN_H:
                pygame.draw.circle(self.screen, (43, 78, 71), (sx, sy), 4)
                pygame.draw.circle(self.screen, (58, 104, 84), (sx - 3, sy - 2), 2)

        for wall in self.walls:
            rect = pygame.Rect(wall.x - camera_x, wall.y - camera_y, wall.width, wall.height)
            if rect.colliderect(self.screen.get_rect()):
                pygame.draw.rect(self.screen, (16, 31, 42), rect.move(0, 7), border_radius=12)
                pygame.draw.rect(self.screen, self.map_data["wall"], rect, border_radius=12)
                pygame.draw.rect(self.screen, self.map_data["wall_edge"], rect, width=3, border_radius=12)
                for mark_x in range(rect.x + 18, rect.right - 8, 34):
                    pygame.draw.line(
                        self.screen, self.map_data["wall_edge"],
                        (mark_x, rect.y + 8), (mark_x + 9, rect.y + 15), 2,
                    )

        for crate in self.crates:
            self.draw_crate(crate, camera_x, camera_y)

        self.draw_arena_event(camera_x, camera_y)

        for particle in self.particles:
            pygame.draw.circle(
                self.screen, particle["color"],
                (int(particle["x"] - camera_x), int(particle["y"] - camera_y)),
                max(2, int(5 * particle["life"] * 2)),
            )

        for projectile in self.projectiles:
            point = (int(projectile["x"] - camera_x), int(projectile["y"] - camera_y))
            if len(projectile["trail"]) > 1:
                trail_points = [
                    (int(x - camera_x), int(y - camera_y))
                    for x, y in projectile["trail"]
                ]
                pygame.draw.lines(self.screen, projectile["color"], False, trail_points + [point], 3)
            pygame.draw.circle(self.screen, projectile["color"], point, projectile["radius"] + 3)
            pygame.draw.circle(self.screen, (255, 255, 255), point, projectile["radius"] // 2 + 1)

        for cube in self.cubes:
            self.draw_power_cube(cube, camera_x, camera_y)
        for powerup in self.powerups:
            self.draw_powerup(powerup, camera_x, camera_y)

        for bot in self.bots:
            x, y = int(bot["x"] - camera_x), int(bot["y"] - camera_y)
            if -40 < x < SCREEN_W + 40 and -40 < y < SCREEN_H + 40:
                self.draw_bar(x - 22, y - 29, 44, 6, bot["hp"] / bot["max_hp"], (255, 93, 103))
                self.draw_brawler(bot, camera_x, camera_y)

        player = self.player
        px, py = int(player["x"] - camera_x), int(player["y"] - camera_y)
        self.draw_brawler(player, camera_x, camera_y, is_player=True)

        pygame.draw.rect(self.screen, (17, 25, 39), (20, 17, 330, 82), border_radius=15)
        self.draw_text_box(
            BRAWLERS[player["brawler"]]["name"], self.font, (229, 246, 255),
            (36, 25, 170, 31),
        )
        self.draw_bar(37, 64, 170, 13, player["hp"] / player["max_hp"], (76, 224, 143))
        self.draw_text_box(
            f"{int(player['hp'])} HP", self.small_font, (223, 239, 241),
            (217, 57, 115, 20),
        )
        eliminations = f"SIEGE  {player['kills']}" if self.network_role is not None else f"SIEGE  {self.kills}/10"
        self.draw_text_box(eliminations, self.small_font, (206, 224, 230), (38, 80, 180, 18))
        self.draw_text_box(
            f"POWER-CUBES  x{player['cubes']}", self.small_font, (162, 255, 174),
            (370, 28, 210, 22),
        )
        brawler_stats = BRAWLERS[player["brawler"]]
        ammo_label = f"MUNITION  {player['ammo']}/{brawler_stats['ammo_capacity']}"
        if player["reload_timer"] > 0:
            ammo_label = f"NACHLADEN  {player['reload_timer']:.1f}s"
        self.draw_text_box(
            ammo_label, self.small_font, (255, 215, 143),
            (370, 52, 210, 22),
        )
        active_effects = []
        if player["shield_timer"] > 0:
            active_effects.append(f"Schild {math.ceil(player['shield_timer'])}s")
        if player["rapid_timer"] > 0:
            active_effects.append(f"Schnellfeuer {math.ceil(player['rapid_timer'])}s")
        if active_effects:
            self.draw_text_box(
                "  |  ".join(active_effects), self.small_font, (168, 221, 255),
                (370, 77, 300, 20),
            )
        if self.network_role is not None:
            for player_id, fighter in self.remote_players.items():
                if fighter["hp"] <= 0:
                    continue
                fx, fy = int(fighter["x"] - camera_x), int(fighter["y"] - camera_y)
                self.draw_bar(fx - 25, fy - 39, 50, 7, fighter["hp"] / fighter["max_hp"], fighter["color"])
                self.draw_brawler(fighter, camera_x, camera_y)
                if -50 < fx < SCREEN_W + 50 and -50 < fy < SCREEN_H + 50:
                    self.draw_text_box(
                        f"{BRAWLERS[fighter['brawler']]['name']}  x{fighter['cubes']}",
                        self.small_font, (232, 242, 248),
                        (fx - 70, fy + 31, 140, 22), centered=True,
                    )
            player_count = 1 + len(self.remote_players)
            alive_count = sum(fighter["hp"] > 0 for fighter in (self.player, *self.remote_players.values()))
            self.draw_text_box(
                f"Spieler {player_count}/{MAX_PLAYERS}   Verbleibend {alive_count}",
                self.small_font, (219, 232, 241),
                (SCREEN_W - 285, 18, 265, 24), centered=True,
            )

        super_x, super_y = SCREEN_W - 210, SCREEN_H - 40
        super_label = f"{BRAWLERS[player['brawler']]['super_name']} [LEERTASTE]"
        self.draw_text_box(
            super_label, self.small_font, (218, 233, 243),
            (SCREEN_W - 245, super_y - 29, 225, 25), centered=True,
        )
        super_color = (255, 202, 75) if player["super"] >= 100 else (102, 197, 246)
        self.draw_bar(super_x, super_y, 176, 13, player["super"] / 100, super_color, (40, 49, 62))
        if player["super"] >= 100:
            pygame.draw.circle(self.screen, (255, 217, 90), (super_x + 190, super_y + 6), 7)

        help_text = "WASD bewegen  |  Maus: zielen & schiessen  |  Kisten zerstoeren  |  LEERTASTE: Dash/Super"
        self.draw_text_box(
            help_text, self.small_font, (208, 224, 230),
            (20, SCREEN_H - 35, SCREEN_W - 40, 30), centered=True,
        )

        if self.damage_flash > 0:
            flash = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
            flash.fill((185, 28, 43, int(85 * self.damage_flash / 0.22)))
            self.screen.blit(flash, (0, 0))

        if self.game_state != "playing":
            overlay = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
            overlay.fill((9, 15, 25, 205))
            self.screen.blit(overlay, (0, 0))
            if self.game_state == "disconnected":
                title = "VERBINDUNG GETRENNT"
                subtitle = "Die Verbindung zum Mitspieler wurde beendet."
                restart_text = "R oder ESC: Zurueck ins Menue"
            elif self.game_state == "won":
                title = "SIEG!"
                subtitle = "Du bist der letzte Brawler in der Arena."
                restart_text = "R: Nochmal spielen     ESC: Zurueck ins Menue"
            else:
                title = "AUSGESCHALTET"
                subtitle = "Ein anderer Brawler hat gewonnen."
                restart_text = "R: Nochmal spielen     ESC: Zurueck ins Menue"
            self.draw_text_box(
                title, self.title_font, (237, 247, 255),
                (50, SCREEN_H // 2 - 82, SCREEN_W - 100, 68), centered=True,
            )
            self.draw_text_box(
                subtitle, self.font, (181, 201, 216),
                (70, SCREEN_H // 2 - 8, SCREEN_W - 140, 38), centered=True,
            )
            self.draw_text_box(
                restart_text, self.small_font, (134, 202, 234),
                (70, SCREEN_H // 2 + 35, SCREEN_W - 140, 36), centered=True,
            )
        self.present()
        return

    def run(self):
        running = True
        while running:
            dt = min(self.clock.tick(60) / 1000, 0.05)
            self.process_network()
            for event in pygame.event.get():
                running = self.handle_event(event) and running
            self.send_network_input(time.monotonic())
            self.update(dt)
            self.draw()
        if self.network is not None:
            self.network.close()
        pygame.quit()
        return 0


if __name__ == "__main__":
    sys.exit(Brawler().run())
