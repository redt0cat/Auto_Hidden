import win32gui
import win32con
import json
import os
import sys

STATE_FILE = "windows_state.json"

def enum_windows_callback(hwnd, windows_list):
    """
    收集「可見且有標題」的視窗 (hwnd, title)
    """
    if win32gui.IsWindowVisible(hwnd):
        title = win32gui.GetWindowText(hwnd)
        if title:  # 有標題
            windows_list.append((hwnd, title))

def list_visible_windows():
    """
    枚舉目前所有可見視窗，回傳 [(hwnd, title), ...]
    """
    result = []
    win32gui.EnumWindows(enum_windows_callback, result)
    return result

def hide_window(hwnd):
    """
    隱藏指定視窗
    """
    win32gui.ShowWindow(hwnd, win32con.SW_HIDE)

def show_window(hwnd):
    """
    顯示指定視窗
    """
    win32gui.ShowWindow(hwnd, win32con.SW_SHOW)

def hide_all_windows_and_save():
    """
    1) 枚舉所有可見視窗並隱藏
    2) 把隱藏的視窗紀錄到 STATE_FILE
    """
    windows = list_visible_windows()
    # 將 (hwnd, title) 都放進一個清單裡
    windows_to_hide = []
    for hwnd, title in windows:
        # 如果你要排除某些視窗（例如自己的 console）可在這裡判斷
        # if "Python" in title:  # 範例：跳過 python console
        #     continue
        hide_window(hwnd)
        windows_to_hide.append((hwnd, title))
        print(f"隱藏視窗：{title} (hwnd={hwnd})")

    # 把隱藏過的視窗資訊寫入檔案
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(windows_to_hide, f, ensure_ascii=False, indent=2)

def show_all_windows_and_remove_file():
    """
    1) 從 STATE_FILE 載入先前隱藏的視窗
    2) 顯示它們
    3) 刪除 STATE_FILE（或清空）
    """
    if not os.path.exists(STATE_FILE):
        print("找不到視窗紀錄檔，無法顯示之前的視窗。")
        return

    with open(STATE_FILE, "r", encoding="utf-8") as f:
        hidden_windows = json.load(f)  # 形式: [(hwnd, title), (hwnd, title), ...]

    for (hwnd, title) in hidden_windows:
        # 需要先確認該 hwnd 是否有效
        if win32gui.IsWindow(hwnd):
            show_window(hwnd)
            print(f"顯示視窗：{title} (hwnd={hwnd})")
        else:
            print(f"無效的 hwnd={hwnd}（視窗可能已關閉）：{title}")

    # 顯示完後，刪除紀錄檔
    os.remove(STATE_FILE)
    print("已移除視窗紀錄檔。")

def main():
    # 如果檔案不存在，代表「第一次執行」，隱藏所有視窗
    if not os.path.exists(STATE_FILE):
        print("[第一次執行] 隱藏所有視窗...")
        hide_all_windows_and_save()
        print("所有可見視窗已隱藏，下次執行時將嘗試顯示它們。")
    else:
        # 檔案存在，代表「第二次(或之後)執行」，顯示之前隱藏的視窗
        print("[第二次執行] 顯示先前隱藏的視窗...")
        show_all_windows_and_remove_file()
        print("視窗已顯示，並移除紀錄檔。")

if __name__ == "__main__":
    main()
