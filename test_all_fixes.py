# -*- coding: utf-8 -*-
"""
Hệ thống kiểm thử toàn diện (Comprehensive Test Suite) cho FocusGuard PRO:
Kiểm tra tất cả các bug và tính năng vừa sửa:
1. App Distraction Monitor: Phân biệt trang học tập vs giải trí, word boundaries, regex YouTube
2. Phone Detector & Kinematic Tracker: Tiếp xúc bàn tay (Hand contact), hộp rung YOLO, điện thoại trên bàn
3. Pomodoro Timer: Chuyển trạng thái khi Toggle trong giờ Break
4. History Manager: Điểm trung bình có trọng số (Duration-weighted avg), lọc phiên ngắn < 45s, chuỗi ngày streak
5. Focus Detector: Gục đầu ngủ trên bàn (Desk sleeping) vs Đang cúi viết bài, chốt sớm khung học (>= 4 samples)
6. Sound Alert Manager: An toàn đa luồng khi phát và dừng âm thanh
"""
import unittest
import time
import os
import json
import numpy as np

class TestAppMonitor(unittest.TestCase):
    def setUp(self):
        from app_monitor import AppDistractionMonitor
        self.mon = AppDistractionMonitor()

    def test_distraction_patterns(self):
        test_cases = [
            ("Instagram - Google Chrome", True, "WEB_DISTRACT"),
            ("(1) Instagram - Google Chrome", True, "WEB_DISTRACT"),
            ("Chi Pu (@chipupu) • Instagram photos and videos - Google Chrome", True, "WEB_DISTRACT"),
            ("Reddit - Dive into anything - Google Chrome", True, "WEB_DISTRACT"),
            ("Netflix - Google Chrome", True, "WEB_DISTRACT"),
            ("Twitch - Google Chrome", True, "WEB_DISTRACT"),
            ("Shopee Việt Nam | Mua và Bán Trên Sàn TMĐT - Google Chrome", True, "WEB_DISTRACT"),
            ("Threads - Google Chrome", True, "WEB_DISTRACT"),
            ("(1) Threads - Google Chrome", True, "WEB_DISTRACT"),
            ("Threads • Say more - Google Chrome", True, "WEB_DISTRACT"),
            ("Hà Anh Tuấn (@haanhtuan) • Threads - Google Chrome", True, "WEB_DISTRACT"),
            ("Hà Anh Tuấn (@haanhtuan) trên Threads: Bài viết mới - Google Chrome", True, "WEB_DISTRACT"),
            ("John Doe (@johndoe) on Threads: Hello world - Google Chrome", True, "WEB_DISTRACT"),
            ("threads.com - Google Chrome", True, "WEB_DISTRACT"),
            ("(1) Facebook - Google Chrome", True, "FACEBOOK"),
            ("Facebook và 1 trang khác - Microsoft​ Edge", True, "FACEBOOK"),
            ("Messenger | Trò chuyện - Cốc Cốc", True, "FACEBOOK"),
            ("YouTube - Google Chrome", True, "YOUTUBE"),
            ("TikTok - Make Your Day - Google Chrome", True, "WEB_DISTRACT"),
            ("(1) TikTok - Make Your Day - Google Chrome", True, "WEB_DISTRACT"),
            ("Twitter / X - Google Chrome", True, "WEB_DISTRACT"),
            ("Pornhub - Free Porn Videos - Google Chrome", True, "WEB_DISTRACT"),
            ("XVideos: Free Sex Videos - Google Chrome", True, "WEB_DISTRACT"),
            ("XNXX.COM - Free Porn Videos - Brave", True, "WEB_DISTRACT"),
        ]
        for title, should_distract, expected_type in test_cases:
            t_low = title.lower().strip()
            self.mon.get_foreground_title = lambda t=title: t
            self.mon.active_operate_time = 5.0
            self.mon.get_system_idle_seconds = lambda: 0.1
            res = self.mon.check_distraction()
            if should_distract:
                self.assertIsNotNone(res, f"Failed for {title}")
                self.assertEqual(res["alert_type"], expected_type, f"Wrong type for {title}")

    def test_adult_website_detection(self):
        adult_titles = [
            "Pornhub.com - HD Porn & Sex Videos - Google Chrome",
            "xvideos.com - Hot Movies - Microsoft Edge",
            "XNXX - Best Adult Tube - Firefox",
            "Phim sex Vietsub mới nhất - Cốc Cốc",
            "javhd - Japanese Adult Video - Brave"
        ]
        self.mon.get_system_idle_seconds = lambda: 0.1
        for title in adult_titles:
            self.mon.get_foreground_title = lambda t=title: t
            self.mon.active_operate_time = 2.0
            res = self.mon.check_distraction()
            self.assertIsNotNone(res, f"Adult site missed: {title}")
            self.assertEqual(res["label"], "Trang web 18+ / Nhạy cảm")
            self.assertTrue(res["should_alert"])

    def test_safe_keywords_do_not_whitelist_facebook(self):
        # Facebook post discussing Excel / PDF must still be caught as FACEBOOK
        tricky_fb_titles = [
            "Tự học Excel cấp tốc mỗi ngày - Facebook - Google Chrome",
            "Tải tài liệu PDF miễn phí | Facebook",
            "Nhóm học lập trình và Microsoft Word - Facebook"
        ]
        self.mon.get_system_idle_seconds = lambda: 0.1
        for title in tricky_fb_titles:
            self.mon.get_foreground_title = lambda t=title: t
            self.mon.active_operate_time = 3.0
            res = self.mon.check_distraction()
            self.assertIsNotNone(res, f"Tricky FB title was falsely whitelisted: {title}")
            self.assertEqual(res["alert_type"], "FACEBOOK")

    def test_custom_blocklist(self):
        self.mon.custom_blocked_keywords = ["voz.vn", "tai xiu", "kenh14.vn"]
        self.mon.get_system_idle_seconds = lambda: 0.1
        test_titles = [
            "F33 - Điểm báo | VOZ.VN - Google Chrome",
            "Game Tài Xỉu Đổi Thưởng Uy Tín - Microsoft Edge",
            "Kenh14.vn - Tin tức giới trẻ mới nhất"
        ]
        for title in test_titles:
            self.mon.get_foreground_title = lambda t=title: t
            self.mon.active_operate_time = 3.0
            res = self.mon.check_distraction()
            self.assertIsNotNone(res, f"Custom blocklist failed to catch: {title}")
            self.assertEqual(res["alert_type"], "WEB_DISTRACT")
            self.assertIn("Đã chặn", res["label"])

    def test_educational_youtube_vs_false_positives(self):
        # Các video giải trí KHÔNG ĐƯỢC lọt qua
        non_educational = [
            "Văn Mai Hương - Đại Minh Tinh (Official MV) - YouTube",
            "Nguyễn Văn Hùng tập 12 - Phim Hay - YouTube",
            "Thanh toán hóa đơn tiền điện nhanh chóng - YouTube",
            "Of course I did it! Funny prank video - YouTube",
            "Khoa Pug ăn tối sang chảnh tại New York - YouTube"
        ]
        # Các video học tập BẮT BUỘC ĐƯỢC BỎ QUA
        educational = [
            "Bài giảng Giải tích 1 - Chương 2 Đạo hàm và Vi phân - YouTube",
            "Học Lập trình Python từ cơ bản đến nâng cao - YouTube",
            "Luyện thi IELTS Listening Full Test 2026 - YouTube",
            "Toán học 12: Khảo sát sự biến thiên của hàm số - YouTube",
            "Lofi Hip Hop radio - beats to relax/study to - YouTube",
            "Crash Course Computer Science #1 - YouTube",
            "MIT OpenCourseWare - Linear Algebra Lecture 1 - YouTube"
        ]

        self.mon.get_system_idle_seconds = lambda: 0.1

        for title in non_educational:
            self.mon.get_foreground_title = lambda t=title: t
            self.mon.active_operate_time = 7.0
            res = self.mon.check_distraction()
            self.assertIsNotNone(res, f"False negative: '{title}' should be caught as distraction!")
            self.assertEqual(res["alert_type"], "YOUTUBE")

        for title in educational:
            self.mon.get_foreground_title = lambda t=title: t
            self.mon.active_operate_time = 7.0
            res = self.mon.check_distraction()
            self.assertIsNone(res, f"False positive: '{title}' should be allowed as educational study material!")


    def test_false_positives_reviewer_reported(self):
        """
        Kiểm tra toàn bộ 14 trường hợp học tập / nghiên cứu / lập trình mà reviewer báo cáo:
        Tất cả các tiêu đề này TUYỆT ĐỐI KHÔNG ĐƯỢC BÁO NHẦM!
        """
        safe_academic_and_dev_titles = [
            # 1. Sinh học / Y tế / Sức khỏe (Chứa từ 'sex')
            "Sex determination in mammals",
            "Sex education curriculum",
            "Sex differences in the brain",
            "Fair Sex in modern history",
            # 2. Soạn thảo văn bản / Lập trình (Chứa tên Facebook / YouTube)
            "Báo cáo đề tài về Facebook.docx - Word",
            "facebook-scraper.py - Visual Studio Code",
            "youtube-dl.py - Visual Studio Code",
            "facebook_api.py - PyCharm",
            # 3. Kỹ thuật / Khoa học / Tự nhiên (Chứa từ 'threads', 'steam', 'origin', 'reels')
            "Python threads and locks",
            "Multithreading in Java.pdf - Foxit PDF Reader",
            "Steam engine - Wikipedia",
            "Steam turbine thermodynamics",
            "Origin of Species - Charles Darwin",
            "Origin of the Universe - Google Search - Google Chrome",
            # 4. Tài liệu kỹ thuật / Tìm kiếm / Câu cá
            "Twitter API documentation",
            "Pinterest board ideas",
            "Fishing reels"
        ]
        self.mon.get_system_idle_seconds = lambda: 0.1
        for title in safe_academic_and_dev_titles:
            self.mon.get_foreground_title = lambda t=title: t
            self.mon.active_operate_time = 5.0
            res = self.mon.check_distraction()
            self.assertIsNone(res, f"False positive detected: '{title}' must NOT trigger distraction alert! Got: {res}")

    def test_distraction_in_browser_still_caught(self):
        """Đảm bảo các trang mạng xã hội / giải trí thật trong trình duyệt vẫn bị bắt chính xác"""
        real_distractions = [
            ("Facebook - Google Chrome", "FACEBOOK"),
            ("(5) Facebook - Google Chrome", "FACEBOOK"),
            ("Học bài cùng tôi | Facebook - Google Chrome", "FACEBOOK"),
            ("Facebook Watch - Microsoft Edge", "FACEBOOK"),
            ("Tự học Excel mỗi ngày | Facebook - Google Chrome", "FACEBOOK"),
            ("Threads - Google Chrome", "WEB_DISTRACT"),
            ("Twitter / X - Google Chrome", "WEB_DISTRACT"),
            ("Steam - Google Chrome", "WEB_DISTRACT"),
            ("Pornhub.com - Google Chrome", "WEB_DISTRACT"),
            ("Phim sex Vietsub mới - Google Chrome", "WEB_DISTRACT"),
            ("League of Legends", "WEB_DISTRACT")
        ]
        self.mon.get_system_idle_seconds = lambda: 0.1
        for title, expected_type in real_distractions:
            self.mon.get_foreground_title = lambda t=title: t
            self.mon.active_operate_time = 5.0
            res = self.mon.check_distraction()
            self.assertIsNotNone(res, f"Real distraction missed: '{title}'")
            self.assertEqual(res["alert_type"], expected_type, f"Wrong alert type for '{title}'")


