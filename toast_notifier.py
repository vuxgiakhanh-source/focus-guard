# -*- coding: utf-8 -*-
import threading
import time

HAS_WINOTIFY = False
try:
    from winotify import Notification, audio
    HAS_WINOTIFY = True
except Exception:
    HAS_WINOTIFY = False

class WindowsToastManager:
    """Quản lý thông báo Windows Toast Notification không gây giật lag (chạy nền)"""
    def __init__(self, app_id="FocusGuard AI"):
        self.app_id = app_id
        self.last_toast_time = {}
        self.lock = threading.Lock()

    def show_toast(self, title, message, toast_key=None, cooldown=12.0, silent=False):
        """Bật thông báo Toast popup ở góc màn hình (luồng nền, có cooldown, hỗ trợ chế độ im lặng)"""
        if not HAS_WINOTIFY:
            return

        key = toast_key or title
        now = time.time()
        with self.lock:
            last = self.last_toast_time.get(key, 0)
            if now - last < cooldown:
                return
            self.last_toast_time[key] = now

        def _worker():
            try:
                notif = Notification(
                    app_id=self.app_id,
                    title=title,
                    msg=message,
                    duration="short"
                )
                if silent:
                    notif.set_audio(audio.Silent, loop=False)
                else:
                    notif.set_audio(audio.Default, loop=False)
                notif.show()
            except Exception:
                pass

        threading.Thread(target=_worker, daemon=True).start()
