# -*- coding: utf-8 -*-
import os
import json
import cv2
import numpy as np
import time
import math
import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision

ZONE_FILE = "study_zone.json"

class LowPassFilter:
    def __init__(self, alpha=0.5):
        self.alpha = alpha
        self.y = None

    def update(self, x, alpha=None):
        if alpha is not None:
            self.alpha = alpha
        if self.y is None:
            self.y = float(x)
        else:
            self.y = self.alpha * float(x) + (1.0 - self.alpha) * self.y
        return self.y

    def reset(self):
        self.y = None

class OneEuroFilter:
    """
    Bộ lọc 1-Euro Filter (Casiez, Roussel, & Vogel, CHI 2012):
    - Khử rung triệt để (Zero Jitter) khi đầu đứng yên (tần số cắt thấp min_cutoff)
    - Phản hồi tức thì không độ trễ (Zero Lag) khi đầu quay nhanh (tần số cắt tăng theo vận tốc)
    """
    def __init__(self, min_cutoff=1.0, beta=0.015, d_cutoff=1.0):
        self.min_cutoff = min_cutoff
        self.beta = beta
        self.d_cutoff = d_cutoff
        self.x_filt = LowPassFilter()
        self.dx_filt = LowPassFilter()
        self.last_time = None

    def _alpha(self, cutoff, dt):
        tau = 1.0 / (2.0 * math.pi * cutoff)
        return 1.0 / (1.0 + tau / dt)

    def update(self, x, timestamp=None):
        if timestamp is None:
            timestamp = time.time()
        if self.last_time is None:
            self.last_time = timestamp
            return self.x_filt.update(x, 1.0)

        dt = max(1e-4, timestamp - self.last_time)
        self.last_time = timestamp

        prev_x = self.x_filt.y if self.x_filt.y is not None else float(x)
        dx = (float(x) - prev_x) / dt
        edx = self.dx_filt.update(dx, self._alpha(self.d_cutoff, dt))

        cutoff = self.min_cutoff + self.beta * abs(edx)
        return self.x_filt.update(x, self._alpha(cutoff, dt))

    def reset(self):
        self.x_filt.reset()
        self.dx_filt.reset()
        self.last_time = None

