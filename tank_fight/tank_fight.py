import math
import random
import tkinter as tk


WINDOW_W = 900
WINDOW_H = 650
CANVAS_W = 820
CANVAS_H = 580
UI_PAD_X = 40
TOP_UI_H = 70

CELL = 20
PLAYER_R = 16
TANK_HP_BASE = 1

BULLET_R = 4
BULLET_SPEED = 6.5


def clamp(v, lo, hi):
    return lo if v < lo else hi if v > hi else v


def circle_rect_distance_sq(cx, cy, rx1, ry1, rx2, ry2):
    # Distance from point (cx, cy) to axis-aligned rectangle.
    closest_x = clamp(cx, rx1, rx2)
    closest_y = clamp(cy, ry1, ry2)
    dx = cx - closest_x
    dy = cy - closest_y
    return dx * dx + dy * dy


class Obstacle:
    def __init__(self, x, y, w, h, hp=1):
        self.x = x
        self.y = y
        self.w = w
        self.h = h
        self.hp = hp

    @property
    def rect(self):
        return (self.x, self.y, self.x + self.w, self.y + self.h)

    def hit_point(self, px, py):
        x1, y1, x2, y2 = self.rect
        return x1 <= px <= x2 and y1 <= py <= y2

    def hit_circle(self, cx, cy, r):
        x1, y1, x2, y2 = self.rect
        return circle_rect_distance_sq(cx, cy, x1, y1, x2, y2) <= r * r


class Bullet:
    def __init__(self, x, y, vx, vy, owner: str):
        self.x = x
        self.y = y
        self.vx = vx
        self.vy = vy
        self.owner = owner  # "player" | "enemy"
        self.dead = False
        self.id = None

    def step(self):
        self.x += self.vx
        self.y += self.vy


class Tank:
    DIRS = [(0, -1), (1, 0), (0, 1), (-1, 0)]  # up, right, down, left

    def __init__(self, x, y, dir_idx=1, hp=1, speed=2.0, is_player=False):
        self.x = x
        self.y = y
        self.dir_idx = dir_idx
        self.hp = hp
        self.speed = speed
        self.is_player = is_player

        self.dead = False

        # movement intent
        self.want_dir = dir_idx
        self.id_body = None
        self.id_turret = None

        self.shoot_cd_ms = 800
        self.shoot_cd_left = 0

    @property
    def dir_vec(self):
        return Tank.DIRS[self.dir_idx]

    def set_dir(self, dir_idx):
        self.dir_idx = dir_idx
        self.want_dir = dir_idx

    def try_move(self, dx, dy, obstacles, bounds):
        # Treat tank as circle; block movement if it intersects an obstacle or boundary.
        nx = self.x + dx
        ny = self.y + dy

        left, top, right, bottom = bounds
        if nx - PLAYER_R < left or nx + PLAYER_R > right or ny - PLAYER_R < top or ny + PLAYER_R > bottom:
            return False

        for ob in obstacles:
            if ob.hit_circle(nx, ny, PLAYER_R):
                return False
        self.x = nx
        self.y = ny
        return True


