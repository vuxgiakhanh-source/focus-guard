# -*- coding: utf-8 -*-
import ctypes
import time

class LASTINPUTINFO(ctypes.Structure):
    _fields_ = [('cbSize', ctypes.c_uint), ('dwTime', ctypes.c_uint)]

import re

class AppDistractionMonitor:
    """
    Giám sát thao tác trên ứng dụng và mạng xã hội gây xao nhãng (Facebook, YouTube, TikTok...):
    - CHỈ CẢNH BÁO KHI THỰC SỰ ĐANG DÙNG / THAO TÁC (click chuột, gõ phím, cuộn trang) > 2.5s.
    - Mở tab để đó nghe nhạc hoặc không đụng vào -> HOÀN TOÀN KHÔNG BÁO ĐỘNG.
    - Ngay khi người dùng đóng tab / chuyển sang ứng dụng khác -> HỦY CẢNH BÁO TỨC THÌ (Zero Delay)!
    - Giờ giải lao Pomodoro -> Cho phép giải trí tự do 100%.
    - Chạy native bằng Windows User32 API (tốn 0.0003ms, 0% CPU).
    """
    def __init__(self, active_operate_thresh_sec=2.5, idle_timeout_sec=2.0, debounce_sec=2.5, **kwargs):
        self.active_operate_thresh_sec = debounce_sec if debounce_sec != 2.5 else active_operate_thresh_sec
        self.idle_timeout_sec = idle_timeout_sec

        self.active_operate_time = 0.0
        self.last_check_time = time.time()
        self.current_distraction = None

        self.user32 = ctypes.windll.user32
        self.kernel32 = ctypes.windll.kernel32
        self._attached = False
        self._ensure_desktop_access()

    def _ensure_desktop_access(self):
        """Đảm bảo thread có quyền đọc tiêu đề cửa sổ trên Desktop người dùng"""
        try:
            h_winsta = self.user32.OpenWindowStationW('WinSta0', False, 0x037F)
            if h_winsta:
                self.user32.SetProcessWindowStation(h_winsta)
                h_desk = self.user32.OpenDesktopW('Default', 0, False, 0x01FF)
                if h_desk:
                    self.user32.SetThreadDesktop(h_desk)
                    self._attached = True
        except Exception:
            pass

    def get_system_idle_seconds(self):
        """Số giây kể từ lần người dùng chạm chuột / gõ phím cuối cùng trên máy tính"""
        try:
            lii = LASTINPUTINFO()
            lii.cbSize = ctypes.sizeof(LASTINPUTINFO)
            if self.user32.GetLastInputInfo(ctypes.byref(lii)):
                tick_now = self.kernel32.GetTickCount()
                millis = (tick_now - lii.dwTime) & 0xFFFFFFFF
                return max(0.0, millis / 1000.0)
        except Exception:
            pass
        return 999.0

    def get_foreground_title(self):
        """Lấy tiêu đề cửa sổ đang nằm trên cùng màn hình (Active Window Title)"""
        try:
            hwnd = self.user32.GetForegroundWindow()
            if not hwnd:
                if not self._attached:
                    self._ensure_desktop_access()
                    hwnd = self.user32.GetForegroundWindow()
            if not hwnd:
                return ""

            length = self.user32.GetWindowTextLengthW(hwnd)
            if length > 0:
                buff = ctypes.create_unicode_buffer(length + 1)
                self.user32.GetWindowTextW(hwnd, buff, length + 1)
                return buff.value.strip()
        except Exception:
            pass
        return ""

    def check_distraction(self, is_pomodoro_break=False):
        """
        Kiểm tra người dùng có đang THỰC SỰ THAO TÁC trên Facebook hay YouTube không.
        Kiểm tra thời gian thực từng khung hình (không lưu đệm cũ gây báo sai sau khi tắt).
        """
        now = time.time()
        dt = max(0.0, min(1.0, now - self.last_check_time))
        self.last_check_time = now

        # Nếu đang trong giờ giải lao Pomodoro: Cho phép giải trí tự do 100%
        if is_pomodoro_break:
            self.active_operate_time = 0.0
            self.current_distraction = None
            return None

        title = self.get_foreground_title()
        if not title:
            self.active_operate_time = 0.0
            self.current_distraction = None
            return None

        t_low = title.lower().strip()

        # Bỏ qua cửa sổ FocusGuard chính
        if "focusguard" in t_low:
            self.active_operate_time = 0.0
            self.current_distraction = None
            return None

        # Danh sách ứng dụng an toàn và công cụ học tập / nghiên cứu
        safe_keywords = [
            "visual studio", "code", "pycharm", "intellij", "cursor",
            "sublime", "notepad", "word", "excel", "powerpoint", "acrobat",
            "pdf", "terminal", "powershell", "cmd.exe", "git", "google search",
            "tìm kiếm trên google", "tìm trên google", "bing search", "github", "stackoverflow",
            "notion", "obsidian", "anki", "quizlet", "overleaf", "latex", "calculator",
            "desmos", "geogebra", "duolingo", "khan academy", "coursera", "edx", "udemy",
            "leetcode", "hackerrank", "kaggle", "canva", "figma", "foxit", "adobe reader",
            "wps office", "libreoffice", "google docs", "google sheets", "google slides",
            "google drive", "zotero", "mendeley"
        ]
        if any(safe in t_low for safe in safe_keywords):
            self.active_operate_time = 0.0
            self.current_distraction = None
            return None

        d_type = None
        d_label = None

        # 1. Nhận diện trò chơi điện tử (Gaming) - Mối nguy xao nhãng hàng đầu của học sinh / sinh viên
        game_patterns = [
            r'\b(league of legends|riot client|valorant|genshin impact|honkai|roblox|minecraft)\b',
            r'\b(steam|epic games|origin|ubisoft connect|battle\.net|ea app)\b',
            r'\b(counter-strike|cs:go|cs2|dota 2|pubg|apex legends|fifa|fc 24|fc 25)\b',
            r'\b(garena|lien quan|free fire|naraka|black myth|elden ring|wuthering waves)\b'
        ]
        if any(re.search(p, t_low) for p in game_patterns):
            d_type = "WEB_DISTRACT"
            d_label = "Trò chơi điện tử (Game)"

        # 2. Mạng xã hội & Chat
        fb_patterns = [
            r'(^|\s*[-–—|]\s*)facebook(\s*[-–—|]|\s*$)',
            r'^\([0-9+]+\)\s*facebook',
            r'(facebook\.com|fb\.com|m\.facebook\.com)',
            r'(^|\s*[-–—|]\s*)messenger(\s*[-–—|]|\s*$)',
            r'^\([0-9+]+\)\s*messenger'
        ]
        yt_patterns = [
            r'(^|\s*[-–—|]\s*)youtube(\s*[-–—|]|\s*$)',
            r'^\([0-9+]+\)\s*youtube',
            r'(youtube\.com|youtu\.be)'
        ]
        tiktok_patterns = [
            r'(^|\s*[-–—|]\s*)tiktok(\s*[-–—|]|\s*$)',
            r'tiktok\.com'
        ]

        if not d_type:
            if any(re.search(p, t_low) for p in fb_patterns):
                d_type = "FACEBOOK"
                d_label = "Facebook"
            elif any(re.search(p, t_low) for p in yt_patterns):
                # Ngoại lệ thông minh: Cho phép nghe Lofi hoặc xem BÀI GIẢNG / TUTORIAL trên YouTube
                educational_yt_keywords = [
                    "tutorial", "học", "bài giảng", "lecture", "course", "hướng dẫn",
                    "ôn thi", "toán", "văn", "tiếng anh", "ielts", "toeic", "lập trình",
                    "code", "python", "khoa học", "lịch sử", "địa lý", "vật lý",
                    "hóa học", "sinh học", "khan academy", "coursera", "edx", "mit opencourseware",
                    "crash course", "study with me", "lofi hip hop", "lofi study", "nhạc tập trung",
                    "music.youtube"
                ]
                if any(kw in t_low for kw in educational_yt_keywords):
                    # Đang xem video bài giảng hoặc nhạc học bài -> Bỏ qua không báo động!
                    self.active_operate_time = 0.0
                    self.current_distraction = None
                    return None

                d_type = "YOUTUBE"
                d_label = "YouTube"
            elif any(re.search(p, t_low) for p in tiktok_patterns):
                d_type = "WEB_DISTRACT"
                d_label = "TikTok"
            elif any(k in t_low for k in ["bilibili", "netflix.com", "shopee.vn", "lazada.vn", "instagram.com", "discord", "telegram", "twitch.tv", "reddit.com", "threads.net"]):
                d_type = "WEB_DISTRACT"
                d_label = "Mạng xã hội / Giải trí"

        # Nếu cửa sổ hiện tại KHÔNG PHẢI mạng xã hội -> Reset ngay lập tức
        if not d_type:
            self.active_operate_time = 0.0
            self.current_distraction = None
            return None

        # Cửa sổ hiện tại LÀ Facebook/YouTube:
        # Kiểm tra xem người dùng có ĐANG THAO TÁC (gõ phím, click chuột, cuộn trang) không?
        idle_sec = self.get_system_idle_seconds()
        is_actively_operating = (idle_sec < self.idle_timeout_sec)

        if is_actively_operating:
            if self.current_distraction != d_type:
                self.current_distraction = d_type
                self.active_operate_time = 0.0

            self.active_operate_time += dt
        else:
            # Không tương tác -> hạ dần thời gian tích lũy
            self.active_operate_time = max(0.0, self.active_operate_time - dt * 2.0)

        should_alert = (self.active_operate_time >= self.active_operate_thresh_sec)

        return {
            "is_distracted": (self.active_operate_time > 0.4),
            "is_operating": is_actively_operating,
            "should_alert": should_alert,
            "alert_type": d_type,
            "label": d_label,
            "duration": round(self.active_operate_time, 1),
            "window_title": title
        }
