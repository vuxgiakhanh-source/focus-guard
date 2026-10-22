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

        # 1. KIỂM TRA ỨNG DỤNG LÀM VIỆC / SOẠN THẢO / LẬP TRÌNH ĐỂ BÀN (LOCAL DESKTOP APPS)
        # Các cửa sổ IDE, Office, Terminal... mở tài liệu hoặc file code (kể cả chứa chữ facebook, sex, threads)
        # PHẢI LUÔN LUÔN ĐƯỢC XEM LÀ AN TOÀN TUYỆT ĐỐI nếu không phải tab trong trình duyệt web.
        known_browser_suffixes = [
            "- google chrome", "- microsoft​ edge", "- microsoft edge",
            "- brave", "- firefox", "- mozilla firefox",
            "- cốc cốc", "- coc coc", "- opera", "- vivaldi", "- chromium"
        ]
        is_in_browser = any(t_low.endswith(browser) or browser in t_low for browser in known_browser_suffixes)

        if not is_in_browser:
            # Ứng dụng để bàn cục bộ:
            local_desktop_safe_patterns = [
                # Lập trình & Kỹ thuật
                r'(?:^|[-–—|]\s*)(?:visual\s+studio(?:\s+code)?|pycharm|intellij(?:\s+idea)?|clion|webstorm|rider|goland|android\s+studio|sublime\s+text|notepad\+\+|notepad|cursor)\b',
                r'(?:^|[-–—|]\s*)(?:terminal|powershell|cmd\.exe|git\s+bash|mintty)\b',
                # Soạn thảo văn bản & Tài liệu văn phòng
                r'(?:^|[-–—|]\s*)(?:microsoft\s+)?(word|excel|powerpoint)\s*$',
                r'\.(?:docx?|xlsx?|pptx?|pdf|py|cpp|c|java|cs|js|ts|html|css|json|sql|md|tex)\s*[-–—|]',
                r'(?:^|[-–—|]\s*)(?:foxit|adobe\s+reader|acrobat|sumatrapdf|wps\s+office|libreoffice)\b',
                # Công cụ ghi chú & Học tập
                r'(?:^|[-–—|]\s*)(?:notion|obsidian|anki|zotero|mendeley|overleaf|calculator|geogebra|desmos)\b'
            ]
            if any(re.search(pat, t_low) for pat in local_desktop_safe_patterns):
                self.active_operate_time = 0.0
                self.current_distraction = None
                return None

        # 2. TỰ ĐỘNG NẠP LẠI BLOCKLIST NẾU NGƯỜI DÙNG SỬA BLOCKLIST.TXT
        if os.path.exists(self.blocklist_file):
            try:
                mtime = os.path.getmtime(self.blocklist_file)
                if mtime != self.last_blocklist_mtime:
                    self.custom_blocked_keywords = self._load_blocklist()
            except Exception:
                pass

        # 3. KIỂM TRA TÀI LIỆU HỌC TẬP / TÌM KIẾM AN TOÀN TRÊN TRÌNH DUYỆT
        # Trừ khi tiêu đề rõ ràng thuộc về Facebook, YouTube giải trí, TikTok, Web người lớn...
        general_safe_keywords = [
            "google search", "tìm kiếm trên google", "tìm trên google", "bing search",
            "github", "stackoverflow", "leetcode", "hackerrank", "kaggle",
            "khan academy", "coursera", "edx", "udemy", "duolingo",
            "google docs", "google sheets", "google slides", "google drive",
            "canva", "figma"
        ]
        # Tài liệu lập trình API không bị tính là mạng xã hội
        is_dev_doc = bool(re.search(r'\b(api\s+documentation|developer\s+platform|developer\s+guide|developer\s+docs)\b', t_low))

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

        # 1. Nhận diện trang web người lớn / nội dung 18+ (Dùng tên miền hoặc cụm từ khiêu dâm rõ ràng)
        # KHÔNG KHỚP TỪ ĐƠN LẺ "sex" để tránh chặn tài liệu sinh học/sức khỏe (Sex determination, Sex differences...)
        if not d_type:
            adult_domains = [
                r'\b(pornhub|xvideos|xnxx|xhamster|redtube|youporn|brazzers|onlyfans|javhd|vlxx|stripchat|chaturbate|spankbang|beeg|fapello|thothub)\b',
                r'\brule34\b'
            ]
            adult_explicit_terms = [
                r'\b(phimsex|phim\s+sex|phim\s+nguoi\s+lon)\b',
                r'\bsex\s+(?:video|clip|phim|hd|movie|hay|gai|tour|show|cam|tape|hub)\b',
                r'\b(?:video|clip|phim|xem)\s+sex\b',
                r'\bxxx\s+(?:video|clip|phim|hd|movie)\b',
                r'\bporn(?:ography|\s+video|\s+movie|\s+pic|\s+hub)?\b',
                r'\b(hentai|javhd|nsfw|rule34)\b'
            ]
            if any(re.search(p, t_low) for p in adult_domains + adult_explicit_terms):
                d_type = "WEB_DISTRACT"
                d_label = "Trang web 18+ / Nhạy cảm"

        # 2. Nhận diện trò chơi điện tử (Gaming)
        # Dùng ranh giới tên miền hoặc cụm tiêu đề rõ ràng, KHÔNG KHỚP TỪ ĐƠN "steam" (Steam engine) hay "origin" (Origin of Species)
        if not d_type:
            game_patterns = [
                r'\b(league of legends|riot client|valorant|genshin impact|honkai|roblox|minecraft)\b',
                r'\b(counter-strike|cs:go|cs2|dota 2|pubg|apex legends|fifa|fc 24|fc 25)\b',
                r'\b(garena|lien quan|free fire|naraka|black myth|elden ring|wuthering waves)\b',
                r'\b(steampowered\.com|steamcommunity\.com|epicgames\.com|ea\.com)\b',
                r'(?:^|[-–—|]\s*)steam(?:\s+(?:community|store|client|support|deck|app))?(?:\s*[-–—|]|\s*$)',
                r'(?:^|[-–—|]\s*)origin(?:\s+(?:client|games?|store))(?:\s*[-–—|]|\s*$)',
                r'\b(ubisoft connect|battle\.net|ea app|epic games launcher)\b',
                r'^steam$'
            ]
            if any(re.search(p, t_low) for p in game_patterns):
                d_type = "WEB_DISTRACT"
                d_label = "Trò chơi điện tử (Game)"

        # 3. Facebook & Messenger:
        # Khớp theo tên miền hoặc cụm nhận diện thương hiệu tab trình duyệt
        if not d_type:
            fb_patterns = [
                r'\b(facebook\.com|messenger\.com|fb\.com|m\.facebook\.com|web\.facebook\.com)\b',
                r'(?:^|[-–—|]\s*)(?:facebook|messenger)(?:\s*[-–—|]|\s*$)',
                r'^\([0-9+]+\)\s*(?:facebook|messenger)\b',
                r'^facebook(?:\s*[-–—|:]|\s+(?:watch|reels|and\s+\d+|va\s+\d+|và\s+\d+)|$)',
                r'\bfacebook\s+(?:watch|reels|and\s+\d+\s+more\s+pages|và\s+\d+\s+trang\s+khác)\b'
            ]
            if any(re.search(p, t_low) for p in fb_patterns):
                d_type = "FACEBOOK"
                d_label = "Facebook"

        # 4. YouTube:
        if not d_type:
            yt_patterns = [
                r'\b(youtube\.com|youtu\.be)\b',
                r'(?:^|[-–—|]\s*)youtube(?:\s*[-–—|]|\s*$)',
                r'^\([0-9+]+\)\s*youtube\b'
            ]
            if any(re.search(p, t_low) for p in yt_patterns):
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
                    self.active_operate_time = 0.0
                    self.current_distraction = None
                    return None

                d_type = "YOUTUBE"
                d_label = "YouTube"

        # 5. TikTok, Threads, Instagram & Các mạng xã hội / Mua sắm khác:
        if not d_type:
            tiktok_patterns = [
                r'\b(tiktok\.com)\b',
                r'(?:^|[-–—|/•]\s*)tiktok(?:\s*[-–—|/•:]|\s*$)',
                r'^\([0-9+]+\)\s*.*?\btiktok\b'
            ]
            threads_patterns = [
                r'\b(threads\.(?:net|com))\b',
                r'(?:^|[-–—|/•]\s*)threads(?:\s*,\s*(?:an\s*instagram\s*app|m[oộ]t\s*[uứ]ng\s*d[uụ]ng\s*c[uủ]a\s*instagram))?(?:\s*[-–—|/•:]|\s*$)',
                r'^\([0-9+]+\)\s*threads(?:\s*[-–—|/•:]|\s*$)',
                r'\b(?:on|tren|trên)\s+threads(?::|\b)',
                r'•\s*threads(?:\s*[-–—|/•:]|\s*$)',
                r'\bthreads\s*[•|–—-]\s*(?:say\s+more|trang\s+ch[uủ]|home|feed|b[aả]ng\s+tin)\b',
                r'\(@[a-zA-Z0-9._]+\)\s*(?:•|[-–—|/:]|on|tr[eê]n)\s*threads\b',
                r'^\([0-9+]+\)\s*.*?(?:•|on|tr[eê]n)\s*threads\b'
            ]
            instagram_patterns = [
                r'\b(instagram\.com)\b',
                r'(?:^|[-–—|/•]\s*)instagram(?:\s*[-–—|/•:]|\s*$)',
                r'^\([0-9+]+\)\s*.*?\binstagram\b',
                r'\b(?:on|tren|trên)\s+instagram(?::|\b)',
                r'•\s*instagram\b'
            ]
            other_social_patterns = [
                r'\b(bilibili|netflix|shopee|lazada|discord|twitch|reddit|weibo)\b',
                r'(?:^|[-–—|/•]\s*)(?:telegram)(?:\s*[-–—|/•]|\s*$)',
                r'(?:^|[-–—|/•]\s*)pinterest(?:\s*[-–—|/•]|\s*$)'
            ]
            if not is_dev_doc:
                other_social_patterns.extend([
                    r'\b(twitter\.com|x\.com)\b',
                    r'(?:^|[-–—|/•]\s*)(?:twitter|x)(?:\s*[-–—|/•]|\s*$)',
                    r'^\([0-9+]+\)\s*(?:twitter|x)\b',
                    r'\b(twitter\s*/\s*x|x\s*/\s*twitter)\b'
                ])

            if any(re.search(p, t_low) for p in tiktok_patterns):
                d_type = "WEB_DISTRACT"
                d_label = "TikTok"
            elif any(re.search(p, t_low) for p in threads_patterns):
                d_type = "WEB_DISTRACT"
                d_label = "Threads"
            elif any(re.search(p, t_low) for p in instagram_patterns):
                d_type = "WEB_DISTRACT"
                d_label = "Instagram"
            elif any(re.search(p, t_low) for p in other_social_patterns):
                d_type = "WEB_DISTRACT"
                d_label = "Mạng xã hội / Mua sắm / Giải trí"

        # Nếu không thuộc bất kỳ nhóm gây xao nhãng nào HOẶC khớp danh mục an toàn chung
        if not d_type or any(safe in t_low for safe in general_safe_keywords):
            if not d_type or (d_type not in ("FACEBOOK", "YOUTUBE") and "Đã chặn" not in (d_label or "") and d_label != "Trang web 18+ / Nhạy cảm" and d_label not in ("Threads", "TikTok", "Instagram")):
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