class TankFightGame:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("坦克大战 - Tank Fight")
        self.root.resizable(False, False)

        self.bg = "#F6FBFF"
        self.panel_bg = "#FFFFFF"
        self.text_color = "#204A66"
        self.accent = "#2EC4B6"
        self.danger = "#D00000"
        self.enemy_color = "#FF6B6B"
        self.player_color = "#00BBF9"
        self.block_color = "#B7D7FF"
        self.block_dark = "#7FB3FF"

        self.canvas = tk.Canvas(root, width=CANVAS_W, height=CANVAS_H, bg=self.bg, highlightthickness=0)
        self.canvas.pack(side="left", padx=(10, 0), pady=10)

        right_panel = tk.Frame(root, width=WINDOW_W - CANVAS_W - 20, bg=self.bg)
        right_panel.pack(side="left", fill="y", padx=10, pady=10)

        self.score_var = tk.StringVar(value="积分: 0")
        self.level_var = tk.StringVar(value="关卡: 1")
        self.status_var = tk.StringVar(value="键位：方向键/WSAD 移动，空格发射，R 重开")

        top_label = tk.Label(
            right_panel,
            textvariable=self.score_var,
            font=("Segoe UI", 16, "bold"),
            fg=self.text_color,
            bg=self.bg,
            anchor="w",
            justify="left",
        )
        top_label.pack(fill="x", pady=(10, 6))

        level_label = tk.Label(
            right_panel,
            textvariable=self.level_var,
            font=("Segoe UI", 12, "bold"),
            fg=self.text_color,
            bg=self.bg,
            anchor="w",
            justify="left",
        )
        level_label.pack(fill="x", pady=(0, 10))

        status_label = tk.Label(
            right_panel,
            textvariable=self.status_var,
            font=("Segoe UI", 10),
            fg=self.text_color,
            bg=self.bg,
            anchor="nw",
            justify="left",
            wraplength=180,
        )
        status_label.pack(fill="x", pady=(0, 14))

        self.menu_frame = tk.Frame(right_panel, bg=self.panel_bg, bd=1, relief="solid")
        self.menu_frame.pack(fill="x", pady=(0, 10))

        self.menu_title = tk.Label(
            self.menu_frame,
            text="选择关卡（1-9）",
            font=("Segoe UI", 12, "bold"),
            fg=self.text_color,
            bg=self.panel_bg,
        )
        self.menu_title.pack(pady=(10, 6))

        btn_frame = tk.Frame(self.menu_frame, bg=self.panel_bg)
        btn_frame.pack(pady=(0, 10))

        self.level_buttons = []
        for i in range(1, 10):
            b = tk.Button(
                btn_frame,
                text=str(i),
                width=4,
                bg="#EAF2FF",
                fg=self.text_color,
                activebackground="#DDEBFF",
                relief="flat",
                command=lambda lv=i: self.start_level(lv),
            )
            b.grid(row=(i - 1) // 3, column=(i - 1) % 3, padx=6, pady=6)
            self.level_buttons.append(b)

        hint = tk.Label(
            self.menu_frame,
            text="击败所有敌人即通关。\n难度随关卡递增。",
            font=("Segoe UI", 9),
            fg=self.text_color,
            bg=self.panel_bg,
            justify="left",
        )
        hint.pack(pady=(0, 10), padx=10)

        self.overlay_id = None

        # Input
        self.keys = {"up": False, "right": False, "down": False, "left": False}
        self.shoot_pressed = False

        self.root.bind("<KeyPress>", self.on_key_press)
        self.root.bind("<KeyRelease>", self.on_key_release)

        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

        self.running = False
        self.in_game = False

        self.score = 0
        self.level = 1
        self.player = None
        self.enemies = []
        self.obstacles = []
        self.bullets = []

        self.game_speed_ms = 16
        self.after_id = None

        # Start with menu visible
        self.show_menu()

    def on_close(self):
        self.running = False
        self.root.destroy()

    def show_menu(self):
        self.in_game = False
        self.running = False
        if self.after_id is not None:
            try:
                self.root.after_cancel(self.after_id)
            except Exception:
                pass
            self.after_id = None

        self.canvas.delete("all")
        self.overlay_id = None
        self.menu_frame.tkraise()

    def set_overlay_text(self, text, color):
        self.canvas.delete("overlay")
        self.overlay_id = self.canvas.create_text(
            CANVAS_W // 2,
            CANVAS_H // 2,
            text=text,
            fill=color,
            font=("Segoe UI", 28, "bold"),
            tags=("overlay",),
        )

    def on_key_press(self, event):
        if event.keysym in ("Up", "w", "W"):
            self.keys["up"] = True
        elif event.keysym in ("Right", "d", "D"):
            self.keys["right"] = True
        elif event.keysym in ("Down", "s", "S"):
            self.keys["down"] = True
        elif event.keysym in ("Left", "a", "A"):
            self.keys["left"] = True
        elif event.keysym == "space":
            self.shoot_pressed = True
        elif event.keysym in ("r", "R", "Return"):
            # restart current level if in game
            if self.in_game:
                self.start_level(self.level)
            else:
                self.show_menu()

    def on_key_release(self, event):
        if event.keysym in ("Up", "w", "W"):
            self.keys["up"] = False
        elif event.keysym in ("Right", "d", "D"):
            self.keys["right"] = False
        elif event.keysym in ("Down", "s", "S"):
            self.keys["down"] = False
        elif event.keysym in ("Left", "a", "A"):
            self.keys["left"] = False
        elif event.keysym == "space":
            self.shoot_pressed = False

    def compute_player_dir(self):
        # Priority: if multiple keys pressed, pick in order U R D L
        if self.keys["up"]:
            return 0
        if self.keys["right"]:
            return 1
        if self.keys["down"]:
            return 2
        if self.keys["left"]:
            return 3
        return None

    def start_level(self, lv: int):
        self.level = int(lv)
        self.level_var.set(f"关卡: {self.level}")
        self.score = 0
        self.score_var.set(f"积分: {self.score}")
        self.status_var.set("战斗中！击败所有敌人。")

        self.menu_frame.lower()

        self.canvas.delete("all")
        self.overlay_id = None

        self.player = None
        self.enemies = []
        self.obstacles = []
        self.bullets = []

        self.build_map_and_entities(self.level)

        self.running = True
        self.in_game = True
        self.schedule_tick()

    def bounds(self):
        # Keep a bit of padding around edges inside the canvas.
        pad = 18
        return (pad, TOP_UI_H + pad, CANVAS_W - pad, CANVAS_H - pad)

    def build_map_and_entities(self, lv: int):
        b = self.bounds()
        left, top, right, bottom = b

        # Subtle background grid / boundary
        self.canvas.create_rectangle(left, top, right, bottom, outline="#DDEBFF", width=2)

        # Obstacles: generate a deterministic layout by level
        random.seed(1000 + lv)
        obstacle_count = 8 + lv * 2
        block_hp = 1 + (lv // 3)

        # Place blocks on grid, avoiding player start and enemy start region
        self.obstacles = []

        # define forbidden zones (player and enemy spawn rectangles)
        player_zone = (CANVAS_W * 0.5 - 80, CANVAS_H * 0.86 - 80, CANVAS_W * 0.5 + 80, CANVAS_H * 0.86 + 80)
        enemy_zone = (CANVAS_W * 0.5 - 80, TOP_UI_H + 60 - 40, CANVAS_W * 0.5 + 80, TOP_UI_H + 120 + 40)

        def in_forbidden(x, y, w, h):
            fx1, fy1, fx2, fy2 = player_zone
            if x >= fx1 and x + w <= fx2 and y >= fy1 and y + h <= fy2:
                return True
            ex1, ey1, ex2, ey2 = enemy_zone
            if x >= ex1 and x + w <= ex2 and y >= ey1 and y + h <= ey2:
                return True
            return False

        # Convert bounds to grid cells
        min_x = int(left // CELL)
        max_x = int(right // CELL)
        min_y = int(top // CELL)
        max_y = int(bottom // CELL)

        placed = 0
        tries = 0
        while placed < obstacle_count and tries < obstacle_count * 30:
            tries += 1
            gx = random.randint(min_x, max_x - 2)
            gy = random.randint(min_y, max_y - 2)
            w = CELL
            h = CELL
            x = gx * CELL
            y = gy * CELL

            # Avoid edges and UI
            if y < TOP_UI_H + 40:
                continue
            if in_forbidden(x, y, w, h):
                continue

            # Avoid overlapping existing blocks
            ok = True
            for ob in self.obstacles:
                if abs(ob.x - x) < CELL and abs(ob.y - y) < CELL:
                    ok = False
                    break
            if not ok:
                continue

            # Place
            hp = block_hp if random.random() < 0.35 else 1
            self.obstacles.append(Obstacle(x, y, w, h, hp=hp))
            placed += 1

        # Player tank
        px = CANVAS_W * 0.5
        py = CANVAS_H - 90
        self.player = Tank(px, py, dir_idx=0, hp=3, speed=2.6, is_player=True)
        self.player.shoot_cd_ms = 420

        # Enemies
        enemy_count = 2 + lv  # 3..11
        enemy_speed = 1.8 + lv * 0.18
        enemy_hp = TANK_HP_BASE + (lv // 3)
        enemy_cd = max(180, 900 - lv * 70)  # ms

        spawn_points = []
        # spawn on grid near top
        random.seed(2000 + lv)
        for _ in range(80):
            sx = random.randint(int(CANVAS_W * 0.18), int(CANVAS_W * 0.82))
            sy = random.randint(int(TOP_UI_H + 80), int(TOP_UI_H + 180))
            sx = int(sx // CELL) * CELL + CELL // 2
            sy = int(sy // CELL) * CELL + CELL // 2
            spawn_points.append((sx, sy))

        # Unique-ish spawn points
        random.shuffle(spawn_points)
        used = []
        self.enemies = []
        for i in range(enemy_count):
            # choose far enough from others
            for sp in spawn_points:
                sx, sy = sp
                ok = True
                for ux, uy in used:
                    if (sx - ux) ** 2 + (sy - uy) ** 2 < (CELL * 1.2) ** 2:
                        ok = False
                        break
                if ok:
                    used.append((sx, sy))
                    break
            else:
                sx, sy = spawn_points[-1]
                used.append((sx, sy))

            t = Tank(sx, sy, dir_idx=2, hp=enemy_hp, speed=enemy_speed, is_player=False)
            t.shoot_cd_ms = enemy_cd
            self.enemies.append(t)

    def schedule_tick(self):
        self.after_id = self.root.after(self.game_speed_ms, self.tick)

    def line_of_sight_clear(self, ax, ay, bx, by):
        # Only support same row/col approximate.
        if abs(ay - by) > 8 and abs(ax - bx) > 8:
            return False
        x1, y1 = ax, ay
        x2, y2 = bx, by

        # Sample along axis to see if any obstacle blocks the path.
        steps = int(max(abs(x2 - x1), abs(y2 - y1)) // 10) + 1
        if steps <= 0:
            steps = 1
        for i in range(1, steps):
            t = i / steps
            px = x1 + (x2 - x1) * t
            py = y1 + (y2 - y1) * t
            for ob in self.obstacles:
                if ob.hit_point(px, py):
                    return False
        return True

    def update_obstacle_draw(self):
        # Draw obstacles each frame (simple, but still fine for this small game).
        for idx, ob in enumerate(self.obstacles):
            x, y = ob.x, ob.y
            w, h = ob.w, ob.h
            shade = self.block_color if ob.hp <= 1 else self.block_dark
            self.canvas.create_rectangle(x, y, x + w, y + h, fill=shade, outline="", tags=("ob",))
            # tiny hp mark
            if ob.hp > 1:
                self.canvas.create_text(
                    x + w // 2,
                    y + h // 2,
                    text=str(ob.hp),
                    fill="#2B5DA8",
                    font=("Segoe UI", 9, "bold"),
                    tags=("ob",),
                )

    def draw_entities(self):
        # Static redraw strategy: clear only dynamic tags.
        self.canvas.delete("dyn")

        # Obstacles
        for ob in self.obstacles:
            x, y = ob.x, ob.y
            w, h = ob.w, ob.h
            shade = self.block_color if ob.hp <= 1 else self.block_dark
            self.canvas.create_rectangle(x, y, x + w, y + h, fill=shade, outline="", tags=("dyn", "ob"))

        # Player tank (menu 状态下 player 可能为 None)
        if self.player is not None and not self.player.dead:
            self.draw_tank(self.player, player=True)

        # Enemies
        for e in self.enemies:
            if e is not None and not e.dead:
                self.draw_tank(e, player=False)

        # Bullets
        for blt in self.bullets:
            if blt.dead:
                continue
            self.canvas.create_oval(
                blt.x - BULLET_R,
                blt.y - BULLET_R,
                blt.x + BULLET_R,
                blt.y + BULLET_R,
                fill="#333333" if blt.owner == "player" else self.enemy_color,
                outline="",
                tags=("dyn", "bullet"),
            )

    def draw_tank(self, tank: Tank, player: bool):
        if tank.dead:
            return

        dir_vec = tank.dir_vec
        dx, dy = dir_vec

        # Body
        body_color = self.player_color if player else self.enemy_color
        body = self.canvas.create_oval(
            tank.x - PLAYER_R,
            tank.y - PLAYER_R,
            tank.x + PLAYER_R,
            tank.y + PLAYER_R,
            fill=body_color,
            outline="",
            tags=("dyn", "tank"),
        )

        # Turret: a small rectangle in dir direction
        tx1 = tank.x + dx * (PLAYER_R - 2) - (-dy) * 6
        ty1 = tank.y + dy * (PLAYER_R - 2) - dx * 6
        tx2 = tank.x + dx * (PLAYER_R + 12) - (-dy) * 6
        ty2 = tank.y + dy * (PLAYER_R + 12) - dx * 6

        # The above is a rotated calc; for simplicity draw a line and a small cap circle.
        self.canvas.create_line(
            tank.x,
            tank.y,
            tank.x + dx * (PLAYER_R + 18),
            tank.y + dy * (PLAYER_R + 18),
            fill="#FFFFFF" if player else "#FFE6E6",
            width=4,
            tags=("dyn", "turret"),
        )
        self.canvas.create_oval(
            tank.x + dx * (PLAYER_R + 14) - 5,
            tank.y + dy * (PLAYER_R + 14) - 5,
            tank.x + dx * (PLAYER_R + 14) + 5,
            tank.y + dy * (PLAYER_R + 14) + 5,
            fill="#F7FBFF",
            outline="",
            tags=("dyn", "turret"),
        )

    def shoot_from_tank(self, tank: Tank, owner: str):
        if tank.shoot_cd_left > 0:
            return
        dx, dy = tank.dir_vec
        # Spawn bullet near turret tip
        sx = tank.x + dx * (PLAYER_R + 14)
        sy = tank.y + dy * (PLAYER_R + 14)
        vx = dx * BULLET_SPEED
        vy = dy * BULLET_SPEED
        self.bullets.append(Bullet(sx, sy, vx, vy, owner=owner))
        tank.shoot_cd_left = tank.shoot_cd_ms

    def tick(self):
        if not self.running:
            return

        dt_ms = self.game_speed_ms
        b = self.bounds()

        # Update timers
        if self.player is not None:
            self.player.shoot_cd_left = max(0, self.player.shoot_cd_left - dt_ms)
        for e in self.enemies:
            e.shoot_cd_left = max(0, e.shoot_cd_left - dt_ms)

        # Player movement + shooting
        if self.player is not None and not self.player.dead:
            dir_idx = self.compute_player_dir()
            if dir_idx is not None:
                self.player.set_dir(dir_idx)

            speed = self.player.speed
            dx, dy = self.player.dir_vec
            moved = False
            if self.keys["up"] or self.keys["down"] or self.keys["left"] or self.keys["right"]:
                # Move along current direction
                if self.player.try_move(dx * speed, dy * speed, self.obstacles, b):
                    moved = True
            # Shoot: space held
            if self.shoot_pressed and moved:
                # If player is not moving due to collision, still allow shooting.
                self.shoot_from_tank(self.player, owner="player")
            elif self.shoot_pressed and not moved:
                self.shoot_from_tank(self.player, owner="player")

        # Enemies: move toward player and shoot when aligned
        alive_enemies = [e for e in self.enemies if not e.dead]
        for e in alive_enemies:
            if self.player is None or self.player.dead:
                break

            px, py = self.player.x, self.player.y
            dx_to = px - e.x
            dy_to = py - e.y

            # Choose direction that brings closer along dominant axis.
            if abs(dx_to) > abs(dy_to):
                e.set_dir(1 if dx_to > 0 else 3)
            else:
                e.set_dir(2 if dy_to > 0 else 0)

            dx, dy = e.dir_vec
            step_dx = dx * e.speed
            step_dy = dy * e.speed
            e.try_move(step_dx, step_dy, self.obstacles, b)

            # Shoot when roughly aligned and within range.
            dist = math.hypot(px - e.x, py - e.y)
            aligned = (abs(px - e.x) < 60 and abs(py - e.y) > 10) or (abs(py - e.y) < 60 and abs(px - e.x) > 10)
            if aligned and dist < 380:
                # Only shoot if line-of-sight is clear
                if self.line_of_sight_clear(e.x, e.y, px, py):
                    self.shoot_from_tank(e, owner="enemy")

        # Bullets move + collisions
        for blt in self.bullets:
            if blt.dead:
                continue
            blt.step()

            # Bounds
            if blt.x < b[0] - 10 or blt.x > b[2] + 10 or blt.y < b[1] - 10 or blt.y > b[3] + 10:
                blt.dead = True
                continue

            # Obstacle collision
            hit_ob = None
            for ob in self.obstacles:
                if circle_rect_distance_sq(blt.x, blt.y, ob.x, ob.y, ob.x + ob.w, ob.y + ob.h) <= (BULLET_R + 2) ** 2:
                    hit_ob = ob
                    break
            if hit_ob is not None:
                hit_ob.hp -= 1
                blt.dead = True
                if hit_ob.hp <= 0:
                    self.obstacles.remove(hit_ob)
                    self.score += 10
                    self.score_var.set(f"积分: {self.score}")
                continue

            # Tank collision
            if blt.owner == "player":
                for e in alive_enemies:
                    if e.dead:
                        continue
                    if (blt.x - e.x) ** 2 + (blt.y - e.y) ** 2 <= (PLAYER_R + BULLET_R) ** 2:
                        e.hp -= 1
                        blt.dead = True
                        if e.hp <= 0:
                            e.dead = True
                            self.score += 100
                            self.score_var.set(f"积分: {self.score}")
                        break
            else:
                if self.player is not None and not self.player.dead:
                    if (blt.x - self.player.x) ** 2 + (blt.y - self.player.y) ** 2 <= (PLAYER_R + BULLET_R) ** 2:
                        self.player.hp -= 1
                        blt.dead = True
                        if self.player.hp <= 0:
                            self.player.dead = True
                            self.end_game(win=False)
                        break

        # Enemy body collision with player (simplify: if close enough => player dies)
        if self.player is not None and not self.player.dead:
            for e in alive_enemies:
                if e.dead:
                    continue
                if (e.x - self.player.x) ** 2 + (e.y - self.player.y) ** 2 <= (PLAYER_R * 1.8) ** 2:
                    self.player.dead = True
                    self.end_game(win=False)
                    break

        # Remove dead bullets
        self.bullets = [blt for blt in self.bullets if not blt.dead]

        # Win condition: all enemies dead
        if self.player is not None and not self.player.dead:
            if all(e.dead for e in self.enemies):
                self.end_game(win=True)
                return

        # Draw
        self.draw_entities()
        self.after_id = self.root.after(self.game_speed_ms, self.tick)

    def end_game(self, win: bool):
        self.running = False
        self.in_game = False

        final_score = self.score
        if win:
            self.status_var.set("通关！准备选择下一关或重开。")
            self.set_overlay_text(f"通关！\n积分: {final_score}", color="#1D8F3A")
        else:
            self.status_var.set("游戏结束！准备选择下一关或重开。")
            self.set_overlay_text(f"游戏结束\n积分: {final_score}", color=self.danger)

        # After a short delay, bring menu back.
        if self.after_id is not None:
            try:
                self.root.after_cancel(self.after_id)
            except Exception:
                pass
            self.after_id = None

        def back_to_menu():
            self.show_menu()

        self.root.after(1200, back_to_menu)

    def run(self):
        self.draw_entities()
        self.root.mainloop()


def main():
    root = tk.Tk()
    # Slightly improve default font on some systems
    try:
        root.option_add("*Font", ("Segoe UI", 10))
    except Exception:
        pass
    game = TankFightGame(root)
    game.run()


if __name__ == "__main__":
    main()