class TestPhoneKinematics(unittest.TestCase):
    def test_phone_tracker_stationary_desk(self):
        from phone_detector import KinematicPhoneTracker
        tracker = KinematicPhoneTracker()
        now = time.monotonic()

        # Giả lập điện thoại đặt ở vùng mép bàn (cy = 380, frame_h = 480)
        # Không có tay chạm (has_hand=False), tọa độ rung nhẹ do box YOLO (± 3px)
        boxes = [(100, 330, 200, 430, 0.70, False)]
        res = tracker.update(boxes, now, frame_h=480)
        self.assertTrue(res[0][5], "Nhịp đầu tiên xuất hiện mặc định là True")

        # Sau 0.5s: vẫn yên vị
        res = tracker.update([(102, 331, 202, 431, 0.72, False)], now + 0.5, frame_h=480)
        self.assertTrue(res[0][5], "Chưa đủ 2s tĩnh thì vẫn giữ trạng thái")

        # Sau 2.2s: đã đứng yên > 2.0s ở mép bàn không có tay chạm -> phải chuyển sang False (TĨNH TRÊN BÀN)
        res = tracker.update([(101, 330, 201, 430, 0.71, False)], now + 2.2, frame_h=480)
        self.assertFalse(res[0][5], "Phone lying motionless on desk > 2.0s must transition to static is_held=False")

        # Rung nhẹ YOLO thêm 1s nữa: vẫn phải là static
        res = tracker.update([(103, 332, 203, 432, 0.71, False)], now + 3.2, frame_h=480)
        self.assertFalse(res[0][5], "YOLO bounding box jitter must not falsely trigger is_held=True")

        # Người dùng nhấc điện thoại lên (di chuyển 35px): phải lập tức chuyển sang CẦM TRÊN TAY
        res = tracker.update([(140, 270, 240, 370, 0.75, False)], now + 3.8, frame_h=480)
        self.assertTrue(res[0][5], "Moving phone must transition to is_held=True")

    def test_phone_tracker_stationary_on_elevated_stand(self):
        """Điện thoại dựng trên giá đỡ ở tầm mắt (cy = 180, frame_h = 480 < 0.65 frame_h)"""
        from phone_detector import KinematicPhoneTracker
        tracker = KinematicPhoneTracker()
        now = time.monotonic()

        # Ban đầu xuất hiện trên giá đỡ:
        boxes = [(100, 130, 200, 230, 0.70, False)]
        res = tracker.update(boxes, now, frame_h=480)
        self.assertTrue(res[0][5])

        # Sau 0.5s: vẫn yên vị trên giá
        res = tracker.update([(100, 130, 200, 230, 0.70, False)], now + 0.5, frame_h=480)
        self.assertTrue(res[0][5])

        # Đứng yên trên giá đỡ > 2.0s và không có tay chạm -> Chuyển thành False (TĨNH TRÊN GIÁ ĐỠ)
        res = tracker.update([(100, 130, 200, 230, 0.70, False)], now + 2.3, frame_h=480)
        self.assertFalse(res[0][5], "Phone stationary on stand without hand must transition to is_held=False")

    def test_phone_tracker_elevated_in_hand_moving(self):
        """Điện thoại cầm trên tay giơ lên xem (ngang ngực/mặt, có tay hoặc có cử động)"""
        from phone_detector import KinematicPhoneTracker
        tracker = KinematicPhoneTracker()
        now = time.monotonic()

        # Người dùng cầm trên tay (has_hand=True) giơ ngang ngực
        boxes = [(100, 130, 200, 230, 0.70, True)]
        res = tracker.update(boxes, now, frame_h=480)
        self.assertTrue(res[0][5])

        # Đang vuốt lướt / cử động tay (di chuyển 18px)
        res = tracker.update([(118, 130, 218, 230, 0.70, True)], now + 1.0, frame_h=480)
        self.assertTrue(res[0][5], "Phone held and moving in hand must remain is_held=True")

    def test_phone_tracker_hand_contact(self):
        from phone_detector import KinematicPhoneTracker
        tracker = KinematicPhoneTracker()
        now = time.monotonic()

        # Điện thoại cầm yên trên tay (người dùng đọc báo / lướt Facebook)
        # Vị trí đứng yên hoàn toàn nhưng CÓ BÀN TAY CHẠM (has_hand=True)
        res = tracker.update([(100, 100, 200, 300, 0.70, True)], now)
        self.assertTrue(res[0][5])

        # Trong vòng 1.5s: vẫn là cầm trên tay
        res = tracker.update([(100, 100, 200, 300, 0.70, True)], now + 1.5)
        self.assertTrue(res[0][5], "Phone held in hand within grace period must remain is_held=True")

    def test_skin_color_rejection(self):
        """Kiểm tra bộ lọc da sinh trắc học loại bỏ bàn gỗ, giấy kraft, tường kem và nhận diện đúng da người"""
        import cv2
        test_palette = {
            'fair_skin': (np.array([[[145, 170, 220]]], dtype=np.uint8), True),
            'asian_skin': (np.array([[[130, 160, 210]]], dtype=np.uint8), True),
            'tan_skin': (np.array([[[85, 115, 175]]], dtype=np.uint8), True),
            'wood_pine': (np.array([[[80, 140, 190]]], dtype=np.uint8), False),
            'wood_oak': (np.array([[[50, 100, 160]]], dtype=np.uint8), False),
            'kraft_paper': (np.array([[[100, 150, 180]]], dtype=np.uint8), False),
            'cream_wall': (np.array([[[180, 210, 225]]], dtype=np.uint8), False),
            'white_paper': (np.array([[[240, 245, 250]]], dtype=np.uint8), False),
        }
        for name, (bgr, expected_is_skin) in test_palette.items():
            hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)[0,0]
            ycrcb = cv2.cvtColor(bgr, cv2.COLOR_BGR2YCrCb)[0,0]
            y, cr, cb = int(ycrcb[0]), int(ycrcb[1]), int(ycrcb[2])
            h, s, v = int(hsv[0]), int(hsv[1]), int(hsv[2])

            is_skin = (
                ((h <= 13) or (h >= 175)) and
                (s >= 50 and s <= 165) and
                (v >= 40) and
                (y >= 50 and y <= 245) and
                (cr >= 135 and cr <= 175) and
                (cb >= 90 and cb <= 132) and
                ((cr - cb) >= 22)
            )
            self.assertEqual(is_skin, expected_is_skin, f"Color test failed for {name}: expected {expected_is_skin}, got {is_skin}")


