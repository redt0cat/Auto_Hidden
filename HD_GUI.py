import win32gui
import win32con
import threading
import json
import os
import time
import tkinter as tk
from tkinter import messagebox
import keyboard

# ==========================
# 1. 全域變數與設定檔
# ==========================
CONFIG_FILE = "config.json"
DEFAULT_HOTKEY = "ctrl+alt+h"
current_hotkey = DEFAULT_HOTKEY
SELF_WINDOW_TITLE = "Window Manager"
ALL_HIDDEN_WINDOWS = {}
TOGGLE_STATE = False

hidden_windows = {}
windows_list = []

hotkey_label = None
hotkey_entry = None

# ==========================
# 2. 設定檔載入與儲存
# ==========================
def load_config():
    global current_hotkey
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            current_hotkey = data.get("hotkey", DEFAULT_HOTKEY)
    else:
        save_config(DEFAULT_HOTKEY)

def save_config(hotkey):
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump({"hotkey": hotkey}, f, indent=2)

# ==========================
# 3. 熱鍵切換功能
# ==========================
def toggle_all_visible_windows():
    global TOGGLE_STATE, ALL_HIDDEN_WINDOWS
    if not TOGGLE_STATE:
        ALL_HIDDEN_WINDOWS = {}
        for hwnd, title in list_windows():
            if title != SELF_WINDOW_TITLE and win32gui.IsWindowVisible(hwnd):
                try:
                    win32gui.ShowWindow(hwnd, win32con.SW_HIDE)
                    ALL_HIDDEN_WINDOWS[title] = hwnd
                except:
                    pass
        TOGGLE_STATE = True
    else:
        for title, hwnd in ALL_HIDDEN_WINDOWS.items():
            if win32gui.IsWindow(hwnd):
                try:
                    win32gui.ShowWindow(hwnd, win32con.SW_SHOW)
                except:
                    pass
        ALL_HIDDEN_WINDOWS.clear()
        TOGGLE_STATE = False

def update_hotkey():
    global current_hotkey
    new_hotkey = hotkey_entry.get().strip().lower()
    if new_hotkey and new_hotkey != current_hotkey:
        try:
            keyboard.remove_hotkey(current_hotkey)
        except:
            pass
        try:
            keyboard.add_hotkey(new_hotkey, toggle_all_visible_windows)
            current_hotkey = new_hotkey
            save_config(current_hotkey)
            hotkey_label.config(text=f"💡 快捷鍵：{current_hotkey}")
            messagebox.showinfo("設定成功", f"新的快捷鍵為：{current_hotkey}")
        except Exception as e:
            messagebox.showerror("錯誤", f"設定失敗：{e}")
    else:
        messagebox.showwarning("提示", "請輸入新的快捷鍵")

# ==========================
# 4. GUI
# ==========================
def start_gui():
    global hotkey_label, hotkey_entry, listbox_windows, listbox_hidden
    root = tk.Tk()
    root.title("system32")

    # 快捷鍵設定欄
    hotkey_frame = tk.Frame(root)
    hotkey_frame.pack(side=tk.TOP, pady=5)
    hotkey_label = tk.Label(hotkey_frame, text=f"💡 快捷鍵：{current_hotkey}", fg="blue")
    hotkey_label.pack()
    hotkey_entry = tk.Entry(hotkey_frame, width=20)
    hotkey_entry.pack()
    hotkey_entry.insert(0, current_hotkey)
    tk.Button(hotkey_frame, text="更新快捷鍵", command=update_hotkey).pack(pady=2)

    # 左側視窗列表
    frame_left = tk.Frame(root)
    frame_left.pack(side=tk.LEFT, padx=10, pady=10)
    tk.Label(frame_left, text="當前視窗列表").pack()
    listbox_windows = tk.Listbox(frame_left, width=40, height=20)
    listbox_windows.pack()

    # 右側隱藏視窗列表
    frame_right = tk.Frame(root)
    frame_right.pack(side=tk.RIGHT, padx=10, pady=10)
    tk.Label(frame_right, text="隱藏視窗列表").pack()
    listbox_hidden = tk.Listbox(frame_right, width=40, height=20)
    listbox_hidden.pack()

    threading.Thread(target=update_windows_list, daemon=True).start()
    root.mainloop()

# ==========================
# 5. 視窗列表管理
# ==========================
def list_windows():
    windows = []
    def enum_callback(hwnd, param):
        if win32gui.IsWindowVisible(hwnd):
            title = win32gui.GetWindowText(hwnd)
            if title:
                param.append((hwnd, title))
    win32gui.EnumWindows(enum_callback, windows)
    return windows

def update_windows_list():
    global windows_list
    while True:
        windows_list = list_windows()
        refresh_listboxes()
        time.sleep(5)

def refresh_listboxes():
    listbox_windows.delete(0, tk.END)
    for hwnd, title in windows_list:
        listbox_windows.insert(tk.END, f"{title} (句柄: {hwnd})")

    listbox_hidden.delete(0, tk.END)
    for title, hwnd in hidden_windows.items():
        if win32gui.IsWindow(hwnd) and not win32gui.IsWindowVisible(hwnd):
            status = "仍隱藏中"
        else:
            status = "可能已顯示/關閉"
        listbox_hidden.insert(tk.END, f"{title} (句柄: {hwnd}) - {status}")

# ==========================
# 6. 系統初始與啟動熱鍵監聽
# ==========================
def set_self_window_title():
    hwnd = win32gui.GetForegroundWindow()
    win32gui.SetWindowText(hwnd, SELF_WINDOW_TITLE)

def start_hotkey_listener():
    keyboard.add_hotkey(current_hotkey, toggle_all_visible_windows)
    keyboard.wait()

def main():
    load_config()
    set_self_window_title()
    threading.Thread(target=start_hotkey_listener, daemon=True).start()
    start_gui()

if __name__ == "__main__":
    main()