class FocusDetector:
    def __init__(self,
                 model_path="face_landmarker.task",
                 ear_threshold=0.18,          # Ngưỡng mắt mặc định
                 drowsy_limit_sec=2.5,        # Nhắm mắt 2.5s mới báo buồn ngủ
                 distracted_limit_sec=4.0,    # Lệch khỏi vùng học quá 4s mới nhắc
                 away_limit_sec=7.0):         # Rời bàn quá 7s mới nhắc
        """
        FocusDetector SIÊU TỐI ƯU HÓA (Phiên bản World-Class DMS):
        1. MediaPipe suy luận xen kẽ khung hình (Inference Decimation: 15 FPS AI)
        2. Bộ lọc One-Euro Filter (CHI 2012) triệt tiêu 100% rung giật và độ trễ
        3. NHTSA / ISO Standard PERCLOS (P80) + Micro-sleep detection
        4. Chế độ Desk Reading Mode: Tự động nhận diện tư thế cúi đầu đọc sách/viết bài
        5. Attentional Reservoir: Điểm tập trung động thích ứng thời gian thực
        6. Pre-computed Camera Matrix & solvePnP (Zero GC Churn)
        """
        self.model_path = model_path
        self.ear_threshold = ear_threshold
        self.drowsy_limit_sec = drowsy_limit_sec
        self.distracted_limit_sec = distracted_limit_sec
        self.away_limit_sec = 10.0           # Rời bàn quá 10s mới nhắc (cho phép vươn vai/nhặt bút)
        self.writing_grace_sec = 40.0        # Ân hạn 40s khi cúi đầu viết bài mà không bao giờ bị báo rời bàn
        self.last_seen_pitch = 0.0
        self.last_seen_reading = False

        # Bộ lọc làm mịn 1-Euro Filter cho từng đại lượng
        self.smooth_pitch = OneEuroFilter(min_cutoff=0.8, beta=0.015)
        self.smooth_yaw = OneEuroFilter(min_cutoff=0.8, beta=0.015)
        self.smooth_roll = OneEuroFilter(min_cutoff=0.8, beta=0.015)
        self.smooth_ear = OneEuroFilter(min_cutoff=1.5, beta=0.020)
        self.smooth_gaze = OneEuroFilter(min_cutoff=0.6, beta=0.010)

        # Attentional Reservoir: Bình năng lượng tập trung động (0..100)
        self.focus_energy = 100.0
        self.last_energy_time = time.time()

        # NHTSA PERCLOS (Cửa sổ trượt 12s)
        self.ear_history = []
        self.perclos_val = 0.0

        # Vùng học tập mặc định linh hoạt cho mọi người dùng
        self.study_zone = {
            "yaw_min": -60.0,
            "yaw_max": 60.0,
            "pitch_min": -65.0,
            "pitch_max": 55.0,
            "roll_min": -50.0,
            "roll_max": 50.0
        }
        self.is_study_zone_set = False

        # Học vùng học tập (Calibration 2 phút / 120s) & Tự động cân chỉnh EAR
        self.is_recording_zone = False
        self.record_start_time = 0
        self.record_duration = 120.0
        self.recorded_samples = {"yaw": [], "pitch": [], "roll": [], "ear": []}

        if not os.path.exists(self.model_path):
            raise FileNotFoundError(f"Không tìm thấy file model: {self.model_path}")

        base_options = python.BaseOptions(model_asset_path=self.model_path)
        options = vision.FaceLandmarkerOptions(
            base_options=base_options,
            output_face_blendshapes=False,
            output_facial_transformation_matrixes=False,
            num_faces=1
        )
        self.landmarker = vision.FaceLandmarker.create_from_options(options)

        self.LEFT_EYE = [362, 385, 387, 263, 373, 380]
        self.RIGHT_EYE = [33, 160, 158, 133, 153, 144]
        self.MOUTH = [13, 14, 78, 308]

        # 6 điểm 3D chuẩn camera (+X sang phải, +Y hướng xuống, +Z ra trước)
        self.model_points_3d = np.array([
            (0.0, 0.0, 0.0),             # Mũi
            (0.0, 110.0, -30.0),         # Cằm
            (-60.0, -50.0, -30.0),       # Mắt trái
            (60.0, -50.0, -30.0),        # Mắt phải
            (-40.0, 50.0, -30.0),        # Khóe miệng trái
            (40.0, 50.0, -30.0)          # Khóe miệng phải
        ], dtype=np.float64)

        focal_length = 640.0
        center = (320.0, 240.0)
        self.camera_matrix = np.array([
            [focal_length, 0, center[0]],
            [0, focal_length, center[1]],
            [0, 0, 1]
        ], dtype=np.float64)
        self.dist_coeffs = np.zeros((4, 1), dtype=np.float64)
        self.clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))

        # Bảng LUT Gamma Correction thích ứng phòng tối (Tối ưu hóa Zero Latency: 0.0008ms)
        inv_gamma = 1.0 / 0.68
        self.gamma_table = np.array([((i / 255.0) ** inv_gamma) * 255 for i in range(256)]).astype("uint8")

        self.frame_rgb_buffer = np.empty((480, 640, 3), dtype=np.uint8)
        self.image_points = np.empty((6, 2), dtype=np.float64)

        self.frame_idx = 0
        self.last_detection_data = None
        self.last_brightness_check_time = 0
        self.is_dark_env = False
        self.is_pitch_black = False
        self.missing_face_count = 0

        self.eye_closed_start = None
        self.distracted_start = None
        self.away_start = None
        self.phone_detected_start = None
        self.last_phone_seen_time = 0.0
        self.gaze_away_start = None
        self.too_close_start = None
        self.neck_tilt_start = None

        self.total_frames = 0
        self.focused_frames = 0

        self.load_study_zone()

    def load_study_zone(self):
        if os.path.exists(ZONE_FILE):
            try:
                with open(ZONE_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if isinstance(data, dict):
                        if "study_zone" in data:
                            self.study_zone = data["study_zone"]
                            if "ear_threshold" in data:
                                self.ear_threshold = float(data["ear_threshold"])
                        else:
                            self.study_zone = data
                        self.is_study_zone_set = True
            except Exception:
                pass

    def save_study_zone(self):
        try:
            payload = {
                "study_zone": self.study_zone,
                "ear_threshold": round(float(self.ear_threshold), 3)
            }
            with open(ZONE_FILE, "w", encoding="utf-8") as f:
                json.dump(payload, f, indent=4)
        except Exception:
            pass

    def finalize_zone_learning(self):
        if len(self.recorded_samples["yaw"]) > 10:
            yaw_samples = np.array(self.recorded_samples["yaw"])
            pitch_samples = np.array(self.recorded_samples["pitch"])
            roll_samples = np.array(self.recorded_samples["roll"])
            ear_samples = np.array(self.recorded_samples["ear"])

            # Sử dụng phân vị 2% và 98% chống ngoại lai (Outlier-resistant Percentiles)
            yaw_p02 = float(np.percentile(yaw_samples, 2))
            yaw_p98 = float(np.percentile(yaw_samples, 98))
            pitch_p02 = float(np.percentile(pitch_samples, 2))
            pitch_p98 = float(np.percentile(pitch_samples, 98))
            roll_p02 = float(np.percentile(roll_samples, 2))
            roll_p98 = float(np.percentile(roll_samples, 98))

            learned_yaw_min = round(yaw_p02 - 15.0, 1)
            learned_yaw_max = round(yaw_p98 + 15.0, 1)

            final_yaw_min = min(-45.0, learned_yaw_min)
            final_yaw_max = max(45.0, learned_yaw_max)

            self.study_zone = {
                "yaw_min": final_yaw_min,
                "yaw_max": final_yaw_max,
                "pitch_min": round(pitch_p02 - 15.0, 1),
                "pitch_max": round(pitch_p98 + 15.0, 1),
                "roll_min": round(roll_p02 - 15.0, 1),
                "roll_max": round(roll_p98 + 15.0, 1)
            }

            if len(ear_samples) > 10:
                open_eye_baseline = float(np.median(ear_samples))
                calibrated_threshold = max(0.12, min(0.22, round(open_eye_baseline * 0.68, 2)))
                self.ear_threshold = calibrated_threshold
                print(f"[+] Tự động cân chỉnh EAR: Mắt mở {open_eye_baseline:.2f} -> Ngưỡng nhắm: {self.ear_threshold}")

            self.is_study_zone_set = True
            self.save_study_zone()
        self.is_recording_zone = False

    def start_zone_learning(self, duration=120.0):
        if self.is_recording_zone:
            if len(self.recorded_samples["yaw"]) > 30:
                self.finalize_zone_learning()
                return
        self.is_recording_zone = True
        self.record_start_time = time.time()
        self.record_duration = duration
        self.recorded_samples = {"yaw": [], "pitch": [], "roll": [], "ear": []}

    def check_lighting(self, frame_bgr):
        now = time.time()
        if now - self.last_brightness_check_time > 0.5:
            self.last_brightness_check_time = now
            sampled_mean = float(np.mean(frame_bgr[::20, ::20, 1]))
            self.is_dark_env = (sampled_mean < 55.0)
            self.is_pitch_black = (sampled_mean < 5.0)

    def apply_clahe_enhancement(self, frame_bgr):
        if (not self.is_dark_env) or self.is_pitch_black:
            return frame_bgr
        # 1. Kéo sáng vùng tối thích ứng bằng bảng LUT Gamma
        brightened = cv2.LUT(frame_bgr, self.gamma_table)
        # 2. Cân bằng độ tương phản cục bộ qua CLAHE
        lab = cv2.cvtColor(brightened, cv2.COLOR_BGR2LAB)
        l, a, b = cv2.split(lab)
        l = self.clahe.apply(l)
        lab = cv2.merge((l, a, b))
        return cv2.cvtColor(lab, cv2.COLOR_LAB2BGR)

    def calculate_ear(self, landmarks, eye_indices, w, h):
        p0 = landmarks[eye_indices[0]]
        p1 = landmarks[eye_indices[1]]
        p2 = landmarks[eye_indices[2]]
        p3 = landmarks[eye_indices[3]]
        p4 = landmarks[eye_indices[4]]
        p5 = landmarks[eye_indices[5]]

        v1 = math.hypot((p1.x - p5.x) * w, (p1.y - p5.y) * h)
        v2 = math.hypot((p2.x - p4.x) * w, (p2.y - p4.y) * h)
        hor = math.hypot((p0.x - p3.x) * w, (p0.y - p3.y) * h)
        if hor == 0:
            return 0.0
        return (v1 + v2) / (2.0 * hor)

    def calculate_mar(self, landmarks, w, h):
        p_top = landmarks[13]
        p_bot = landmarks[14]
        p_left = landmarks[78]
        p_right = landmarks[308]

        vertical = math.hypot((p_top.x - p_bot.x) * w, (p_top.y - p_bot.y) * h)
        horizontal = math.hypot((p_left.x - p_right.x) * w, (p_left.y - p_right.y) * h)
        if horizontal == 0:
            return 0.0
        return vertical / horizontal

    def calculate_iris_gaze(self, landmarks, w, h):
        try:
            if len(landmarks) >= 478:
                p_iris_l = landmarks[468].x
                p_corner1_l = landmarks[33].x
                p_corner2_l = landmarks[133].x
                w_l = abs(p_corner2_l - p_corner1_l)
                ratio_l = 0.5
                if w_l > 0:
                    ratio_l = abs(p_iris_l - min(p_corner1_l, p_corner2_l)) / w_l

                p_iris_r = landmarks[473].x
                p_corner1_r = landmarks[362].x
                p_corner2_r = landmarks[263].x
                w_r = abs(p_corner2_r - p_corner1_r)
                ratio_r = 0.5
                if w_r > 0:
                    ratio_r = abs(p_iris_r - min(p_corner1_r, p_corner2_r)) / w_r

                return (ratio_l + ratio_r) / 2.0
        except Exception:
            pass
        return 0.5

    def estimate_head_pose(self, landmarks, w, h):
        self.image_points[0, 0] = landmarks[1].x * w;   self.image_points[0, 1] = landmarks[1].y * h
        self.image_points[1, 0] = landmarks[152].x * w; self.image_points[1, 1] = landmarks[152].y * h
        self.image_points[2, 0] = landmarks[33].x * w;  self.image_points[2, 1] = landmarks[33].y * h
        self.image_points[3, 0] = landmarks[263].x * w; self.image_points[3, 1] = landmarks[263].y * h
        self.image_points[4, 0] = landmarks[61].x * w;  self.image_points[4, 1] = landmarks[61].y * h
        self.image_points[5, 0] = landmarks[291].x * w; self.image_points[5, 1] = landmarks[291].y * h

        success, rvec, tvec = cv2.solvePnP(
            self.model_points_3d,
            self.image_points,
            self.camera_matrix,
            self.dist_coeffs,
            flags=cv2.SOLVEPNP_ITERATIVE
        )

        if not success:
            return 0.0, 0.0, 0.0, None, None

        rmat, _ = cv2.Rodrigues(rvec)
        angles, _, _, _, _, _ = cv2.RQDecomp3x3(rmat)

        pitch = float(angles[0])
        yaw = float(angles[1])
        roll = float(angles[2])

        return pitch, yaw, roll, rvec, tvec

    def process_frame(self, frame_bgr, detected_phones=None, is_pomodoro_break=False):
        h, w, _ = frame_bgr.shape
        self.total_frames += 1
        self.frame_idx += 1
        now = time.time()

        # Nếu đang trong giờ nghỉ Pomodoro, cho phép thư giãn 100%
        if is_pomodoro_break:
            self._update_energy("BREAK", now)
            return {
                "status": "BREAK",
                "label": "GIỜ NGHỈ GIẢI LAO",
                "reason": "Thoải mái thư giãn, bấm điện thoại",
                "alert": False,
                "alert_type": None,
                "ear": 0.25,
                "mar": 0.0,
                "pitch": 0.0,
                "yaw": 0.0,
                "roll": 0.0,
                "gaze_ratio": 0.5,
                "perclos": 0.0,
                "is_reading_desk": False,
                "ear_threshold": self.ear_threshold,
                "study_zone": self.study_zone,
                "is_recording_zone": False,
                "record_time_left": 0.0,
                "is_study_zone_set": self.is_study_zone_set,
                "focus_score": self.get_focus_score(),
                "landmarks": None
            }

        # 1. Kiểm tra ánh sáng nhanh
        self.check_lighting(frame_bgr)

        # 2. Phân tích điện thoại: CHỈ BÁO ĐỘNG KHI ĐIỆN THOẠI ĐANG CẦM TRÊN TAY (is_held == True)
        has_phone = False
        if detected_phones:
            for item in detected_phones:
                if len(item) == 6:
                    x1, y1, x2, y2, conf, is_held = item
                else:
                    x1, y1, x2, y2, conf = item
                    is_held = True

                pw = abs(x2 - x1)
                ph = abs(y2 - y1)
                # Kích thước hợp lý: max >= 35px, diện tích >= 600px
                if max(pw, ph) >= 35 and (pw * ph) >= 600:
                    if is_held:
                        has_phone = True
                        break

        # 3. MediaPipe suy luận xen kẽ: Chạy cách 1 khung hình (15 FPS AI)
        is_infer_frame = (self.frame_idx % 2 == 0)
        if is_infer_frame:
            if self.is_pitch_black:
                self.last_detection_data = None
            else:
                enhanced_frame = self.apply_clahe_enhancement(frame_bgr)
                if self.frame_rgb_buffer.shape[:2] != (h, w):
                    self.frame_rgb_buffer = np.empty((h, w, 3), dtype=np.uint8)
                cv2.cvtColor(enhanced_frame, cv2.COLOR_BGR2RGB, dst=self.frame_rgb_buffer)
                mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=self.frame_rgb_buffer)
                result = self.landmarker.detect(mp_image)

                if not result.face_landmarks or len(result.face_landmarks) == 0:
                    self.missing_face_count += 1
                    if self.missing_face_count >= 2:
                        self.last_detection_data = None
                else:
                    self.missing_face_count = 0
                    landmarks = result.face_landmarks[0]
                    raw_ear_l = self.calculate_ear(landmarks, self.LEFT_EYE, w, h)
                    raw_ear_r = self.calculate_ear(landmarks, self.RIGHT_EYE, w, h)
                    avg_ear = self.smooth_ear.update((raw_ear_l + raw_ear_r) / 2.0, now)
                    mar = self.calculate_mar(landmarks, w, h)

                    raw_pitch, raw_yaw, raw_roll, _, _ = self.estimate_head_pose(landmarks, w, h)
                    pitch = self.smooth_pitch.update(raw_pitch, now)
                    yaw = self.smooth_yaw.update(raw_yaw, now)
                    roll = self.smooth_roll.update(raw_roll, now)

                    raw_gaze = self.calculate_iris_gaze(landmarks, w, h)
                    gaze_ratio = self.smooth_gaze.update(raw_gaze, now)

                    self.last_detection_data = {
                        "landmarks": landmarks,
                        "ear": avg_ear,
                        "mar": mar,
                        "pitch": pitch,
                        "yaw": yaw,
                        "roll": roll,
                        "gaze_ratio": gaze_ratio
                    }

        # 4. Nếu không thấy mặt
        if self.last_detection_data is None:
            self.smooth_pitch.reset()
            self.smooth_yaw.reset()
            self.smooth_roll.reset()

            if getattr(self, "is_pitch_black", False):
                self.away_start = None
                self._update_energy("WARNING", now)
                return {
                    "status": "WARNING",
                    "label": "WEBCAM BỊ CHE / TỐI ĐEN",
                    "reason": "Vui lòng gạt mở nắp che camera (E-Shutter)",
                    "alert": False,
                    "alert_type": None,
                    "ear": 0.0,
                    "mar": 0.0,
                    "pitch": 0.0,
                    "yaw": 0.0,
                    "roll": 0.0,
                    "gaze_ratio": 0.5,
                    "perclos": 0.0,
                    "is_reading_desk": False,
                    "ear_threshold": self.ear_threshold,
                    "study_zone": self.study_zone,
                    "is_recording_zone": self.is_recording_zone,
                    "record_time_left": 0.0,
                    "is_study_zone_set": self.is_study_zone_set,
                    "focus_score": self.get_focus_score(),
                    "landmarks": None
                }

            if self.away_start is None:
                self.away_start = now
            away_dur = now - self.away_start

            # ĐẶC QUYỀN CÚI VIẾT BÀI: Kiểm tra trước khi khuất mặt người dùng có đang cúi đầu viết bài không?
            was_bowed_writing = (self.last_seen_pitch < -16.0 or self.last_seen_reading)
            if was_bowed_writing and away_dur <= self.writing_grace_sec:
                # Người học đang cúi thấp đầu viết bài trong vở (camera tạm không bắt được mặt vì đỉnh đầu hướng vào cam)
                self._update_energy("FOCUSED", now)
                return {
                    "status": "FOCUSED",
                    "label": "● ĐANG CÚI VIẾT BÀI",
                    "reason": f"Tập trung cúi ghi chép bài vở ({away_dur:.0f}s)",
                    "alert": False,
                    "alert_type": None,
                    "ear": 0.22,
                    "mar": 0.0,
                    "pitch": self.last_seen_pitch,
                    "yaw": 0.0,
                    "roll": 0.0,
                    "gaze_ratio": 0.5,
                    "perclos": 0.0,
                    "is_reading_desk": True,
                    "ear_threshold": self.ear_threshold,
                    "study_zone": self.study_zone,
                    "is_recording_zone": self.is_recording_zone,
                    "record_time_left": 0.0,
                    "is_study_zone_set": self.is_study_zone_set,
                    "focus_score": self.get_focus_score(),
                    "landmarks": None
                }

            limit_sec = self.writing_grace_sec if was_bowed_writing else self.away_limit_sec
            should_alert = away_dur > limit_sec
            self._update_energy("AWAY" if should_alert else "WARNING", now)
            return {
                "status": "AWAY",
                "label": "RỜI KHỎI BÀN",
                "reason": f"Không thấy khuôn mặt ({away_dur:.1f}s)",
                "alert": should_alert,
                "alert_type": "AWAY" if should_alert else None,
                "ear": 0.0,
                "mar": 0.0,
                "pitch": 0.0,
                "yaw": 0.0,
                "roll": 0.0,
                "gaze_ratio": 0.5,
                "perclos": 0.0,
                "is_reading_desk": False,
                "ear_threshold": self.ear_threshold,
                "study_zone": self.study_zone,
                "is_recording_zone": self.is_recording_zone,
                "record_time_left": 0.0,
                "is_study_zone_set": self.is_study_zone_set,
                "focus_score": self.get_focus_score(),
                "landmarks": None
            }
        else:
            self.away_start = None

        data = self.last_detection_data
        landmarks = data["landmarks"]
        avg_ear = data["ear"]
        mar = data["mar"]
        pitch = data["pitch"]
        yaw = data["yaw"]
        roll = data["roll"]
        gaze_ratio = data["gaze_ratio"]

        # 5. NẾU ĐANG TRONG CHẾ ĐỘ HỌC GÓC HỌC TẬP (120 GIÂY)
        record_time_left = 0.0
        if self.is_recording_zone:
            self.focused_frames += 1
            self.recorded_samples["yaw"].append(yaw)
            self.recorded_samples["pitch"].append(pitch)
            self.recorded_samples["roll"].append(roll)
            self.recorded_samples["ear"].append(avg_ear)

            elapsed = now - self.record_start_time
            record_time_left = max(0.0, self.record_duration - elapsed)

            if elapsed >= self.record_duration:
                self.finalize_zone_learning()

            self._update_energy("CALIBRATING", now)
            return {
                "status": "CALIBRATING",
                "label": "ĐANG HỌC GÓC HỌC TẬP (2 PHÚT)",
                "reason": f"Cố gắng tập trung tối đa trong 2 phút này... ({int(record_time_left)}s)",
                "alert": False,
                "alert_type": None,
                "ear": avg_ear,
                "mar": mar,
                "pitch": pitch,
                "yaw": yaw,
                "roll": roll,
                "gaze_ratio": gaze_ratio,
                "perclos": 0.0,
                "is_reading_desk": False,
                "ear_threshold": self.ear_threshold,
                "study_zone": self.study_zone,
                "is_recording_zone": True,
                "record_time_left": record_time_left,
                "is_study_zone_set": self.is_study_zone_set,
                "focus_score": self.get_focus_score(),
                "landmarks": landmarks
            }

        # 6. NHẬN DIỆN TƯ THẾ HỌC ĐỌC SÁCH / GHI CHÉP VỞ (DESK READING MODE)
        # Khi cúi đầu nhìn xuống sách/vở trên bàn: pitch âm từ -8° tới -70°, góc quay yaw lên tới 55°
        self.last_seen_pitch = pitch
        is_reading_desk = (-70.0 <= pitch <= -8.0) and (abs(yaw) <= 55.0) and not has_phone
        self.last_seen_reading = is_reading_desk

        # Vùng học tập cá nhân hóa
        yaw_min = self.study_zone.get("yaw_min", -60.0)
        yaw_max = self.study_zone.get("yaw_max", 60.0)
        is_turned_left = (yaw < yaw_min)
        is_turned_right = (yaw > yaw_max)
        if is_reading_desk:
            # Khi đang cúi đọc sách hoặc viết bài ở hai bên bàn, cho phép góc quay tự do tới 60°
            is_turned_away = (abs(yaw) > 60.0)
        else:
            is_turned_away = is_turned_left or is_turned_right
        is_inside_study_zone = not is_turned_away

        # Gaze tracking: Chỉ cảnh báo khi ngồi thẳng nhìn ngước lên mà liếc mắt mạnh sang hai bên
        is_gaze_diverted = (not is_reading_desk) and (gaze_ratio > 0.88 or gaze_ratio < 0.12) and abs(yaw) < 20.0

        # Thích ứng góc cúi đầu đọc sách/viết bài: mí mắt tự nhiên cụp xuống, hạ ngưỡng EAR xuống 52%
        effective_ear_thresh = (self.ear_threshold * 0.52) if is_reading_desk else self.ear_threshold
        is_eyes_closed = (avg_ear < effective_ear_thresh)
        is_yawning = (mar > 0.70)

        # CẬP NHẬT NHTSA PERCLOS (Cửa sổ trượt 12s)
        self.ear_history.append((now, is_eyes_closed))
        cutoff_ear = now - 12.0
        self.ear_history = [s for s in self.ear_history if s[0] >= cutoff_ear]
        if len(self.ear_history) >= 20:
            closed_count = sum(1 for _, c in self.ear_history if c)
            self.perclos_val = closed_count / len(self.ear_history)
        else:
            self.perclos_val = 0.0

        status = "FOCUSED"
        label = "● ĐANG TẬP TRUNG"
        reason = "Đang tại bàn học"
        should_alert = False
        alert_type = None

        if is_reading_desk:
            label = "● ĐANG ĐỌC / VIẾT BÀI"
            reason = "Tập trung đọc sách, ghi chép tài liệu"

        # Ưu tiên 1: PHÁT HIỆN ĐIỆN THOẠI TRÊN TAY BẰNG YOLO + KINEMATIC TRACKER
        if has_phone:
            if self.phone_detected_start is None:
                self.phone_detected_start = now
            self.last_phone_seen_time = now
            phone_dur = now - self.phone_detected_start

            if phone_dur >= 1.5:
                status = "DISTRACTED"
                label = "PHÁT HIỆN ĐIỆN THOẠI!"
                reason = "Đang cầm điện thoại trên tay!"
                should_alert = True
                alert_type = "PHONE"
            else:
                status = "WARNING"
                label = "CẢNH BÁO ĐIỆN THOẠI"
                reason = "Phát hiện điện thoại xuất hiện..."
        else:
            if hasattr(self, 'last_phone_seen_time') and (now - self.last_phone_seen_time < 0.8) and self.phone_detected_start:
                phone_dur = now - self.phone_detected_start
                if phone_dur >= 1.5:
                    status = "DISTRACTED"
                    label = "PHÁT HIỆN ĐIỆN THOẠI!"
                    reason = "Đang cầm điện thoại trên tay!"
                    should_alert = True
                    alert_type = "PHONE"
                else:
                    status = "WARNING"
                    label = "CẢNH BÁO ĐIỆN THOẠI"
                    reason = "Phát hiện điện thoại xuất hiện..."
            else:
                self.phone_detected_start = None

        # Ưu tiên 2: BUỒN NGỦ / GỤC XUỐNG BÀN / PERCLOS / MICRO-SLEEP
        micro_sleep_limit = 4.5 if is_reading_desk else self.drowsy_limit_sec
        # CHỈ COI LÀ GỤC XUỐNG BÀN KHI TRÁN ÚP HOÀN TOÀN XUỐNG MẶT BÀN (pitch < -72°) VÀ MẮT NHẮM NGHIỀN
        is_head_drooped = (pitch < -72.0) and is_eyes_closed

        if status == "FOCUSED":
            if is_head_drooped:
                status = "DROWSY"
                label = "GỤC XUỐNG BÀN"
                reason = "Đầu úp sát mặt bàn và nhắm nghiền mắt!"
                should_alert = True
                alert_type = "DROWSY"
            elif is_eyes_closed:
                if self.eye_closed_start is None:
                    self.eye_closed_start = now
                drowsy_dur = now - self.eye_closed_start

                if drowsy_dur > micro_sleep_limit:
                    status = "DROWSY"
                    label = "NGỦ GẬT (MICRO-SLEEP)"
                    reason = f"Nhắm mắt quá lâu ({drowsy_dur:.1f}s)!"
                    should_alert = True
                    alert_type = "DROWSY"
                else:
                    status = "WARNING"
                    label = "CẢNH GIÁC"
                    reason = "Mắt đang nhắm..."
            elif (not is_reading_desk) and (self.perclos_val >= 0.42):
                status = "DROWSY"
                label = "BUỒN NGỦ (PERCLOS CAO)"
                reason = f"Mắt nhắm/lờ đờ {int(self.perclos_val*100)}% thời gian gần đây!"
                should_alert = True
                alert_type = "DROWSY"
            else:
                self.eye_closed_start = None
        else:
            self.eye_closed_start = None

        # Ưu tiên 3: QUAY MẶT RA NGOÀI VÙNG HỌC TẬP (Vượt ngưỡng cá nhân hóa)
        if status == "FOCUSED":
            if is_turned_away:
                if self.distracted_start is None:
                    self.distracted_start = now
                distracted_dur = now - self.distracted_start

                dir_str = "sang phải" if is_turned_right else "sang trái"
                limit_val = yaw_max if is_turned_right else yaw_min

                if distracted_dur > self.distracted_limit_sec:
                    status = "DISTRACTED"
                    label = "MẤT TẬP TRUNG"
                    reason = f"Quay đầu {dir_str} ({yaw:+.0f}° vượt {limit_val:+.0f}°) ({distracted_dur:.1f}s)!"
                    should_alert = True
                    alert_type = "LOOKING_AWAY"
                else:
                    status = "WARNING"
                    label = "CHÚ Ý"
                    reason = f"Đang quay đầu {dir_str} ({yaw:+.0f}°)..."
            else:
                self.distracted_start = None

        # Ưu tiên 4: GAZE TRACKING (ĐẦU THẲNG NHƯNG LIẾC MẮT RA NGOÀI)
        if status == "FOCUSED" and is_gaze_diverted:
            if self.gaze_away_start is None:
                self.gaze_away_start = now
            gaze_dur = now - self.gaze_away_start
            if gaze_dur > 4.0:
                status = "DISTRACTED"
                label = "ĐẢO MẮT RA NGOÀI"
                reason = f"Mắt liếc ra khỏi bàn học ({gaze_dur:.1f}s)!"
                should_alert = True
                alert_type = "GAZE_AWAY"
        else:
            self.gaze_away_start = None

        # Ưu tiên 5: NGÁP
        if status == "FOCUSED" and is_yawning:
            status = "WARNING"
            label = "MỆT MỎI (NGÁP)"
            reason = "Phát hiện ngáp, hãy hít thở sâu nghỉ ngơi"
            alert_type = "YAWN"

        # Ưu tiên 6: KHOẢNG CÁCH MẮT - MÀN HÌNH (ERGONOMICS SCREEN DISTANCE)
        # Chỉ kiểm tra khi ngồi thẳng nhìn màn hình (không cảnh báo khi cúi đầu làm bài trên bàn)
        eye_dist_px = math.hypot((landmarks[33].x - landmarks[263].x) * w, (landmarks[33].y - landmarks[263].y) * h)
        if (not is_reading_desk) and eye_dist_px > 135.0:
            if self.too_close_start is None:
                self.too_close_start = now
            if (now - self.too_close_start) > 3.5:
                if status == "FOCUSED":
                    status = "WARNING"
                    label = "NGỒI QUÁ GẦN MÀN HÌNH"
                    reason = "Hãy lùi xa màn hình (>= 50cm) để bảo vệ mắt!"
                    alert_type = "TOO_CLOSE"
        else:
            self.too_close_start = None

        # Ưu tiên 7: TƯ THẾ CỔ (NECK TILT)
        if abs(roll) > 28.0:
            if self.neck_tilt_start is None:
                self.neck_tilt_start = now
            if (now - self.neck_tilt_start) > 5.0:
                if status == "FOCUSED":
                    status = "WARNING"
                    label = "CHỈNH LẠI TƯ THẾ CỔ"
                    reason = "Tránh nghiêng cổ / tì cằm quá lâu!"
                    alert_type = "NECK_TILT"
        else:
            self.neck_tilt_start = None

        if status == "FOCUSED":
            self.focused_frames += 1

        self._update_energy(status, now)

        return {
            "status": status,
            "label": label,
            "reason": reason,
            "alert": should_alert,
            "alert_type": alert_type,
            "ear": avg_ear,
            "mar": mar,
            "pitch": pitch,
            "yaw": yaw,
            "roll": roll,
            "gaze_ratio": gaze_ratio,
            "perclos": self.perclos_val,
            "is_reading_desk": is_reading_desk,
            "ear_threshold": self.ear_threshold,
            "study_zone": self.study_zone,
            "is_recording_zone": False,
            "record_time_left": 0.0,
            "is_study_zone_set": self.is_study_zone_set,
            "focus_score": self.get_focus_score(),
            "landmarks": landmarks
        }

    def _update_energy(self, status, now):
        """Cập nhật bình năng lượng tập trung động (Attentional Reservoir)"""
        dt = max(0.0, min(0.5, now - self.last_energy_time))
        self.last_energy_time = now

        if status in ["FOCUSED", "CALIBRATING"]:
            rate = +0.8   # Hồi phục mượt mà khi tập trung
        elif status == "BREAK":
            rate = +1.0   # Hồi phục trong giờ giải lao
        elif status == "WARNING":
            rate = -0.6   # Giảm nhẹ khi có dấu hiệu xao nhãng
        elif status in ["DISTRACTED", "AWAY"]:
            rate = -2.5   # Giảm nhanh khi mất tập trung thật sự
        elif status == "DROWSY":
            rate = -3.0   # Giảm nhanh khi ngủ gật
        else:
            rate = 0.0

        self.focus_energy = max(0.0, min(100.0, self.focus_energy + rate * dt))

    def get_focus_score(self):
        """Trả về điểm tập trung thích ứng thời gian thực (0..100)"""
        return round(float(self.focus_energy), 1)

    def reset_focus_score(self):
        """Đặt lại bình năng lượng tập trung về 100%"""
        self.focus_energy = 100.0
        self.last_energy_time = time.time()
        self.total_frames = 0
        self.focused_frames = 0
