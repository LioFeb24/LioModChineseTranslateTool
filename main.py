import os
import queue
import shutil
import sys
import tempfile
import threading
import tkinter as tk
import webbrowser
from tkinter import filedialog, messagebox

import customtkinter as ctk

from call_llm import validate_api_key
from config import DEFAULT_BASE_URL, get_config, save_config
from create_jar import create_jar
from find_json import find_json
from translate_json import translate_json
from unpack_jar import unpack_jar


ctk.set_appearance_mode("light")
ctk.set_default_color_theme("blue")

BG_COLOR = "#EEF6FF"
CARD_COLOR = "#F7FBFF"
INSET_OUTER = "#CFE2F6"
INSET_INNER = "#FCFEFF"
TEXT_COLOR = "#12385C"
SUBTEXT_COLOR = "#4B6B8D"
BUTTON_COLOR = "#A9D4FF"
BUTTON_HOVER = "#8CC4FF"
PROGRESS_COLOR = "#5CA9FF"
BORDER_COLOR = "#BCD8F4"


def get_resource_path(*parts: str) -> str:
    base_dir = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base_dir, *parts)


def choose_target_json(json_paths: list[str]) -> str:
    if not json_paths:
        raise FileNotFoundError("未找到可翻译的语言 json 文件")
    for path in json_paths:
        name = os.path.basename(path).lower()
        if name in {"en_us.json", "en-us.json"}:
            return path
    return json_paths[0]


def run_pipeline(
    jar_path: str,
    output_path: str,
    *,
    emit_event,
) -> str:
    jar_abs = os.path.abspath(jar_path)
    out_abs = os.path.abspath(output_path)
    files_root = os.path.abspath("files")
    temp_root = os.path.join(files_root, "temp")
    os.makedirs(temp_root, exist_ok=True)
    work_dir = tempfile.mkdtemp(prefix="autochinese_", dir=temp_root)
    completed = False

    try:
        emit_event({"type": "phase", "message": "开始解包 jar..."})
        unpack_jar(jar_abs, work_dir)

        json_list = find_json(work_dir)
        emit_event({"type": "phase", "message": f"找到 {len(json_list)} 个语言 json 文件"})
        target_json = choose_target_json(json_list)
        emit_event({"type": "phase", "message": f"目标语言文件：{target_json}"})

        emit_event({"type": "phase", "message": "开始翻译 json..."})
        translate_json(
            target_json,
            progress_callback=emit_event,
        )

        emit_event({"type": "phase", "message": "开始重新打包 jar..."})
        create_jar(work_dir, out_abs, prefer_java=True)
        emit_event({"type": "phase", "message": "处理完成"})
        completed = True
        return out_abs
    finally:
        shutil.rmtree(work_dir, ignore_errors=True)
        if completed:
            shutil.rmtree(files_root, ignore_errors=True)


