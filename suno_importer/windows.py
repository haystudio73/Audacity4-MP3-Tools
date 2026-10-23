"""Narrow Windows adapter: target one Audacity 4 window and its native Import dialog.

No shell commands, clipboard changes, screen coordinates, or arbitrary window input.
"""
from __future__ import annotations
import ctypes as C
import os
from ctypes import wintypes as W
from dataclasses import dataclass
from pathlib import Path
import time

U = C.WinDLL("user32", use_last_error=True)
K = C.WinDLL("kernel32", use_last_error=True)
PTR = C.c_size_t
CALLBACK = C.WINFUNCTYPE(W.BOOL, W.HWND, W.LPARAM)

def bind(dll, name, result, *args):
    fn = getattr(dll, name)
    fn.restype, fn.argtypes = result, args
    return fn

foreground = bind(U, "GetForegroundWindow", W.HWND)
set_foreground = bind(U, "SetForegroundWindow", W.BOOL, W.HWND)
set_window_long = bind(U, "SetWindowLongPtrW" if C.sizeof(PTR) == 8 else "SetWindowLongW",
                       C.c_ssize_t, W.HWND, C.c_int, C.c_ssize_t)
get_window = bind(U, "GetWindow", W.HWND, W.HWND, W.UINT)
set_window_pos = bind(U, "SetWindowPos", W.BOOL, W.HWND, W.HWND,
                      C.c_int, C.c_int, C.c_int, C.c_int, W.UINT)
ancestor = bind(U, "GetAncestor", W.HWND, W.HWND, W.UINT)
is_window = bind(U, "IsWindow", W.BOOL, W.HWND)
visible = bind(U, "IsWindowVisible", W.BOOL, W.HWND)
enabled = bind(U, "IsWindowEnabled", W.BOOL, W.HWND)
get_pid = bind(U, "GetWindowThreadProcessId", W.DWORD, W.HWND, C.POINTER(W.DWORD))
get_text = bind(U, "GetWindowTextW", C.c_int, W.HWND, W.LPWSTR, C.c_int)
get_class = bind(U, "GetClassNameW", C.c_int, W.HWND, W.LPWSTR, C.c_int)
enum_windows = bind(U, "EnumWindows", W.BOOL, CALLBACK, W.LPARAM)
enum_children = bind(U, "EnumChildWindows", W.BOOL, W.HWND, CALLBACK, W.LPARAM)
control_id = bind(U, "GetDlgCtrlID", C.c_int, W.HWND)
send_timeout = bind(U, "SendMessageTimeoutW", PTR, W.HWND, W.UINT, PTR, W.LPARAM, W.UINT, W.UINT, C.POINTER(PTR))
open_process = bind(K, "OpenProcess", W.HANDLE, W.DWORD, W.BOOL, W.DWORD)
close_handle = bind(K, "CloseHandle", W.BOOL, W.HANDLE)
query_exe = bind(K, "QueryFullProcessImageNameW", W.BOOL, W.HANDLE, W.DWORD, W.LPWSTR, C.POINTER(W.DWORD))
get_times = bind(K, "GetProcessTimes", W.BOOL, W.HANDLE, *([C.POINTER(W.FILETIME)] * 4))
key_state = bind(U, "GetAsyncKeyState", C.c_short, C.c_int)

class Mouse(C.Structure):
    _fields_ = [("dx", W.LONG), ("dy", W.LONG), ("mouseData", W.DWORD),
                ("dwFlags", W.DWORD), ("time", W.DWORD), ("dwExtraInfo", PTR)]
class Keyboard(C.Structure):
    _fields_ = [("wVk", W.WORD), ("wScan", W.WORD), ("dwFlags", W.DWORD),
                ("time", W.DWORD), ("dwExtraInfo", PTR)]
class Payload(C.Union):
    _fields_ = [("ki", Keyboard), ("mi", Mouse)]
class Input(C.Structure):
    _anonymous_ = ("data",)
    _fields_ = [("type", W.DWORD), ("data", Payload)]
send_input = bind(U, "SendInput", W.UINT, W.UINT, C.POINTER(Input), C.c_int)

def pid(hwnd):
    result = W.DWORD()
    get_pid(hwnd, C.byref(result))
    return result.value

