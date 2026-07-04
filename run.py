from __future__ import annotations

import io
import logging
import socket
import sys
import threading
import time
import ctypes
import webbrowser
from tkinter import messagebox
from pathlib import Path

import pystray
import uvicorn
import customtkinter as ctk
from app.main import app as fastapi_app
from PIL import Image, ImageDraw, ImageTk

# Enable High-DPI support on Windows to make UI text and icons perfectly crisp
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(2) # Per-Monitor DPI aware (Windows 8.1+)
except Exception:
    try:
        ctypes.windll.user32.SetProcessDPIAware() # Fallback (Windows Vista+)
    except Exception:
        pass

# Fix taskbar icon grouping on Windows 7+ (avoid generic Python icon in taskbar)
MY_APP_ID = "ru.uk-uchet.billingapp.1.0"
try:
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(MY_APP_ID)
except Exception:
    pass

APP_TITLE = "Учет недвижимости"
HOST = "127.0.0.1"
PORT = 8000
SERVER_URL = f"http://{HOST}:{PORT}"
ICON_SIZE = 64
_NULL_STDOUT: io.TextIOWrapper | None = None
_NULL_STDERR: io.TextIOWrapper | None = None

def build_icon_image(size: int = 64) -> Image.Image:
    # Dynamically draw a clean icon image with a stylized building/house logo
    img = Image.new("RGBA", (size, size), "#1e2324")
    draw = ImageDraw.Draw(img)
    # Draw simple building outline
    padding = size // 5
    draw.rectangle(
        [padding, padding * 2, size - padding, size - padding],
        fill="#b05d2d",
        outline="#fff6ea",
        width=max(1, size // 20)
    )
    draw.polygon(
        [
            (padding // 2, padding * 2),
            (size // 2, padding // 2),
            (size - padding // 2, padding * 2)
        ],
        fill="#7a3f1e",
        outline="#fff6ea",
        width=max(1, size // 20)
    )
    return img

def ensure_standard_streams() -> None:
    global _NULL_STDOUT, _NULL_STDERR
    if sys.stdout is None:
        if _NULL_STDOUT is None:
            _NULL_STDOUT = io.TextIOWrapper(open("NUL", "wb"), encoding="utf-8", line_buffering=True)
        sys.stdout = _NULL_STDOUT
    if sys.stderr is None:
        if _NULL_STDERR is None:
            _NULL_STDERR = io.TextIOWrapper(open("NUL", "wb"), encoding="utf-8", line_buffering=True)
        sys.stderr = _NULL_STDERR

def is_port_busy(host: str, port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(1)
        return sock.connect_ex((host, port)) == 0

def build_server_url(port: int) -> str:
    return f"http://{HOST}:{port}"

def is_our_app_running(host: str, port: int) -> bool:
    try:
        with urllib.request.urlopen(f"http://{host}:{port}/__health", timeout=1) as response:
            return b"RealEstateUtilityApp" in response.read()
    except (OSError, Exception):
        return False

def find_free_port(host: str, start_port: int) -> int:
    for port in range(start_port, start_port + 50):
        if not is_port_busy(host, port):
            return port
    raise RuntimeError("No free local port found")

# Configure CustomTkinter
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")  # fallback but we configure custom hex colors

class DesktopLauncher:
    def __init__(self) -> None:
        ensure_standard_streams()
        logging.basicConfig(level=logging.INFO, stream=sys.stderr)

        self.exiting = False
        self.browser_opened = False
        self.already_running = False
        self.port = PORT
        self.server_url = SERVER_URL
        self.server: uvicorn.Server | None = None
        self.server_thread: threading.Thread | None = None
        self.tray_icon: pystray.Icon | None = None
        self.tray_thread: threading.Thread | None = None

        # Resolve asset paths (supports frozen and raw script execution)
        self.script_dir = Path(__file__).resolve().parent
        self.bundle_dir = Path(getattr(sys, "_MEIPASS", self.script_dir))
        
        self.ico_path = self.bundle_dir / "app_icon.ico"
        self.png_path = self.bundle_dir / "app_icon.png"

        # CustomTkinter Window setup
        self.root = ctk.CTk()
        self.root.title(APP_TITLE)
        self.root.geometry("520x260")
        self.root.resizable(False, False)
        self.root.configure(fg_color="#1e2324")  # matching the sidebar background
        self.root.protocol("WM_DELETE_WINDOW", self.hide_window)

        # Apply application icon to main window using native Tkinter method
        if self.ico_path.exists():
            try:
                self.root.iconbitmap(str(self.ico_path))
            except Exception:
                try:
                    # Fallback to iconphoto if iconbitmap fails
                    from PIL import ImageTk
                    img = Image.open(self.png_path)
                    self.root.iconphoto(True, ImageTk.PhotoImage(img))
                except Exception:
                    pass

        self.status_var = ctk.StringVar(value="Подготавливаем запуск локального сервера...")
        self.url_var = ctk.StringVar(value=SERVER_URL)
        self._build_ui()

    def _build_ui(self) -> None:
        # Title
        self.title_label = ctk.CTkLabel(
            self.root, 
            text=APP_TITLE, 
            font=ctk.CTkFont(family="Inter", size=20, weight="bold"),
            text_color="#fff6ea"
        )
        self.title_label.pack(anchor="w", padx=25, pady=(25, 5))

        # Description
        self.desc_label = ctk.CTkLabel(
            self.root,
            text="Приложение работает в фоновом режиме. Управление сервером и запуск:",
            font=ctk.CTkFont(family="Inter", size=12),
            text_color="#a0a0a0"
        )
        self.desc_label.pack(anchor="w", padx=25, pady=(0, 15))

        # Status
        self.status_label = ctk.CTkLabel(
            self.root,
            textvariable=self.status_var,
            font=ctk.CTkFont(family="Inter", size=13, slant="italic"),
            text_color="#77c7ff"
        )
        self.status_label.pack(anchor="w", padx=25, pady=(0, 10))

        # Input field (readonly link)
        self.url_entry = ctk.CTkEntry(
            self.root,
            textvariable=self.url_var,
            font=ctk.CTkFont(family="Consolas", size=12),
            width=470,
            height=36,
            corner_radius=8,
            fg_color="#2d3335",
            border_color="#3a3f41",
            text_color="#ffffff",
            state="readonly"
        )
        self.url_entry.pack(padx=25, pady=(0, 20))

        # Action Buttons frame
        self.btn_frame = ctk.CTkFrame(self.root, fg_color="transparent")
        self.btn_frame.pack(fill="x", padx=25, pady=0)

        # Flat button style config
        self.open_btn = ctk.CTkButton(
            self.btn_frame,
            text="Открыть в браузере",
            command=self.open_browser,
            font=ctk.CTkFont(family="Inter", size=12, weight="bold"),
            fg_color="#b05d2d",
            hover_color="#7a3f1e",
            text_color="#ffffff",
            height=38,
            corner_radius=8
        )
        self.open_btn.pack(side="left", expand=True, fill="x", padx=(0, 8))

        self.control_btn = ctk.CTkButton(
            self.btn_frame,
            text="Выключить сервер",
            command=self.toggle_server,
            font=ctk.CTkFont(family="Inter", size=12, weight="bold"),
            fg_color="#d32f2f",
            hover_color="#b71c1c",
            text_color="#ffffff",
            height=38,
            corner_radius=8
        )
        self.control_btn.pack(side="left", expand=True, fill="x", padx=(8, 0))

    def run(self) -> None:
        # Load high quality icons via WinAPI using exact System Metrics for scaling
        if self.ico_path.exists():
            try:
                # Force Tkinter to create the window handle and initialize WinAPI components
                self.root.update_idletasks()
                
                user32 = ctypes.windll.user32
                hwnd = self.root.winfo_id()
                
                # Get exact required sizes for large (taskbar) and small (titlebar) icons based on current DPI
                cx_icon = user32.GetSystemMetrics(11) # SM_CXICON
                cy_icon = user32.GetSystemMetrics(12) # SM_CYICON
                cx_smicon = user32.GetSystemMetrics(49) # SM_CXSMICON
                cy_smicon = user32.GetSystemMetrics(50) # SM_CYSMICON
                
                # Load big and small icons using LoadImageW from the ICO file (0x00000010 = LR_LOADFROMFILE)
                hicon_big = user32.LoadImageW(0, str(self.ico_path), 1, cx_icon, cy_icon, 0x00000010)
                hicon_small = user32.LoadImageW(0, str(self.ico_path), 1, cx_smicon, cy_smicon, 0x00000010)
                
                if hicon_big:
                    user32.SendMessageW(hwnd, 0x0080, 1, hicon_big) # WM_SETICON, ICON_BIG
                if hicon_small:
                    user32.SendMessageW(hwnd, 0x0080, 0, hicon_small) # WM_SETICON, ICON_SMALL
            except Exception:
                pass

        if is_port_busy(HOST, PORT):
            if is_our_app_running(HOST, PORT):
                self.already_running = True
                self.status_var.set("Приложение уже запущено. Открываем веб-интерфейс.")
                self._start_tray()
                self.root.after(100, self._notify_already_running)
                self.root.mainloop()
                return
            self.port = find_free_port(HOST, PORT + 1)
            self.server_url = build_server_url(self.port)
            self.url_var.set(self.server_url)

        self._start_tray()
        self._start_server()
        threading.Thread(target=self._wait_for_server_ready, name="server-ready-waiter", daemon=True).start()
        self.root.mainloop()

    def _notify_already_running(self) -> None:
        self.open_browser()
        messagebox.showinfo(APP_TITLE, "Приложение уже запущено. Открываю страницу в браузере.")
        self.show_window()

    def _start_server(self) -> None:
        config = uvicorn.Config(
            fastapi_app,
            host=HOST,
            port=self.port,
            reload=False,
            log_config=None,
            access_log=False,
        )
        self.server = uvicorn.Server(config)
        self.server_thread = threading.Thread(target=self._run_server, name="uvicorn-server", daemon=True)
        self.server_thread.start()
        self.status_var.set("Запускаем веб-сервер...")
        self.control_btn.configure(text="Выключить сервер", fg_color="#d32f2f", hover_color="#b71c1c")
        self.open_btn.configure(state="normal")

    def _run_server(self) -> None:
        try:
            assert self.server is not None
            self.server.run()
        except Exception:
            logging.exception("Desktop launcher failed to start the server")
            self.root.after(0, self._handle_server_failure)
        finally:
            self.root.after(0, self._handle_server_stopped)

    def _wait_for_server_ready(self) -> None:
        for _ in range(120):
            if self.exiting:
                return
            if is_port_busy(HOST, self.port):
                self.root.after(0, self._handle_server_ready)
                return
            if self.server_thread and not self.server_thread.is_alive():
                return
            time.sleep(0.25)
        self.root.after(0, self._handle_server_timeout)

    def _handle_server_ready(self) -> None:
        if self.exiting:
            return
        self.status_var.set("Локальный сервер готов. Можно работать.")
        if self.tray_icon is not None:
            try:
                self.tray_icon.title = f"{APP_TITLE} - запущено"
            except Exception:
                logging.exception("Failed to update tray icon title")
        if not self.browser_opened:
            self.browser_opened = True
            self.open_browser()

    def _handle_server_timeout(self) -> None:
        if self.exiting:
            return
        self.status_var.set("Сервер не ответил вовремя. Пожалуйста, перезапустите.")
        self.show_window()

    def _handle_server_failure(self) -> None:
        if self.exiting:
            return
        self.status_var.set("Не удалось запустить сервер.")
        self.show_window()
        self.control_btn.configure(text="Запустить сервер", fg_color="#2e7d32", hover_color="#1b5e20")
        self.open_btn.configure(state="disabled")
        messagebox.showerror(APP_TITLE, "Не удалось запустить локальный сервер приложения.")

    def _handle_server_stopped(self) -> None:
        if self.exiting:
            return
        self.status_var.set("Локальный сервер остановлен.")
        self.control_btn.configure(text="Запустить сервер", fg_color="#2e7d32", hover_color="#1b5e20")
        self.open_btn.configure(state="disabled")
        if self.tray_icon is not None:
            try:
                self.tray_icon.title = f"{APP_TITLE} - остановлен"
            except Exception:
                pass

    def toggle_server(self) -> None:
        # If server is running, stop it
        if self.server is not None and not self.server.should_exit:
            self.status_var.set("Останавливаем сервер...")
            self.server.should_exit = True
            self.server.force_exit = True
        else:
            # If server is stopped, start it
            self._start_server()
            threading.Thread(target=self._wait_for_server_ready, name="server-ready-waiter", daemon=True).start()

    def _start_tray(self) -> None:
        self.tray_thread = threading.Thread(target=self._run_tray_icon, name="tray-icon", daemon=True)
        self.tray_thread.start()

    def _run_tray_icon(self) -> None:
        menu = pystray.Menu(
            pystray.MenuItem("Открыть в браузере", lambda icon, item: self._run_in_ui_thread(self.open_browser)),
            pystray.MenuItem("Панель управления", lambda icon, item: self._run_in_ui_thread(self.show_window), default=True),
            pystray.MenuItem("Выход", lambda icon, item: self._run_in_ui_thread(self.exit_application)),
        )
        # Load app_icon.png for the tray icon
        try:
            tray_img = Image.open(self.png_path)
        except Exception:
            # Fallback if file not found
            tray_img = build_icon_image(64)

        self.tray_icon = pystray.Icon(
            "realestateutilityapp", 
            tray_img, 
            APP_TITLE, 
            menu,
            # Single or double click on tray icon restores control panel
            action=lambda icon, item: self._run_in_ui_thread(self.show_window)
        )
        self.tray_icon.run()

    def _run_in_ui_thread(self, callback) -> None:
        if not self.exiting:
            self.root.after(0, callback)

    def open_browser(self) -> None:
        if self.server is not None and not self.server.should_exit:
            webbrowser.open(self.server_url)

    def show_window(self) -> None:
        if self.exiting:
            return
        
        # WinAPI focus restoration to bypass Windows restrictions on background deiconify
        try:
            user32 = ctypes.windll.user32
            hwnd = self.root.winfo_id()
            user32.ShowWindow(hwnd, 9) # SW_RESTORE
            user32.SetForegroundWindow(hwnd)
        except Exception:
            pass

        self.root.deiconify()
        self.root.state("normal")
        self.root.lift()
        self.root.focus_force()

    def hide_window(self) -> None:
        if self.exiting:
            return
        self.status_var.set("Сервер работает в фоне. Иконка доступна в трее Windows.")
        self.root.withdraw()

    def exit_application(self) -> None:
        if self.exiting:
            return
        self.exiting = True
        self.status_var.set("Завершаем процессы...")
        self.root.withdraw()
        threading.Thread(target=self._shutdown_worker, name="shutdown-worker", daemon=True).start()

    def _shutdown_worker(self) -> None:
        if self.server is not None:
            self.server.should_exit = True
            self.server.force_exit = True
        if self.server_thread and self.server_thread.is_alive():
            self.server_thread.join(timeout=10)
        if self.tray_icon is not None:
            self.tray_icon.stop()
        self.root.after(0, self.root.destroy)

if __name__ == "__main__":
    DesktopLauncher().run()
