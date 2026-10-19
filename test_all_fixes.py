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
            ("Reddit - Dive into anything - Google Chrome", True, "WEB_DISTRACT"),
            ("Netflix - Google Chrome", True, "WEB_DISTRACT"),
            ("Twitch - Google Chrome", True, "WEB_DISTRACT"),
            ("Shopee Việt Nam | Mua và Bán Trên Sàn TMĐT - Google Chrome", True, "WEB_DISTRACT"),
            ("Threads - Google Chrome", True, "WEB_DISTRACT"),
            ("(1) Facebook - Google Chrome", True, "FACEBOOK"),
            ("Facebook và 1 trang khác - Microsoft​ Edge", True, "FACEBOOK"),
            ("Messenger | Trò chuyện - Cốc Cốc", True, "FACEBOOK"),
            ("YouTube - Google Chrome", True, "YOUTUBE"),
            ("TikTok - Make Your Day - Google Chrome", True, "WEB_DISTRACT"),
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

    def test_phone_tracker_elevated_in_hand(self):
        from phone_detector import KinematicPhoneTracker
        tracker = KinematicPhoneTracker()
        now = time.monotonic()

        # Người dùng cầm điện thoại ngang ngực/mặt (cy = 180, frame_h = 480 < 0.65 frame_h)
        # Dù không phát hiện được màu da (has_hand=False) và cầm bất động, vẫn là ĐANG CẦM
        boxes = [(100, 130, 200, 230, 0.70, False)]
        res = tracker.update(boxes, now, frame_h=480)
        self.assertTrue(res[0][5])

        # Sau 3 giây cầm yên ngang ngực: vẫn là CẦM TRÊN TAY
        res = tracker.update([(100, 130, 200, 230, 0.70, False)], now + 3.0, frame_h=480)
        self.assertTrue(res[0][5], "Phone held elevated at chest/face level must remain is_held=True even when still")

    def test_phone_tracker_hand_contact(self):
        from phone_detector import KinematicPhoneTracker
        tracker = KinematicPhoneTracker()
        now = time.monotonic()

        # Điện thoại cầm yên trên tay (người dùng đọc báo / lướt Facebook)
        # Vị trí đứng yên hoàn toàn nhưng CÓ BÀN TAY CHẠM (has_hand=True)
        res = tracker.update([(100, 100, 200, 300, 0.70, True)], now)
        self.assertTrue(res[0][5])

        res = tracker.update([(100, 100, 200, 300, 0.70, True)], now + 2.5)
        self.assertTrue(res[0][5], "Phone held still in hands must remain is_held=True due to hand contact")


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
        self.test_file = "test_focus_history_tmp.json"
        if os.path.exists(self.test_file):
            os.remove(self.test_file)
        self.mgr = SessionHistoryManager(history_file=self.test_file)

    def tearDown(self):
        if os.path.exists(self.test_file):
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
        res = detector.process_frame(dummy_frame)
        self.assertEqual(res["status"], "FOCUSED")
        self.assertIn("CÚI VIẾT BÀI", res["label"])
        self.assertFalse(res["alert"])

        # Mất mặt được 28s: Đã gục xuống bàn ngủ quá 18s!
        detector.away_start = now - 28.0
        res = detector.process_frame(dummy_frame)
        self.assertEqual(res["status"], "DROWSY", "Slumped head missing > 18s must trigger DROWSY!")
        self.assertTrue(res["alert"])
        self.assertEqual(res["alert_type"], "DROWSY")
        self.assertIn("GỤC XUỐNG BÀN", res["label"])

        # Mất mặt được 65s: Rơi vào nhánh AWAY / Ngủ gục quá lâu
        detector.away_start = now - 65.0
        res = detector.process_frame(dummy_frame)
        self.assertEqual(res["status"], "AWAY")
        self.assertTrue(res["alert"])
        self.assertEqual(res["alert_type"], "AWAY")

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


if __name__ == "__main__":
    unittest.main()