def text(hwnd, class_name=False):
    buf = C.create_unicode_buffer(2048)
    (get_class if class_name else get_text)(hwnd, buf, len(buf))
    return buf.value

def windows(parent=None):
    found = []
    @CALLBACK
    def visit(hwnd, _):
        found.append(hwnd)
        return True
    if parent is None:
        enum_windows(visit, 0)
    else:
        enum_children(parent, visit, 0)
    return found

def process_identity(process_id):
    handle = open_process(0x1000, False, process_id)
    if not handle:
        raise RuntimeError("Khong doc duoc tien trinh Audacity.")
    try:
        buf, size = C.create_unicode_buffer(32768), W.DWORD(32768)
        times = [W.FILETIME() for _ in range(4)]
        if not query_exe(handle, 0, buf, C.byref(size)) or not get_times(handle, *[C.byref(t) for t in times]):
            raise RuntimeError("Khong xac minh duoc tien trinh Audacity.")
        birth = (times[0].dwHighDateTime << 32) | times[0].dwLowDateTime
        return buf.value, birth
    finally:
        close_handle(handle)

@dataclass(frozen=True)
class Target:
    hwnd: int
    pid: int
    birth: int
    title: str

    def validate(self):
        if not is_window(self.hwnd) or pid(self.hwnd) != self.pid:
            raise RuntimeError("Cua so Audacity ban dau da dong; file van duoc giu lai.")
        exe, birth = process_identity(self.pid)
        if birth != self.birth or Path(exe).name.lower() != "audacity4.exe":
            raise RuntimeError("Tien trinh dich da thay doi; khong import.")
        if text(self.hwnd) != self.title:
            raise RuntimeError("Ten du an da thay doi trong khi tai. Hay import file da tai bang Ctrl+Shift+I.")

def capture_target():
    hwnd = ancestor(foreground(), 3)  # GA_ROOTOWNER: modal -> original project window
    process_id = pid(hwnd)
    exe, birth = process_identity(process_id)
    if Path(exe).name.lower() != "audacity4.exe" or not visible(hwnd):
        raise RuntimeError("Hay giu cua so Audacity o phia truoc khi nhan Apply trong plugin.")
    return Target(hwnd, process_id, birth, text(hwnd))


def return_to_target(target):
    """Best effort after closing our URL dialog; import still verifies focus."""
    try:
        target.validate()
        set_foreground(target.hwnd)
    except RuntimeError:
        pass


def own_url_dialog(widget_id, target):
    """Keep our mapped Tk dialog above its Audacity owner, without global topmost.

    Tk winfo_id identifies the client window, so use GA_ROOT (not ROOTOWNER)
    to find its native top-level wrapper. Only mutate our own window.
    """
    target.validate()
    hwnd = ancestor(widget_id, 2)  # GA_ROOT
    if not hwnd or pid(hwnd) != os.getpid() or hwnd == target.hwnd:
        raise RuntimeError("Khong xac minh duoc cua so nhap URL cua helper.")
    C.set_last_error(0)
    previous = set_window_long(hwnd, -8, target.hwnd)  # GWLP_HWNDPARENT: owner, not parent
    if not previous and C.get_last_error():
        raise C.WinError(C.get_last_error())
    if get_window(hwnd, 4) != target.hwnd:  # GW_OWNER
        raise RuntimeError("Khong gan duoc hop thoai URL voi du an Audacity.")
    # Ownership preserves ordering even if Audacity reactivates after Nyquist.
    # SWP_NOSIZE | SWP_NOMOVE | SWP_NOACTIVATE | SWP_FRAMECHANGED
    if not set_window_pos(hwnd, 0, 0, 0, 0, 0, 0x0033):
        raise C.WinError(C.get_last_error())
    current = foreground()
    if current == hwnd or ancestor(current, 3) == target.hwnd or pid(current) == os.getpid():
        set_foreground(hwnd)
    return hwnd

def message(hwnd, msg, wparam=0, lparam=0):
    result = PTR()
    if not send_timeout(hwnd, msg, wparam, lparam, 0x2, 3000, C.byref(result)):
        raise RuntimeError("Audacity khong phan hoi; dung tu dong import.")
    return result.value

