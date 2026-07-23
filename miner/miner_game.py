import random
import tkinter as tk
from dataclasses import dataclass


WINDOW_W = 980
WINDOW_H = 680
FPS_MS = 33

TILE = 20
COLS = 48  # WINDOW_W ~ COLS*TILE
ROWS = 33  # WINDOW_H ~ ROWS*TILE

PANEL_H = 90
PLAY_TOP = PANEL_H
PLAY_H = ROWS * TILE

GROUND_ROW = ROWS - 2


T_EMPTY = 0
T_EARTH = 1
T_ROCK = 2
T_GOLD = 3


@dataclass
class Block:
    kind: int


class MinerGame:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("黄金矿工 - Miner")
        self.root.resizable(False, False)

        self.canvas = tk.Canvas(root, width=WINDOW_W, height=WINDOW_H, bg="#0b1220", highlightthickness=0)
        self.canvas.pack()

        self.restart_btn = tk.Button(root, text="重新开始", command=self.reset_game, font=("Microsoft YaHei UI", 12, "bold"))
        self.canvas.create_window(WINDOW_W - 140, 40, window=self.restart_btn)

        self.score = 0
        self.lives = 3
        self.gold_total = 0
        self.gold_left = 0
        self.game_over = False
        self.paused = False

        self.keys = set()
        self.facing = 1  # 1 right, -1 left

        # Player uses tile coordinates; position is float for smooth movement.
        self.px = 5
        self.py = GROUND_ROW - 1
        self.player_w = 0.75
        self.player_h = 0.9
        self.player_vx = 0.0
        self.player_vy = 0.0
        self.on_ground = False

        self.map = [[T_EARTH for _ in range(COLS)] for __ in range(ROWS)]
        self._bg_stars()
        self._init_ui_text()
        self.reset_game()
        self.root.bind("<KeyPress>", self.on_key_down)
        self.root.bind("<KeyRelease>", self.on_key_up)
        self.canvas.bind("<Button-1>", self.on_click_canvas)
        self.tick()

    def _bg_stars(self):
        random.seed(0)
        for _ in range(90):
            x = random.randint(0, WINDOW_W - 1)
            y = random.randint(0, PLAY_TOP + PLAY_H - 1)
            r = random.choice([1, 1, 2])
            self.canvas.create_oval(x - r, y - r, x + r, y + r, fill="#16233a", outline="")

    def _init_ui_text(self):
        self.ui_score = self.canvas.create_text(20, 26, text="分数: 0", fill="#dbeafe", font=("Microsoft YaHei UI", 14, "bold"), anchor="w")
        self.ui_lives = self.canvas.create_text(180, 26, text="生命: ♥♥♥", fill="#fecaca", font=("Microsoft YaHei UI", 14, "bold"), anchor="w")
        self.ui_gold = self.canvas.create_text(340, 26, text="金币: 0 / 0", fill="#fef08a", font=("Microsoft YaHei UI", 14, "bold"), anchor="w")
        self.ui_hint = self.canvas.create_text(
            20,
            60,
            text="方向键/A-D 移动，空格挖掘，R 重开，避免被岩石砸到。",
            fill="#93c5fd",
            font=("Microsoft YaHei UI", 11, "bold"),
            anchor="w",
        )

    def on_click_canvas(self, _event):
        if self.game_over:
            self.reset_game()

    def on_key_down(self, event):
        key = event.keysym.lower()
        self.keys.add(key)
        if key == "r":
            self.reset_game()
        if key in {"left", "a"}:
            self.facing = -1
        if key in {"right", "d"}:
            self.facing = 1
        if key == "escape":
            # Toggle pause for convenience.
            self.paused = not self.paused

    def on_key_up(self, event):
        self.keys.discard(event.keysym.lower())

    def reset_game(self):
        self.game_over = False
        self.paused = False

        self.score = 0
        self.lives = 3
        self.player_vx = 0.0
        self.player_vy = 0.0
        self.on_ground = False

        # Create terrain:
        # - Top area is empty (sky)
        # - Then earth.
        # - Add rock/gold pockets below with some empty tunnels.
        for r in range(ROWS):
            for c in range(COLS):
                if r < 6:
                    self.map[r][c] = T_EMPTY
                else:
                    self.map[r][c] = T_EARTH

        # Earth shape: make a few tunnels of emptiness that lead down.
        self._carve_tunnels()

        # Rocks and gold: spawn in earth layers.
        self._spawn_rocks_and_gold()

        # Ensure a starting platform under the player.
        self.py = GROUND_ROW - 1
        self.px = 5
        self.player_vx = 0.0
        self.player_vy = 0.0
        self._ensure_support()

        self.gold_left = self.gold_total
        self._redraw()

    def _carve_tunnels(self):
        # Carve one main shaft and some branches.
        shaft_c = random.randint(10, 14)
        for r in range(6, GROUND_ROW + 1):
            self.map[r][shaft_c] = T_EMPTY
            if random.random() < 0.45:
                self.map[r][shaft_c - 1] = T_EMPTY
            if random.random() < 0.45:
                self.map[r][shaft_c + 1] = T_EMPTY

        # Create left/right branch tunnels.
        for branch in range(10):
            start_r = random.randint(10, GROUND_ROW - 10)
            c = random.randint(2, COLS - 3)
            dir_ = random.choice([-1, 1])
            length = random.randint(8, 16)
            r = start_r
            for i in range(length):
                self.map[r][c] = T_EMPTY
                if random.random() < 0.35:
                    self.map[r + 1][c] = T_EMPTY
                c += dir_
                r += random.choice([0, 1])
                c = max(2, min(COLS - 3, c))
                r = max(6, min(GROUND_ROW, r))

    def _spawn_rocks_and_gold(self):
        self.gold_total = 0
        # Base fill: lower rows dense earth.
        for r in range(6, GROUND_ROW + 1):
            for c in range(0, COLS):
                if self.map[r][c] != T_EARTH:
                    continue
                # Rocks slightly more likely deeper.
                depth_factor = (r - 6) / (GROUND_ROW - 6 + 1e-9)
                if random.random() < 0.04 + 0.06 * depth_factor:
                    self.map[r][c] = T_ROCK
                elif random.random() < 0.015 + 0.04 * depth_factor:
                    self.map[r][c] = T_GOLD
                    self.gold_total += 1

        # Add rock clusters.
        for _ in range(18):
            r0 = random.randint(10, GROUND_ROW - 6)
            c0 = random.randint(2, COLS - 3)
            for dr in (-1, 0, 1, 2):
                for dc in (-1, 0, 1):
                    rr = r0 + dr
                    cc = c0 + dc
                    if 0 <= rr < ROWS and 0 <= cc < COLS and self.map[rr][cc] == T_EARTH:
                        if random.random() < 0.6:
                            self.map[rr][cc] = T_ROCK

        # Make sure there's at least some gold.
        if self.gold_total < 10:
            attempts = 0
            while self.gold_total < 10 and attempts < 4000:
                attempts += 1
                r = random.randint(10, GROUND_ROW - 2)
                c = random.randint(2, COLS - 3)
                if self.map[r][c] == T_EARTH:
                    self.map[r][c] = T_GOLD
                    self.gold_total += 1

    def _ensure_support(self):
        # Player start around (px, py) in tile coords; ensure below is earth.
        pr = int(self.py)
        pc = int(self.px)
        for dc in (-1, 0, 1):
            c = pc + dc
            r = pr + 1
            if 0 <= r < ROWS and 0 <= c < COLS:
                if self.map[r][c] == T_EMPTY:
                    self.map[r][c] = T_EARTH

    def tick(self):
        if not self.paused and not self.game_over:
            self.update_player()
            self._dig_if_needed()
            self._apply_gravity_blocks()
            self._check_player_damage()
            self._check_win()
        self._redraw()
        self.root.after(FPS_MS, self.tick)

    def _tile_at(self, tx, ty):
        if tx < 0 or tx >= COLS or ty < 0 or ty >= ROWS:
            return T_EARTH
        return self.map[ty][tx]

    def _set_tile(self, tx, ty, kind):
        if 0 <= tx < COLS and 0 <= ty < ROWS:
            self.map[ty][tx] = kind

    def update_player(self):
        # Input
        left = "left" in self.keys or "a" in self.keys
        right = "right" in self.keys or "d" in self.keys
        accel = 0.75
        max_vx = 4.2

        if left and not right:
            self.player_vx = -max_vx
            self.facing = -1
        elif right and not left:
            self.player_vx = max_vx
            self.facing = 1
        else:
            # Smooth stop
            self.player_vx *= 0.78
            if abs(self.player_vx) < 0.05:
                self.player_vx = 0.0

        # Jump not included; classic miner is dig-and-fall.
        # Gravity:
        gravity = 15.0
        self.player_vy += gravity * (FPS_MS / 1000.0)
        self.player_vy = min(self.player_vy, 18.0)

        # Move horizontally, then vertically with collision against tiles.
        self.px += self.player_vx * (FPS_MS / 1000.0)
        self._collide_horizontal()

        self.py += self.player_vy * (FPS_MS / 1000.0)
        self._collide_vertical()

    def _collide_horizontal(self):
        # Player bounding box in tile space.
        half_w = self.player_w / 2
        top = self.py
        bottom = self.py + self.player_h

        min_tx = int((self.px - half_w) // 1)
        max_tx = int((self.px + half_w) // 1)
        # Keep within bounds.
        self.px = max(1.0, min(COLS - 2.0, self.px))

        # Check tiles overlapped.
        for ty in range(int(top), int(bottom) + 1):
            if self._tile_at(min_tx, ty) != T_EMPTY and self.player_vx < 0:
                self.px = min_tx + 1.0 - half_w
                self.player_vx = 0.0
            if self._tile_at(max_tx, ty) != T_EMPTY and self.player_vx > 0:
                self.px = max_tx - half_w
                self.player_vx = 0.0

    def _collide_vertical(self):
        self.on_ground = False
        half_w = self.player_w / 2
        left = self.px - half_w
        right = self.px + half_w

        min_ty = int((self.py) // 1)
        max_ty = int((self.py + self.player_h) // 1)

        # Collision detection for falling/rising.
        if self.player_vy > 0:
            # Falling: check bottom
            target_ty = max_ty
            for tx in range(int(left) - 1, int(right) + 2):
                if self._tile_at(tx, target_ty) != T_EMPTY:
                    self.py = target_ty - self.player_h
                    self.player_vy = 0.0
                    self.on_ground = True
                    break
        elif self.player_vy < 0:
            # Rising: check top
            target_ty = min_ty
            for tx in range(int(left) - 1, int(right) + 2):
                if self._tile_at(tx, target_ty) != T_EMPTY:
                    self.py = target_ty + 1.0
                    self.player_vy = 0.0
                    break

        # Clamp inside mine area.
        self.py = max(1.0, min(GROUND_ROW - 1.0, self.py))

    def _dig_if_needed(self):
        if " " not in self.keys and "space" not in self.keys:
            return

        # Only dig when on ground or adjacent to earth for a classic feel.
        if self.game_over:
            return

        dx = self.facing
        dig_tx = int(self.px + dx * 0.8)
        dig_ty = int(self.py + self.player_h - 0.55)
        if 0 <= dig_tx < COLS and 0 <= dig_ty < ROWS:
            kind = self._tile_at(dig_tx, dig_ty)
            if kind == T_EARTH:
                self._set_tile(dig_tx, dig_ty, T_EMPTY)
            elif kind == T_GOLD:
                self._set_tile(dig_tx, dig_ty, T_EMPTY)
                self.score += 20
                self.gold_left = max(0, self.gold_left - 1)
            elif kind == T_ROCK:
                # Digging rocks breaks them (they will fall in gravity step).
                self._set_tile(dig_tx, dig_ty, T_EMPTY)

    def _apply_gravity_blocks(self):
        # Rock and gold fall when empty below.
        # We simulate by scanning from bottom-1 up to top.
        for r in range(GROUND_ROW, 4, -1):
            for c in range(COLS):
                kind = self.map[r][c]
                if kind not in (T_ROCK, T_GOLD):
                    continue
                if self.map[r + 1][c] == T_EMPTY:
                    # Move down by one tile per frame for stability.
                    self.map[r + 1][c] = kind
                    self.map[r][c] = T_EMPTY

                # If gold falls, auto-collect when it crosses player.
                if kind == T_GOLD:
                    if self._gold_hits_player(c, r + 1):
                        self.map[r + 1][c] = T_EMPTY
                        self.score += 20
                        self.gold_left = max(0, self.gold_left - 1)

    def _gold_hits_player(self, tx, ty):
        # Player occupies roughly (px, py) with dimensions.
        px1 = self.px - self.player_w / 2
        px2 = self.px + self.player_w / 2
        py1 = self.py
        py2 = self.py + self.player_h
        return (px1 <= tx <= px2) and (py1 <= ty <= py2)

    def _check_player_damage(self):
        # If player overlaps with rock tile -> lose life.
        px1 = self.px - self.player_w / 2
        px2 = self.px + self.player_w / 2
        py1 = self.py
        py2 = self.py + self.player_h

        tx1 = int(px1)
        tx2 = int(px2) + 1
        ty1 = int(py1)
        ty2 = int(py2) + 1

        for ty in range(ty1, ty2 + 1):
            for tx in range(tx1, tx2 + 1):
                if self._tile_at(tx, ty) == T_ROCK:
                    self.lives -= 1
                    # Knock player up/away
                    self.player_vy = -8.0
                    self.player_vx = 0.0
                    # Briefly clear the rock to reduce repeated damage.
                    self._set_tile(tx, ty, T_EARTH)
                    self.status = "被岩石砸到了！"
                    if self.lives <= 0:
                        self.game_over = True
                        self.status = "游戏失败！按 R 重开。"
                    return

    def _check_win(self):
        if self.gold_left <= 0:
            self.game_over = True
            self.status = "恭喜通关！全部金币已收集。"

    def _redraw(self):
        self.canvas.delete("all")
        self._bg_stars_redraw()

        # Panel background
        self.canvas.create_rectangle(0, 0, WINDOW_W, PANEL_H, fill="#0f172a", outline="")

        self.ui_score = self.canvas.create_text(20, 26, text=f"分数: {self.score}", fill="#dbeafe", font=("Microsoft YaHei UI", 14, "bold"), anchor="w")
        self.ui_lives = self.canvas.create_text(180, 26, text=f"生命: {'♥' * max(0, self.lives)}{'♡' * max(0, 3 - self.lives)}", fill="#fecaca", font=("Microsoft YaHei UI", 14, "bold"), anchor="w")
        self.ui_gold = self.canvas.create_text(
            340, 26, text=f"金币: {self.gold_total - self.gold_left} / {self.gold_total}", fill="#fef08a", font=("Microsoft YaHei UI", 14, "bold"), anchor="w"
        )
        status_text = getattr(self, "status", "挖掘并收集金币，避免被岩石砸到！")
        self.canvas.create_text(
            20,
            60,
            text=status_text if not self.game_over else status_text,
            fill="#93c5fd",
            font=("Microsoft YaHei UI", 11, "bold"),
            anchor="w",
        )

        # Mine bounds
        self.canvas.create_rectangle(0, PLAY_TOP, WINDOW_W, PLAY_TOP + PLAY_H, outline="#1f2937", width=3, fill="#0b1220")

        # Draw tiles
        for r in range(6, GROUND_ROW + 1):
            y = PLAY_TOP + r * TILE
            for c in range(COLS):
                kind = self.map[r][c]
                if kind == T_EMPTY:
                    continue
                x = c * TILE
                if kind == T_EARTH:
                    self.canvas.create_rectangle(x, y, x + TILE, y + TILE, fill="#6b4f2a", outline="#5a3f1e")
                elif kind == T_ROCK:
                    self.canvas.create_rectangle(x, y, x + TILE, y + TILE, fill="#64748b", outline="#475569")
                    self.canvas.create_oval(x + 4, y + 6, x + 10, y + 12, fill="#94a3b8", outline="")
                elif kind == T_GOLD:
                    self.canvas.create_rectangle(x, y, x + TILE, y + TILE, fill="#6b4f2a", outline="#5a3f1e")
                    self._draw_gold(x + 5, y + 5, TILE - 10)

        # Draw player
        self._draw_player()

        # Overlay end screen
        if self.game_over:
            self._draw_end_banner()

        # Restart button
        # We recreate UI window is tricky after delete-all; draw text hint instead.
        self.canvas.create_text(WINDOW_W - 150, 26, text="R 重开", fill="#e2e8f0", font=("Microsoft YaHei UI", 12, "bold"))

    def _bg_stars_redraw(self):
        # Recreate a lightweight star field (kept deterministic enough).
        for i in range(80):
            x = (i * 73) % WINDOW_W
            y = (i * 41) % PLAY_H
            y = y + PLAY_TOP
            r = 1 if i % 7 else 2
            self.canvas.create_oval(x - r, y - r, x + r, y + r, fill="#16233a", outline="")

    def _draw_player(self):
        x = self.px * TILE
        y = self.py * TILE + PLAY_TOP
        w = int(self.player_w * TILE)
        h = int(self.player_h * TILE)
        left = x - w / 2
        top = y
        right = left + w
        bottom = top + h

        # Body
        self.canvas.create_rectangle(left, top, right, bottom, fill="#38bdf8", outline="#0ea5e9", width=2)
        # Helmet
        self.canvas.create_oval(left + 4, top + 2, right - 4, top + 18, fill="#bae6fd", outline="#93c5fd")
        # Pickaxe
        px = right if self.facing > 0 else left - 10
        py = top + 12
        self.canvas.create_line(px, py, px + 24 * self.facing, py + 6, fill="#f59e0b", width=4)
        self.canvas.create_oval(px + 20 * self.facing, py + 3, px + 28 * self.facing, py + 11, fill="#fbbf24", outline="")

    def _draw_gold(self, cx, cy, size):
        # Diamond shape with glints.
        self.canvas.create_polygon(
            cx,
            cy + size,
            cx + size,
            cy + size / 2,
            cx + size / 2,
            cy,
            cx,
            cy + size / 2,
            fill="#fbbf24",
            outline="#b45309",
        )
        self.canvas.create_oval(cx + size * 0.25, cy + size * 0.55, cx + size * 0.5, cy + size * 0.75, fill="#fde68a", outline="")

    def _draw_end_banner(self):
        if not getattr(self, "status", None):
            return
        title = "通关成功！" if self.lives > 0 and self.gold_left <= 0 else "游戏结束"
        self.canvas.create_rectangle(WINDOW_W / 2 - 240, PLAY_TOP + PLAY_H / 2 - 120, WINDOW_W / 2 + 240, PLAY_TOP + PLAY_H / 2 + 120, fill="#0f172a", outline="#22c55e", width=4)
        self.canvas.create_text(WINDOW_W / 2, PLAY_TOP + PLAY_H / 2 - 40, text=title, fill="#dcfce7", font=("Microsoft YaHei UI", 34, "bold"))
        self.canvas.create_text(WINDOW_W / 2, PLAY_TOP + PLAY_H / 2 + 10, text=self.status, fill="#e2e8f0", font=("Microsoft YaHei UI", 16, "bold"))
        self.canvas.create_text(WINDOW_W / 2, PLAY_TOP + PLAY_H / 2 + 60, text="点击画面或按 R 重新开始", fill="#93c5fd", font=("Microsoft YaHei UI", 14, "bold"))


def main():
    root = tk.Tk()
    game = MinerGame(root)
    _ = game  # keep reference
    root.mainloop()


if __name__ == "__main__":
    main()