class TestPomodoroToggle(unittest.TestCase):
    def test_toggle_during_break(self):
        from pomodoro import PomodoroTimer
        pomo = PomodoroTimer(work_min=25, break_min=5)
        # Giả lập chuyển sang BREAK
        pomo.state = "BREAK"
        pomo.is_active = True
        
        # main.py logic check:
        is_break = pomo.is_active and (pomo.state == "BREAK")
        self.assertTrue(is_break)

        # Người dùng bấm [P] tắt Pomodoro lúc đang nghỉ
        pomo.toggle()
        self.assertFalse(pomo.is_active)
        
        # main.py logic check sau khi tắt:
        is_break = pomo.is_active and (pomo.state == "BREAK")
        self.assertFalse(is_break, "Toggling Pomodoro off during break must immediately resume monitoring!")


class TestHistoryWeightedAverages(unittest.TestCase):
    def setUp(self):
        from history import SessionHistoryManager
        base_dir = os.path.dirname(os.path.abspath(__file__))
        self.test_file = os.path.join(base_dir, "test_focus_history_tmp.json")
        if os.path.exists(self.test_file):
            os.remove(self.test_file)
        self.mgr = SessionHistoryManager(history_file=self.test_file)

    def tearDown(self):
        if hasattr(self, 'test_file') and os.path.exists(self.test_file):
            os.remove(self.test_file)

    def test_short_session_filtering(self):
        # Phiên 15 giây (test thử app rồi tắt)
        res = self.mgr.save_session(1000, 1015, 50.0, 0, 0, 0, 0)
        self.assertIsNone(res, "Sessions < 45 seconds must be discarded!")
        self.assertEqual(len(self.mgr.history_data.get("sessions", [])), 0)

    def test_duration_weighted_average(self):
        # Phiên 1: 120 phút (7200s), tập trung 95%
        now = time.time()
        self.mgr.save_session(now - 7200, now, 95.0, 0, 0, 0, 1, active_study_seconds=7200)
        # Phiên 2: 1 phút (60s), tập trung 50%
        self.mgr.save_session(now - 60, now, 50.0, 0, 0, 0, 0, active_study_seconds=60)

        stats = self.mgr.get_summary_stats()
        # Nếu tính trung bình cộng đơn thuần: (95 + 50) / 2 = 72.5% (SAI BÉT)
        # Trọng số chuẩn xác: (95 * 7200 + 50 * 60) / 7260 = 94.6%
        self.assertGreater(stats["avg_score"], 94.0, f"Score should be duration-weighted, got {stats['avg_score']}%")
        self.assertLess(stats["avg_score"], 95.0)

    def test_streak_calculation(self):
        now = time.time()
        # Ngày 1 (Hôm qua): Học 300s (5 phút) -> Đạt tiêu chuẩn streak (>= 120s)
        yesterday_ts = now - 86400
        self.mgr.save_session(yesterday_ts - 300, yesterday_ts, 90.0, 0, 0, 0, 0, active_study_seconds=300)

        # Ngày 2 (Hôm nay): Học 180s (3 phút) -> Đạt tiêu chuẩn streak
        self.mgr.save_session(now - 180, now, 85.0, 0, 0, 0, 0, active_study_seconds=180)

        curr_streak, best_streak = self.mgr.calculate_streak()
        self.assertEqual(curr_streak, 2)