def control_text(hwnd):
    # GetWindowTextW cannot read controls belonging to another process.
    # WM_GETTEXT is marshalled by Windows (system message < WM_USER).
    buf = C.create_unicode_buffer(32768)
    message(hwnd, 0x000D, len(buf), C.addressof(buf))
    return buf.value

def import_mp3(target: Target, path: Path, status=lambda s: None, cancelled=lambda: False):
    path = Path(path).resolve(strict=True)
    if path.suffix.lower() != ".mp3":
        raise ValueError("Chi import MP3 da tai va kiem tra.")
    deadline = time.monotonic() + 90
    status("Da tai xong. Quay lai cua so Audacity ban dau de import...")
    while True:
        if cancelled():
            raise RuntimeError("Da dung. MP3 da tai van duoc giu lai.")
        target.validate()
        if foreground() == target.hwnd and enabled(target.hwnd):
            time.sleep(0.3)
            if foreground() == target.hwnd and enabled(target.hwnd):
                break
        if time.monotonic() > deadline:
            raise RuntimeError("Chua quay lai du an sau 90 giay. Dung Ctrl+Shift+I de nhap file da tai.")
        time.sleep(0.1)
    # Never press modifiers on top of a user's held key.
    if any(key_state(k) & 0x8000 for k in (0x10, 0x11, 0x12, 0x5B, 0x5C)):
        raise RuntimeError("Hay tha phim Ctrl/Shift/Alt/Windows va thu lai.")
    events = (Input * 6)()
    for event, (key, up) in zip(events, [(0x11,0),(0x10,0),(0x49,0),(0x49,2),(0x10,2),(0x11,2)]):
        event.type = 1
        event.ki = Keyboard(key, 0, up, 0, 0)
    target.validate()
    if foreground() != target.hwnd:
        raise RuntimeError("Cua so dang chon da thay doi; khong gui phim.")
    if send_input(6, events, C.sizeof(Input)) != 6:
        # Release only the modifiers we attempted to press.
        release = (Input * 2)()
        for event, key in zip(release, (0x10, 0x11)):
            event.type, event.ki = 1, Keyboard(key, 0, 2, 0, 0)
        send_input(2, release, C.sizeof(Input))
        raise RuntimeError("Windows khong cho gui phim import. Chay helper va Audacity cung quyen.")
    deadline = time.monotonic() + 8
    dialog = None
    while time.monotonic() < deadline:
        target.validate()
        candidates = [h for h in windows() if visible(h) and pid(h) == target.pid
                      and text(h, True) == "#32770" and ancestor(h, 3) == target.hwnd]
        if len(candidates) == 1:
            dialog = candidates[0]
            break
        time.sleep(0.1)
    if dialog is None:
        raise RuntimeError("Khong thay hop thoai Import. Kiem tra phim tat Ctrl+Shift+I trong Audacity.")
    edits = [h for h in windows(dialog) if visible(h) and text(h, True) == "Edit" and control_id(h) == 1148]
    buttons = [h for h in windows(dialog) if text(h, True) == "Button" and control_id(h) == 1]
    if len(edits) != 1 or len(buttons) != 1:
        raise RuntimeError("Hop thoai file khong dung mau Windows; khong tu dong dien.")
    if foreground() != dialog:
        raise RuntimeError("Ban da chuyen cua so; dung import de tranh nham thao tac.")
    buf = C.create_unicode_buffer(str(path))
    message(edits[0], 0x000C, 0, C.addressof(buf))  # WM_SETTEXT, only known filename control
    if control_text(edits[0]) != str(path):
        raise RuntimeError("Khong dien duoc ten file vao hop thoai Import.")
    target.validate()
    if foreground() != dialog or not is_window(dialog):
        raise RuntimeError("Hop thoai import da thay doi; dung thao tac.")
    message(buttons[0], 0x00F5)  # BM_CLICK on that dialog's Open button
    deadline = time.monotonic() + 30
    while is_window(dialog) and time.monotonic() < deadline:
        time.sleep(0.1)
    if is_window(dialog):
        raise RuntimeError("Audacity chua dong hop thoai. Hay kiem tra thong bao trong Audacity.")
    status("Da gui MP3 vao du an. Kiem tra track moi trong Audacity.")
