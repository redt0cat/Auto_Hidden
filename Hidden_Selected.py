import win32gui
import win32con
import threading
import json
import os
import time
import tkinter as tk
from tkinter import messagebox

# ==========================
#  1) 自動隱藏目標視窗標題
# ==========================
# 只要程式偵測到這些標題的視窗，將自動執行隱藏 (SW_HIDE)
TARGET_TITLES_TO_HIDE = [
    "Notepad",       # 範例：記事本
    "Calculator",    # 範例：計算機
    # 你可以在這裡加入更多標題
]

# ==========================
#  2) 全域變數
# ==========================
hidden_windows = {}          # {視窗標題: hwnd}，記錄「已隱藏」的視窗
windows_list = []            # 當前所有可見視窗 (hwnd, title)
SAVE_FILE = "hidden_windows.json"  # 隱藏視窗記錄檔案
SELF_WINDOW_TITLE = "Window Manager"  # 防止隱藏到自己，可改成你想要的視窗標題

# ================
#   枚舉 & 列表
# ================
def enum_windows_callback(hwnd, windows):
    """收集所有可見的視窗 (hwnd, title)"""
    if win32gui.IsWindowVisible(hwnd):
        title = win32gui.GetWindowText(hwnd)
        if title:
            windows.append((hwnd, title))

def list_windows():
    """列出系統中所有可見視窗，回傳 [(hwnd, title), (hwnd, title), ...]"""
    windows = []
    win32gui.EnumWindows(enum_windows_callback, windows)
    return windows

# ================
#   隱藏 & 顯示
# ================
def hide_window(hwnd, title):
    """隱藏視窗"""
    win32gui.ShowWindow(hwnd, win32con.SW_HIDE)
    hidden_windows[title] = hwnd  # 加入隱藏清單
    save_hidden_windows()
    refresh_hidden_list()
    messagebox.showinfo("操作成功", f"已隱藏視窗：{title}")

def show_window(title):
    """顯示名稱匹配的視窗"""
    if title in hidden_windows:
        hwnd = hidden_windows[title]
        if win32gui.IsWindow(hwnd):  # 句柄仍有效
            win32gui.ShowWindow(hwnd, win32con.SW_SHOW)
            hidden_windows.pop(title, None)
            save_hidden_windows()
            refresh_hidden_list()
            messagebox.showinfo("操作成功", f"已顯示視窗：{title}")
        else:
            messagebox.showerror("錯誤", f"句柄失效，無法顯示：{title}")
    else:
        messagebox.showerror("錯誤", f"未找到名稱為 '{title}' 的隱藏視窗")

# ===================
#  (A) GUI 操作函式
# ===================
def hide_selected_window():
    """隱藏選擇的視窗（手動）"""
    try:
        selection = listbox_windows.get(listbox_windows.curselection())
        title = selection.split(" (句柄: ")[0]
        if title == SELF_WINDOW_TITLE:
            messagebox.showwarning("警告", "無法隱藏自身視窗")
            return
        for hwnd, win_title in windows_list:
            if win_title == title:
                hide_window(hwnd, title)
                break
    except tk.TclError:
        messagebox.showwarning("警告", "請選擇一個視窗")

def show_selected_window():
    """顯示選擇的視窗（手動）"""
    try:
        selection = listbox_hidden.get(listbox_hidden.curselection())
        title = selection.split(" (句柄: ")[0]
        show_window(title)
    except tk.TclError:
        messagebox.showwarning("警告", "請選擇一個隱藏中的視窗")

def refresh_window_list():
    """刷新當前視窗清單 (左側 Listbox)"""
    listbox_windows.delete(0, tk.END)
    for hwnd, title in windows_list:
        listbox_windows.insert(tk.END, f"{title} (句柄: {hwnd})")

def refresh_hidden_list():
    """刷新隱藏視窗清單 (右側 Listbox)"""
    listbox_hidden.delete(0, tk.END)
    for title, hwnd in hidden_windows.items():
        # 若視窗尚在且依然隱藏中，就顯示「仍隱藏中」
        # 若視窗雖在 hidden_windows，但可能已被手動關閉
        status = "仍隱藏中" if (win32gui.IsWindow(hwnd) and not win32gui.IsWindowVisible(hwnd)) else "可能已顯示/關閉"
        listbox_hidden.insert(tk.END, f"{title} (句柄: {hwnd}) - {status}")