class App:
    def __init__(self, root: ctk.CTk) -> None:
        self.root = root
        self.root.title("Lio's Mod汉化工具")
        self.root.geometry("600x730")
        self.root.resizable(False, False)
        self.root.configure(fg_color=BG_COLOR)
        self._icon_image: tk.PhotoImage | None = None
        self._set_window_icon()

        self.event_queue: queue.Queue[dict] = queue.Queue()
        self.worker: threading.Thread | None = None
        self.auth_worker: threading.Thread | None = None

        config = get_config()

        self.jar_path_var = tk.StringVar()
        self.output_path_var = tk.StringVar()
        self.api_key_var = tk.StringVar(value=config.get("api_key", ""))
        self.base_url_var = tk.StringVar(value=config.get("base_url", DEFAULT_BASE_URL))
        self.status_var = tk.StringVar(value="就绪")
        self.detail_var = tk.StringVar(value="等待开始")
        self.src_var = tk.StringVar(value="")
        self.dst_var = tk.StringVar(value="")

        self.font_main = ctk.CTkFont(family="宋体", size=13)
        self.font_title = ctk.CTkFont(family="宋体", size=14, weight="bold")
        self.font_small = ctk.CTkFont(family="宋体", size=12)
        self.api_validated = False
        self._suspend_validation_watch = False

        self._build_ui()
        self._bind_validation_watchers()
        self._set_start_button_enabled(False)
        self.status_var.set("待鉴权")
        self.detail_var.set("请先填写 API Key，并点击“检查 API Key”")
        self.root.after(100, self._poll_event_queue)

    def _set_window_icon(self) -> None:
        png_icon_path = get_resource_path("icon.png")
        ico_icon_path = get_resource_path("icon.ico")

        if not os.path.exists(png_icon_path) and not os.path.exists(ico_icon_path):
            return

        try:
            # 单文件打包后资源会被解压到临时目录，优先直接使用已内嵌的 ico/png。
            if os.name == "nt" and os.path.exists(ico_icon_path):
                self.root.iconbitmap(ico_icon_path)
            if os.path.exists(png_icon_path):
                self._icon_image = tk.PhotoImage(file=png_icon_path)
                self.root.iconphoto(True, self._icon_image)
        except Exception:
            pass

    def _make_inset_display(
        self,
        parent,
        *,
        textvariable: tk.StringVar,
        width: int,
        height: int,
        on_click=None,
    ):
        outer = ctk.CTkFrame(
            parent,
            fg_color=INSET_OUTER,
            corner_radius=12,
            border_width=1,
            border_color=BORDER_COLOR,
        )
        outer.configure(width=width, height=height)
        outer.grid_propagate(False)

        inner = ctk.CTkFrame(
            outer,
            fg_color=INSET_INNER,
            corner_radius=10,
        )
        inner.place(relx=0.5, rely=0.5, anchor="center", relwidth=0.97, relheight=0.94)

        label = ctk.CTkLabel(
            inner,
            text="",
            textvariable=textvariable,
            font=self.font_small,
            text_color=TEXT_COLOR,
            justify="left",
            anchor="nw",
            wraplength=width - 36,
        )
        label.pack(fill="both", expand=True, padx=12, pady=10)
        if on_click is not None:
            for widget in (outer, inner, label):
                widget.bind("<Button-1>", on_click)
                widget.configure(cursor="hand2")
        return outer

    def _build_ui(self) -> None:
        frame = ctk.CTkFrame(self.root, fg_color=BG_COLOR, corner_radius=0)
        frame.pack(fill="both", expand=True, padx=14, pady=14)
        frame.grid_columnconfigure(0, weight=0)
        frame.grid_columnconfigure(1, weight=1)
        frame.grid_columnconfigure(2, weight=0)
        frame.grid_rowconfigure(5, weight=1)

        ctk.CTkLabel(
            frame,
            text="Mod文件",
            font=self.font_title,
            text_color=TEXT_COLOR,
        ).grid(row=0, column=0, sticky="w", padx=(0, 8), pady=(0, 8))

        self.jar_entry = ctk.CTkEntry(
            frame,
            textvariable=self.jar_path_var,
            width=320,
            height=36,
            corner_radius=10,
            fg_color=INSET_INNER,
            border_color=BORDER_COLOR,
            text_color=TEXT_COLOR,
            font=self.font_main,
        )
        self.jar_entry.grid(row=0, column=1, sticky="ew", pady=(0, 8))

        ctk.CTkButton(
            frame,
            text="选择文件",
            command=self.select_jar_file,
            width=92,
            height=36,
            corner_radius=12,
            fg_color=BUTTON_COLOR,
            hover_color=BUTTON_HOVER,
            text_color=TEXT_COLOR,
            font=self.font_main,
            border_width=1,
            border_color="#D6EAFF",
        ).grid(row=0, column=2, padx=(10, 0), pady=(0, 8))

        ctk.CTkLabel(
            frame,
            text="汉化Mod文件",
            font=self.font_title,
            text_color=TEXT_COLOR,
        ).grid(row=1, column=0, sticky="nw", padx=(0, 8), pady=(0, 10))

        self.output_card = self._make_inset_display(
            frame,
            textvariable=self.output_path_var,
            width=422,
            height=54,
            on_click=self.copy_output_path,
        )
        self.output_card.grid(row=1, column=1, columnspan=2, sticky="ew", pady=(0, 10))

        config_box = ctk.CTkFrame(
            frame,
            fg_color=CARD_COLOR,
            corner_radius=14,
            border_width=1,
            border_color=BORDER_COLOR,
        )
        config_box.grid(row=2, column=0, columnspan=3, sticky="ew", pady=(0, 12))
        config_box.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(
            config_box,
            text="LLM 配置",
            font=self.font_title,
            text_color=TEXT_COLOR,
        ).grid(row=0, column=0, sticky="w", padx=14, pady=(12, 8))
        platform_label = ctk.CTkLabel(
            config_box,
            text="获取apikey",
            font=self.font_small,
            text_color=BUTTON_HOVER,
            cursor="hand2",
        )
        platform_label.grid(row=0, column=1, sticky="e", padx=14, pady=(12, 8))
        platform_label.bind("<Button-1>", self.open_deepseek_platform)

        ctk.CTkLabel(config_box, text="API Key", font=self.font_main, text_color=TEXT_COLOR).grid(
            row=1, column=0, sticky="w", padx=14, pady=6
        )
        ctk.CTkEntry(
            config_box,
            textvariable=self.api_key_var,
            show="*",
            height=34,
            corner_radius=10,
            fg_color=INSET_INNER,
            border_color=BORDER_COLOR,
            text_color=TEXT_COLOR,
            font=self.font_main,
        ).grid(row=1, column=1, sticky="ew", padx=(0, 14), pady=6)

        ctk.CTkLabel(config_box, text="Base URL", font=self.font_main, text_color=TEXT_COLOR).grid(
            row=2, column=0, sticky="w", padx=14, pady=6
        )
        ctk.CTkEntry(
            config_box,
            textvariable=self.base_url_var,
            height=34,
            corner_radius=10,
            fg_color=INSET_INNER,
            border_color=BORDER_COLOR,
            text_color=TEXT_COLOR,
            font=self.font_main,
        ).grid(row=2, column=1, sticky="ew", padx=(0, 14), pady=6)

        option_row = ctk.CTkFrame(config_box, fg_color="transparent")
        option_row.grid(row=3, column=0, columnspan=2, sticky="ew", padx=14, pady=(6, 12))
        option_row.grid_columnconfigure(0, weight=1)
        option_row.grid_columnconfigure(1, weight=0)
        option_row.grid_columnconfigure(2, weight=1)
        ctk.CTkButton(
            option_row,
            text="检查 API Key",
            command=self.check_api_key,
            width=120,
            height=34,
            corner_radius=12,
            fg_color=BUTTON_COLOR,
            hover_color=BUTTON_HOVER,
            text_color=TEXT_COLOR,
            font=self.font_main,
            border_width=1,
            border_color="#D6EAFF",
        ).grid(row=0, column=1)

        button_row = ctk.CTkFrame(frame, fg_color="transparent")
        button_row.grid(row=3, column=0, columnspan=3, sticky="ew", pady=(0, 10))
        button_row.grid_columnconfigure(0, weight=1)
        button_row.grid_columnconfigure(1, weight=0)
        button_row.grid_columnconfigure(2, weight=1)
        self.start_button = ctk.CTkButton(
            button_row,
            text="开始处理",
            command=self.start_pipeline,
            width=112,
            height=38,
            corner_radius=14,
            fg_color=BUTTON_COLOR,
            hover_color=BUTTON_HOVER,
            text_color=TEXT_COLOR,
            font=self.font_title,
            border_width=1,
            border_color="#D6EAFF",
        )
        self.start_button.grid(row=0, column=1)
        ctk.CTkLabel(
            button_row,
            textvariable=self.status_var,
            font=self.font_main,
            text_color=SUBTEXT_COLOR,
        ).grid(row=1, column=0, columnspan=3, pady=(8, 0))

        progress_box = ctk.CTkFrame(
            frame,
            fg_color=CARD_COLOR,
            corner_radius=14,
            border_width=1,
            border_color=BORDER_COLOR,
        )
        progress_box.grid(row=4, column=0, columnspan=3, sticky="ew", pady=(0, 10))
        progress_box.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            progress_box,
            text="翻译进度",
            font=self.font_title,
            text_color=TEXT_COLOR,
        ).grid(row=0, column=0, sticky="w", padx=14, pady=(10, 6))

        self.progress_bar = ctk.CTkProgressBar(
            progress_box,
            width=540,
            height=18,
            corner_radius=10,
            progress_color=PROGRESS_COLOR,
            fg_color="#DCEBFA",
            border_color="#DCEBFA",
        )
        self.progress_bar.grid(row=1, column=0, sticky="ew", padx=14)
        self.progress_bar.set(0)

        ctk.CTkLabel(
            progress_box,
            textvariable=self.detail_var,
            font=self.font_small,
            text_color=SUBTEXT_COLOR,
            justify="left",
            anchor="w",
            wraplength=540,
        ).grid(row=2, column=0, sticky="w", padx=14, pady=(8, 12))

        content_box = ctk.CTkFrame(frame, fg_color="transparent")
        content_box.grid(row=5, column=0, columnspan=3, sticky="nsew")
        content_box.grid_columnconfigure(0, weight=1)
        content_box.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(
            content_box,
            text="原文",
            font=self.font_title,
            text_color=TEXT_COLOR,
        ).grid(row=0, column=0, sticky="w", pady=(0, 6))
        ctk.CTkLabel(
            content_box,
            text="译文",
            font=self.font_title,
            text_color=TEXT_COLOR,
        ).grid(row=0, column=1, sticky="w", padx=(10, 0), pady=(0, 6))

        src_box = self._make_inset_display(
            content_box,
            textvariable=self.src_var,
            width=276,
            height=100,
        )
        src_box.grid(row=1, column=0, sticky="w")

        dst_box = self._make_inset_display(
            content_box,
            textvariable=self.dst_var,
            width=276,
            height=100,
        )
        dst_box.grid(row=1, column=1, sticky="e", padx=(10, 0))

        footer_row = ctk.CTkFrame(frame, fg_color="transparent")
        footer_row.grid(row=6, column=0, columnspan=3, sticky="ew", pady=(8, 0))
        footer_row.grid_columnconfigure(0, weight=1)

        github_label = ctk.CTkLabel(
            footer_row,
            text="GitHub",
            font=self.font_small,
            text_color=BUTTON_HOVER,
            cursor="hand2",
        )
        github_label.grid(row=0, column=1, sticky="e", padx=(0, 10))
        github_label.bind("<Button-1>", self.open_github_profile)

        bilibili_label = ctk.CTkLabel(
            footer_row,
            text="BiliBili",
            font=self.font_small,
            text_color=BUTTON_HOVER,
            cursor="hand2",
        )
        bilibili_label.grid(row=0, column=2, sticky="e")
        bilibili_label.bind("<Button-1>", self.open_bilibili_profile)

    def open_deepseek_platform(self, _event=None) -> None:
        self._open_url("https://platform.deepseek.com/", "无法打开 DeepSeek 平台页面喵")

    def open_github_profile(self, _event=None) -> None:
        self._open_url("https://github.com/LioFeb24", "无法打开 GitHub 页面喵")

    def open_bilibili_profile(self, _event=None) -> None:
        self._open_url("https://space.bilibili.com/171385676", "无法打开 BiliBili 页面喵")

    def _open_url(self, url: str, error_message: str) -> None:
        try:
            webbrowser.open(url, new=2)
        except Exception:
            messagebox.showerror("错误", error_message)

    def emit_event(self, event: dict) -> None:
        self.event_queue.put(event)

    def _set_display_text(self, src: str = "", dst: str = "") -> None:
        self.src_var.set(src)
        self.dst_var.set(dst)

    def _bind_validation_watchers(self) -> None:
        self.api_key_var.trace_add("write", self._on_llm_config_changed)
        self.base_url_var.trace_add("write", self._on_llm_config_changed)

    def _set_start_button_enabled(self, enabled: bool) -> None:
        if enabled:
            self.start_button.configure(state="normal")
        else:
            self.start_button.configure(state="disabled")

    def _current_llm_signature(self) -> tuple[str, str]:
        return (
            self.api_key_var.get().strip(),
            self.base_url_var.get().strip() or DEFAULT_BASE_URL,
        )

    def _on_llm_config_changed(self, *_args) -> None:
        if self._suspend_validation_watch:
            return
        if self.api_validated:
            self.api_validated = False
            self._set_start_button_enabled(False)
            self.status_var.set("待鉴权")
            self.detail_var.set("API Key 或 Base URL 已变更，请重新检查 API Key")

    def _show_copied_toast(self, message: str) -> None:
        toast = ctk.CTkToplevel(self.root)
        toast.overrideredirect(True)
        toast.attributes("-topmost", True)
        toast.configure(fg_color=BUTTON_COLOR)

        width = 96
        height = 38
        self.root.update_idletasks()
        if hasattr(self, "output_card"):
            x = self.output_card.winfo_rootx() + max(0, (self.output_card.winfo_width() - width) // 2)
            y = self.output_card.winfo_rooty() + self.output_card.winfo_height() + 6
        else:
            x = self.root.winfo_rootx() + (self.root.winfo_width() - width) // 2
            y = self.root.winfo_rooty() + 80
        toast.geometry(f"{width}x{height}+{x}+{y}")

        ctk.CTkLabel(
            toast,
            text=message,
            font=self.font_main,
            text_color=TEXT_COLOR,
            justify="center",
            anchor="center",
        ).pack(expand=True, fill="both", padx=1, pady=1)

        toast.after(1200, toast.destroy)

    def copy_output_path(self, _event=None) -> None:
        output_path = self.output_path_var.get().strip()
        if not output_path:
            return
        self.root.clipboard_clear()
        self.root.clipboard_append(output_path)
        self.root.update()
        self._show_copied_toast("已复制！")

    def _poll_event_queue(self) -> None:
        while True:
            try:
                event = self.event_queue.get_nowait()
            except queue.Empty:
                break

            event_type = event.get("type")
            if event_type == "phase":
                self.status_var.set(event.get("message", "运行中"))
            elif event_type == "auth_running":
                self.status_var.set("鉴权中")
                self.detail_var.set(event.get("message", "正在检查 API Key..."))
            elif event_type == "auth_success":
                if tuple(event.get("signature", ())) != self._current_llm_signature():
                    continue
                save_config(
                    {
                        "api_key": self.api_key_var.get().strip(),
                        "base_url": self.base_url_var.get().strip() or DEFAULT_BASE_URL,
                    }
                )
                self.api_validated = True
                self._set_start_button_enabled(True)
                self.status_var.set("鉴权成功")
                self.detail_var.set(event.get("message", "API Key 鉴权成功，已自动应用到当前运行"))
            elif event_type == "auth_error":
                if tuple(event.get("signature", ())) != self._current_llm_signature():
                    continue
                self.api_validated = False
                self._set_start_button_enabled(False)
                self.status_var.set("鉴权失败")
                self.detail_var.set(event.get("message", "API Key 鉴权失败"))
            elif event_type == "start":
                self.progress_bar.set(0)
                total = event.get("total", 0)
                self.detail_var.set(f"准备翻译，共 {total} 条")
                self._set_display_text()
            elif event_type == "progress":
                total = max(1, int(event.get("total", 0)))
                done = int(event.get("done", 0))
                changed = int(event.get("changed", 0))
                skipped = int(event.get("skipped", 0))
                failed = int(event.get("failed", 0))
                cached = bool(event.get("cached", False))
                path = event.get("path", "")
                self.progress_bar.set(done / total)
                tag = "缓存" if cached else "翻译"
                self.detail_var.set(
                    f"{tag}中：{done}/{total} | changed={changed} | skipped={skipped} | failed={failed} | path={path}"
                )
                self._set_display_text(event.get("src", ""), event.get("dst", ""))
            elif event_type == "warning":
                total = max(1, int(event.get("total", 0)))
                done = int(event.get("done", 0))
                changed = int(event.get("changed", 0))
                skipped = int(event.get("skipped", 0))
                failed = int(event.get("failed", 0))
                path = event.get("path", "")
                self.progress_bar.set(done / total)
                self.status_var.set("部分条目保留原文")
                self.detail_var.set(
                    f"警告：{done}/{total} | changed={changed} | skipped={skipped} | failed={failed} | path={path}"
                )
                self._set_display_text(event.get("src", ""), event.get("dst", ""))
            elif event_type == "done":
                self.progress_bar.set(1)
                self.status_var.set("翻译完成")
                self.detail_var.set(
                    f"完成：done={event.get('done', 0)}/{event.get('total', 0)} | "
                    f"changed={event.get('changed', 0)} | skipped={event.get('skipped', 0)} | failed={event.get('failed', 0)}"
                )
            elif event_type == "error":
                self.status_var.set("翻译失败")
                self.detail_var.set(f"失败位置：{event.get('path', '')}")
                self._set_display_text(event.get("src", ""), "")

        self.root.after(100, self._poll_event_queue)

    def select_jar_file(self) -> None:
        path = filedialog.askopenfilename(
            title="选择Mod文件",
            filetypes=[("Mod文件", "*.jar"), ("所有文件", "*.*")],
        )
        if not path:
            return
        self.jar_path_var.set(path)
        self.output_path_var.set(self._default_output_path(path))

    def _default_output_path(self, jar_path: str) -> str:
        if not jar_path:
            return ""
        if jar_path.lower().endswith(".jar"):
            return jar_path[:-4] + "-chinese.jar"
        return jar_path + "-chinese.jar"

    def check_api_key(self) -> None:
        if self.worker and self.worker.is_alive():
            messagebox.showinfo("提示", "翻译任务运行中，暂不能进行鉴权检查")
            return
        if self.auth_worker and self.auth_worker.is_alive():
            messagebox.showinfo("提示", "API Key 正在检查中")
            return

        api_key = self.api_key_var.get().strip()
        base_url = self.base_url_var.get().strip() or DEFAULT_BASE_URL
        signature = (api_key, base_url)
        self._suspend_validation_watch = True
        self.base_url_var.set(base_url)
        self._suspend_validation_watch = False
        self.api_validated = False
        self._set_start_button_enabled(False)
        self.emit_event({"type": "auth_running", "message": "正在检查 API Key 可用性...", "signature": signature})

        def worker() -> None:
            ok, message = validate_api_key(api_key, base_url)
            self.emit_event(
                {
                    "type": "auth_success" if ok else "auth_error",
                    "message": message,
                    "signature": signature,
                }
            )

        self.auth_worker = threading.Thread(target=worker, daemon=True)
        self.auth_worker.start()

    def start_pipeline(self) -> None:
        if self.worker and self.worker.is_alive():
            messagebox.showinfo("提示", "任务正在运行中")
            return
        if self.auth_worker and self.auth_worker.is_alive():
            messagebox.showinfo("提示", "请等待 API Key 检查完成")
            return
        if not self.api_validated:
            messagebox.showerror("错误", "请先点击“检查 API Key”，鉴权成功后再开始处理")
            return

        jar_path = self.jar_path_var.get().strip()
        output_path = self.output_path_var.get().strip()
        if not jar_path:
            messagebox.showerror("错误", "请先选择 Mod 文件")
            return
        if not os.path.isfile(jar_path):
            messagebox.showerror("错误", f"Mod 文件不存在：{jar_path}")
            return
        if not output_path:
            output_path = self._default_output_path(jar_path)
            self.output_path_var.set(output_path)

        self._set_display_text()
        self.progress_bar.set(0)
        self.detail_var.set("准备开始")
        self.status_var.set("运行中")

        def worker() -> None:
            try:
                result = run_pipeline(
                    jar_path,
                    output_path,
                    emit_event=self.emit_event,
                )
            except Exception as e:
                error_message = str(e)
                self.emit_event({"type": "phase", "message": "处理失败"})
                self.root.after(0, lambda: self.status_var.set("失败"))
                self.root.after(0, lambda msg=error_message: messagebox.showerror("处理失败", msg))
                return
            result_message = f"已生成：\n{result}"
            self.emit_event({"type": "phase", "message": f"输出文件：{result}"})
            self.root.after(0, lambda: self.status_var.set("完成"))
            self.root.after(0, lambda msg=result_message: messagebox.showinfo("完成", msg))

        self.worker = threading.Thread(target=worker, daemon=True)
        self.worker.start()


def main() -> None:
    root = ctk.CTk()
    App(root)
    root.mainloop()


if __name__ == "__main__":
    main()
