import math
import random
import tkinter as tk
from dataclasses import dataclass


WINDOW_W = 1100
WINDOW_H = 720
CANVAS_W = 820
CANVAS_H = 700
PANEL_W = WINDOW_W - CANVAS_W

ROAD_CENTER = CANVAS_W // 2
PLAYER_Y = CANVAS_H - 135
BIKE_W = 28
BIKE_H = 46
FINISH_DISTANCE = 5200


def clamp(value, low, high):
    return max(low, min(high, value))


@dataclass(frozen=True)
class Track:
    key: str
    name: str
    road_width: int
    lane_count: int
    bg: str
    road: str
    road_edge: str
    lane: str
    accent: str
    obstacle_rate: float
    traffic_rate: float
    opponent_count: int
    description: str


@dataclass
class Rider:
    name: str
    x: float
    y: float
    color: str
    speed: float
    hp: int = 3
    wobble: float = 0.0
    attack_cooldown: int = 0
    stun: int = 0
    distance: float = 0.0
    active: bool = True


@dataclass
class Obstacle:
    x: float
    y: float
    size: int
    kind: str


TRACKS = [
    Track(
        key="coast",
        name="海岸公路",
        road_width=430,
        lane_count=3,
        bg="#9ED7E8",
        road="#59606B",
        road_edge="#F6E7A8",
        lane="#F8F9D7",
        accent="#2A9D8F",
        obstacle_rate=0.035,
        traffic_rate=0.012,
        opponent_count=7,
        description="宽阔清爽，适合熟悉操作。",
    ),
    Track(
        key="city",
        name="霓虹城区",
        road_width=380,
        lane_count=4,
        bg="#263042",
        road="#404856",
        road_edge="#FFBE0B",
        lane="#CDE7FF",
        accent="#FF006E",
        obstacle_rate=0.05,
        traffic_rate=0.018,
        opponent_count=9,
        description="车多路窄，节奏更快。",
    ),
    Track(
        key="desert",
        name="荒漠峡谷",
        road_width=360,
        lane_count=3,
        bg="#E9C46A",
        road="#76513B",
        road_edge="#F4A261",
        lane="#FFE8B6",
        accent="#E76F51",
        obstacle_rate=0.06,
        traffic_rate=0.01,
        opponent_count=8,
        description="障碍密集，容错较低。",
    ),
    Track(
        key="forest",
        name="森林山路",
        road_width=340,
        lane_count=3,
        bg="#4E8F57",
        road="#4C5B4D",
        road_edge="#B7E4A8",
        lane="#E7F6D5",
        accent="#95D5B2",
        obstacle_rate=0.052,
        traffic_rate=0.012,
        opponent_count=10,
        description="弯道感更强，对手很多。",
    ),
    Track(
        key="snow",
        name="雪原赛道",
        road_width=400,
        lane_count=3,
        bg="#DFF7FF",
        road="#718096",
        road_edge="#FFFFFF",
        lane="#EAFBFF",
        accent="#00B4D8",
        obstacle_rate=0.045,
        traffic_rate=0.014,
        opponent_count=8,
        description="路面打滑，转向更飘。",
    ),
]


