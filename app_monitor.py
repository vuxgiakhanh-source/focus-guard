# -*- coding: utf-8 -*-
import os
import ctypes
import time
import re
import unicodedata

def strip_vietnamese_accents(text):
    if not text:
        return ""
    nfkd = unicodedata.normalize('NFKD', text)
    res = ''.join([c for c in nfkd if not unicodedata.combining(c)])
    return res.replace('đ', 'd').replace('Đ', 'd')

class LASTINPUTINFO(ctypes.Structure):
    _fields_ = [('cbSize', ctypes.c_uint), ('dwTime', ctypes.c_uint)]

class AppDistractionMonitor:
    """
    Giám sát thao tác trên ứng dụng và mạng xã hội gây xao nhãng (Facebook, YouTube, TikTok...):
    - CHỈ CẢNH BÁO SAU KHI THỰC SỰ THAO TÁC (click chuột, gõ phím, cuộn trang).
    - Hỗ trợ file blocklist.txt để người dùng tự thêm từ khóa tùy biến.
    - Mở tab để đó nghe nhạc hoặc không đụng vào -> HOÀN TOÀN KHÔNG BÁO ĐỘNG.
    - Giờ giải lao Pomodoro -> Cho phép giải trí tự do 100%.
    """
    def __init__(self, active_operate_thresh_sec=2.8, idle_timeout_sec=3.5, debounce_sec=None, **kwargs):
        if debounce_sec is not None:
            self.active_operate_thresh_sec = float(debounce_sec)
        else:
            self.active_operate_thresh_sec = float(active_operate_thresh_sec)
        self.idle_timeout_sec = float(idle_timeout_sec)

        self.active_operate_time = 0.0
        self.last_check_time = time.monotonic()
        self.current_distraction = None

        base_dir = os.path.dirname(os.path.abspath(__file__))
        self.blocklist_file = os.path.join(base_dir, "blocklist.txt")
        self.last_blocklist_mtime = 0.0
        self.custom_blocked_keywords = self._load_blocklist()

        self.user32 = ctypes.windll.user32
        self.kernel32 = ctypes.windll.kernel32
        self.user32.GetForegroundWindow.argtypes = []
        self.user32.GetForegroundWindow.restype = ctypes.c_void_p
        self.user32.GetWindowTextLengthW.argtypes = [ctypes.c_void_p]
        self.user32.GetWindowTextLengthW.restype = ctypes.c_int
        self.user32.GetWindowTextW.argtypes = [ctypes.c_void_p, ctypes.POINTER(ctypes.c_wchar), ctypes.c_int]
        self.user32.GetWindowTextW.restype = ctypes.c_int
        self.user32.GetLastInputInfo.argtypes = [ctypes.POINTER(LASTINPUTINFO)]
        self.user32.GetLastInputInfo.restype = ctypes.c_bool
        self.kernel32.GetTickCount.argtypes = []
        self.kernel32.GetTickCount.restype = ctypes.c_uint32

    def _load_blocklist(self):
        """Đọc danh sách từ khóa chặn tùy chỉnh từ file blocklist.txt"""
        keywords = []
        if os.path.exists(self.blocklist_file):
            try:
                self.last_blocklist_mtime = os.path.getmtime(self.blocklist_file)
                with open(self.blocklist_file, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith("#"):
                            keywords.append(line.lower())
            except Exception:
                pass
        return keywords

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
        """Lấy tiêu đề cửa sổ trước mặt bằng HWND đúng độ rộng trên Windows 64-bit."""
        try:
            hwnd = self.user32.GetForegroundWindow()
            if not hwnd:
                return ""

            length = self.user32.GetWindowTextLengthW(hwnd)
            if length <= 0:
                return ""
            buff = ctypes.create_unicode_buffer(length + 1)
            self.user32.GetWindowTextW(hwnd, buff, length + 1)
            return buff.value.strip()
        except Exception:
            return ""

    def check_distraction(self, is_pomodoro_break=False):
        """
        Kiểm tra người dùng có đang THỰC SỰ THAO TÁC trên Facebook hay YouTube không.
        Được gọi khoảng 10 lần/giây; main.py giữ kết quả mới nhất giữa các khung hình camera.
        """
        now = time.monotonic()
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
        t_norm = strip_vietnamese_accents(t_low)

        # Bỏ qua cửa sổ FocusGuard chính
        if "focusguard" in t_low:
            self.active_operate_time = 0.0
            self.current_distraction = None
            return None

        # Tự động nạp lại blocklist nếu người dùng vừa sửa file blocklist.txt
        if os.path.exists(self.blocklist_file):
            try:
                mtime = os.path.getmtime(self.blocklist_file)
                if mtime != self.last_blocklist_mtime:
                    self.custom_blocked_keywords = self._load_blocklist()
            except Exception:
                pass

        # Kiểm tra trước xem có phải trang giải trí / mạng xã hội không
        # để tránh bị safe_keywords (như "excel", "pdf") whitelist nhầm khi đọc bài viết Facebook về Excel
        is_known_distraction = any(re.search(p, t_low) for p in [
            r'\b(facebook|fb\.com|messenger|reels|tiktok|youtube|youtu\.be)\b',
            r'\b(pornhub|xvideos|xnxx|xhamster|redtube|youporn|brazzers|onlyfans|javhd|jav|hentai|vlxx|phimsex|sex|xxx|nsfw|rule34|stripchat|chaturbate|spankbang|beeg|fapello|thothub)\b',
            r'\b(bilibili|netflix|shopee|lazada|instagram|discord|telegram|twitch|reddit|threads|twitter|weibo|pinterest)\b'
        ])
        if not is_known_distraction and self.custom_blocked_keywords:
            for kw in self.custom_blocked_keywords:
                kw_low = kw.lower().strip()
                kw_norm = strip_vietnamese_accents(kw_low)
                if kw_low in t_low or kw_norm in t_norm:
                    is_known_distraction = True
                    break

        if not is_known_distraction:
            # Danh sách ứng dụng an toàn và công cụ học tập / nghiên cứu
            safe_keywords = [
                "visual studio code", "pycharm", "intellij", "cursor",
                "sublime", "notepad", "terminal", "powershell", "cmd.exe", "git bash", "google search",
                "tìm kiếm trên google", "tìm trên google", "bing search", "github", "stackoverflow",
                "notion", "obsidian", "anki", "quizlet", "overleaf", "latex", "calculator",
                "desmos", "geogebra", "duolingo", "khan academy", "coursera", "edx", "udemy",
                "leetcode", "hackerrank", "kaggle", "canva", "figma", "foxit", "adobe reader",
                "wps office", "libreoffice", "google docs", "google sheets", "google slides",
                "google drive", "zotero", "mendeley"
            ]
            safe_title_patterns = [
                r"(?:^|[-–—|]\s*)(?:microsoft\s+)?(word|excel|powerpoint)\s*$",
                r"\.pdf\s*[-–—|]"
            ]
            if any(safe in t_low for safe in safe_keywords) or any(
                re.search(pattern, t_low) for pattern in safe_title_patterns
            ):
                self.active_operate_time = 0.0
                self.current_distraction = None
                return None

        d_type = None
        d_label = None

        # 0. Kiểm tra danh sách chặn tùy chọn từ blocklist.txt của người dùng
        if self.custom_blocked_keywords:
            for kw in self.custom_blocked_keywords:
                kw_low = kw.lower().strip()
                kw_norm = strip_vietnamese_accents(kw_low)
                if kw_low in t_low or kw_norm in t_norm:
                    d_type = "WEB_DISTRACT"
                    d_label = f"Đã chặn: {kw}"
                    break

        # 1. Nhận diện trang web người lớn / nội dung 18+ / nhạy cảm
        if not d_type:
            adult_patterns = [
                r'\b(pornhub|xvideos|xnxx|xhamster|redtube|youporn|brazzers|onlyfans|javhd|jav|hentai|vlxx|phimsex|sex|xxx|nsfw|rule34|stripchat|chaturbate|spankbang|beeg|fapello|thothub)\b'
            ]
            if any(re.search(p, t_low) for p in adult_patterns):
                d_type = "WEB_DISTRACT"
                d_label = "Trang web 18+ / Nhạy cảm"

        # 2. Nhận diện trò chơi điện tử (Gaming) - Mối nguy xao nhãng hàng đầu của học sinh / sinh viên
        if not d_type:
            game_patterns = [
                r'\b(league of legends|riot client|valorant|genshin impact|honkai|roblox|minecraft)\b',
                r'\b(steam|epic games|origin|ubisoft connect|battle\.net|ea app)\b',
                r'\b(counter-strike|cs:go|cs2|dota 2|pubg|apex legends|fifa|fc 24|fc 25)\b',
                r'\b(garena|lien quan|free fire|naraka|black myth|elden ring|wuthering waves)\b'
            ]
            if any(re.search(p, t_low) for p in game_patterns):
                d_type = "WEB_DISTRACT"
                d_label = "Trò chơi điện tử (Game)"

        # 3. Mạng xã hội & Chat
        fb_patterns = [
            r'\b(facebook|fb\.com|messenger|reels)\b'
        ]
        yt_patterns = [
            r'\b(youtube|youtu\.be)\b'
        ]
        tiktok_patterns = [
            r'\b(tiktok)\b'
        ]

        if not d_type:
            if any(re.search(p, t_low) for p in fb_patterns):
                d_type = "FACEBOOK"
                d_label = "Facebook"
            elif any(re.search(p, t_low) for p in yt_patterns):
                # Ngoại lệ thông minh: Cho phép nghe Lofi hoặc xem BÀI GIẢNG / TUTORIAL trên YouTube
                educational_yt_patterns = [
                    r'\b(toán\s+học|môn\s+toán|đại\s+số|hình\s+học|giải\s+tích|ngữ\s+văn|môn\s+văn|tiếng\s+anh|ielts|toeic|toefl)\b',
                    r'\b(vật\s+lý|hóa\s+học|sinh\s+học|lịch\s+sử|địa\s+lý|tin\s+học|khoa\s+học|triết\s+học)\b',
                    r'\b(bài\s+giảng|giáo\s+trình|ôn\s+thi|luyện\s+thi|hướng\s+dẫn|tự\s+học|study\s+with\s+me)\b',
                    r'\b(tutorial|lecture|online\s+course|crash\s+course|khan\s+academy|coursera|edx|mit\s+opencourseware)\b',
                    r'\b(lập\s+trình|coding|programming|python|javascript|c\+\+|golang|rust|react|fullstack)\b',
                    r'\b(lofi\s+hip\s+hop|lofi\s+study|nhạc\s+tập\s+trung|music\.youtube)\b'
                ]
                if any(re.search(p, t_low) for p in educational_yt_patterns):
                    # Đang xem video bài giảng hoặc nhạc học bài -> Bỏ qua không báo động!
                    self.active_operate_time = 0.0
                    self.current_distraction = None
                    return None

                d_type = "YOUTUBE"
                d_label = "YouTube"
            elif any(re.search(p, t_low) for p in tiktok_patterns):
                d_type = "WEB_DISTRACT"
                d_label = "TikTok"
            elif re.search(r'\b(bilibili|netflix|shopee|lazada|instagram|discord|telegram|twitch|reddit|threads|twitter|weibo|pinterest)\b', t_low):
                d_type = "WEB_DISTRACT"
                d_label = "Mạng xã hội / Mua sắm / Giải trí"

        # Nếu cửa sổ hiện tại KHÔNG PHẢI mạng xã hội -> Reset ngay lập tức
        if not d_type:
            self.active_operate_time = 0.0
            self.current_distraction = None
            return None

        # Cửa sổ hiện tại LÀ Facebook/YouTube/Giải trí:
        # Kiểm tra xem người dùng có ĐANG THAO TÁC (gõ phím, click chuột, cuộn trang) không?
        idle_sec = self.get_system_idle_seconds()
        is_actively_operating = (idle_sec < self.idle_timeout_sec)

        if is_actively_operating:
            if self.current_distraction != d_type:
                self.current_distraction = d_type
                self.active_operate_time = 0.0

            self.active_operate_time += dt
        else:
            # Không tương tác -> hạ chậm dần thời gian tích lũy (không bị xóa sạch khi dừng 1-2s đọc bài viết)
            self.active_operate_time = max(0.0, self.active_operate_time - dt * 0.4)

        thresh = 0.0 if d_label == "Trang web 18+ / Nhạy cảm" else self.active_operate_thresh_sec
        should_alert = (self.active_operate_time >= thresh) and is_actively_operating

        return {
            "is_distracted": (self.active_operate_time > 0.4),
            "is_operating": is_actively_operating,
            "should_alert": should_alert,
            "alert_type": d_type,
            "label": d_label,
            "duration": round(self.active_operate_time, 1),
            "window_title": title
        }
