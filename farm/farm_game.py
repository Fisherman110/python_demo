import time
import tkinter as tk
from dataclasses import dataclass
from tkinter import messagebox


WINDOW_W = 1080
WINDOW_H = 680
CANVAS_W = 720
CANVAS_H = 640

ROWS = 4
COLS = 4
PLOT_SIZE = 128
PLOT_GAP = 18
PLOT_START_X = 32
PLOT_START_Y = 72


@dataclass(frozen=True)
class CropInfo:
    name: str
    seed_name: str
    seed_price: int
    sell_price: int
    grow_seconds: int
    seed_color: str
    crop_color: str


@dataclass
class Plot:
    row: int
    col: int
    crop_key: str | None = None
    planted_at: float = 0.0
    ready_at: float = 0.0

    @property
    def is_empty(self):
        return self.crop_key is None

    def progress(self, now):
        if self.crop_key is None:
            return 0.0
        duration = max(self.ready_at - self.planted_at, 0.1)
        return min(1.0, max(0.0, (now - self.planted_at) / duration))

    def is_ready(self, now):
        return self.crop_key is not None and now >= self.ready_at


CROPS = {
    "carrot": CropInfo(
        name="胡萝卜",
        seed_name="胡萝卜种子",
        seed_price=5,
        sell_price=12,
        grow_seconds=8,
        seed_color="#F77F00",
        crop_color="#E85D04",
    ),
    "wheat": CropInfo(
        name="小麦",
        seed_name="小麦种子",
        seed_price=8,
        sell_price=22,
        grow_seconds=14,
        seed_color="#F9C74F",
        crop_color="#DDA15E",
    ),
    "tomato": CropInfo(
        name="番茄",
        seed_name="番茄种子",
        seed_price=12,
        sell_price=36,
        grow_seconds=22,
        seed_color="#F94144",
        crop_color="#D62828",
    ),
}


