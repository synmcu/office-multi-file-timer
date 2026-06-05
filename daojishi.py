import tkinter as tk
from tkinter import ttk, colorchooser, filedialog, messagebox
import pygetwindow as gw
import threading
import time
import os
import json
from PIL import Image, ImageDraw
import pystray


class TrayRememberFileTimerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Office多文件批量控时器（系统托盘数据记忆版）")
        self.root.geometry("820x620")

        # 配置文件路径
        self.config_file = "timer_config.json"

        # 核心数据初始化（先设定默认值，随后会被本地缓存覆盖）
        self.tasks = []
        self.font_size = 24
        self.default_fg = "#FFFFFF"
        self.default_bg = "#0000FF"
        self.bg_opacity = 0.8

        # 加载上次保存的数据
        self.load_config_from_local()

        self.setup_ui()
        self.setup_tray()

        # 拦截窗口关闭事件，使其隐藏到托盘
        self.root.protocol('WM_DELETE_WINDOW', self.hide_to_tray)

        # 启动后台监控线程
        self.running = True
        self.monitor_thread = threading.Thread(target=self.monitor_logic, daemon=True)
        self.monitor_thread.start()

    def setup_ui(self):
        # ---- 顶部操作区域 ----
        top_frame = ttk.Frame(self.root, padding=10)
        top_frame.pack(fill="x")

        batch_btn = ttk.Button(top_frame, text="📂 批量导入文件 (可多选)", command=self.batch_add_files)
        batch_btn.pack(side="left", padx=5)

        del_btn = ttk.Button(top_frame, text="❌ 删除选中文件 (支持多选)", command=self.delete_selected_tasks)
        del_btn.pack(side="left", padx=5)

        tip_lbl = ttk.Label(top_frame, text="💡 提示：双击下方列表中的任意一行，可直接修改其时间和延迟", foreground="gray")
        tip_lbl.pack(side="right", padx=5)

        # ---- 初始默认配置区域 ----
        config_frame = ttk.LabelFrame(self.root, text="新导入文件默认配置", padding=10)
        config_frame.pack(fill="x", padx=10, pady=5)

        ttk.Label(config_frame, text="默认倒计时:").pack(side="left", padx=2)
        self.time_min = ttk.Entry(config_frame, width=4)
        self.time_min.pack(side="left", padx=2)
        self.time_min.insert(0, "5")
        ttk.Label(config_frame, text="分").pack(side="left", padx=2)

        self.time_sec = ttk.Entry(config_frame, width=4)
        self.time_sec.pack(side="left", padx=2)
        self.time_sec.insert(0, "0")
        ttk.Label(config_frame, text="秒").pack(side="left", padx=5)

        ttk.Label(config_frame, text="｜ 默认手动延迟:").pack(side="left", padx=5)
        self.delay_entry = ttk.Entry(config_frame, width=4)
        self.delay_entry.pack(side="left", padx=2)
        self.delay_entry.insert(0, "10")
        ttk.Label(config_frame, text="秒开始倒计时").pack(side="left", padx=2)

        # ---- 核心列表区域 ----
        list_frame = ttk.LabelFrame(self.root, text="文件监控列表", padding=10)
        list_frame.pack(fill="both", expand=True, padx=10, pady=5)

        self.tree = ttk.Treeview(list_frame, columns=("id", "filename", "cfg_time", "delay_cfg", "status"),
                                 show="headings", height=10, selectmode="extended")
        self.tree.heading("filename", text="已选文件名")
        self.tree.heading("cfg_time", text="设定时间")
        self.tree.heading("delay_cfg", text="手动延迟")
        self.tree.heading("status", text="当前状态")

        self.tree.column("id", width=0, minwidth=0, stretch=False)
        self.tree.column("filename", width=280, anchor="w")
        self.tree.column("cfg_time", width=110, anchor="center")
        self.tree.column("delay_cfg", width=110, anchor="center")
        self.tree.column("status", width=180, anchor="center")
        self.tree.pack(fill="both", expand=True, side="left")

        # 绑定双击单行修改事件
        self.tree.bind("<Double-1>", self.on_tree_double_click)

        # ---- 底部外观控制与【100%真实预览】区域 ----
        style_frame = ttk.LabelFrame(self.root, text="常规外观自定义与效果实时预览", padding=10)
        style_frame.pack(fill="x", padx=10, pady=5)

        ctrl_frame = ttk.Frame(style_frame)
        ctrl_frame.pack(fill="x", pady=5)

        ttk.Button(ctrl_frame, text="🎨 更改字体颜色", command=self.choose_fg_color).grid(row=0, column=0, padx=5,
                                                                                         pady=5)
        ttk.Button(ctrl_frame, text="🔷 更改背景颜色", command=self.choose_bg_color).grid(row=0, column=1, padx=5,
                                                                                         pady=5)

        ttk.Label(ctrl_frame, text="字体大小:").grid(row=0, column=2, padx=5, pady=5)
        self.size_spin = ttk.Spinbox(ctrl_frame, from_=12, to=72, width=5, command=self.on_style_change)
        self.size_spin.grid(row=0, column=3, padx=5, pady=5)
        self.size_spin.set(self.font_size)
        self.size_spin.bind("<KeyRelease>", lambda e: self.on_style_change())

        ttk.Label(ctrl_frame, text="不透明度:").grid(row=0, column=4, padx=5, pady=5)
        self.alpha_scale = ttk.Scale(ctrl_frame, from_=0.2, to=1.0, value=self.bg_opacity,
                                     command=self.on_alpha_scale_move)
        self.alpha_scale.grid(row=0, column=5, padx=5, pady=5)

        # 100% 高仿真预览看板
        preview_label_frame = ttk.LabelFrame(style_frame, text="【悬浮窗真实效果预览看板（支持透明度全真模拟）】")
        preview_label_frame.pack(fill="x", pady=5)

        # 使用外层容器模拟 Windows 桌面背景底色（灰白色），方便看清透明度
        self.desktop_simulator = tk.Frame(preview_label_frame, bg="#E1E1E1", bd=1, relief="sunken")
        self.desktop_simulator.pack(padx=20, pady=10, fill="x")

        # 实际预览框
        self.preview_box = tk.Frame(self.desktop_simulator, bg=self.default_bg)
        self.preview_box.pack(pady=15)

        self.preview_text = tk.Label(self.preview_box, text="05:00", font=("Helvetica", self.font_size, "bold"),
                                     fg=self.default_fg, bg=self.default_bg)
        self.preview_text.pack(padx=15, pady=5)

        # 渲染初版界面
        self.on_style_change()
        self.refresh_list_view()

    # ---- 1. 双击修改单行弹出极简框 ----
    def on_tree_double_click(self, event):
        item_id = self.tree.identify_row(event.y)
        if not item_id:
            return

        item_values = self.tree.item(item_id, "values")
        task_id = item_values[0]

        target_task = None
        for t in self.tasks:
            if t["id"] == task_id:
                target_task = t
                break

        if target_task:
            self.pop_inline_edit_window(target_task)

    def pop_inline_edit_window(self, task):
        edit_win = tk.Toplevel(self.root)
        edit_win.title("修改配置")
        edit_win.geometry("320x140")
        edit_win.resizable(False, False)
        edit_win.grab_set()
        edit_win.geometry(f"+{self.root.winfo_x() + 200}+{self.root.winfo_y() + 150}")

        ttk.Label(edit_win, text=f"正在修改: {task['keyword']}", font=("Arial", 9, "bold")).pack(pady=5)

        inputs_frame = ttk.Frame(edit_win)
        inputs_frame.pack(pady=5)

        # 时间输入
        ttk.Label(inputs_frame, text="时间:").grid(row=0, column=0, padx=2)
        m_entry = ttk.Entry(inputs_frame, width=4)
        m_entry.grid(row=0, column=1, padx=2)
        m_entry.insert(0, str(task["total_seconds"] // 60))
        ttk.Label(inputs_frame, text="分").grid(row=0, column=2, padx=1)

        s_entry = ttk.Entry(inputs_frame, width=4)
        s_entry.grid(row=0, column=3, padx=2)
        s_entry.insert(0, str(task["total_seconds"] % 60))
        ttk.Label(inputs_frame, text="秒").grid(row=0, column=4, padx=1)

        # 延迟输入
        ttk.Label(inputs_frame, text="｜ 延迟:").grid(row=0, column=5, padx=5)
        d_entry = ttk.Entry(inputs_frame, width=4)
        d_entry.grid(row=0, column=6, padx=2)
        d_entry.insert(0, str(task["total_delay"]))
        ttk.Label(inputs_frame, text="秒").grid(row=0, column=7, padx=1)

        def save_inline_changes():
            try:
                new_total = int(m_entry.get().strip()) * 60 + int(s_entry.get().strip())
                new_delay = int(d_entry.get().strip())
                if new_total > 0 and new_delay >= 0:
                    task["total_seconds"] = new_total
                    task["timer_clock"] = new_total
                    task["total_delay"] = new_delay
                    task["delay_counter"] = new_delay
                    self.save_config_to_local()  # 瞬间同步记忆
                    self.refresh_list_view()
                    edit_win.destroy()
            except ValueError:
                pass

        ttk.Button(edit_win, text="保存修改", command=save_inline_changes).pack(pady=10)

    # ---- 2. 100% 像素级高仿真实时预览逻辑 ----
    def on_alpha_scale_move(self, val):
        self.bg_opacity = float(val)
        self.on_style_change()

    def on_style_change(self):
        try:
            self.font_size = int(self.size_spin.get())
        except:
            self.font_size = 24

        # 核心：通过与桌面背景色进行算法混合（Color Blending），在不透明的 Tkinter 组件上完美模拟出透明度视觉效果！
        # 目标背景色与灰色底色 (#E1E1E1 -> RGB: 225, 225, 225) 进行混合
        try:
            target_rgb = self.root.winfo_rgb(self.default_bg)  # 获取16位RGB
            r1, g1, b1 = target_rgb[0] // 256, target_rgb[1] // 256, target_rgb[2] // 256
            r2, g2, b2 = 225, 225, 225
            # 混合公式：C = C1 * alpha + C2 * (1 - alpha)
            r_mixed = int(r1 * self.bg_opacity + r2 * (1 - self.bg_opacity))
            g_mixed = int(g1 * self.bg_opacity + g2 * (1 - self.bg_opacity))
            b_mixed = int(b1 * self.bg_opacity + b2 * (1 - self.bg_opacity))
            mixed_hex = f"#{r_mixed:02x}{g_mixed:02x}{b_mixed:02x}"
        except:
            mixed_hex = self.default_bg

        # 更新预览看板视觉效果
        self.preview_box.config(bg=mixed_hex)
        self.preview_text.config(font=("Helvetica", self.font_size, "bold"), fg=self.default_fg, bg=mixed_hex)

        # 同步应用到所有激活的桌面真实悬浮窗
        for t in self.tasks:
            if t["overlay_label"] and t["overlay_label"].winfo_exists():
                t["overlay_win"].attributes("-alpha", self.bg_opacity)
                if t["timer_clock"] >= 0:
                    t["overlay_win"].config(bg=self.default_bg)
                    t["overlay_label"].config(font=("Helvetica", self.font_size, "bold"), fg=self.default_fg,
                                              bg=self.default_bg)
        self.save_config_to_local()

    # ---- 3. 本地持久化数据记忆逻辑 ----
    def save_config_to_local(self):
        # 抽取核心配置和列表保存为 JSON 文件
        file_list = []
        for t in self.tasks:
            file_list.append({
                "file_path": t["file_path"],
                "total_seconds": t["total_seconds"],
                "total_delay": t["total_delay"]
            })
        config_data = {
            "font_size": self.font_size,
            "default_fg": self.default_fg,
            "default_bg": self.default_bg,
            "bg_opacity": self.bg_opacity,
            "file_list": file_list
        }
        with open(self.config_file, "w", encoding="utf-8") as f:
            json.dump(config_data, f, ensure_ascii=False, indent=4)

    def load_config_from_local(self):
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.font_size = data.get("font_size", 24)
                    self.default_fg = data.get("default_fg", "#FFFFFF")
                    self.default_bg = data.get("default_bg", "#0000FF")
                    self.bg_opacity = data.get("bg_opacity", 0.8)

                    saved_files = data.get("file_list", [])
                    for item in saved_files:
                        path = item["file_path"]
                        base_name = os.path.basename(path)
                        name_without_ext, _ = os.path.splitext(base_name)
                        self.tasks.append({
                            "id": path,
                            "file_path": path,
                            "keyword": name_without_ext,
                            "total_seconds": item["total_seconds"],
                            "timer_clock": item["total_seconds"],
                            "total_delay": item["total_delay"],
                            "delay_counter": item["total_delay"],
                            "overlay_win": None,
                            "overlay_label": None
                        })
            except Exception as e:
                print(f"载入历史配置失败: {e}")

    # ---- 4. 右下角系统托盘逻辑 ----
    def setup_tray(self):
        # 用 PIL 动态绘制一个精美的时钟小图标
        icon_image = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
        dc = ImageDraw.Draw(icon_image)
        dc.ellipse([4, 4, 60, 60], fill="#0000FF", outline="#FFFFFF", width=4)
        dc.line([32, 32, 32, 16], fill="#FFFFFF", width=4)
        dc.line([32, 32, 48, 32], fill="#FFFFFF", width=4)

        # 菜单
        menu = pystray.Menu(
            pystray.MenuItem("显示主界面", self.show_window_from_tray, default=True),
            pystray.MenuItem("彻底退出程序", self.quit_app_completely)
        )
        self.tray_icon = pystray.Icon("OfficeTimer", icon_image, "Office多文件精准控时器", menu)

        # 异步线程启动托盘防卡死
        threading.Thread(target=self.tray_icon.run, daemon=True).start()

    def hide_to_tray(self):
        self.root.withdraw()  # 隐藏主窗口

    def show_window_from_tray(self, icon=None, item=None):
        self.root.after(0, self.root.deiconify)  # 主线程唤醒窗口

    def quit_app_completely(self, icon, item):
        self.running = False
        self.tray_icon.stop()  # 停止托盘
        # 销毁所有活着的悬浮窗
        for t in self.tasks:
            if t["overlay_win"] and t["overlay_win"].winfo_exists():
                t["overlay_win"].destroy()
        self.root.after(0, self.root.destroy)  # 退出 Tkinter 主进程

    # ---- 基础批量管理逻辑 ----
    def batch_add_files(self):
        file_paths = filedialog.askopenfilenames(
            title="批量选择Office文档",
            filetypes=[("Office Files", "*.pptx *.ppt *.docx *.doc *.xlsx *.xls"), ("All Files", "*.*")]
        )
        if not file_paths:
            return

        try:
            minutes = int(self.time_min.get().strip())
            seconds = int(self.time_sec.get().strip())
            total_seconds = minutes * 60 + seconds
            delay_seconds = int(self.delay_entry.get().strip())
        except ValueError:
            return

        for path in file_paths:
            if any(t["file_path"] == path for t in self.tasks):
                continue
            base_name = os.path.basename(path)
            file_name_without_ext, _ = os.path.splitext(base_name)

            self.tasks.append({
                "id": path,
                "file_path": path,
                "keyword": file_name_without_ext,
                "total_seconds": total_seconds,
                "timer_clock": total_seconds,
                "total_delay": delay_seconds,
                "delay_counter": delay_seconds,
                "overlay_win": None,
                "overlay_label": None
            })
        self.save_config_to_local()
        self.refresh_list_view()

    def delete_selected_tasks(self):
        selected_items = self.tree.selection()
        if not selected_items:
            return
        for item in selected_items:
            task_id = self.tree.item(item, "values")[0]
            for t in self.tasks:
                if t["id"] == task_id:
                    if t["overlay_win"] and t["overlay_win"].winfo_exists():
                        t["overlay_win"].destroy()
                    self.tasks.remove(t)
                    break
            self.tree.delete(item)
        self.save_config_to_local()

    def refresh_list_view(self):
        existing_items = {self.tree.item(item)['values'][0]: item for item in self.tree.get_children()}
        for t in self.tasks:
            cfg_str = f"{t['total_seconds'] // 60}分{t['total_seconds'] % 60}秒"
            delay_cfg_str = f"{t['total_delay']} 秒"
            if t["timer_clock"] < 0:
                status = f"🔴 已超时 {abs(t['timer_clock'])} 秒"
            elif t["overlay_win"] is not None:
                if t["delay_counter"] > 0:
                    status = f"⏳ 延迟缓冲中 ({t['delay_counter']}s)"
                else:
                    status = f"🟢 倒计时中 ({t['timer_clock']}s)"
            else:
                status = "⚪ 等待文件打开"

            if t["id"] in existing_items:
                self.tree.item(existing_items[t["id"]], values=(t["id"], t["keyword"], cfg_str, delay_cfg_str, status))
            else:
                self.tree.insert("", "end", values=(t["id"], t["keyword"], cfg_str, delay_cfg_str, status))

    def choose_fg_color(self):
        color = colorchooser.askcolor(title="选择常规字体颜色")
        if color[1]:
            self.default_fg = color[1]
            self.on_style_change()

    def choose_bg_color(self):
        color = colorchooser.askcolor(title="选择常规背景颜色")
        if color[1]:
            self.default_bg = color[1]
            self.on_style_change()

    # ---- 后台多路监控核心核心线程 ----
    def monitor_logic(self):
        while self.running:
            time.sleep(1)
            try:
                windows = gw.getAllWindows()
                active_windows = [w for w in windows if w.title]
                for task in self.tasks:
                    target_window = None
                    for w in active_windows:
                        if task["keyword"].lower() in w.title.lower():
                            target_window = w
                            break
                    if target_window:
                        if task["delay_counter"] > 0:
                            task["delay_counter"] -= 1
                        else:
                            task["timer_clock"] -= 1
                        self.root.after(0, self.create_or_update_file_overlay, task, target_window)
                    else:
                        if task["overlay_win"] is not None:
                            self.root.after(0, self.destroy_file_overlay, task)
                            task["timer_clock"] = task["total_seconds"]
                            task["delay_counter"] = task["total_delay"]
                self.root.after(0, self.refresh_list_view)
            except Exception as e:
                pass

    def create_or_update_file_overlay(self, task, win):
        current_clock = task["timer_clock"]
        if current_clock >= 0:
            mins, secs = divmod(current_clock, 60)
            time_str = f"{mins:02d}:{secs:02d}"
            bg_color = self.default_bg
            fg_color = self.default_fg
        else:
            over_seconds = abs(current_clock)
            mins, secs = divmod(over_seconds, 60)
            time_str = f"超时 {mins:02d}:{secs:02d}"
            bg_color = "#FF0000"
            fg_color = "#FFFFFF"

        if task["overlay_win"] is None or not task["overlay_win"].winfo_exists():
            overlay = tk.Toplevel(self.root)
            overlay.overrideredirect(True)
            overlay.attributes("-topmost", True)
            overlay.attributes("-alpha", self.bg_opacity)
            overlay.configure(bg=bg_color)
            try:
                win_x, win_y, win_w = win.left, win.top, win.width
                pos_x = win_x + win_w - 180
                pos_y = win_y + 40
                if pos_x < 0 or pos_y < 0: pos_x, pos_y = 150, 150
                overlay.geometry(f"+{pos_x}+{pos_y}")
            except:
                overlay.geometry("+200+200")
            lbl = tk.Label(overlay, text=time_str, font=("Helvetica", self.font_size, "bold"), fg=fg_color, bg=bg_color)
            lbl.pack(padx=10, pady=5)
            lbl.bind("<Button-1>", lambda e: self.start_drag(e, overlay))
            lbl.bind("<B1-Motion>", lambda e: self.drag(e, overlay))
            task["overlay_win"] = overlay
            task["overlay_label"] = lbl
        else:
            task["overlay_win"].config(bg=bg_color)
            task["overlay_label"].config(text=time_str, fg=fg_color, bg=bg_color)

    def destroy_file_overlay(self, task):
        if task["overlay_win"] and task["overlay_win"].winfo_exists():
            task["overlay_win"].destroy()
        task["overlay_win"] = None
        task["overlay_label"] = None

    def start_drag(self, event, window):
        window.drag_data_x = event.x
        window.drag_data_y = event.y

    def drag(self, event, window):
        deltax = event.x - window.drag_data_x
        deltay = event.y - window.drag_data_y
        window.geometry(f"+{window.winfo_x() + deltax}+{window.winfo_y() + deltay}")


if __name__ == "__main__":
    root = tk.Tk()
    app = TrayRememberFileTimerApp(root)
    root.mainloop()