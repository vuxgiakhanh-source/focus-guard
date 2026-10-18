# -*- coding: utf-8 -*-
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import os
import time

class HUDRenderer:
    """
    HUDRenderer PRO - Giao diện Glassmorphism Hiện Đại, Tinh Tế & Thân Thiện:
    - Phong cách Cyber-Glassmorphism trong suốt, không che khuất không gian học.
    - Bố cục thông minh: Header nổi, Thẻ Focus & Pomodoro tích hợp Sparkline, Mini Pose Card.
    - Thanh điều khiển Dock bo tròn phong cách macOS / iOS hiện đại.
    - Cache các panel chữ để không dựng lại qua PIL ở mọi frame webcam.
    """
    def __init__(self, width=640, height=480):
        self.width = width
        self.height = height

        font_paths = [
            "C:/Windows/Fonts/segoeui.ttf",
            "C:/Windows/Fonts/segoeuib.ttf",
            "C:/Windows/Fonts/arial.ttf",
            "C:/Windows/Fonts/calibri.ttf"
        ]
        self.font_path = None
        for p in font_paths:
            if os.path.exists(p):
                self.font_path = p
                break

        self.font_cache = {}
        self.score_history = [100.0, 100.0]
        self.last_history_sample = 0
        self.buttons = {}

        # Tiền cấp phát các khối màu nền kính mờ (Glassmorphism dark overlays)
        self.overlay_header = np.full((44, 433, 3), (18, 22, 28), dtype=np.uint8)
        self.overlay_score  = np.full((110, 173, 3), (18, 22, 28), dtype=np.uint8)
        self.overlay_pose   = np.full((56, 238, 3), (18, 22, 28), dtype=np.uint8)
        self.overlay_calib  = np.full((64, 433, 3), (18, 24, 34), dtype=np.uint8)

        # Tiền render thanh Dock nút bấm ở đáy màn hình
        self.cached_button_strips = {}
        for m in (False, True):
            for r in (False, True):
                self._pre_render_dock_bar(is_muted=m, is_rec=r)

        # Làm mới chữ mỗi 0,2 giây và vẽ ngay khi trạng thái đổi.
        self.last_text_refresh_time = 0.0
        self.last_text_state = None
        self.cached_header = None
        self.cached_score_card = None
        self.cached_pose_card = None

    def get_font(self, size):
        if size not in self.font_cache:
            if self.font_path:
                try:
                    self.font_cache[size] = ImageFont.truetype(self.font_path, size)
                except Exception:
                    self.font_cache[size] = ImageFont.load_default()
            else:
                self.font_cache[size] = ImageFont.load_default()
        return self.font_cache[size]

    def _pre_render_dock_bar(self, is_muted, is_rec=False):
        """Vẽ sẵn thanh Dock điều khiển bo tròn nổi dưới đáy màn hình"""
        dock_w = 616
        dock_h = 34
        dock_y1 = self.height - 44
        dock_y2 = self.height - 10
        dock_x1 = 12

        strip_bgr = np.full((dock_h, dock_w, 3), (15, 18, 24), dtype=np.uint8)
        strip_pil = Image.fromarray(cv2.cvtColor(strip_bgr, cv2.COLOR_BGR2RGB))
        d_btn = ImageDraw.Draw(strip_pil)

        # Khung viền ngoài của cả Dock
        d_btn.rounded_rectangle([0, 0, dock_w - 1, dock_h - 1], radius=8, fill=(18, 22, 30), outline=(50, 60, 75), width=1)

        calib_label = "[C] Lưu ngay" if is_rec else "[C] Khung học"
        calib_bg = (20, 75, 55) if is_rec else (25, 45, 75)
        calib_txt = (100, 255, 180) if is_rec else (100, 210, 255)

        mute_label = "Mở tiếng" if is_muted else "Âm thanh"
        mute_bg = (55, 30, 45) if is_muted else (40, 35, 55)
        mute_text_col = (255, 160, 200) if is_muted else (210, 180, 255)

        buttons_def = [
            ("CALIBRATE", 6,   112, calib_label,       calib_bg,      calib_txt),
            ("POMODORO",  116, 218, "[P] Pomodoro",    (25, 55, 45),  (110, 240, 175)),
            ("STATS",     222, 324, "[H] Thống kê",    (45, 35, 65),  (210, 180, 255)),
            ("MUTE",      328, 428, f"[M] {mute_label}", mute_bg,     mute_text_col),
            ("RESET",     432, 518, "[R] Đặt lại",     (50, 42, 25),  (255, 205, 90)),
            ("QUIT",      522, 610, "[Q] Thoát",       (65, 25, 35),  (255, 130, 130))
        ]

        for (btn_id, lx1, lx2, label, bg_color, text_color) in buttons_def:
            # Tọa độ tuyệt đối trên cửa sổ
            abs_x1 = dock_x1 + lx1
            abs_x2 = dock_x1 + lx2
            self.buttons[btn_id] = (abs_x1, dock_y1, abs_x2, dock_y2)

            # Vẽ nút bo góc phong cách pill
            d_btn.rounded_rectangle([lx1, 3, lx2, dock_h - 4], radius=6, fill=bg_color, outline=(80, 95, 120), width=1)
            # Căn giữa văn bản trong nút
            font = self.get_font(11)
            d_btn.text((lx1 + 8, 8), label, font=font, fill=text_color)

        self.cached_button_strips[(is_muted, is_rec)] = cv2.cvtColor(np.array(strip_pil), cv2.COLOR_RGB2BGR)
        if not is_rec:
            self.cached_button_strips[is_muted] = self.cached_button_strips[(is_muted, is_rec)]

    def get_clicked_button(self, x, y):
        for name, (bx1, by1, bx2, by2) in self.buttons.items():
            if bx1 <= x <= bx2 and by1 <= y <= by2:
                return name
        return None

    def draw_hud(self, frame, result, session_duration_sec, pomodoro_info=None, is_muted=False, alert_msg="", show_stats=False, stats_data=None):
        h, w, _ = frame.shape
        now = time.monotonic()

        status = result.get("status", "FOCUSED")
        score = result.get("focus_score", 100)
        is_rec = result.get("is_recording_zone", False)
        is_zone_set = result.get("is_study_zone_set", False)
        zone = result.get("study_zone", {})
        ear_thresh = result.get("ear_threshold", 0.18)

        # Cập nhật dữ liệu Sparkline xu hướng tập trung
        if now - self.last_history_sample > 0.5:
            self.score_history.append(score)
            if len(self.score_history) > 35:
                self.score_history.pop(0)
            self.last_history_sample = now

        pomo_state = "WORK"
        pomo_time = 0
        if pomodoro_info:
            pomo_state, pomo_time = pomodoro_info

        # Bảng màu chủ đạo Theme Màu Sắc Công Nghệ
        if pomo_state == "BREAK":
            theme_color = (236, 72, 153)    # Sakura Pink
            theme_rgb = (250, 110, 180)
            status_badge_bg = (70, 20, 50)
        elif status == "FOCUSED":
            theme_color = (34, 197, 94)     # Emerald Green
            theme_rgb = (34, 197, 94)
            status_badge_bg = (18, 55, 32)
        elif status == "CALIBRATING":
            theme_color = (0, 210, 255)     # Cyan
            theme_rgb = (0, 210, 255)
            status_badge_bg = (20, 50, 75)
        elif status == "WARNING":
            theme_color = (245, 158, 11)    # Amber
            theme_rgb = (245, 158, 11)
            status_badge_bg = (60, 42, 15)
        else:
            theme_color = (239, 68, 68)     # Crimson Alert
            theme_rgb = (239, 68, 68)
            status_badge_bg = (75, 20, 25)

        # ---------------- ĐỊNH VỊ CÁC PANEL THÔNG MINH ----------------
        text_state = (status, result.get("label"), is_rec, is_muted, pomo_state, int(pomo_time), alert_msg)
        should_refresh_text = (
            self.cached_header is None
            or text_state != self.last_text_state
            or now - self.last_text_refresh_time >= 0.2
        )
        if should_refresh_text:
            self.last_text_refresh_time = now
            self.last_text_state = text_state

        # 1. Header nổi góc trên bên trái: x:[12..445], y:[8..52] (433 x 44)
        hx1, hy1, hx2, hy2 = 12, 8, 445, 52

        # 2. Thẻ Focus Score góc trên bên phải: x:[455..628], y:[8..118] (173 x 110)
        sx1, sy1, sx2, sy2 = 455, 8, 628, 118

        # 3. Thẻ Tư Thế Học góc dưới bên trái: x:[12..250], y:[380..436] (238 x 56)
        bx1, by1, bx2, by2 = 12, 380, 250, 436

        # Lấy các vùng cắt (ROIs)
        head_roi = frame[hy1:hy2, hx1:hx2]
        sc_roi   = frame[sy1:sy2, sx1:sx2]
        pose_roi = frame[by1:by2, bx1:bx2]

        if not should_refresh_text and self.cached_header is not None:
            # Tái sử dụng bảng từ nhịp trước (tốn 0.001ms)
            head_roi[:] = self.cached_header
            sc_roi[:]   = self.cached_score_card
            pose_roi[:] = self.cached_pose_card
        else:
            # ================= 1. HEADER NỔI (STATUS PILL HEADER) =================
            cv2.addWeighted(head_roi, 0.28, self.overlay_header, 0.72, 0, head_roi)
            cv2.rectangle(frame, (hx1, hy1), (hx2, hy2), (55, 65, 80), 1)

            h_pil = Image.fromarray(cv2.cvtColor(head_roi, cv2.COLOR_BGR2RGB))
            d_h = ImageDraw.Draw(h_pil)

            if pomo_state == "BREAK":
                p_min, p_sec = divmod(pomo_time, 60)
                status_title = f"● NGHỈ GIẢI LAO [{p_min:02d}:{p_sec:02d}]"
                sub_detail = "Thư giãn, nghe nhạc hoặc lướt điện thoại thoải mái!"
            else:
                lbl = result.get("label", "ĐANG TẬP TRUNG")
                rsn = result.get("reason", "Đang tại bàn học")
                status_title = f"{lbl}" if lbl.startswith("●") else f"● {lbl}"
                sub_detail = rsn

            # Vẽ Badge trạng thái
            d_h.rounded_rectangle([6, 6, 215, 26], radius=4, fill=status_badge_bg, outline=theme_rgb, width=1)
            d_h.text((12, 8), status_title, font=self.get_font(12), fill=theme_rgb)

            # Trạng thái âm thanh nhỏ góc phải của header
            sound_txt = "● Loa Bật" if not is_muted else "○ Đã Tắt Loa"
            sound_col = (110, 240, 160) if not is_muted else (170, 170, 180)
            d_h.text((433 - 78, 9), sound_txt, font=self.get_font(11), fill=sound_col)

            # Dòng mô tả chi tiết lý do (rất sạch và thoáng mắt)
            d_h.text((10, 28), sub_detail, font=self.get_font(11), fill=(225, 230, 240))
            head_roi[:] = cv2.cvtColor(np.array(h_pil), cv2.COLOR_RGB2BGR)
            self.cached_header = head_roi.copy()

            # ================= 2. THẺ FOCUS SCORE & POMODORO (TOP-RIGHT) =================
            cv2.addWeighted(sc_roi, 0.28, self.overlay_score, 0.72, 0, sc_roi)
            cv2.rectangle(frame, (sx1, sy1), (sx2, sy2), (55, 65, 80), 1)

            mins, secs = divmod(int(session_duration_sec), 60)
            p_min, p_sec = divmod(pomo_time, 60)
            pomo_badge_txt = f"POMO: {p_min:02d}:{p_sec:02d} [{'HỌC' if pomo_state=='WORK' else 'NGHỈ'}]"
            pomo_badge_bg = (20, 50, 35) if pomo_state == "WORK" else (55, 25, 45)
            pomo_badge_col = (100, 255, 180) if pomo_state == "WORK" else (255, 150, 220)

            sc_pil = Image.fromarray(cv2.cvtColor(sc_roi, cv2.COLOR_BGR2RGB))
            d_sc = ImageDraw.Draw(sc_pil)

            d_sc.text((10, 6), "ĐỘ TẬP TRUNG", font=self.get_font(11), fill=(160, 175, 195))
            d_sc.text((10, 20), f"{score:.0f}%", font=self.get_font(26), fill=theme_rgb)

            # Vẽ biểu đồ Sparkline mini xu hướng tập trung mượt mà
            sp_x1 = 92
            sp_y1 = 18
            sp_w = 70
            sp_h = 32
            d_sc.rounded_rectangle([sp_x1, sp_y1, sp_x1 + sp_w, sp_y1 + sp_h], radius=4, fill=(12, 16, 22), outline=(45, 55, 70), width=1)
            if len(self.score_history) >= 2:
                pts = []
                n = len(self.score_history)
                for i, val in enumerate(self.score_history):
                    px = sp_x1 + int((i / max(1, n - 1)) * sp_w)
                    norm_val = max(0.0, min(100.0, float(val))) / 100.0
                    py = sp_y1 + sp_h - int(norm_val * (sp_h - 4)) - 2
                    pts.append((px, py))
                d_sc.line(pts, fill=theme_rgb, width=2)

            # Pomodoro badge bo tròn
            d_sc.rounded_rectangle([8, 58, 164, 80], radius=4, fill=pomo_badge_bg, outline=pomo_badge_col, width=1)
            d_sc.text((12, 62), pomo_badge_txt, font=self.get_font(11), fill=pomo_badge_col)

            # Tổng thời gian phiên học
            d_sc.text((10, 88), f"Thời gian: {mins:02d}p {secs:02d}s", font=self.get_font(11), fill=(150, 160, 175))
            sc_roi[:] = cv2.cvtColor(np.array(sc_pil), cv2.COLOR_RGB2BGR)
            self.cached_score_card = sc_roi.copy()

            # ================= 3. THẺ TƯ THẾ HỌC GỌN GÀNG (BOTTOM-LEFT) =================
            cv2.addWeighted(pose_roi, 0.28, self.overlay_pose, 0.72, 0, pose_roi)
            cv2.rectangle(frame, (bx1, by1), (bx2, by2), (55, 65, 80), 1)

            yaw_val = result.get("yaw", 0.0)
            ear_val = result.get("ear", 0.25)
            perclos_val = result.get("perclos", 0.0)
            is_reading = result.get("is_reading_desk", False)
            yaw_min_val = zone.get("yaw_min", -60.0)
            yaw_max_val = zone.get("yaw_max", 60.0)

            if yaw_min_val <= -170.0:
                limit_str = f"Trái tự do | Phải <= {yaw_max_val:+.0f}°"
            elif yaw_max_val >= 170.0:
                limit_str = f"Trái >= {yaw_min_val:+.0f}° | Phải tự do"
            else:
                limit_str = f"[{yaw_min_val:+.0f}°, {yaw_max_val:+.0f}°]"

            face_dot = "●" if result.get("status") != "AWAY" else "○"
            if is_reading:
                face_state = "Đọc/Viết bài"
            else:
                face_state = "Tại bàn" if result.get("status") != "AWAY" else "Rời bàn"

            pose_pil = Image.fromarray(cv2.cvtColor(pose_roi, cv2.COLOR_BGR2RGB))
            d_p = ImageDraw.Draw(pose_pil)
            d_p.text((8, 6), f"{face_dot} {face_state}  |  Góc quay: {yaw_val:+.0f}°", font=self.get_font(11), fill=(210, 230, 255))
            d_p.text((8, 24), f"Mắt: {ear_val:.2f} (Ngưỡng: {ear_thresh:.2f})  |  P80: {int(perclos_val*100)}%", font=self.get_font(11), fill=(185, 205, 225))
            d_p.text((8, 40), f"Vùng cá nhân: {limit_str}", font=self.get_font(10), fill=(140, 160, 185))

            pose_roi[:] = cv2.cvtColor(np.array(pose_pil), cv2.COLOR_RGB2BGR)
            self.cached_pose_card = pose_roi.copy()

        # ================= 3.5. BANNER XÁC ĐỊNH KHUNG HỌC TẬP (TOP-MODULAR HUD) =================
        if is_rec:
            cal_x1, cal_y1, cal_x2, cal_y2 = 12, 58, 445, 122
            cal_roi = frame[cal_y1:cal_y2, cal_x1:cal_x2]
            cv2.addWeighted(cal_roi, 0.20, self.overlay_calib, 0.80, 0, cal_roi)
            cv2.rectangle(frame, (cal_x1, cal_y1), (cal_x2, cal_y2), (0, 210, 255), 1)

            cal_time_left = result.get("record_time_left", 0.0)
            cal_duration = max(1.0, float(result.get("record_duration", 60.0)))
            cal_progress = max(0.0, min(1.0, (cal_duration - cal_time_left) / cal_duration))

            cal_pil = Image.fromarray(cv2.cvtColor(cal_roi, cv2.COLOR_BGR2RGB))
            d_cal = ImageDraw.Draw(cal_pil)

            # Tiêu đề & phím tắt hoàn tất nhanh
            d_cal.text((8, 4), f"🎯 XÁC ĐỊNH KHUNG HỌC TẬP ({cal_time_left:.1f}s)", font=self.get_font(12), fill=(0, 225, 255))
            d_cal.text((310, 6), "[C] Hoàn tất ngay", font=self.get_font(10), fill=(100, 210, 255))

            # Thanh tiến độ thời gian (Progress Bar)
            bar_w = 417
            d_cal.rounded_rectangle([8, 22, 8 + bar_w, 28], radius=3, fill=(35, 45, 60))
            fill_w = int(bar_w * cal_progress)
            if fill_w > 0:
                d_cal.rounded_rectangle([8, 22, 8 + fill_w, 28], radius=3, fill=(0, 220, 255))

            # Hướng dẫn động theo từng giai đoạn
            if cal_time_left > 6.5:
                guide_txt = "1️⃣ Nhìn thẳng tự nhiên vào màn hình / camera"
                guide_col = (255, 235, 120)
            elif cal_time_left > 3.0:
                guide_txt = "2️⃣ Quay nhẹ sang 2 bên mép bàn học của bạn"
                guide_col = (100, 240, 255)
            else:
                guide_txt = "3️⃣ Cúi đầu nhìn vở như lúc đang viết bài"
                guide_col = (120, 255, 180)

            d_cal.text((8, 32), guide_txt, font=self.get_font(11), fill=guide_col)

            # Đọc góc thời gian thực
            cur_yaw = result.get("yaw", 0.0)
            cur_pitch = result.get("pitch", 0.0)
            cur_ear = result.get("ear", 0.22)
            d_cal.text((8, 47), f"Góc quay: {cur_yaw:+.0f}°  |  Cúi: {cur_pitch:+.0f}°  |  Mắt: {cur_ear:.2f}", font=self.get_font(10), fill=(185, 205, 235))

            cal_roi[:] = cv2.cvtColor(np.array(cal_pil), cv2.COLOR_RGB2BGR)

        # ================= 4. BLIT DOCK NÚT BẤM (0.001 MS - ZERO CPU) =================
        dock_y1 = h - 44
        dock_y2 = h - 10
        dock_x1 = 12
        dock_cached = self.cached_button_strips.get((is_muted, is_rec))
        if dock_cached is None:
            dock_cached = self.cached_button_strips.get(is_muted)
        if dock_cached is not None:
            frame[dock_y1:dock_y2, dock_x1:dock_x1 + 616] = dock_cached

        # ================= 5. BANNER CẢNH BÁO TỨC THÌ (FLASH TOAST) =================
        if alert_msg:
            box_w = 460
            box_h = 56
            mx1 = w // 2 - box_w // 2
            my1 = h // 2 - box_h // 2
            mx2 = mx1 + box_w
            my2 = my1 + box_h
            msg_roi = frame[my1:my2, mx1:mx2]
            msg_pil = Image.fromarray(cv2.cvtColor(msg_roi, cv2.COLOR_BGR2RGB))
            d_msg = ImageDraw.Draw(msg_pil)
            d_msg.rounded_rectangle([0, 0, box_w, box_h], radius=8, fill=(20, 95, 45), outline=(100, 255, 180), width=2)
            d_msg.text((22, 18), alert_msg, font=self.get_font(13), fill=(255, 255, 255))
            msg_roi[:] = cv2.cvtColor(np.array(msg_pil), cv2.COLOR_RGB2BGR)

        elif show_stats and stats_data:
            box_w = 540
            box_h = 246
            cx1 = w // 2 - box_w // 2
            cy1 = h // 2 - box_h // 2
            cx2 = cx1 + box_w
            cy2 = cy1 + box_h

            st_roi = frame[cy1:cy2, cx1:cx2]
            cv2.rectangle(frame, (cx1, cy1), (cx2, cy2), (180, 130, 255), 2)
            st_pil = Image.fromarray(cv2.cvtColor(st_roi, cv2.COLOR_BGR2RGB))
            d_st = ImageDraw.Draw(st_pil)
            d_st.rounded_rectangle([0, 0, box_w, box_h], radius=8, fill=(16, 20, 32))

            # Header
            d_st.text((22, 12), "📊 BẢNG THỐNG KÊ HỌC TẬP & NĂNG SUẤT", font=self.get_font(15), fill=(210, 180, 255))
            d_st.line([(22, 36), (box_w - 22, 36)], fill=(60, 70, 95), width=1)

            st_today_mins = stats_data.get("today_minutes", 0)
            st_today_score = stats_data.get("today_avg_score", 100)
            st_streak = stats_data.get("current_streak", 0)
            st_best = stats_data.get("best_streak", 0)
            st_pomo = stats_data.get("total_pomodoro", 0)
            st_goal = stats_data.get("today_goal_pct", 0)
            st_tot_mins = stats_data.get("total_minutes", 0)
            st_tot_sess = stats_data.get("total_sessions", 0)

            d_st.text((22, 46), f"🔥 Chuỗi ngày học liên tục: {st_streak} ngày  (Kỷ lục: {st_best} ngày)", font=self.get_font(12), fill=(255, 180, 60))
            d_st.text((22, 70), f"⏱️ Hôm nay đã học: {st_today_mins} phút  |  Tiến độ ngày: {st_goal}% (Mục tiêu 120p)", font=self.get_font(12), fill=(100, 240, 175))
            d_st.text((22, 94), f"🎯 Độ tập trung trung bình hôm nay: {st_today_score:.0f}%", font=self.get_font(12), fill=(100, 210, 255))
            d_st.text((22, 118), f"🍅 Tổng chu kỳ Pomodoro hoàn thành: {st_pomo} chu kỳ", font=self.get_font(12), fill=(255, 140, 180))

            d_st.line([(22, 144), (box_w - 22, 144)], fill=(45, 55, 75), width=1)
            d_st.text((22, 154), f"🏆 Lịch sử tích lũy: {st_tot_sess} phiên học  |  Tổng thời lượng: {round(st_tot_mins/60.0, 1)} giờ", font=self.get_font(11), fill=(180, 195, 215))
            d_st.text((22, 176), f"🛡️ Đã ngăn ngừa: {stats_data.get('total_phone',0)} lần điện thoại, {stats_data.get('total_distraction',0)} lần quay mặt", font=self.get_font(11), fill=(160, 175, 195))

            # Nút đóng
            d_st.rounded_rectangle([22, box_h - 36, box_w - 22, box_h - 10], radius=4, fill=(35, 45, 65))
            d_st.text((box_w // 2 - 120, box_h - 29), "Bấm [H] hoặc [Click bất kỳ] để đóng bảng", font=self.get_font(11), fill=(200, 220, 255))

            st_roi[:] = cv2.cvtColor(np.array(st_pil), cv2.COLOR_RGB2BGR)

        # ================= 6. VIỀN ĐỎ BÁO ĐỘNG (NẾU ĐANG CÓ LỖI) =================
        if result.get("alert", False) and pomo_state != "BREAK":
            cv2.rectangle(frame, (0, 0), (w, h), (0, 0, 235), 6)

        return frame