class FarmGame:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("农场游戏 - Farm Game")
        self.root.geometry(f"{WINDOW_W}x{WINDOW_H}")
        self.root.resizable(False, False)

        self.bg = "#F5F7E8"
        self.panel_bg = "#FFF8E8"
        self.text_color = "#2F3E2F"
        self.accent = "#3A9D23"
        self.warn = "#B08900"
        self.plot_empty = "#9D6B3D"
        self.plot_border = "#6B4226"

        self.money = 50
        self.inventory = {self.seed_key(key): 0 for key in CROPS}
        self.inventory.update({self.crop_key(key): 0 for key in CROPS})
        self.selected_seed: str | None = None
        self.plots = [Plot(row, col) for row in range(ROWS) for col in range(COLS)]

        self.money_var = tk.StringVar()
        self.selected_var = tk.StringVar()
        self.status_var = tk.StringVar()
        self.inventory_var = tk.StringVar()

        self.canvas = tk.Canvas(
            root,
            width=CANVAS_W,
            height=CANVAS_H,
            bg="#BEE6A4",
            highlightthickness=0,
        )
        self.canvas.pack(side="left", padx=(14, 8), pady=14)
        self.canvas.bind("<Button-1>", self.on_canvas_click)

        right_panel = tk.Frame(root, width=WINDOW_W - CANVAS_W - 36, bg=self.bg)
        right_panel.pack(side="left", fill="both", expand=True, padx=(8, 14), pady=14)
        right_panel.pack_propagate(False)

        self.build_side_panel(right_panel)
        self.set_status("欢迎来到农场！先在商店购买种子，再点击农田播种。")
        self.select_seed("carrot")
        self.refresh_ui()
        self.tick()

    @staticmethod
    def seed_key(crop_key):
        return f"seed:{crop_key}"

    @staticmethod
    def crop_key(crop_key):
        return f"crop:{crop_key}"

    def build_side_panel(self, parent):
        title = tk.Label(
            parent,
            text="我的农场",
            font=("Microsoft YaHei UI", 22, "bold"),
            fg=self.text_color,
            bg=self.bg,
        )
        title.pack(anchor="w", pady=(0, 8))

        self.money_label = tk.Label(
            parent,
            textvariable=self.money_var,
            font=("Microsoft YaHei UI", 15, "bold"),
            fg="#1B6B2A",
            bg=self.bg,
        )
        self.money_label.pack(anchor="w", pady=(0, 8))

        self.selected_label = tk.Label(
            parent,
            textvariable=self.selected_var,
            font=("Microsoft YaHei UI", 11),
            fg=self.text_color,
            bg=self.bg,
            wraplength=300,
            justify="left",
        )
        self.selected_label.pack(anchor="w", pady=(0, 12))

        shop = tk.LabelFrame(
            parent,
            text="商店菜单",
            font=("Microsoft YaHei UI", 12, "bold"),
            bg=self.panel_bg,
            fg=self.text_color,
            padx=10,
            pady=10,
        )
        shop.pack(fill="x", pady=(0, 12))

        for crop_key, info in CROPS.items():
            row = tk.Frame(shop, bg=self.panel_bg)
            row.pack(fill="x", pady=4)
            desc = f"{info.seed_name}  ${info.seed_price}  成熟 {info.grow_seconds}s"
            tk.Label(
                row,
                text=desc,
                bg=self.panel_bg,
                fg=self.text_color,
                font=("Microsoft YaHei UI", 10),
                anchor="w",
            ).pack(side="left", fill="x", expand=True)
            tk.Button(
                row,
                text="购买",
                command=lambda key=crop_key: self.buy_seed(key),
                bg="#E9F5DB",
                fg=self.text_color,
                relief="groove",
                width=7,
            ).pack(side="right")

        bag = tk.LabelFrame(
            parent,
            text="背包",
            font=("Microsoft YaHei UI", 12, "bold"),
            bg=self.panel_bg,
            fg=self.text_color,
            padx=10,
            pady=10,
        )
        bag.pack(fill="both", expand=True, pady=(0, 12))

        tk.Label(
            bag,
            textvariable=self.inventory_var,
            bg=self.panel_bg,
            fg=self.text_color,
            font=("Microsoft YaHei UI", 10),
            justify="left",
            anchor="nw",
        ).pack(fill="both", expand=True)

        select_box = tk.LabelFrame(
            parent,
            text="选择要种的种子",
            font=("Microsoft YaHei UI", 12, "bold"),
            bg=self.panel_bg,
            fg=self.text_color,
            padx=10,
            pady=8,
        )
        select_box.pack(fill="x", pady=(0, 12))

        for crop_key, info in CROPS.items():
            tk.Button(
                select_box,
                text=info.seed_name,
                command=lambda key=crop_key: self.select_seed(key),
                bg=info.seed_color,
                fg="#2B2118",
                relief="raised",
            ).pack(side="left", expand=True, fill="x", padx=3)

        actions = tk.Frame(parent, bg=self.bg)
        actions.pack(fill="x", pady=(0, 10))
        tk.Button(
            actions,
            text="出售所有作物",
            command=self.sell_all_crops,
            bg="#D8F3DC",
            fg=self.text_color,
            font=("Microsoft YaHei UI", 10, "bold"),
        ).pack(side="left", expand=True, fill="x", padx=(0, 5))
        tk.Button(
            actions,
            text="重新开始",
            command=self.reset_game,
            bg="#FFE8D6",
            fg=self.text_color,
            font=("Microsoft YaHei UI", 10, "bold"),
        ).pack(side="left", expand=True, fill="x", padx=(5, 0))

        tk.Label(
            parent,
            textvariable=self.status_var,
            font=("Microsoft YaHei UI", 10),
            fg=self.warn,
            bg=self.bg,
            wraplength=300,
            justify="left",
        ).pack(anchor="w", fill="x")

    def buy_seed(self, crop_key):
        info = CROPS[crop_key]
        if self.money < info.seed_price:
            self.set_status(f"金钱不足，购买 {info.seed_name} 需要 ${info.seed_price}。")
            return
        self.money -= info.seed_price
        self.inventory[self.seed_key(crop_key)] += 1
        self.select_seed(crop_key)
        self.set_status(f"购买成功：{info.seed_name} +1。")
        self.refresh_ui()

    def select_seed(self, crop_key):
        self.selected_seed = crop_key
        info = CROPS[crop_key]
        count = self.inventory[self.seed_key(crop_key)]
        self.selected_var.set(f"当前选择：{info.seed_name}（背包里有 {count} 个）")

    def on_canvas_click(self, event):
        plot = self.find_plot(event.x, event.y)
        if plot is None:
            return

        now = time.time()
        if plot.is_ready(now):
            self.harvest(plot)
            return

        if not plot.is_empty:
            info = CROPS[plot.crop_key]
            remaining = max(0, int(plot.ready_at - now) + 1)
            self.set_status(f"{info.name} 还在生长，约 {remaining} 秒后成熟。")
            return

        self.plant(plot)

    def plant(self, plot):
        if self.selected_seed is None:
            self.set_status("请先选择一种要种的种子。")
            return

        seed_item = self.seed_key(self.selected_seed)
        if self.inventory[seed_item] <= 0:
            info = CROPS[self.selected_seed]
            self.set_status(f"背包里没有 {info.seed_name}，请先去商店购买。")
            return

        now = time.time()
        info = CROPS[self.selected_seed]
        self.inventory[seed_item] -= 1
        plot.crop_key = self.selected_seed
        plot.planted_at = now
        plot.ready_at = now + info.grow_seconds
        self.set_status(f"已播种 {info.name}，等待 {info.grow_seconds} 秒成熟。")
        self.refresh_ui()

    def harvest(self, plot):
        if plot.crop_key is None:
            return

        info = CROPS[plot.crop_key]
        self.inventory[self.crop_key(plot.crop_key)] += 1
        plot.crop_key = None
        plot.planted_at = 0.0
        plot.ready_at = 0.0
        self.set_status(f"收获成功：{info.name} +1，已放入背包。")
        self.refresh_ui()

    def sell_all_crops(self):
        total = 0
        sold_items = []
        for crop_key, info in CROPS.items():
            item_key = self.crop_key(crop_key)
            count = self.inventory[item_key]
            if count:
                total += count * info.sell_price
                sold_items.append(f"{info.name} x{count}")
                self.inventory[item_key] = 0

        if total == 0:
            self.set_status("背包里没有可以出售的作物。")
            return

        self.money += total
        self.set_status(f"出售 {'、'.join(sold_items)}，获得 ${total}。")
        self.refresh_ui()

    def reset_game(self):
        if not messagebox.askyesno("重新开始", "确定要清空当前进度并重新开始吗？"):
            return

        self.money = 50
        for key in self.inventory:
            self.inventory[key] = 0
        for plot in self.plots:
            plot.crop_key = None
            plot.planted_at = 0.0
            plot.ready_at = 0.0
        self.select_seed("carrot")
        self.set_status("农场已重置。")
        self.refresh_ui()

    def find_plot(self, x, y):
        for plot in self.plots:
            left, top, right, bottom = self.plot_rect(plot)
            if left <= x <= right and top <= y <= bottom:
                return plot
        return None

    def plot_rect(self, plot):
        left = PLOT_START_X + plot.col * (PLOT_SIZE + PLOT_GAP)
        top = PLOT_START_Y + plot.row * (PLOT_SIZE + PLOT_GAP)
        return left, top, left + PLOT_SIZE, top + PLOT_SIZE

    def refresh_ui(self):
        self.money_var.set(f"金钱：${self.money}")
        if self.selected_seed:
            self.select_seed(self.selected_seed)
        self.inventory_var.set(self.format_inventory())
        self.draw()

    def format_inventory(self):
        lines = ["种子："]
        for crop_key, info in CROPS.items():
            lines.append(f"  {info.seed_name}: {self.inventory[self.seed_key(crop_key)]}")

        lines.append("")
        lines.append("作物：")
        for crop_key, info in CROPS.items():
            lines.append(
                f"  {info.name}: {self.inventory[self.crop_key(crop_key)]} "
                f"(售价 ${info.sell_price})"
            )
        return "\n".join(lines)

    def draw(self):
        self.canvas.delete("all")
        self.draw_header()
        self.draw_plots()
        self.draw_footer()

    def draw_header(self):
        self.canvas.create_rectangle(0, 0, CANVAS_W, 54, fill="#8BC34A", outline="")
        self.canvas.create_text(
            24,
            27,
            text="点击空农田播种，点击成熟作物收获",
            anchor="w",
            fill="#173B12",
            font=("Microsoft YaHei UI", 16, "bold"),
        )

    def draw_footer(self):
        self.canvas.create_text(
            24,
            CANVAS_H - 24,
            text="提示：成熟作物会发光；收获后可在右侧出售作物换钱。",
            anchor="w",
            fill="#2F3E2F",
            font=("Microsoft YaHei UI", 11),
        )

    def draw_plots(self):
        now = time.time()
        for plot in self.plots:
            left, top, right, bottom = self.plot_rect(plot)
            self.draw_plot_base(left, top, right, bottom)

            if plot.crop_key is None:
                self.canvas.create_text(
                    (left + right) / 2,
                    (top + bottom) / 2,
                    text="空地",
                    fill="#FDEBD0",
                    font=("Microsoft YaHei UI", 12, "bold"),
                )
                continue

            info = CROPS[plot.crop_key]
            progress = plot.progress(now)
            ready = plot.is_ready(now)
            self.draw_crop(left, top, right, bottom, info, progress, ready)

    def draw_plot_base(self, left, top, right, bottom):
        self.canvas.create_rectangle(
            left + 5,
            top + 6,
            right + 5,
            bottom + 6,
            fill="#6F4E37",
            outline="",
        )
        self.canvas.create_rectangle(
            left,
            top,
            right,
            bottom,
            fill=self.plot_empty,
            outline=self.plot_border,
            width=3,
        )
        for offset in range(18, PLOT_SIZE, 24):
            self.canvas.create_line(
                left + 8,
                top + offset,
                right - 8,
                top + offset + 9,
                fill="#7B4F2A",
                width=2,
            )

    def draw_crop(self, left, top, right, bottom, info, progress, ready):
        cx = (left + right) / 2
        base_y = bottom - 30
        stem_h = 18 + int(progress * 48)
        leaf_count = 2 + int(progress * 4)

        if ready:
            self.canvas.create_oval(
                left + 10,
                top + 10,
                right - 10,
                bottom - 10,
                fill="#FFF3B0",
                outline="",
                stipple="gray25",
            )

        self.canvas.create_line(cx, base_y, cx, base_y - stem_h, fill="#2D6A4F", width=5)
        for i in range(leaf_count):
            y = base_y - 10 - i * 10
            side = -1 if i % 2 == 0 else 1
            self.canvas.create_oval(
                cx + side * 6,
                y - 8,
                cx + side * 30,
                y + 7,
                fill="#52B788",
                outline="#2D6A4F",
            )

        fruit_r = 10 + int(progress * 12)
        self.canvas.create_oval(
            cx - fruit_r,
            base_y - stem_h - fruit_r,
            cx + fruit_r,
            base_y - stem_h + fruit_r,
            fill=info.crop_color,
            outline="#4A2C2A",
            width=2,
        )

        label = f"{info.name}\n可收获" if ready else f"{info.name}\n{int(progress * 100)}%"
        self.canvas.create_text(
            cx,
            top + 20,
            text=label,
            fill="#FFF8E8",
            font=("Microsoft YaHei UI", 11, "bold"),
            justify="center",
        )

    def set_status(self, text):
        self.status_var.set(text)

    def tick(self):
        self.draw()
        self.root.after(500, self.tick)


def main():
    root = tk.Tk()
    FarmGame(root)
    root.mainloop()


if __name__ == "__main__":
    main()
