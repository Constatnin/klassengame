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


def circle_rect_collision(x, y, radius, rect):
    closest_x = max(rect.left, min(x, rect.right))
    closest_y = max(rect.top, min(y, rect.bottom))
    return (x - closest_x) ** 2 + (y - closest_y) ** 2 < radius**2


def move_circle(x, y, dx, dy, radius):
    next_x = max(radius, min(WORLD_W - radius, x + dx))
    if not any(circle_rect_collision(next_x, y, radius, wall) for wall in WALLS):
        x = next_x
    next_y = max(radius, min(WORLD_H - radius, y + dy))
    if not any(circle_rect_collision(x, next_y, radius, wall) for wall in WALLS):
        y = next_y
    return x, y


def line_hits_wall(start, end):
    return any(wall.clipline(start, end) for wall in WALLS)


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

    def reset(self):
        self.stop_network()
        self.game_state = "menu"
        self.player = None
        self.bots = []
        self.projectiles = []
        self.particles = []
        self.cubes = []
        self.kills = 0

    def start_game(self):
        if not 0 <= self.selected_brawler < len(BRAWLERS):
            self.selected_brawler = 0
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
        self.kills = 0
        self.spawn_timer = 0
        self.game_state = "playing"
        self.state_send_timer = 0
        self.dash_pending = False
        self.super_pending = False
        if self.network_role == "host":
            self.remote_input = {}
            self.cubes = []
            for x, y in (
                (650, 410), (1150, 390), (430, 720), (1370, 820),
                (830, 1040), (1530, 570), (1850, 650), (500, 1380),
            ):
                self.spawn_cube(x, y)
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
            "kills": self.kills,
            "game_state": self.game_state,
            "winner_id": self.winner_id,
        }
        for player_id in self.remote_players:
            self.network.send(state, player_id)

    @staticmethod
    def serialize_fighter(fighter):
        return {
            key: fighter[key]
            for key in ("x", "y", "hp", "max_hp", "super", "brawler", "cubes", "kills", "move_phase", "move_amount", "hurt_timer", "flash", "dash_timer")
        }

    def apply_network_state(self, message):
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
            fighter.update(state)
            fighter["color"] = BRAWLERS[brawler_index]["color"]
        self.remote_players = {
            player_id: fighter
            for player_id, fighter in self.remote_players.items()
            if player_id in players and player_id != self.client_id
        }
        self.network_error = ""
        self.cubes = [
            {"x": item[0], "y": item[1], "phase": item[2], "pickup": 0}
            for item in message.get("cubes", [])
            if isinstance(item, list) and len(item) == 3
        ]
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
                circle_rect_collision(x, y, 22, wall) for wall in WALLS
            ):
                max_hp = random.choice((62, 76, 90))
                self.bots.append({
                    "x": float(x),
                    "y": float(y),
                    "hp": max_hp,
                    "max_hp": max_hp,
                    "radius": 17,
                    "color": random.choice(BOT_COLORS),
                    "brawler": random.randrange(len(BRAWLERS)),
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
            attacker["x"], attacker["y"], dx * 300, dy * 300, attacker["radius"]
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
        if self.game_state != "playing":
            return
        if self.network_role == "client":
            return
        player = self.player
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
                player["x"], player["y"], dx * 700 * dt, dy * 700 * dt, player["radius"]
            )
        else:
            player["x"], player["y"] = move_circle(
                player["x"], player["y"],
                mx * (BRAWLERS[player["brawler"]]["speed"] + player["cubes"] * 2) * dt,
                my * (BRAWLERS[player["brawler"]]["speed"] + player["cubes"] * 2) * dt,
                player["radius"],
            )

        if player["hp"] > 0 and pygame.mouse.get_pressed()[0] and player["cooldown"] <= 0:
            target = self.screen_to_world(self.logical_mouse_pos())
            brawler = BRAWLERS[player["brawler"]]
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
            player["cooldown"] = brawler["fire_rate"]

        if self.network_role == "host":
            for player_id, fighter in list(self.remote_players.items()):
                self.update_remote_player(player_id, fighter, self.remote_input.get(player_id, {}), dt)

        for bot in self.bots:
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
                bot["x"], bot["y"], vx / length * 105 * dt, vy / length * 105 * dt, bot["radius"]
            )
            bot["move_amount"] = min(1, abs(vx) + abs(vy))
            if bot["cooldown"] <= 0 and distance < 540 and not line_hits_wall(
                (int(bot["x"]), int(bot["y"])),
                (int(player["x"]), int(player["y"])),
            ):
                self.shoot(bot, (player["x"], player["y"]), "bot", 380, 12, (255, 115, 125))
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
            hit_wall = any(wall.collidepoint(projectile["x"], projectile["y"]) for wall in WALLS)
            if (
                projectile["life"] <= 0
                or hit_wall
                or not (0 <= projectile["x"] <= WORLD_W and 0 <= projectile["y"] <= WORLD_H)
            ):
                self.projectiles.remove(projectile)
                continue
            player_owner = projectile["owner"] in ("player", "host") or projectile["owner"] in self.remote_players
            if projectile["owner"] in ("player", "host") and self.network_role is None:
                target = next((
                    bot for bot in self.bots
                    if math.hypot(projectile["x"] - bot["x"], projectile["y"] - bot["y"])
                    < bot["radius"] + projectile["radius"]
                ), None)
                if target is not None:
                    target["hp"] = max(0, target["hp"] - projectile["damage"])
                    target["hurt_timer"] = 0.13
                    target["flash"] = 0.12
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
                    fighter["hp"] = max(0, fighter["hp"] - projectile["damage"])
                    fighter["hurt_timer"] = 0.55
                    fighter["flash"] = 0.12
                    attacker["super"] = min(100, attacker["super"] + 18)
                    if fighter["hp"] <= 0:
                        attacker["kills"] += 1
                    self.add_burst_particles(projectile["x"], projectile["y"], count=7, colors=((255, 108, 122), (255, 230, 230)))
                    self.projectiles.remove(projectile)
            elif projectile["owner"] == "bot" and math.hypot(
                projectile["x"] - player["x"], projectile["y"] - player["y"]
            ) < player["radius"] + projectile["radius"]:
                player["hp"] = max(0, player["hp"] - projectile["damage"])
                player["hurt_timer"] = 0.55
                self.add_burst_particles(projectile["x"], projectile["y"], count=7, colors=((255, 108, 122), (255, 230, 230)))
                self.projectiles.remove(projectile)
                if player["hp"] <= 0:
                    self.game_state = "lost"
        self.check_match_winner()

        for cube in self.cubes[:]:
            cube["phase"] += dt * 3
            cube["pickup"] = max(0, cube["pickup"] - dt)
            if math.hypot(cube["x"] - player["x"], cube["y"] - player["y"]) < player["radius"] + 25:
                self.cubes.remove(cube)
                player["cubes"] += 1
                player["max_hp"] = BRAWLERS[player["brawler"]]["hp"] + player["cubes"] * 10
                player["hp"] = min(player["max_hp"], player["hp"] + 15)
                self.add_burst_particles(cube["x"], cube["y"], count=18)

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
                opponent["x"], opponent["y"], dx * 700 * dt, dy * 700 * dt, opponent["radius"]
            )
        else:
            speed = BRAWLERS[opponent["brawler"]]["speed"] + opponent["cubes"] * 2
            opponent["x"], opponent["y"] = move_circle(
                opponent["x"], opponent["y"], mx * speed * dt, my * speed * dt, opponent["radius"]
            )

        aim = controls.get("aim", [self.player["x"], self.player["y"]])
        if not isinstance(aim, (tuple, list)) or len(aim) != 2:
            aim = [self.player["x"], self.player["y"]]
        try:
            aim = [max(0, min(WORLD_W, float(aim[0]))), max(0, min(WORLD_H, float(aim[1])))]
        except (TypeError, ValueError):
            aim = [self.player["x"], self.player["y"]]
        if controls.get("fire") and opponent["cooldown"] <= 0:
            stats = BRAWLERS[opponent["brawler"]]
            damage = stats["damage"] * (1 + opponent["cubes"] * 0.08)
            self.shoot(opponent, aim, player_id, stats["bullet_speed"], damage, stats["color"])
            opponent["cooldown"] = stats["fire_rate"]

        if controls.get("super") and opponent["super"] >= 100:
            self.activate_super(player_id, opponent, aim)

    def return_to_menu(self):
        self.stop_network()
        self.player = None
        self.bots = []
        self.projectiles = []
        self.particles = []
        self.cubes = []
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
            if self.host_button_rect().collidepoint(mouse_pos):
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
        lines = []
        current = ""
        for word in str(text).split():
            candidate = f"{current} {word}".strip()
            if font.size(candidate)[0] <= max_width:
                current = candidate
                continue
            if current:
                lines.append(current)
                current = ""
            while word and font.size(word)[0] > max_width:
                split_at = 1
                while split_at < len(word) and font.size(word[:split_at + 1])[0] <= max_width:
                    split_at += 1
                lines.append(word[:split_at])
                word = word[split_at:]
            current = word
            if len(lines) >= max_lines:
                break
        if current and len(lines) < max_lines:
            lines.append(current)
        all_words = " ".join(lines).split()
        if " ".join(all_words) != str(text).strip() and lines:
            last = lines[-1]
            while last and font.size(last + "...")[0] > max_width:
                last = last[:-1]
            lines[-1] = last.rstrip() + "..."
        return lines[:max_lines]

    def draw_text_box(self, text, font, color, rect, max_lines=1, centered=False, line_spacing=0):
        rect = pygame.Rect(rect)
        lines = self.wrap_text(font, text, rect.width, max_lines)
        previous_clip = self.screen.get_clip()
        self.screen.set_clip(previous_clip.clip(rect))
        line_height = font.get_linesize() + line_spacing
        total_height = len(lines) * line_height - line_spacing
        y = rect.y + max(0, (rect.height - total_height) // 2)
        for line in lines:
            surface = font.render(line, True, color)
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
            pygame.draw.line(self.screen, (20, 40, 54), (0, y), (SCREEN_W, y))

        panel = pygame.Surface((SCREEN_W - 110, 635), pygame.SRCALPHA)
        panel.fill((17, 28, 39, 160))
        panel_rect = panel.get_rect(center=(SCREEN_W // 2, SCREEN_H // 2 + 18))
        self.screen.blit(panel, panel_rect)
        pygame.draw.rect(self.screen, (76, 112, 142), panel_rect, 1, border_radius=24)

        self.draw_text_box("NEON BRAWL", self.title_font, (239, 247, 255), (80, 62, 800, 62), centered=True)
        self.draw_text_box(
            "FUENF HELDEN. EINE ARENA. WIE LANGE UEBERLEBST DU?",
            self.font, (166, 204, 222), (80, 126, 800, 32), centered=True,
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
            (self.local_button_rect(), "ALLEIN SPIELEN", (76, 190, 149)),
            (self.host_button_rect(), "LAN SPIEL HOSTEN", (97, 164, 233)),
            (self.join_button_rect(), "LAN SPIEL BEITRETEN", (170, 122, 239)),
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
        ip_label = self.small_font.render("HOST-IP:", True, (176, 204, 221))
        self.screen.blit(ip_label, (field.x - 82, field.y + 10))
        visible_ip = self.ip_address or "IPv4 des Hosts eingeben"
        ip_text = self.font.render(visible_ip, True, (238, 246, 252))
        if ip_text.get_width() > field.width - 26:
            ip_text = self.small_font.render(visible_ip, True, (238, 246, 252))
        if self.editing_ip and self.ip_input_selected and self.ip_address:
            selection = pygame.Rect(field.x + 10, field.y + 5, ip_text.get_width() + 6, ip_text.get_height() + 6)
            pygame.draw.rect(self.screen, (73, 112, 145), selection, border_radius=4)
        ip_clip = self.screen.get_clip()
        self.screen.set_clip(ip_clip.clip(field.inflate(-8, -4)))
        self.screen.blit(ip_text, (field.x + 13, field.centery - ip_text.get_height() // 2))
        self.screen.set_clip(ip_clip)
        if self.editing_ip and int(self.animation_time * 2) % 2 == 0:
            cursor_x = field.x + 13 + ip_text.get_width() + 2
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
                "WASD: Bewegen   Maus: Zielen & Schiessen   SPACE: Dash / Super   F11: Vollbild",
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

        if is_player and entity.get("dash_timer", 0) > 0:
            dash_radius = radius + int((0.16 - entity["dash_timer"]) * 100)
            pygame.draw.circle(self.screen, (145, 231, 255), (sx, sy), dash_radius, 3)
        if entity.get("super", 0) >= 100:
            pulse = int(math.sin(self.animation_time * 7) * 2)
            pygame.draw.circle(self.screen, (255, 217, 90), (sx, sy), radius + 8 + pulse, 2)

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
            name = self.small_font.render(BRAWLERS[entity["brawler"]]["name"], True, (243, 247, 248))
            self.screen.blit(name, name.get_rect(center=(sx, sy - radius - 19)))

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

    def draw(self):
        if self.game_state in ("menu", "lobby", "connecting"):
            self.draw_menu()
            return
        camera_x, camera_y = self.player_screen_pos()
        self.screen.fill((27, 51, 58))
        grid = 48
        for x in range(-int(camera_x) % grid, SCREEN_W, grid):
            pygame.draw.line(self.screen, (31, 57, 63), (x, 0), (x, SCREEN_H))
        for y in range(-int(camera_y) % grid, SCREEN_H, grid):
            pygame.draw.line(self.screen, (31, 57, 63), (0, y), (SCREEN_W, y))

        for index in range(32):
            world_x = (index * 263 + 117) % WORLD_W
            world_y = (index * 397 + 83) % WORLD_H
            sx, sy = int(world_x - camera_x), int(world_y - camera_y)
            if 0 <= sx < SCREEN_W and 0 <= sy < SCREEN_H:
                pygame.draw.circle(self.screen, (43, 78, 71), (sx, sy), 4)
                pygame.draw.circle(self.screen, (58, 104, 84), (sx - 3, sy - 2), 2)

        for wall in WALLS:
            rect = pygame.Rect(wall.x - camera_x, wall.y - camera_y, wall.width, wall.height)
            if rect.colliderect(self.screen.get_rect()):
                pygame.draw.rect(self.screen, (16, 31, 42), rect.move(0, 7), border_radius=12)
                pygame.draw.rect(self.screen, (67, 91, 94), rect, border_radius=12)
                pygame.draw.rect(self.screen, (89, 119, 116), rect, width=3, border_radius=12)
                for mark_x in range(rect.x + 18, rect.right - 8, 34):
                    pygame.draw.line(self.screen, (78, 103, 103), (mark_x, rect.y + 8), (mark_x + 9, rect.y + 15), 2)

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

        for bot in self.bots:
            x, y = int(bot["x"] - camera_x), int(bot["y"] - camera_y)
            if -40 < x < SCREEN_W + 40 and -40 < y < SCREEN_H + 40:
                self.draw_bar(x - 22, y - 29, 44, 6, bot["hp"] / bot["max_hp"], (255, 93, 103))
                self.draw_brawler(bot, camera_x, camera_y)

        player = self.player
        px, py = int(player["x"] - camera_x), int(player["y"] - camera_y)
        self.draw_brawler(player, camera_x, camera_y, is_player=True)

        pygame.draw.rect(self.screen, (17, 25, 39), (20, 17, 330, 82), border_radius=15)
        self.screen.blit(self.font.render(BRAWLERS[player["brawler"]]["name"], True, (229, 246, 255)), (36, 27))
        self.draw_bar(37, 64, 170, 13, player["hp"] / player["max_hp"], (76, 224, 143))
        self.screen.blit(self.small_font.render(f"{int(player['hp'])} HP", True, (223, 239, 241)), (217, 60))
        eliminations = f"ELIMS  {player['kills']}" if self.network_role is not None else f"ELIMS  {self.kills}/10"
        self.screen.blit(self.small_font.render(eliminations, True, (206, 224, 230)), (38, 81))
        cube_label = self.small_font.render(f"POWER CUBES  x{player['cubes']}", True, (162, 255, 174))
        self.screen.blit(cube_label, (370, 31))
        if self.network_role is not None:
            for player_id, fighter in self.remote_players.items():
                if fighter["hp"] <= 0:
                    continue
                fx, fy = int(fighter["x"] - camera_x), int(fighter["y"] - camera_y)
                self.draw_bar(fx - 25, fy - 39, 50, 7, fighter["hp"] / fighter["max_hp"], fighter["color"])
                self.draw_brawler(fighter, camera_x, camera_y)
                if -50 < fx < SCREEN_W + 50 and -50 < fy < SCREEN_H + 50:
                    label = self.small_font.render(
                        f"{BRAWLERS[fighter['brawler']]['name']}  x{fighter['cubes']}",
                        True, (232, 242, 248),
                    )
                    self.screen.blit(label, label.get_rect(center=(fx, fy + 34)))
            player_count = 1 + len(self.remote_players)
            alive_count = sum(fighter["hp"] > 0 for fighter in (self.player, *self.remote_players.values()))
            lobby_label = self.small_font.render(
                f"Spieler {player_count}/{MAX_PLAYERS}   Verbleibend {alive_count}",
                True, (219, 232, 241),
            )
            self.screen.blit(lobby_label, (SCREEN_W - lobby_label.get_width() - 20, 22))

        super_x, super_y = SCREEN_W - 210, SCREEN_H - 40
        super_label = f"{BRAWLERS[player['brawler']]['super_name']} [SPACE]"
        self.draw_text_box(
            super_label, self.small_font, (218, 233, 243),
            (SCREEN_W - 245, super_y - 29, 225, 25), centered=True,
        )
        super_color = (255, 202, 75) if player["super"] >= 100 else (102, 197, 246)
        self.draw_bar(super_x, super_y, 176, 13, player["super"] / 100, super_color, (40, 49, 62))
        if player["super"] >= 100:
            pygame.draw.circle(self.screen, (255, 217, 90), (super_x + 190, super_y + 6), 7)

        help_text = "WASD bewegen  |  Maus zielen & schiessen  |  SPACE: Dash/Super  |  F11: Vollbild"
        self.draw_text_box(
            help_text, self.small_font, (208, 224, 230),
            (20, SCREEN_H - 35, SCREEN_W - 40, 30), centered=True,
        )

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

        pygame.draw.ellipse(
            self.screen, (12, 25, 33), (sx - radius, int(y + radius * 0.55), radius * 2, radius // 2 + 5)
        )
        if is_player and entity.get("dash_timer", 0) > 0:
            dash_radius = radius + int((0.16 - entity["dash_timer"]) * 100)
            pygame.draw.circle(self.screen, (145, 231, 255), (sx, sy), dash_radius, 3)
        if entity.get("super", 0) >= 100:
            pygame.draw.circle(self.screen, (255, 217, 90), (sx, sy), radius + 8, 2)

        if is_player:
            aim_x, aim_y = pygame.mouse.get_pos()
            angle = math.atan2(aim_y - sy, aim_x - sx)
        else:
            dx, dy = self.player["x"] - entity["x"], self.player["y"] - entity["y"]
            angle = math.atan2(dy, dx)
        direction = (math.cos(angle), math.sin(angle))
        start = (sx + int(direction[0] * radius * 0.55), sy + int(direction[1] * radius * 0.55))
        end_distance = radius + 13 + (7 if entity.get("flash", 0) > 0 else 0)
        end = (sx + int(direction[0] * end_distance), sy + int(direction[1] * end_distance))
        pygame.draw.line(self.screen, (25, 37, 51), start, end, 12)
        pygame.draw.line(self.screen, body_color, start, end, 7)
        if entity.get("flash", 0) > 0:
            pygame.draw.circle(self.screen, (255, 247, 177), end, 9 + int(entity["flash"] * 35))

        kind = entity["brawler"]
        if kind == 1:
            points = [
                (sx, sy - radius - 2), (sx + radius, sy),
                (sx, sy + radius + 2), (sx - radius, sy),
            ]
            pygame.draw.polygon(self.screen, (17, 31, 43), [(px, py + 4) for px, py in points])
            pygame.draw.polygon(self.screen, body_color, points)
            pygame.draw.polygon(self.screen, (255, 246, 198), points, 2)
        elif kind == 2:
            pygame.draw.circle(self.screen, (17, 31, 43), (sx, sy + 4), radius + 3)
            pygame.draw.circle(self.screen, body_color, (sx, sy), radius + 2)
            pygame.draw.circle(self.screen, (255, 210, 187), (sx, sy), radius + 2, 3)
            pygame.draw.circle(self.screen, body_color, (sx - radius + 2, sy - 12), 7)
            pygame.draw.circle(self.screen, body_color, (sx + radius - 2, sy - 12), 7)
        else:
            pygame.draw.circle(self.screen, (17, 31, 43), (sx, sy + 4), radius + 3)
            pygame.draw.circle(self.screen, body_color, (sx, sy), radius)
            pygame.draw.circle(self.screen, (210, 247, 255), (sx, sy), radius, 2)

        eye_color = (26, 43, 56) if body_color != (255, 255, 255) else (82, 82, 82)
        pygame.draw.circle(self.screen, eye_color, (sx - 6, sy - 4), 3)
        pygame.draw.circle(self.screen, eye_color, (sx + 6, sy - 4), 3)
        pygame.draw.arc(self.screen, eye_color, (sx - 6, sy, 12, 9), 3.4, 5.9, 2)


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