class RoadRageGame:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("暴力摩托 - Road Rage")
        self.root.geometry(f"{WINDOW_W}x{WINDOW_H}")
        self.root.resizable(False, False)

        self.canvas = tk.Canvas(root, width=CANVAS_W, height=CANVAS_H, highlightthickness=0)
        self.canvas.pack(side="left", padx=(10, 0), pady=10)

        self.panel = tk.Frame(root, width=PANEL_W - 20, height=CANVAS_H, bg="#F4F1DE")
        self.panel.pack(side="left", fill="y", padx=10, pady=10)
        self.panel.pack_propagate(False)

        self.info_var = tk.StringVar()
        self.status_var = tk.StringVar()
        self.track: Track | None = None
        self.player: Rider | None = None
        self.opponents: list[Rider] = []
        self.obstacles: list[Obstacle] = []
        self.decorations: list[tuple[float, float, int, str]] = []
        self.keys: set[str] = set()
        self.mode = "menu"
        self.frame = 0
        self.countdown = 0
        self.camera_distance = 0.0
        self.road_curve = 0.0
        self.spawn_timer = 0
        self.finish_shown = False

        self.build_panel()
        self.bind_keys()
        self.show_menu()
        self.tick()

    def build_panel(self):
        tk.Label(
            self.panel,
            text="暴力摩托",
            font=("Microsoft YaHei UI", 22, "bold"),
            fg="#263238",
            bg="#F4F1DE",
        ).pack(anchor="w", pady=(8, 12))

        tk.Label(
            self.panel,
            textvariable=self.info_var,
            justify="left",
            anchor="nw",
            font=("Microsoft YaHei UI", 11),
            fg="#2F3E46",
            bg="#FFF8E8",
            padx=12,
            pady=12,
            wraplength=230,
        ).pack(fill="x", pady=(0, 12))

        tk.Label(
            self.panel,
            text="按键提示",
            font=("Microsoft YaHei UI", 14, "bold"),
            fg="#263238",
            bg="#F4F1DE",
        ).pack(anchor="w")

        key_text = (
            "W / ↑：加速\n"
            "S / ↓：刹车\n"
            "A / ←：左转\n"
            "D / →：右转\n"
            "空格：攻击附近选手\n"
            "R：重开当前赛道\n"
            "Esc：返回赛道选择"
        )
        tk.Label(
            self.panel,
            text=key_text,
            justify="left",
            font=("Microsoft YaHei UI", 11),
            fg="#475569",
            bg="#F4F1DE",
            pady=8,
        ).pack(anchor="w", fill="x")

        tk.Label(
            self.panel,
            textvariable=self.status_var,
            justify="left",
            anchor="nw",
            font=("Microsoft YaHei UI", 10, "bold"),
            fg="#B35C00",
            bg="#F4F1DE",
            wraplength=240,
        ).pack(anchor="w", fill="x", pady=(16, 0))

    def bind_keys(self):
        self.root.bind("<KeyPress>", self.on_key_down)
        self.root.bind("<KeyRelease>", self.on_key_up)
        self.root.focus_set()

    def on_key_down(self, event):
        key = event.keysym.lower()
        self.keys.add(key)

        if self.mode == "menu":
            if key in {"1", "2", "3", "4", "5"}:
                index = int(key) - 1
                if 0 <= index < len(TRACKS):
                    self.start_track(TRACKS[index])
            return

        if key == "escape":
            self.show_menu()
        elif key == "r" and self.track:
            self.start_track(self.track)
        elif key == "space" and self.mode == "race":
            self.player_attack()

    def on_key_up(self, event):
        self.keys.discard(event.keysym.lower())

    def show_menu(self):
        self.mode = "menu"
        self.track = None
        self.keys.clear()
        self.canvas.delete("all")
        self.canvas.configure(bg="#BEE3DB")
        self.status_var.set("请选择一条赛道开始比赛。")
        self.info_var.set(
            "赛道选择\n\n"
            "点击画面中的赛道卡片，或按数字 1-5 快速开始。\n\n"
            "目标：躲避障碍、攻击对手，尽快冲过终点。"
        )
        self.draw_track_menu()

    def draw_track_menu(self):
        self.canvas.delete("all")
        self.canvas.create_rectangle(0, 0, CANVAS_W, CANVAS_H, fill="#BEE3DB", outline="")
        self.canvas.create_text(
            CANVAS_W // 2,
            62,
            text="选择赛道",
            fill="#173B33",
            font=("Microsoft YaHei UI", 32, "bold"),
        )
        self.canvas.create_text(
            CANVAS_W // 2,
            108,
            text="不同赛道拥有不同宽度、障碍密度和对手数量",
            fill="#315C54",
            font=("Microsoft YaHei UI", 13),
        )

        for index, track in enumerate(TRACKS):
            x = 95 + (index % 2) * 360
            y = 160 + (index // 2) * 150
            self.draw_track_card(index, track, x, y)

        self.canvas.bind("<Button-1>", self.on_menu_click)

    def draw_track_card(self, index, track, x, y):
        self.canvas.create_rectangle(x + 5, y + 8, x + 305, y + 120, fill="#83A79E", outline="")
        self.canvas.create_rectangle(x, y, x + 300, y + 112, fill="#FFF8E8", outline="#FFFFFF", width=3)
        self.canvas.create_rectangle(x, y, x + 300, y + 34, fill=track.accent, outline="")
        self.canvas.create_text(
            x + 18,
            y + 17,
            text=f"{index + 1}. {track.name}",
            anchor="w",
            fill="#FFFFFF",
            font=("Microsoft YaHei UI", 14, "bold"),
        )
        self.canvas.create_text(
            x + 18,
            y + 53,
            text=track.description,
            anchor="w",
            fill="#2F3E46",
            font=("Microsoft YaHei UI", 10),
        )
        self.canvas.create_text(
            x + 18,
            y + 82,
            text=f"道路宽度 {track.road_width} · 对手 {track.opponent_count} · 车道 {track.lane_count}",
            anchor="w",
            fill="#64748B",
            font=("Microsoft YaHei UI", 9),
        )

    def on_menu_click(self, event):
        if self.mode != "menu":
            return
        for index, track in enumerate(TRACKS):
            x = 95 + (index % 2) * 360
            y = 160 + (index // 2) * 150
            if x <= event.x <= x + 300 and y <= event.y <= y + 112:
                self.start_track(track)
                return

    def start_track(self, track: Track):
        self.canvas.unbind("<Button-1>")
        self.track = track
        self.mode = "countdown"
        self.frame = 0
        self.countdown = 120
        self.camera_distance = 0.0
        self.road_curve = 0.0
        self.spawn_timer = 0
        self.finish_shown = False
        self.obstacles = []
        self.decorations = []
        self.player = Rider("玩家", ROAD_CENTER, PLAYER_Y, "#00B4D8", 0, hp=5)
        self.opponents = self.make_opponents(track)
        self.make_decorations(track)
        self.status_var.set("倒计时结束后出发，准备加速！")
        self.update_info()

    def make_opponents(self, track):
        colors = ["#E63946", "#F77F00", "#8338EC", "#2A9D8F", "#FF006E", "#118AB2", "#BC6C25"]
        names = ["疾风", "黑豹", "赤焰", "猎鹰", "野狼", "闪电", "钢牙", "幽灵", "山猫", "毒蜂"]
        riders = []
        road_left, road_right = self.road_bounds()
        for index in range(track.opponent_count):
            x = random.uniform(road_left + 40, road_right - 40)
            y = PLAYER_Y - 80 - index * random.uniform(42, 78)
            speed = random.uniform(4.2, 6.8)
            riders.append(Rider(names[index % len(names)], x, y, colors[index % len(colors)], speed))
        return riders

    def make_decorations(self, track):
        self.decorations = []
        for _ in range(60):
            side = random.choice([-1, 1])
            road_left, road_right = self.road_bounds()
            x = random.uniform(15, road_left - 20) if side < 0 else random.uniform(road_right + 20, CANVAS_W - 15)
            y = random.uniform(-CANVAS_H, CANVAS_H * 2)
            size = random.randint(8, 22)
            color = random.choice([track.accent, "#FFFFFF", "#31572C", "#F4A261"])
            self.decorations.append((x, y, size, color))

    def road_bounds(self):
        width = self.track.road_width if self.track else 400
        return ROAD_CENTER - width // 2, ROAD_CENTER + width // 2

    def update_info(self):
        if not self.track or not self.player:
            return
        rank = self.current_rank()
        distance = min(FINISH_DISTANCE, int(self.camera_distance))
        self.info_var.set(
            f"赛道：{self.track.name}\n"
            f"生命：{'♥' * max(0, self.player.hp)}\n"
            f"速度：{self.player.speed:.1f}\n"
            f"名次：{rank}/{len(self.opponents) + 1}\n"
            f"进度：{distance}/{FINISH_DISTANCE}\n"
            f"对手：{sum(1 for rider in self.opponents if rider.active)} 人仍在比赛"
        )

    def current_rank(self):
        if not self.player:
            return 1
        distances = [self.camera_distance]
        distances.extend(rider.distance for rider in self.opponents if rider.active)
        return 1 + sum(1 for distance in distances if distance > self.camera_distance)

    def tick(self):
        if self.mode == "menu":
            pass
        elif self.mode == "countdown":
            self.update_countdown()
        elif self.mode == "race":
            self.update_race()
        elif self.mode in {"win", "lose"}:
            self.draw_race()
            self.draw_end_banner()
        self.root.after(33, self.tick)

    def update_countdown(self):
        self.countdown -= 1
        if self.countdown <= 0:
            self.mode = "race"
            self.status_var.set("比赛开始！靠近对手后按空格攻击。")
        self.draw_race()
        number = max(1, math.ceil(self.countdown / 40))
        text = "GO!" if self.countdown <= 12 else str(number)
        self.canvas.create_text(
            CANVAS_W // 2,
            CANVAS_H // 2,
            text=text,
            fill="#FFF8E8",
            font=("Microsoft YaHei UI", 54, "bold"),
        )

    def update_race(self):
        self.frame += 1
        self.handle_player_input()
        self.update_player()
        self.update_opponents()
        self.spawn_obstacles()
        self.update_obstacles()
        self.check_collisions()
        self.camera_distance += max(1.0, self.player.speed) * 1.1
        self.road_curve = math.sin((self.camera_distance + self.frame * 3) / 360) * 55

        if self.player.hp <= 0:
            self.mode = "lose"
            self.status_var.set("摩托损坏，比赛失败。按 R 重新挑战。")
        elif self.camera_distance >= FINISH_DISTANCE:
            self.mode = "win"
            self.status_var.set("冲过终点！按 Esc 返回赛道选择。")

        self.draw_race()
        self.update_info()

    def handle_player_input(self):
        if not self.player:
            return

        accel = "w" in self.keys or "up" in self.keys
        brake = "s" in self.keys or "down" in self.keys
        left = "a" in self.keys or "left" in self.keys
        right = "d" in self.keys or "right" in self.keys

        max_speed = 9.5
        turn_factor = 1.0
        if self.track and self.track.key == "snow":
            turn_factor = 0.72

        if accel:
            self.player.speed += 0.18
        else:
            self.player.speed -= 0.045
        if brake:
            self.player.speed -= 0.22

        self.player.speed = clamp(self.player.speed, 1.8, max_speed)

        steer = 0
        if left:
            steer -= 1
        if right:
            steer += 1
        self.player.x += steer * (3.8 + self.player.speed * 0.28) * turn_factor

    def update_player(self):
        road_left, road_right = self.road_bounds()
        curve = self.road_curve * 0.18
        self.player.x = clamp(self.player.x, road_left + 22 + curve, road_right - 22 + curve)
        if self.player.attack_cooldown > 0:
            self.player.attack_cooldown -= 1
        if self.player.stun > 0:
            self.player.stun -= 1
            self.player.speed = max(1.8, self.player.speed - 0.06)

    def update_opponents(self):
        road_left, road_right = self.road_bounds()
        for rider in self.opponents:
            if not rider.active:
                continue
            rider.distance += rider.speed
            rider.y += (self.player.speed - rider.speed) * 1.9
            target_x = ROAD_CENTER + math.sin((self.frame + rider.wobble) / 42) * (self.track.road_width * 0.34)
            rider.x += (target_x - rider.x) * 0.025
            rider.x = clamp(rider.x, road_left + 24, road_right - 24)
            rider.wobble += random.uniform(-0.3, 0.7)
            if rider.stun > 0:
                rider.stun -= 1
                rider.speed = max(2.4, rider.speed - 0.05)
            else:
                rider.speed = clamp(rider.speed + random.uniform(-0.04, 0.05), 3.3, 8.2)

            if rider.y > CANVAS_H + 80:
                rider.y = random.uniform(-360, -120)
                rider.x = random.uniform(road_left + 35, road_right - 35)
            elif rider.y < -520:
                rider.y = random.uniform(-260, -80)

    def spawn_obstacles(self):
        if not self.track:
            return
        self.spawn_timer += 1
        chance = self.track.obstacle_rate + self.player.speed * 0.002
        if random.random() < chance:
            road_left, road_right = self.road_bounds()
            kind = random.choice(["barrel", "cone", "stone", "oil"])
            size = random.randint(22, 38)
            self.obstacles.append(
                Obstacle(
                    x=random.uniform(road_left + 36, road_right - 36),
                    y=-60,
                    size=size,
                    kind=kind,
                )
            )

    def update_obstacles(self):
        scroll = self.player.speed * 3.2
        for obstacle in self.obstacles:
            obstacle.y += scroll
        self.obstacles = [obstacle for obstacle in self.obstacles if obstacle.y < CANVAS_H + 80]

    def check_collisions(self):
        for obstacle in self.obstacles[:]:
            if self.hit_rect(self.player.x, PLAYER_Y, BIKE_W, BIKE_H, obstacle.x, obstacle.y, obstacle.size, obstacle.size):
                self.obstacles.remove(obstacle)
                self.player.hp -= 1
                self.player.speed = max(1.8, self.player.speed - 2.4)
                self.player.stun = 20
                self.status_var.set("撞上障碍物！生命 -1。")
                continue

            for rider in self.opponents:
                if rider.active and self.hit_rect(rider.x, rider.y, BIKE_W, BIKE_H, obstacle.x, obstacle.y, obstacle.size, obstacle.size):
                    rider.hp -= 1
                    rider.stun = 20
                    rider.speed = max(2.2, rider.speed - 1.4)
                    if rider.hp <= 0:
                        rider.active = False
                    if obstacle in self.obstacles:
                        self.obstacles.remove(obstacle)
                    break

        for rider in self.opponents:
            if not rider.active:
                continue
            if self.hit_rect(self.player.x, PLAYER_Y, BIKE_W, BIKE_H, rider.x, rider.y, BIKE_W, BIKE_H):
                push = -1 if rider.x < self.player.x else 1
                self.player.x += push * 10
                rider.x -= push * 12
                self.player.speed = max(1.8, self.player.speed - 0.45)

    @staticmethod
    def hit_rect(ax, ay, aw, ah, bx, by, bw, bh):
        return abs(ax - bx) < (aw + bw) / 2 and abs(ay - by) < (ah + bh) / 2

    def player_attack(self):
        if not self.player or self.player.attack_cooldown > 0:
            return

        self.player.attack_cooldown = 24
        hit_any = False
        for rider in self.opponents:
            if not rider.active:
                continue
            distance = math.hypot(rider.x - self.player.x, rider.y - PLAYER_Y)
            if distance <= 72:
                rider.hp -= 1
                rider.stun = 35
                rider.speed = max(2.1, rider.speed - 1.8)
                rider.x += 38 if rider.x >= self.player.x else -38
                hit_any = True
                if rider.hp <= 0:
                    rider.active = False
                    self.status_var.set(f"击倒了 {rider.name}！")
                else:
                    self.status_var.set(f"攻击命中 {rider.name}！")
                break

        if not hit_any:
            self.status_var.set("挥空了，靠近其它选手再攻击。")

    def draw_race(self):
        track = self.track
        if not track:
            return

        self.canvas.delete("all")
        self.canvas.configure(bg=track.bg)
        self.draw_scenery(track)
        self.draw_road(track)
        for obstacle in self.obstacles:
            self.draw_obstacle(obstacle)
        for rider in sorted([r for r in self.opponents if r.active], key=lambda item: item.y):
            self.draw_bike(rider.x, rider.y, rider.color, rider.name, rider.hp, is_player=False)
        attack_flash = self.player.attack_cooldown > 17 if self.player else False
        self.draw_bike(self.player.x, PLAYER_Y, self.player.color, "玩家", self.player.hp, is_player=True, attack_flash=attack_flash)
        self.draw_progress_bar()

    def draw_scenery(self, track):
        self.canvas.create_rectangle(0, 0, CANVAS_W, CANVAS_H, fill=track.bg, outline="")
        scroll = (self.camera_distance * 0.7) % CANVAS_H
        for x, y, size, color in self.decorations:
            draw_y = (y + scroll) % (CANVAS_H + 120) - 60
            if track.key == "city":
                self.canvas.create_rectangle(x - size, draw_y - size, x + size, draw_y + size * 2, fill="#1F2937", outline="")
                self.canvas.create_rectangle(x - size // 2, draw_y - size // 2, x - 2, draw_y - 2, fill=color, outline="")
                self.canvas.create_rectangle(x + 2, draw_y - size // 2, x + size // 2, draw_y - 2, fill=color, outline="")
            elif track.key == "desert":
                self.canvas.create_oval(x - size, draw_y - size // 2, x + size, draw_y + size // 2, fill="#DDA15E", outline="")
                self.canvas.create_line(x, draw_y - size, x, draw_y + size, fill="#7F5539", width=3)
            elif track.key == "snow":
                self.canvas.create_oval(x - size, draw_y - size, x + size, draw_y + size, fill="#FFFFFF", outline="#BDE0FE")
            else:
                self.canvas.create_oval(x - size, draw_y - size, x + size, draw_y + size, fill=color, outline="")
                self.canvas.create_rectangle(x - 3, draw_y, x + 3, draw_y + size + 12, fill="#6B4F2A", outline="")

    def draw_road(self, track):
        road_left, road_right = self.road_bounds()
        curve = self.road_curve
        points = [
            road_left + curve * 0.4,
            0,
            road_right + curve * 0.4,
            0,
            road_right - curve * 0.18,
            CANVAS_H,
            road_left - curve * 0.18,
            CANVAS_H,
        ]
        self.canvas.create_polygon(points, fill=track.road, outline=track.road_edge, width=8)

        lane_gap = track.road_width / track.lane_count
        dash_offset = (self.camera_distance * 2.2) % 56
        for lane in range(1, track.lane_count):
            x_top = road_left + lane * lane_gap + curve * 0.4
            x_bottom = road_left + lane * lane_gap - curve * 0.18
            for y in range(-60, CANVAS_H + 80, 56):
                y1 = y + dash_offset
                y2 = y1 + 30
                t1 = y1 / CANVAS_H
                t2 = y2 / CANVAS_H
                x1 = x_top + (x_bottom - x_top) * t1
                x2 = x_top + (x_bottom - x_top) * t2
                self.canvas.create_line(x1, y1, x2, y2, fill=track.lane, width=4)

    def draw_obstacle(self, obstacle):
        x, y, s = obstacle.x, obstacle.y, obstacle.size
        if obstacle.kind == "cone":
            self.canvas.create_polygon(x, y - s // 2, x - s // 2, y + s // 2, x + s // 2, y + s // 2, fill="#F97316", outline="#7C2D12", width=2)
            self.canvas.create_line(x - s // 4, y, x + s // 4, y, fill="#FFF7ED", width=3)
        elif obstacle.kind == "oil":
            self.canvas.create_oval(x - s, y - s // 2, x + s, y + s // 2, fill="#111827", outline="#374151")
            self.canvas.create_arc(x - s // 2, y - s // 3, x + s // 2, y + s // 3, start=20, extent=120, outline="#6B7280", width=2)
        elif obstacle.kind == "stone":
            self.canvas.create_oval(x - s // 2, y - s // 2, x + s // 2, y + s // 2, fill="#78716C", outline="#44403C", width=2)
        else:
            self.canvas.create_rectangle(x - s // 2, y - s // 2, x + s // 2, y + s // 2, fill="#B45309", outline="#7C2D12", width=2)
            self.canvas.create_arc(x - s // 2, y - s // 2, x + s // 2, y + s // 2, start=0, extent=180, outline="#FDE68A", width=3)

    def draw_bike(self, x, y, color, name, hp, is_player=False, attack_flash=False):
        shadow = "#000000"
        self.canvas.create_oval(x - 22, y + 18, x + 22, y + 30, fill=shadow, outline="", stipple="gray50")
        self.canvas.create_oval(x - 15, y + 12, x - 3, y + 28, fill="#1F2937", outline="#111827")
        self.canvas.create_oval(x + 3, y + 12, x + 15, y + 28, fill="#1F2937", outline="#111827")
        self.canvas.create_rectangle(x - 10, y - 22, x + 10, y + 22, fill=color, outline="#172554", width=2)
        self.canvas.create_polygon(x - 14, y - 14, x, y - 36, x + 14, y - 14, fill=color, outline="#172554", width=2)
        self.canvas.create_oval(x - 9, y - 48, x + 9, y - 30, fill="#FFE0B2", outline="#7C2D12")
        self.canvas.create_line(x - 18, y - 14, x - 34, y + 2, fill="#111827", width=4)
        self.canvas.create_line(x + 18, y - 14, x + 34, y + 2, fill="#111827", width=4)

        if attack_flash:
            self.canvas.create_arc(x - 78, y - 36, x + 78, y + 50, start=20, extent=140, outline="#FFD166", width=6)

        label_fill = "#FFFFFF" if is_player else "#F8FAFC"
        self.canvas.create_text(x, y - 62, text=name, fill=label_fill, font=("Microsoft YaHei UI", 9, "bold"))
        self.canvas.create_text(x, y - 74, text="♥" * max(0, hp), fill="#FF4D6D", font=("Microsoft YaHei UI", 8, "bold"))

    def draw_progress_bar(self):
        x1, y1, x2, y2 = 28, 22, CANVAS_W - 28, 38
        progress = clamp(self.camera_distance / FINISH_DISTANCE, 0, 1)
        self.canvas.create_rectangle(x1, y1, x2, y2, fill="#213547", outline="#FFFFFF", width=2)
        self.canvas.create_rectangle(x1, y1, x1 + (x2 - x1) * progress, y2, fill=self.track.accent, outline="")
        self.canvas.create_text((x1 + x2) / 2, y2 + 18, text="终点进度", fill="#FFFFFF", font=("Microsoft YaHei UI", 10, "bold"))

    def draw_end_banner(self):
        if self.mode == "win":
            title = "冲线成功！"
            sub = f"最终名次：{self.current_rank()}/{len(self.opponents) + 1}"
            color = "#2A9D8F"
        else:
            title = "比赛失败"
            sub = "摩托损坏，按 R 重新挑战"
            color = "#D62828"
        self.canvas.create_rectangle(145, 250, CANVAS_W - 145, 430, fill="#FFF8E8", outline=color, width=5)
        self.canvas.create_text(CANVAS_W // 2, 310, text=title, fill=color, font=("Microsoft YaHei UI", 34, "bold"))
        self.canvas.create_text(CANVAS_W // 2, 365, text=sub, fill="#263238", font=("Microsoft YaHei UI", 16, "bold"))
        self.canvas.create_text(CANVAS_W // 2, 398, text="Esc 返回赛道选择", fill="#64748B", font=("Microsoft YaHei UI", 11))


def main():
    root = tk.Tk()
    RoadRageGame(root)
    root.mainloop()


if __name__ == "__main__":
    main()
