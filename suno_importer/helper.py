"""A visible status window; minimize it while using Tools > Suno URL Import."""
from __future__ import annotations
import json
import os
from pathlib import Path
import queue
import threading
import time
import traceback
import uuid
import tkinter as tk
from tkinter import ttk
from urllib.error import HTTPError
from .downloader import download, DownloadError, validate_url

ROOT = Path(__file__).resolve().parents[1]
RUNTIME = ROOT / "runtime"

def parse_request(data, session):
    if len(data) > 5000:
        raise ValueError("Yeu cau qua dai.")
    lines = data.splitlines()
    if len(lines) != 4 or lines[0] not in ("SUNO-IMPORT-1", "SUNO-OPEN-1") or lines[-1] != "END":
        raise ValueError("Yeu cau chua hoan tat.")
    if lines[1] != session:
        raise ValueError("Yeu cau cu; hay chon lai Suno URL Import trong menu Tools.")
    if lines[0] == "SUNO-OPEN-1":
        if lines[2] != "OPEN":
            raise ValueError("Yeu cau mo hop thoai khong hop le.")
        return None
    return lines[2]


def write_heartbeat(directory, session, now=None):
    """Publish only complete records; the plugin can reject a crashed helper."""
    temporary = directory / "heartbeat.tmp"
    temporary.write_text(f"{session}\n{int(time.time() if now is None else now)}\n", encoding="ascii")
    temporary.replace(directory / "heartbeat.txt")

