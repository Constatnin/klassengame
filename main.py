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
WORLD_W, WORLD_H = 1800, 1300
LAN_PORT = 50505
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
        self.send_lock = threading.Lock()
        self.closed = False

    def host(self):
        self.listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.listener.bind(("", LAN_PORT))
        self.listener.listen(1)
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
            self.connection = connection
            self.messages.put({"type": "connected", "address": address[0]})
            threading.Thread(target=self._receive, args=(connection,), daemon=True).start()
            return

    def join(self, address):
        def connect():
            connection = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            connection.settimeout(6)
            try:
                connection.connect((address, LAN_PORT))
                connection.settimeout(None)
                connection.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
                self.connection = connection
                self.messages.put({"type": "connected", "address": address})
                threading.Thread(target=self._receive, args=(connection,), daemon=True).start()
            except OSError as error:
                connection.close()
                self.messages.put({"type": "error", "message": str(error)})
        threading.Thread(target=connect, daemon=True).start()

    def _receive(self, connection):
        buffer = b""
        try:
            while not self.closed:
                data = connection.recv(4096)
                if not data:
                    break
                buffer += data
                while b"\n" in buffer:
                    line, buffer = buffer.split(b"\n", 1)
                    self.messages.put(json.loads(line.decode("utf-8")))
        except (OSError, json.JSONDecodeError, UnicodeDecodeError) as error:
            if not self.closed:
                self.messages.put({"type": "error", "message": str(error)})
        finally:
            if not self.closed:
                self.messages.put({"type": "disconnected"})

    def send(self, message):
        connection = self.connection
        if connection is None:
            return
        payload = (json.dumps(message, separators=(",", ":")) + "\n").encode("utf-8")
        try:
            with self.send_lock:
                connection.sendall(payload)
        except OSError as error:
            self.messages.put({"type": "error", "message": str(error)})

    def close(self):
        self.closed = True
        for connection in (self.connection, self.listener):
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
        self.screen = pygame.display.set_mode((SCREEN_W, SCREEN_H))
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
        self.last_network_send = 0
        self.remote_input = {}
        self.remote_dash_cooldown = 0
        self.reset()

    def reset(self):
        if self.network is not None:
            self.network.close()
        self.network = None
        self.network_role = None
        self.game_state = "menu"
        self.bots = []
        self.projectiles = []
        self.particles = []
        self.cubes = []
        self.kills = 0
        self.network_error = ""

    def start_game(self):
        brawler = BRAWLERS[self.selected_brawler]
        self.player = {
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
            "brawler": self.selected_brawler,
            "cubes": 0,
            "kills": 0,
        }
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
            self.bots.clear()
            self.opponent = self.make_opponent(self.remote_brawler)
            self.remote_input = {}
            self.cubes = []
            for x, y in ((650, 410), (1150, 390), (430, 720), (1370, 820), (830, 1040), (1530, 570)):
                self.spawn_cube(x, y)
            return
        if self.network_role == "client":
            self.bots.clear()
            self.opponent = self.make_opponent(self.remote_brawler)
            self.remote_input = {}
            return
        for _ in range(4):
            self.spawn_bot()

    def start_host(self):
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
        self.game_state = "lobby"

    def start_join(self):
        address = self.ip_address.strip()
        if not address:
            self.network_error = "Bitte die IP-Adresse des Hosts eingeben."
            return
        connection = LanConnection()
        connection.join(address)
        self.network = connection
        self.network_role = "client"
        self.network_status = f"Verbinde mit {address} ..."
        self.game_state = "connecting"
        self.network_error = ""

    def process_network(self):
        if self.network is None:
            return
        while True:
            try:
                message = self.network.messages.get_nowait()
            except queue.Empty:
                break
            kind = message.get("type")
            if kind == "connected":
                self.network_status = f"Verbunden mit {message.get('address', 'Mitspieler')}"
                self.network.send({
                    "type": "hello",
                    "brawler": self.selected_brawler,
                })
            elif kind == "hello":
                brawler = message.get("brawler")
                if not isinstance(brawler, int) or not 0 <= brawler < len(BRAWLERS):
                    self.network_error = "Der Mitspieler hat einen ungueltigen Brawler gesendet."
                    self.network.close()
                    self.network = None
                    self.network_role = None
                    self.game_state = "menu"
                    continue
                self.remote_brawler = brawler
                self.network_status = f"Gegner: {BRAWLERS[brawler]['name']}"
                if self.network_role == "host":
                    self.start_game()
                elif self.network_role == "client":
                    self.start_game()
            elif kind == "input" and self.network_role == "host":
                self.remote_input = message
            elif kind == "restart" and self.network_role == "host":
                self.start_game()
            elif kind == "state" and self.network_role == "client":
                self.apply_network_state(message)
            elif kind == "error":
                self.network_error = f"Netzwerkfehler: {message.get('message', 'Unbekannter Fehler')}"
                if self.game_state in ("connecting", "lobby"):
                    self.network.close()
                    self.network = None
                    self.network_role = None
                    self.game_state = "menu"
                self.network_status = self.network_error
            elif kind == "disconnected":
                self.network_status = "Verbindung zum Mitspieler verloren."
                self.network_error = self.network_status
                if self.game_state == "playing":
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
            "aim": list(self.screen_to_world(pygame.mouse.get_pos())),
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
        if self.network_role != "host" or self.network is None or self.game_state not in ("playing", "won", "lost"):
            return
        self.state_send_timer += dt
        if self.state_send_timer < 1 / 20 and not force:
            return
        self.state_send_timer = 0
        self.network.send({
            "type": "state",
            "player": self.serialize_fighter(self.player),
            "opponent": self.serialize_fighter(self.opponent),
            "cubes": [[cube["x"], cube["y"], cube["phase"]] for cube in self.cubes],
            "projectiles": [
                [p["x"], p["y"], p["vx"], p["vy"], p["owner"], p["color"]]
                for p in self.projectiles if p["owner"] != "bot"
            ],
            "kills": self.kills,
            "game_state": self.game_state,
        })

    @staticmethod
    def serialize_fighter(fighter):
        return {
            key: fighter[key]
            for key in ("x", "y", "hp", "max_hp", "super", "brawler", "cubes", "kills", "move_phase", "move_amount", "hurt_timer", "flash", "dash_timer")
        }

    def apply_network_state(self, message):
        host_player = message.get("player")
        host_opponent = message.get("opponent")
        if not isinstance(host_player, dict) or not isinstance(host_opponent, dict):
            self.network_error = "Ungueltige Spieldaten vom Host empfangen."
            return
        for key, value in host_opponent.items():
            self.player[key] = value
        self.opponent.update(host_player)
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
        self.kills = host_opponent.get("kills", 0)
        host_state = message.get("game_state", "playing")
        self.game_state = {"won": "lost", "lost": "won"}.get(host_state, host_state)

    @staticmethod
    def make_opponent(brawler_index):
        brawler = BRAWLERS[brawler_index]
        return {
            "x": WORLD_W / 2 + 150,
            "y": WORLD_H / 2,
            "hp": brawler["hp"],
            "max_hp": brawler["hp"],
            "radius": 19,
            "cooldown": 0,
            "hurt_timer": 0,
            "flash": 0,
            "super": 0,
            "dash_timer": 0,
            "dash_dir": (0, 0),
            "dash_cooldown": 0,
            "move_phase": 0,
            "move_amount": 0,
            "brawler": brawler_index,
            "cubes": 0,
            "kills": 0,
            "color": brawler["color"],
        }

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
        player = self.player
        if player["super"] < 100:
            return
        player["super"] = 0
        defeated = []
        for bot in self.bots:
            dx, dy = bot["x"] - player["x"], bot["y"] - player["y"]
            distance = math.hypot(dx, dy)
            if distance <= 185 and not line_hits_wall(
                (int(player["x"]), int(player["y"])),
                (int(bot["x"]), int(bot["y"])),
            ):
                bot["hp"] -= 38
                bot["hurt_timer"] = 0.15
                if distance:
                    bot["x"], bot["y"] = move_circle(
                        bot["x"], bot["y"], dx / distance * 45, dy / distance * 45, bot["radius"]
                    )
                if bot["hp"] <= 0:
                    defeated.append(bot)
        if self.network_role == "host":
            opponent = self.opponent
            dx, dy = opponent["x"] - player["x"], opponent["y"] - player["y"]
            distance = math.hypot(dx, dy)
            if distance <= 185 and not line_hits_wall(
                (int(player["x"]), int(player["y"])),
                (int(opponent["x"]), int(opponent["y"])),
            ):
                opponent["hp"] -= 38
                opponent["hurt_timer"] = 0.2
                opponent["flash"] = 0.15
                if distance:
                    opponent["x"], opponent["y"] = move_circle(
                        opponent["x"], opponent["y"],
                        dx / distance * 45, dy / distance * 45, opponent["radius"],
                    )
                if opponent["hp"] <= 0:
                    opponent["hp"] = 0
                    player["kills"] += 1
                    self.game_state = "won"
        for bot in defeated:
            self.defeat_bot(bot)
        self.add_burst_particles(player["x"], player["y"])
        if self.game_state != "playing":
            self.send_network_state(0, force=True)

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

        if pygame.mouse.get_pressed()[0] and player["cooldown"] <= 0:
            target = self.screen_to_world(pygame.mouse.get_pos())
            brawler = BRAWLERS[player["brawler"]]
            damage = brawler["damage"] * (1 + player["cubes"] * 0.08)
            self.shoot(player, target, "player", brawler["bullet_speed"], damage, brawler["color"])
            if player["brawler"] == 1:
                dx, dy = target[0] - player["x"], target[1] - player["y"]
                length = max(1, math.hypot(dx, dy))
                offset = 9
                side_target = (
                    target[0] - dy / length * offset,
                    target[1] + dx / length * offset,
                )
                self.shoot(player, side_target, "player", brawler["bullet_speed"], damage, brawler["color"])
            player["cooldown"] = brawler["fire_rate"]

        if self.network_role == "host":
            self.update_opponent(dt)

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
            if projectile["owner"] == "player":
                target = next((
                    bot for bot in self.bots
                    if math.hypot(projectile["x"] - bot["x"], projectile["y"] - bot["y"])
                    < bot["radius"] + projectile["radius"]
                ), None)
                if target is None and self.network_role == "host" and math.hypot(
                    projectile["x"] - self.opponent["x"],
                    projectile["y"] - self.opponent["y"],
                ) < self.opponent["radius"] + projectile["radius"]:
                    target = self.opponent
                if target is not None:
                    target["hp"] -= projectile["damage"]
                    target["hurt_timer"] = 0.13
                    target["flash"] = 0.12
                    self.add_burst_particles(projectile["x"], projectile["y"], count=5)
                    player["super"] = min(100, player["super"] + 18)
                    self.projectiles.remove(projectile)
                    if target is self.opponent:
                        if target["hp"] <= 0:
                            target["hp"] = 0
                            self.game_state = "won"
                            player["kills"] += 1
                    elif target["hp"] <= 0:
                        self.defeat_bot(target)
            elif projectile["owner"] in ("bot", "opponent") and math.hypot(
                projectile["x"] - player["x"], projectile["y"] - player["y"]
            ) < player["radius"] + projectile["radius"]:
                player["hp"] -= projectile["damage"]
                player["hurt_timer"] = 0.55
                self.add_burst_particles(projectile["x"], projectile["y"], count=7, colors=((255, 108, 122), (255, 230, 230)))
                self.projectiles.remove(projectile)
                if projectile["owner"] == "opponent":
                    self.opponent["super"] = min(100, self.opponent["super"] + 18)
                    self.opponent["flash"] = 0.12
                if player["hp"] <= 0:
                    player["hp"] = 0
                    self.game_state = "lost"
                    if projectile["owner"] == "opponent":
                        self.opponent["kills"] += 1

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
            for cube in self.cubes[:]:
                if math.hypot(cube["x"] - self.opponent["x"], cube["y"] - self.opponent["y"]) < self.opponent["radius"] + 25:
                    self.cubes.remove(cube)
                    self.opponent["cubes"] += 1
                    self.opponent["max_hp"] = BRAWLERS[self.opponent["brawler"]]["hp"] + self.opponent["cubes"] * 10
                    self.opponent["hp"] = min(self.opponent["max_hp"], self.opponent["hp"] + 15)
                    self.add_burst_particles(cube["x"], cube["y"], count=18)

        if self.network_role is None and len(self.bots) < 4 and self.game_state == "playing":
            self.spawn_timer += dt
            if self.spawn_timer >= 1.5:
                self.spawn_timer = 0
                self.spawn_bot()

        if player["hurt_timer"] <= 0 and player["hp"] < player["max_hp"]:
            player["hp"] = min(player["max_hp"], player["hp"] + 5 * dt)
        if self.network_role == "host" and self.opponent["hurt_timer"] <= 0 and self.opponent["hp"] < self.opponent["max_hp"]:
            self.opponent["hp"] = min(self.opponent["max_hp"], self.opponent["hp"] + 5 * dt)

        for particle in self.particles[:]:
            particle["x"] += particle["vx"] * dt
            particle["y"] += particle["vy"] * dt
            particle["life"] -= dt
            if particle["life"] <= 0:
                self.particles.remove(particle)
        self.send_network_state(dt, force=self.game_state != "playing")

    def update_opponent(self, dt):
        opponent = self.opponent
        controls = self.remote_input
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
        opponent["move_amount"] = min(1, math.hypot(mx, my))
        opponent["move_phase"] += dt * (13 if opponent["move_amount"] else 3)

        if controls.get("dash") and opponent["dash_cooldown"] <= 0:
            if length:
                direction = (mx / max(length, 1), my / max(length, 1))
            else:
                direction = (self.player["x"] - opponent["x"], self.player["y"] - opponent["y"])
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
            self.shoot(opponent, aim, "opponent", stats["bullet_speed"], damage, stats["color"])
            opponent["cooldown"] = stats["fire_rate"]

        if controls.get("super"):
            if opponent["super"] >= 100:
                opponent["super"] = 0
                dx = self.player["x"] - opponent["x"]
                dy = self.player["y"] - opponent["y"]
                if math.hypot(dx, dy) <= 185 and not line_hits_wall(
                    (int(opponent["x"]), int(opponent["y"])),
                    (int(self.player["x"]), int(self.player["y"])),
                ):
                    self.player["hp"] -= 38
                    self.player["hurt_timer"] = 0.3
                    if self.player["hp"] <= 0:
                        self.player["hp"] = 0
                        self.game_state = "lost"
                        opponent["kills"] += 1
                self.add_burst_particles(opponent["x"], opponent["y"])

    def handle_event(self, event):
        if event.type == pygame.QUIT:
            return False
        if event.type == pygame.TEXTINPUT and self.game_state == "menu" and self.editing_ip:
            if len(self.ip_address) + len(event.text) <= 45:
                self.ip_address += event.text
            return True
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                return False
            if event.key == pygame.K_r and self.game_state in ("won", "lost", "disconnected"):
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
                    self.ip_address = self.ip_address[:-1]
                elif self.editing_ip and event.key == pygame.K_RETURN:
                    self.editing_ip = False
                elif not self.editing_ip and event.key in (pygame.K_1, pygame.K_2, pygame.K_3):
                    self.selected_brawler = event.key - pygame.K_1
                elif not self.editing_ip and event.key in (pygame.K_LEFT, pygame.K_a):
                    self.selected_brawler = (self.selected_brawler - 1) % len(BRAWLERS)
                elif not self.editing_ip and event.key in (pygame.K_RIGHT, pygame.K_d):
                    self.selected_brawler = (self.selected_brawler + 1) % len(BRAWLERS)
                elif not self.editing_ip and event.key in (pygame.K_RETURN, pygame.K_SPACE):
                    self.network_role = None
                    self.start_game()
                return True
            if event.key == pygame.K_SPACE and self.game_state == "playing":
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
                        target = self.screen_to_world(pygame.mouse.get_pos())
                        dx, dy = target[0] - self.player["x"], target[1] - self.player["y"]
                        length = max(1, math.hypot(dx, dy))
                    if self.player["dash_cooldown"] <= 0:
                        self.player["dash_dir"] = (dx / length, dy / length)
                        self.player["dash_timer"] = 0.16
                        self.player["dash_cooldown"] = 1.2
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 and self.game_state == "menu":
            for index in range(len(BRAWLERS)):
                if self.character_card_rect(index).collidepoint(event.pos):
                    self.selected_brawler = index
                    return True
            if self.host_button_rect().collidepoint(event.pos):
                self.editing_ip = False
                self.start_host()
            elif self.join_button_rect().collidepoint(event.pos):
                self.editing_ip = False
                self.start_join()
            elif self.local_button_rect().collidepoint(event.pos):
                self.network_role = None
                self.start_game()
            elif self.ip_field_rect().collidepoint(event.pos):
                self.editing_ip = True
                pygame.key.start_text_input()
            else:
                self.editing_ip = False
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
        return pygame.Rect(95 + index * 260, 285, 230, 215)

    def draw_bar(self, x, y, width, height, ratio, color, background=(43, 47, 59)):
        pygame.draw.rect(self.screen, background, (x, y, width, height), border_radius=height // 2)
        if ratio > 0:
            pygame.draw.rect(
                self.screen, color,
                (x, y, max(height, int(width * min(1, ratio))), height),
                border_radius=height // 2,
            )

    def draw_menu(self):
        self.screen.fill((18, 34, 50))
        for radius in range(330, 0, -30):
            shade = 35 + (330 - radius) // 12
            pygame.draw.circle(
                self.screen, (shade // 2, shade, min(95, shade + 25)),
                (SCREEN_W // 2, 210), radius,
            )
        for y in range(0, SCREEN_H, 48):
            pygame.draw.line(self.screen, (22, 43, 59), (0, y), (SCREEN_W, y))
        title = self.title_font.render("NEON BRAWL", True, (237, 248, 255))
        subtitle = self.font.render("DREI HELDEN. EINE ARENA. WIE LANGE UEBERLEBST DU?", True, (157, 195, 218))
        self.screen.blit(title, title.get_rect(center=(SCREEN_W // 2, 105)))
        self.screen.blit(subtitle, subtitle.get_rect(center=(SCREEN_W // 2, 166)))

        for index, brawler in enumerate(BRAWLERS):
            rect = self.character_card_rect(index)
            selected = index == self.selected_brawler
            card_color = (40, 65, 84) if selected else (27, 47, 66)
            pygame.draw.rect(self.screen, card_color, rect, border_radius=20)
            border_color = brawler["color"] if selected else (55, 78, 96)
            pygame.draw.rect(self.screen, border_color, rect, 3 if selected else 1, border_radius=20)
            cx = rect.centerx
            cy = rect.y + 66 + int(math.sin(self.animation_time * 3 + index) * 5)
            preview = {
                "x": cx, "y": cy, "radius": 25, "brawler": index,
                "color": brawler["color"], "phase": self.animation_time * 3 + index,
                "move_phase": self.animation_time * 3 + index, "move_amount": 0.35,
                "flash": 0, "hurt_timer": 0, "super": 0,
            }
            self.draw_brawler(preview, 0, 0, is_player=True, menu_preview=True)
            name = self.font.render(brawler["name"], True, (242, 247, 252))
            desc = self.small_font.render(brawler["description"], True, (176, 199, 215))
            self.screen.blit(name, name.get_rect(center=(cx, rect.y + 119)))
            self.screen.blit(desc, desc.get_rect(center=(cx, rect.y + 148)))
            self.screen.blit(self.small_font.render("LEBEN", True, (161, 184, 200)), (rect.x + 23, rect.y + 169))
            self.draw_bar(rect.x + 83, rect.y + 173, 122, 8, brawler["hp"] / 145, brawler["color"])
            self.screen.blit(self.small_font.render("ANGRIFF", True, (161, 184, 200)), (rect.x + 23, rect.y + 188))
            self.draw_bar(rect.x + 83, rect.y + 192, 122, 8, brawler["damage"] / 38, (255, 177, 96))
            self.screen.blit(
                self.small_font.render(str(index + 1), True, (140, 167, 186)),
                (rect.x + 14, rect.y + 12),
            )

        buttons = (
            (self.local_button_rect(), "ALLEIN SPIELEN", (78, 193, 151)),
            (self.host_button_rect(), "LAN SPIEL HOSTEN", (86, 167, 231)),
            (self.join_button_rect(), "LAN SPIEL BEITRETEN", (170, 126, 235)),
        )
        for rect, label, color in buttons:
            pygame.draw.rect(self.screen, (color[0] // 3, color[1] // 3, color[2] // 3), rect, border_radius=15)
            pygame.draw.rect(self.screen, color, rect, 2, border_radius=15)
            text = self.small_font.render(label, True, (242, 248, 252))
            self.screen.blit(text, text.get_rect(center=rect.center))

        field = self.ip_field_rect()
        field_color = (54, 78, 101) if self.editing_ip else (35, 52, 70)
        pygame.draw.rect(self.screen, field_color, field, border_radius=10)
        pygame.draw.rect(self.screen, (109, 154, 190), field, 2, border_radius=10)
        ip_label = self.small_font.render("HOST-IP:", True, (174, 198, 216))
        self.screen.blit(ip_label, (field.x - 83, field.y + 10))
        ip_text = self.font.render(self.ip_address or "IP eingeben", True, (237, 245, 251))
        self.screen.blit(ip_text, (field.x + 13, field.y + 7))
        if self.editing_ip and int(self.animation_time * 2) % 2 == 0:
            cursor_x = field.x + 13 + ip_text.get_width() + 2
            pygame.draw.line(self.screen, (240, 248, 255), (cursor_x, field.y + 8), (cursor_x, field.bottom - 8), 2)
        if self.game_state in ("lobby", "connecting"):
            status = self.network_status
            if self.network_role == "host":
                status = f"{self.network_status}  (IP: {self.get_local_ip()})"
            status_surface = self.small_font.render(status, True, (255, 221, 137))
            self.screen.blit(status_surface, status_surface.get_rect(center=(SCREEN_W // 2, 663)))
        elif self.network_error:
            error_surface = self.small_font.render(self.network_error[:90], True, (255, 132, 142))
            self.screen.blit(error_surface, error_surface.get_rect(center=(SCREEN_W // 2, 663)))
        else:
            controls = self.small_font.render(
                "WASD: Bewegen   Maus: Zielen & Schiessen   SPACE: Dash / Super", True, (160, 188, 205)
            )
            self.screen.blit(controls, controls.get_rect(center=(SCREEN_W // 2, 663)))
        pygame.display.flip()

    @staticmethod
    def get_local_ip():
        try:
            addresses = socket.getaddrinfo(socket.gethostname(), None, socket.AF_INET)
            for address in addresses:
                ip = address[4][0]
                if not ip.startswith("127."):
                    return ip
            return "127.0.0.1"
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
                aim_x, aim_y = pygame.mouse.get_pos()
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
        else:
            armor = pygame.Rect(sx - radius - 2, sy - radius, radius * 2 + 4, radius * 2 + 5)
            pygame.draw.rect(self.screen, (47, 38, 51), armor, border_radius=9)
            pygame.draw.rect(self.screen, body_color, armor.inflate(-5, -5), border_radius=7)
            pygame.draw.rect(self.screen, (255, 208, 187), (sx - 11, sy - 6, 22, 12), border_radius=4)
            pygame.draw.line(self.screen, (85, 41, 51), (sx - 6, sy), (sx - 2, sy + 2), 2)
            pygame.draw.line(self.screen, (85, 41, 51), (sx + 2, sy + 2), (sx + 6, sy), 2)
            pygame.draw.circle(self.screen, (255, 223, 112), (sx - radius - 1, sy + 2), 5)
            pygame.draw.circle(self.screen, (255, 223, 112), (sx + radius + 1, sy + 2), 5)

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
        self.screen.blit(self.small_font.render(f"ELIMS  {self.kills}/10", True, (206, 224, 230)), (38, 81))
        cube_label = self.small_font.render(f"POWER CUBES  x{player['cubes']}", True, (162, 255, 174))
        self.screen.blit(cube_label, (370, 31))
        if self.network_role is not None:
            opponent = self.opponent
            ox, oy = int(opponent["x"] - camera_x), int(opponent["y"] - camera_y)
            self.draw_bar(ox - 27, oy - 40, 54, 7, opponent["hp"] / opponent["max_hp"], (255, 90, 111))
            self.draw_brawler(opponent, camera_x, camera_y)
            rival_label = self.small_font.render(
                f"{BRAWLERS[opponent['brawler']]['name']}  x{opponent['cubes']}",
                True, (255, 190, 188),
            )
            self.screen.blit(rival_label, (370, 57))
            self.draw_bar(20, 112, 180, 9, opponent["super"] / 100, (255, 187, 89), (40, 49, 62))
            self.screen.blit(
                self.small_font.render("GEGNER-SUPER", True, (255, 200, 180)),
                (207, 106),
            )

        super_x, super_y = SCREEN_W - 210, SCREEN_H - 40
        self.screen.blit(self.small_font.render("SUPER [SPACE]", True, (218, 233, 243)), (super_x, super_y - 23))
        super_color = (255, 202, 75) if player["super"] >= 100 else (102, 197, 246)
        self.draw_bar(super_x, super_y, 176, 13, player["super"] / 100, super_color, (40, 49, 62))
        if player["super"] >= 100:
            pygame.draw.circle(self.screen, (255, 217, 90), (super_x + 190, super_y + 6), 7)

        help_text = "WASD bewegen  |  Maus zielen & halten: schiessen  |  SPACE: Dash / Super"
        help_surface = self.small_font.render(help_text, True, (208, 224, 230))
        self.screen.blit(help_surface, help_surface.get_rect(center=(SCREEN_W // 2, SCREEN_H - 19)))

        if self.game_state != "playing":
            overlay = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
            overlay.fill((9, 15, 25, 205))
            self.screen.blit(overlay, (0, 0))
            title = "SIEG!" if self.game_state == "won" else "AUSGESCHALTET"
            subtitle = "Du hast die Arena gemeistert." if self.game_state == "won" else "Die Bots waren staerker."
            title_surface = self.title_font.render(title, True, (237, 247, 255))
            sub_surface = self.font.render(subtitle, True, (181, 201, 216))
            restart = self.small_font.render("R: Nochmal spielen     ESC: Beenden", True, (134, 202, 234))
            self.screen.blit(title_surface, title_surface.get_rect(center=(SCREEN_W // 2, SCREEN_H // 2 - 46)))
            self.screen.blit(sub_surface, sub_surface.get_rect(center=(SCREEN_W // 2, SCREEN_H // 2 + 4)))
            self.screen.blit(restart, restart.get_rect(center=(SCREEN_W // 2, SCREEN_H // 2 + 48)))
        pygame.display.flip()
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

    def draw_power_cube_legacy(self, cube, camera_x, camera_y):
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
        pygame.draw.circle(self.screen, (57, 155, 83), (x, y), 19)
        pygame.draw.polygon(self.screen, (117, 255, 139), points)
        pygame.draw.polygon(self.screen, (233, 255, 208), points, 2)
        pygame.draw.circle(self.screen, (255, 255, 255), (x - 3, y - 4), 2)

    def draw_legacy(self):
        if self.game_state == "menu":
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
        self.screen.blit(self.small_font.render(f"ELIMS  {self.kills}/10", True, (206, 224, 230)), (38, 81))
        cube_label = self.small_font.render(f"POWER CUBES  x{player['cubes']}", True, (162, 255, 174))
        self.screen.blit(cube_label, (370, 31))

        super_x, super_y = SCREEN_W - 210, SCREEN_H - 40
        self.screen.blit(self.small_font.render("SUPER [SPACE]", True, (218, 233, 243)), (super_x, super_y - 23))
        super_color = (255, 202, 75) if player["super"] >= 100 else (102, 197, 246)
        self.draw_bar(super_x, super_y, 176, 13, player["super"] / 100, super_color, (40, 49, 62))
        if player["super"] >= 100:
            pygame.draw.circle(self.screen, (255, 217, 90), (super_x + 190, super_y + 6), 7)

        help_text = "WASD bewegen  |  Maus zielen & halten: schiessen  |  SPACE: Dash / Super"
        help_surface = self.small_font.render(help_text, True, (208, 224, 230))
        self.screen.blit(help_surface, help_surface.get_rect(center=(SCREEN_W // 2, SCREEN_H - 19)))

        if self.game_state != "playing":
            overlay = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
            overlay.fill((9, 15, 25, 205))
            self.screen.blit(overlay, (0, 0))
            title = "SIEG!" if self.game_state == "won" else "AUSGESCHALTET"
            subtitle = "Du hast die Arena gemeistert." if self.game_state == "won" else "Die Bots waren staerker."
            title_surface = self.title_font.render(title, True, (237, 247, 255))
            sub_surface = self.font.render(subtitle, True, (181, 201, 216))
            restart = self.small_font.render("R: Nochmal spielen     ESC: Beenden", True, (134, 202, 234))
            self.screen.blit(title_surface, title_surface.get_rect(center=(SCREEN_W // 2, SCREEN_H // 2 - 46)))
            self.screen.blit(sub_surface, sub_surface.get_rect(center=(SCREEN_W // 2, SCREEN_H // 2 + 4)))
            self.screen.blit(restart, restart.get_rect(center=(SCREEN_W // 2, SCREEN_H // 2 + 48)))
        pygame.display.flip()

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
