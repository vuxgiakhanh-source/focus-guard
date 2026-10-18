# -*- coding: utf-8 -*-

class WindowsToastManager:
    """
    Quản lý thông báo: ĐÃ TẮT HOÀN TOÀN (Zero Toast Popups) theo yêu cầu người dùng.
    Không bao giờ hiển thị bất kỳ banner popup nào ở góc phải màn hình Windows.
    Toàn bộ thông tin được hiển thị trực tiếp trên giao diện HUD và âm thanh của FocusGuard.
    """
    def __init__(self, app_id="FocusGuard AI"):
        self.app_id = app_id
        self.enabled = False

    def show_toast(self, title, message, toast_key=None, cooldown=12.0, silent=True):
        """Bỏ qua 100% mọi popup thông báo ở góc phải màn hình (No-op)"""
        return