def main():
    from . import windows
    import msvcrt
    RUNTIME.mkdir(exist_ok=True)
    lock = (RUNTIME / "helper.lock").open("a+b")
    lock.seek(0)
    if not lock.read(1):
        lock.write(b"0"); lock.flush()
    lock.seek(0)
    try:
        msvcrt.locking(lock.fileno(), msvcrt.LK_NBLCK, 1)
    except OSError:
        return
    session = uuid.uuid4().hex
    # Old requests must never be replayed on launch.
    if (RUNTIME / "request.txt").exists():
        (RUNTIME / "request.txt").replace(RUNTIME / "previous-request.txt")
    (RUNTIME / "session.txt").write_text(session, encoding="ascii")
    (RUNTIME / "busy.txt").unlink(missing_ok=True)
    stopped = threading.Event()
    updates = queue.Queue()
    prompts = queue.Queue()
    last_url = [""]
    root = tk.Tk()
    root.title("Suno Import Helper")
    root.geometry("630x260")
    root.minsize(560, 230)
    frame = ttk.Frame(root, padding=20)
    frame.pack(fill="both", expand=True)
    ttk.Label(frame, text="Suno → Audacity 4", font=("Segoe UI", 17, "bold")).pack(anchor="w")
    ttk.Label(frame, text="Giữ cửa sổ này chạy. Trong Audacity: Tools → Suno URL Import.", wraplength=580).pack(anchor="w", pady=(8,12))
    status = tk.StringVar(value="Sẵn sàng nhận URL từ plugin.")
    ttk.Label(frame, textvariable=status, wraplength=580).pack(anchor="w", fill="x")
    saved = tk.StringVar()
    ttk.Entry(frame, textvariable=saved, state="readonly").pack(fill="x", pady=12)
    row = ttk.Frame(frame); row.pack(fill="x")
    ttk.Button(row, text="Mở thư mục MP3", command=lambda: os.startfile(str(ROOT / "downloads"))).pack(side="left")
    ttk.Button(row, text="Thu nhỏ", command=root.iconify).pack(side="left", padx=8)
    ttk.Button(row, text="Dừng helper", command=lambda: close()).pack(side="right")
    (ROOT / "downloads").mkdir(exist_ok=True)

    def show_url_dialog(target, reply, ready):
        dialog = tk.Toplevel(root)
        dialog.withdraw()
        dialog.title("Suno URL Import")
        dialog.resizable(True, False)
        dialog.geometry("720x235")
        dialog.minsize(580, 235)
        pane = ttk.Frame(dialog, padding=20)
        pane.pack(fill="both", expand=True)
        ttk.Label(pane, text="Nhập audio từ Suno", font=("Segoe UI", 14, "bold")).pack(anchor="w")
        ttk.Label(pane, text=f"Dự án: {target.title}", wraplength=660).pack(anchor="w", pady=(5, 12))
        field_row = ttk.Frame(pane)
        field_row.pack(fill="x")
        value = tk.StringVar(value=last_url[0])
        entry = ttk.Entry(field_row, textvariable=value)
        entry.pack(side="left", fill="x", expand=True)

        def clear_url():
            value.set("")
            last_url[0] = ""
            error.set("")
            entry.focus_set()

        ttk.Button(field_row, text="✕ Xóa", width=8, command=clear_url).pack(side="left", padx=(8, 0))
        error = tk.StringVar()
        ttk.Label(pane, textvariable=error, foreground="#b42318", wraplength=660).pack(anchor="w", pady=(6, 8))
        actions = ttk.Frame(pane)
        actions.pack(fill="x")

        def finish(url=None):
            reply.append(url)
            dialog.destroy()
            # The user invoked this dialog from this project; return focus there.
            windows.return_to_target(target)
            ready.set()

        def submit():
            try:
                url = validate_url(value.get().strip())
            except (DownloadError, ValueError) as exc:
                error.set(str(exc))
                entry.focus_set()
                return
            last_url[0] = url
            finish(url)

        ttk.Button(actions, text="Import", command=submit).pack(side="right")
        ttk.Button(actions, text="Hủy", command=finish).pack(side="right", padx=8)
        dialog.protocol("WM_DELETE_WINDOW", finish)
        dialog.bind("<Escape>", lambda _event: finish())
        dialog.bind("<Return>", lambda _event: submit())

        def destroyed(event):
            # Windows also destroys owned dialogs when their Audacity owner closes.
            if event.widget is dialog and not reply:
                reply.append(None)
                ready.set()

        dialog.bind("<Destroy>", destroyed)
        def present():
            try:
                dialog.deiconify()
                dialog.update_idletasks()
                hwnd = windows.own_url_dialog(dialog.winfo_id(), target)
                if windows.foreground() == hwnd:
                    entry.focus_set()
            except (RuntimeError, OSError, tk.TclError) as exc:
                # Always release the waiting worker if presentation fails.
                reply.append(exc)
                try:
                    dialog.destroy()
                except tk.TclError:
                    pass
                ready.set()

        # Let the menu's Nyquist invocation finish before requesting activation.
        dialog.after(200, present)

    def update(message, **extra):
        updates.put((message, extra))
        record = {"time": time.strftime("%Y-%m-%d %H:%M:%S"), "message": message, **extra}
        (RUNTIME / "status.json").write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")

    def worker():
        while not stopped.wait(0.1):
            request = RUNTIME / "request.txt"
            if not request.exists():
                continue
            try:
                data = request.read_text(encoding="utf-8")
                if not data.endswith("END\n"):
                    continue  # Nyquist still writing; do not claim a partial request.
                target = windows.capture_target()
                url = parse_request(data, session)
                (RUNTIME / "busy.txt").write_text(session, encoding="ascii")
                request.replace(RUNTIME / "last-request.txt")
                if url is None:
                    reply, ready = [], threading.Event()
                    update("Nhập URL trong cửa sổ Suno URL Import.", state="prompt")
                    prompts.put((target, reply, ready))
                    while not ready.wait(0.1):
                        if stopped.is_set():
                            return
                    url = reply[0]
                    if isinstance(url, Exception):
                        raise url
                    if url is None:
                        update("Đã hủy. Sẵn sàng nhận yêu cầu mới.", state="cancelled")
                        continue
                update("Đang tải MP3 từ Suno…", state="downloading", target=target.hwnd)
                last_update = [0.0]
                def progress(count, total):
                    if stopped.is_set():
                        raise DownloadError("Da dung helper.")
                    if time.monotonic() - last_update[0] > 0.5:
                        last_update[0] = time.monotonic()
                        update(f"Đang tải: {count / 1048576:.1f} MB" + (f" / {total / 1048576:.1f} MB" if total else ""), state="downloading")
                path = download(url, ROOT / "downloads", progress=progress)
                update("Đã tải MP3. Đang chờ cửa sổ Audacity ban đầu…", path=str(path), state="downloaded")
                windows.import_mp3(target, path, lambda msg: update(msg, path=str(path), state="import"), stopped.is_set)
                update("Đã gửi MP3 vào dự án. Kiểm tra track mới trong Audacity.", path=str(path), state="submitted")
            except Exception as exc:
                if request.exists():
                    request.replace(RUNTIME / "failed-request.txt")
                if isinstance(exc, HTTPError) and exc.code in (401,403,404):
                    message = f"Suno trả HTTP {exc.code}. Hãy dùng link MP3 public từ Download; bài này có thể không cung cấp MP3 công khai."
                else:
                    message = str(exc)
                update("Lỗi: " + message, state="error")
                with (RUNTIME / "errors.log").open("a", encoding="utf-8") as log:
                    log.write(traceback.format_exc() + "\n")
            finally:
                (RUNTIME / "busy.txt").unlink(missing_ok=True)
        lock.close()

    def tick():
        try:
            show_url_dialog(*prompts.get_nowait())
        except queue.Empty:
            pass
        try:
            while True:
                message, extra = updates.get_nowait()
                status.set(message)
                if "path" in extra:
                    saved.set(extra["path"])
        except queue.Empty:
            pass
        root.after(150, tick)

    def heartbeat():
        if stopped.is_set():
            return
        try:
            write_heartbeat(RUNTIME, session)
        except OSError:
            # The Nyquist reader can briefly hold the file open on Windows.
            pass
        root.after(1000, heartbeat)

    def close():
        stopped.set()
        (RUNTIME / "session.txt").unlink(missing_ok=True)
        (RUNTIME / "heartbeat.txt").unlink(missing_ok=True)
        root.destroy()

    root.protocol("WM_DELETE_WINDOW", close)
    threading.Thread(target=worker, daemon=True).start()
    heartbeat()
    tick()
    root.mainloop()
    (RUNTIME / "session.txt").unlink(missing_ok=True)

if __name__ == "__main__":
    main()