# ===================
#  (B) 自動隱藏邏輯
# ===================
def auto_hide_check():
    """
    自動偵測：若有視窗標題在 TARGET_TITLES_TO_HIDE 內，就執行隱藏。
    同時檢查已隱藏的視窗是否被關閉，若關閉則自動從清單移除。
    此函式將在背景 thread 中週期性被呼叫。
    """
    global hidden_windows

    # 取得最新視窗清單
    current = list_windows()
    current_hwnds = set(hwnd for hwnd, t in current)

    # (A) 自動隱藏機制
    for hwnd, title in current:
        # 若標題是我們想要自動隱藏的，且還沒被隱藏
        if title in TARGET_TITLES_TO_HIDE and title not in hidden_windows:
            # 避免隱藏到自己
            if title == SELF_WINDOW_TITLE:
                continue
            # 執行隱藏
            win32gui.ShowWindow(hwnd, win32con.SW_HIDE)
            hidden_windows[title] = hwnd
            save_hidden_windows()
            print(f"[自動隱藏] 偵測到目標視窗: '{title}', 已執行隱藏。")

    # (B) 檢查已隱藏的視窗是否死亡（關閉程式或標題改變）
    dead_list = []
    for title, hwnd in hidden_windows.items():
        if not win32gui.IsWindow(hwnd):
            # 代表視窗已關閉/失效
            dead_list.append(title)

    # 從隱藏清單移除已死亡視窗
    for dead_title in dead_list:
        hidden_windows.pop(dead_title, None)
        save_hidden_windows()
        print(f"[自動隱藏] 已隱藏的視窗 '{dead_title}' 已關閉，從清單移除。")

def update_windows_list():
    """
    背景執行緒：負責每隔幾秒掃描「所有視窗」並刷新 GUI，
    並且呼叫 auto_hide_check() 做自動隱藏邏輯。
    """
    global windows_list
    while True:
        windows_list = list_windows()       # 枚舉所有可見視窗
        refresh_window_list()               # 更新左側清單 (當前視窗)
        auto_hide_check()                   # 執行自動隱藏檢查
        refresh_hidden_list()               # 更新右側清單 (隱藏視窗)
        time.sleep(5)                      # 每 5 秒掃描一次，可依需求自行調整

# ================
#   儲存 & 載入
# ================
def save_hidden_windows():
    """將 hidden_windows 寫入檔案 (JSON)"""
    with open(SAVE_FILE, "w", encoding="utf-8") as f:
        json.dump(hidden_windows, f)

def load_hidden_windows():
    """從檔案 (JSON) 載入 hidden_windows"""
    global hidden_windows
    if os.path.exists(SAVE_FILE):
        with open(SAVE_FILE, "r", encoding="utf-8") as f:
            hidden_windows = json.load(f)
    else:
        hidden_windows = {}

# ================
#   GUI 主流程
# ================
def set_self_window_title():
    """設定自身視窗標題，以避免不小心將自己隱藏"""
    hwnd = win32gui.GetForegroundWindow()
    win32gui.SetWindowText(hwnd, SELF_WINDOW_TITLE)

def start_gui():
    global listbox_windows, listbox_hidden

    root = tk.Tk()
    root.title("system32")

    # ----- Frame：當前視窗列表 -----
    frame_current = tk.Frame(root)
    frame_current.pack(side=tk.LEFT, padx=10, pady=10)
    tk.Label(frame_current, text="當前視窗列表").pack()
    listbox_windows = tk.Listbox(frame_current, width=40, height=20)
    listbox_windows.pack()
    tk.Button(frame_current, text="隱藏選定視窗", command=hide_selected_window).pack(pady=5)

    # ----- Frame：隱藏視窗列表 -----
    frame_hidden = tk.Frame(root)
    frame_hidden.pack(side=tk.RIGHT, padx=10, pady=10)
    tk.Label(frame_hidden, text="隱藏視窗列表").pack()
    listbox_hidden = tk.Listbox(frame_hidden, width=40, height=20)
    listbox_hidden.pack()
    tk.Button(frame_hidden, text="顯示選定視窗", command=show_selected_window).pack(pady=5)

    # 在背景執行緒中不斷刷新「當前視窗列表」&「自動隱藏」檢查
    threading.Thread(target=update_windows_list, daemon=True).start()

    root.mainloop()

def main():
    # 1. 設定自身視窗標題 (防止隱藏到自己)
    set_self_window_title()

    # 2. 載入已隱藏視窗記錄
    load_hidden_windows()

    # 3. 啟動 GUI
    start_gui()

if __name__ == "__main__":
    main()