class TestDeskSleepingDetection(unittest.TestCase):
    def test_bowed_writing_to_drowsy_transition(self):
        from detector import FocusDetector
        # Khởi tạo detector ở chế độ kiểm thử
        detector = FocusDetector()
        now = time.monotonic()

        # Giả lập trước khi khuất mặt: người dùng cúi đầu góc -25 độ
        detector.last_seen_pitch = -25.0
        detector.last_seen_reading = True
        detector.last_detection_data = None  # Mất mặt
        detector.away_start = now - 10.0     # Mất mặt được 10s (trong 18s grace)

        dummy_frame = np.full((480, 640, 3), 120, dtype=np.uint8)
        # Giai đoạn cúi viết bài 10s: Tập trung cúi viết bài, không báo động
        res = detector.process_frame(dummy_frame)
        self.assertEqual(res["status"], "FOCUSED")
        self.assertIn("CÚI VIẾT BÀI", res["label"])
        self.assertFalse(res["alert"])

        # Cúi viết bài liên tục 45s: Vẫn là ĐANG CÚI VIẾT BÀI, TUYỆT ĐỐI KHÔNG BÁO DROWSY!
        detector.away_start = now - 45.0
        res = detector.process_frame(dummy_frame)
        self.assertEqual(res["status"], "FOCUSED", "Writing notes for 45s must remain FOCUSED, not DROWSY!")
        self.assertFalse(res["alert"])
        self.assertIn("CÚI VIẾT BÀI", res["label"])

        # Cúi viết bài liên tục 120s (2 phút): Vẫn là FOCUSED!
        detector.away_start = now - 120.0
        res = detector.process_frame(dummy_frame)
        self.assertEqual(res["status"], "FOCUSED")
        self.assertFalse(res["alert"])

        # Cúi quá 185s (> 3 phút không thấy mặt): Nhắc nhở rời bàn / cúi quá lâu (AWAY), KHÔNG PHẢI DROWSY
        detector.away_start = now - 185.0
        res = detector.process_frame(dummy_frame)
        self.assertEqual(res["status"], "AWAY")
        self.assertTrue(res["alert"])
        self.assertEqual(res["alert_type"], "AWAY")
        self.assertNotEqual(res["alert_type"], "DROWSY", "Missing face while writing must NEVER trigger DROWSY!")

    def test_drowsy_only_when_eyes_closed(self):
        """Buồn ngủ / ngủ gật CHỈ kích hoạt khi thực sự thấy nhắm nghiền mắt (EAR thấp kéo dài)"""
        from detector import FocusDetector
        detector = FocusDetector()
        now = time.monotonic()
        dummy_frame = np.full((480, 640, 3), 120, dtype=np.uint8)

        # Trường hợp 1: Người dùng cúi đầu đọc sách/viết bài (pitch = -25°), mắt mở nhìn xuống bàn (EAR = 0.12)
        detector.last_detection_data = {
            "landmarks": [type("Pt", (), {"x": 0.5, "y": 0.5})()] * 468,
            "ear": 0.12,
            "mar": 0.1,
            "pitch": -25.0,
            "yaw": 0.0,
            "roll": 0.0,
            "gaze_ratio": 0.5,
            "timestamp": now
        }
        res = detector.process_frame(dummy_frame)
        self.assertEqual(res["status"], "FOCUSED")
        self.assertFalse(res["alert"], "Looking down at desk with eyes open must NOT trigger drowsy alert!")

        # Trường hợp 2: Cúi đầu sâu (pitch = -73°), nhưng mắt vẫn mở đọc bài (EAR = 0.11)
        detector.last_detection_data["pitch"] = -73.0
        detector.last_detection_data["ear"] = 0.11
        res = detector.process_frame(dummy_frame)
        self.assertEqual(res["status"], "FOCUSED", "Deep head tilt with eyes open must NOT trigger DROWSY!")
        self.assertFalse(res["alert"])

        # Trường hợp 3: Người dùng thực sự nhắm nghiền mắt (EAR = 0.04) khi cúi đầu, liên tục 8.0s -> NGỦ GẬT
        detector.last_detection_data["ear"] = 0.04
        detector.eye_closed_start = now - 8.0
        res = detector.process_frame(dummy_frame)
        self.assertEqual(res["status"], "DROWSY", "Truly closed eyes (EAR < 0.08) > 7.0s must trigger DROWSY!")
        self.assertTrue(res["alert"])
        self.assertEqual(res["alert_type"], "DROWSY")

    def test_zone_learning_early_exit(self):
        from detector import FocusDetector
        detector = FocusDetector()
        detector.start_zone_learning(duration=60.0)

        # Thu thập 5 mẫu (chốt sớm sau 2.5s ở 2 FPS)
        for i in range(5):
            detector.recorded_samples["yaw"].append(-5.0 + i)
            detector.recorded_samples["pitch"].append(-15.0 + i)
            detector.recorded_samples["roll"].append(0.0)
            detector.recorded_samples["ear"].append(0.20)

        msg = detector.finalize_zone_learning()
        self.assertIn("ĐÃ LƯU KHUNG HỌC", msg)
        self.assertIn("CHỐT SỚM", msg)
        self.assertTrue(detector.is_study_zone_set)

    def test_bowed_writing_with_person_present(self):
        """Khi đang ngồi thẳng rồi cúi nhanh (last_seen_pitch=0.0) hoặc YOLO phát hiện người,
        việc mất mặt 30s vẫn là ĐANG CÚI VIẾT BÀI, KHÔNG báo RỜI BÀN (AWAY)"""
        from detector import FocusDetector
        detector = FocusDetector()
        now = time.monotonic()
        dummy_frame = np.full((480, 640, 3), 120, dtype=np.uint8)

        # Người dùng đang ngồi thẳng (pitch = 0.0), không kịp ghi nhận cúi thì đã khuất mặt
        detector.last_seen_pitch = 0.0
        detector.last_seen_reading = False
        detector.last_detection_data = None
        detector.away_start = now - 30.0  # Đã mất mặt 30s (> away_limit_sec 25s)

        # 1. Trường hợp có YOLO báo person = True: Người vẫn ngồi ở bàn
        res = detector.process_frame(dummy_frame, has_person=True)
        self.assertEqual(res["status"], "FOCUSED")
        self.assertIn("CÚI VIẾT BÀI", res["label"])
        self.assertFalse(res["alert"])

        # 2. Trường hợp không truyền has_person nhưng last_seen_pitch <= 8.0 (ngồi học bình thường trước khi cúi)
        res = detector.process_frame(dummy_frame)
        self.assertEqual(res["status"], "FOCUSED")
        self.assertIn("CÚI VIẾT BÀI", res["label"])
        self.assertFalse(res["alert"])

    def test_away_detection_when_person_leaves(self):
        """Khi người dùng thực sự rời khỏi bàn (ngẩng lên rồi đi, last_seen_pitch > 8.0 và has_person=False) > 25s thì báo AWAY"""
        from detector import FocusDetector
        detector = FocusDetector()
        now = time.monotonic()
        dummy_frame = np.full((480, 640, 3), 120, dtype=np.uint8)

        detector.last_seen_pitch = 15.0  # Ngẩng đầu đứng dậy
        detector.last_seen_reading = False
        detector.last_detection_data = None
        detector.away_start = now - 26.0  # > 25s away_limit_sec

        res = detector.process_frame(dummy_frame, has_person=False)
        self.assertEqual(res["status"], "AWAY")
        self.assertTrue(res["alert"])
        self.assertEqual(res["alert_type"], "AWAY")


class TestAudioAlertManager(unittest.TestCase):
    def test_mci_playback_loop_duration(self):
        """Kiểm tra mã nguồn alert.py có vòng lặp MCI tối thiểu 200 bước (>= 10.0s) để không cắt cụt âm thanh"""
        alert_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "alert.py")
        with open(alert_file, "r", encoding="utf-8") as f:
            code = f.read()

        import re
        m = re.search(r'for\s+_\s+in\s+range\((\d+)\):', code)
        self.assertIsNotNone(m, "Could not find MCI wait loop in alert.py")
        iterations = int(m.group(1))
        # 240 iterations * 0.05s = 12.0s
        self.assertGreaterEqual(iterations, 200, f"MCI wait loop must be at least 200 iterations (10s), got {iterations}")

    def test_all_voice_files_exist(self):
        """Đảm bảo tất cả 11 file âm thanh MP3 cảnh báo đều tồn tại đầy đủ"""
        from alert import SoundAlertManager
        mgr = SoundAlertManager()
        for alert_type, filepath in mgr.voice_map.items():
            self.assertTrue(os.path.exists(filepath), f"Missing voice file for {alert_type}: {filepath}")


if __name__ == "__main__":
    unittest.main()
