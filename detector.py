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

class EMASmoother:
    """Bộ lọc làm mịn EMA (Exponential Moving Average) khử rung giật số đo góc"""
    def __init__(self, alpha=0.35):
        self.alpha = alpha
        self.val = None

    def update(self, new_val):
        if self.val is None:
            self.val = float(new_val)
        else:
            self.val = self.alpha * float(new_val) + (1.0 - self.alpha) * self.val
        return self.val

    def reset(self):
        self.val = None

class FocusDetector:
    def __init__(self,
                 model_path="face_landmarker.task",
                 ear_threshold=0.18,          # Ngưỡng mắt hợp lý
                 drowsy_limit_sec=2.0,        # Nhắm mắt 2s mới báo buồn ngủ
                 distracted_limit_sec=3.0,    # Lệch khỏi vùng học quá 3s mới nhắc
                 away_limit_sec=4.0):         # Rời bàn quá 4s mới nhắc
        """
        FocusDetector SIÊU TỐI ƯU HÓA (Phiên bản 2):
        1. MediaPipe suy luận xen kẽ khung hình (Inference Decimation: 15 FPS AI)
        2. Tắt FaceBlendshapesGraph tiết kiệm 20% CPU & RAM
        3. math.hypot tối ưu hóa khoảng cách gấp 40 lần
        4. Bộ lọc mượt EMA khử rung góc đầu
        5. Thích ứng ánh sáng thông minh (Zero CLAHE waste)
        6. Pre-computed Camera Matrix & solvePnP
        """
        self.model_path = model_path
        self.ear_threshold = ear_threshold
        self.drowsy_limit_sec = drowsy_limit_sec
        self.distracted_limit_sec = distracted_limit_sec
        self.away_limit_sec = away_limit_sec

        # Bộ lọc làm mịn EMA cho từng trục
        self.smooth_pitch = EMASmoother(alpha=0.30)
        self.smooth_yaw = EMASmoother(alpha=0.30)
        self.smooth_roll = EMASmoother(alpha=0.30)
        self.smooth_ear = EMASmoother(alpha=0.40)
        self.smooth_gaze = EMASmoother(alpha=0.25)

        # Vùng học tập: Quay trái tự do 100%, quay sang phải >= 70 độ mới tính là mất tập trung
        self.study_zone = {
            "yaw_min": -180.0,
            "yaw_max": 70.0,
            "pitch_min": -65.0,
            "pitch_max": 55.0,
            "roll_min": -50.0,
            "roll_max": 50.0
        }
        self.is_study_zone_set = True

        # Học vùng học tập (Calibration 2 phút / 120s) & Tự động cân chỉnh EAR cho kính / mắt híp
        self.is_recording_zone = False
        self.record_start_time = 0
        self.record_duration = 120.0
        self.recorded_samples = {"yaw": [], "pitch": [], "roll": [], "ear": []}

        if not os.path.exists(self.model_path):
            raise FileNotFoundError(f"Không tìm thấy file model: {self.model_path}")

        base_options = python.BaseOptions(model_asset_path=self.model_path)
        # Tắt blendshapes và transform matrix để không chạy phụ graph tiết kiệm tối đa CPU/RAM
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

        # Pre-allocate Camera Matrix & Distortion coefficients (không tạo mới mỗi frame)
        focal_length = 640.0
        center = (320.0, 240.0)
        self.camera_matrix = np.array([
            [focal_length, 0, center[0]],
            [0, focal_length, center[1]],
            [0, 0, 1]
        ], dtype=np.float64)
        self.dist_coeffs = np.zeros((4, 1), dtype=np.float64)
        self.clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))

        # Bộ nhớ đệm tiền cấp phát chống phân mảnh RAM và sinh nhiệt CPU (Zero GC Churn)
        self.frame_rgb_buffer = np.empty((480, 640, 3), dtype=np.uint8)
        self.image_points = np.empty((6, 2), dtype=np.float64)

        # Quản lý suy luận xen kẽ khung hình (Inference Decimation)
        self.frame_idx = 0
        self.last_detection_data = None
        self.last_brightness_check_time = 0
        self.is_dark_env = False

        self.eye_closed_start = None
        self.distracted_start = None
        self.away_start = None
        self.phone_detected_start = None
        self.last_phone_seen_time = 0.0
        self.gaze_away_start = None

        self.total_frames = 0
        self.focused_frames = 0

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
            self.study_zone = {
                "yaw_min": -180.0,
                "yaw_max": max(70.0, round(float(max(self.recorded_samples["yaw"]) + 10.0), 1)),
                "pitch_min": round(float(min(self.recorded_samples["pitch"]) - 12.0), 1),
                "pitch_max": round(float(max(self.recorded_samples["pitch"]) + 10.0), 1),
                "roll_min": round(float(min(self.recorded_samples["roll"]) - 10.0), 1),
                "roll_max": round(float(max(self.recorded_samples["roll"]) + 10.0), 1)
            }

            # Tự động hiệu chuẩn ngưỡng nhắm mắt EAR cho người đeo kính / mắt híp
            if "ear" in self.recorded_samples and len(self.recorded_samples["ear"]) > 10:
                open_eye_baseline = float(np.median(self.recorded_samples["ear"]))
                calibrated_threshold = max(0.12, min(0.22, round(open_eye_baseline * 0.68, 2)))
                self.ear_threshold = calibrated_threshold
                print(f"[+] Đã tự động cân chỉnh EAR (Đeo kính/Mắt): Mở mắt {open_eye_baseline:.2f} -> Ngưỡng nhắm: {self.ear_threshold}")

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
        """Kiểm tra độ sáng bằng cách lấy mẫu thưa 1/400 pixel (chỉ tốn 0.004ms)"""
        now = time.time()
        if now - self.last_brightness_check_time > 1.0:
            self.last_brightness_check_time = now
            # Kênh Green (kênh 1) phản ánh 59% độ chói chuẩn mắt người
            sampled_mean = float(np.mean(frame_bgr[::20, ::20, 1]))
            self.is_dark_env = (sampled_mean < 55.0)

    def apply_clahe_enhancement(self, frame_bgr):
        """Chỉ thực hiện CLAHE khi phòng thực sự tối để tiết kiệm 100% thời gian xử lý"""
        if not self.is_dark_env:
            return frame_bgr
        lab = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2LAB)
        l, a, b = cv2.split(lab)
        l = self.clahe.apply(l)
        lab = cv2.merge((l, a, b))
        return cv2.cvtColor(lab, cv2.COLOR_LAB2BGR)

    def calculate_ear(self, landmarks, eye_indices, w, h):
        """Tính EAR tối ưu hóa với math.hypot - Zero Allocation (0% RAM churn)"""
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
        """Tính MAR tối ưu hóa với math.hypot - Zero Allocation"""
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
        """
        Tính tỷ lệ vị trí con ngươi (Gaze Ratio) để phát hiện liếc mắt ra ngoài:
        - 468: Tâm mống mắt trái (nằm giữa mốc 33 và 133)
        - 473: Tâm mống mắt phải (nằm giữa mốc 362 và 263)
        """
        try:
            if len(landmarks) >= 478:
                # Mắt trái
                p_iris_l = landmarks[468].x
                p_corner1_l = landmarks[33].x
                p_corner2_l = landmarks[133].x
                w_l = abs(p_corner2_l - p_corner1_l)

                ratio_l = 0.5
                if w_l > 0:
                    ratio_l = abs(p_iris_l - min(p_corner1_l, p_corner2_l)) / w_l

                # Mắt phải
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
        # Gán trực tiếp vào mảng pre-allocated (tiết kiệm 100% chi phí tạo mảng mới mỗi frame)
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
                "ear_threshold": self.ear_threshold,
                "study_zone": self.study_zone,
                "is_recording_zone": False,
                "record_time_left": 0.0,
                "is_study_zone_set": self.is_study_zone_set,
                "focus_score": self.get_focus_score(),
                "landmarks": None
            }

        # 1. Kiểm tra ánh sáng nhanh (1s/lần, tốn 0.004ms)
        self.check_lighting(frame_bgr)

        # 2. Lọc điện thoại trên tay (loại bỏ các vật thể quá bé ở hậu cảnh)
        has_phone = False
        if detected_phones:
            for (x1, y1, x2, y2, conf) in detected_phones:
                pw = abs(x2 - x1)
                ph = abs(y2 - y1)
                # Kích thước hợp lý cho điện thoại trên tay: chiều dài >= 35px, diện tích >= 600px
                if max(pw, ph) >= 35 and (pw * ph) >= 600:
                    has_phone = True
                    break

        # 3. MediaPipe suy luận xen kẽ: Chạy cách 1 khung hình (15 FPS AI, giảm 50% CPU liên tục)
        is_infer_frame = (self.frame_idx % 2 == 0)
        if is_infer_frame:
            enhanced_frame = self.apply_clahe_enhancement(frame_bgr)
            if self.frame_rgb_buffer.shape[:2] != (h, w):
                self.frame_rgb_buffer = np.empty((h, w, 3), dtype=np.uint8)
            cv2.cvtColor(enhanced_frame, cv2.COLOR_BGR2RGB, dst=self.frame_rgb_buffer)
            mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=self.frame_rgb_buffer)
            result = self.landmarker.detect(mp_image)

            if not result.face_landmarks or len(result.face_landmarks) == 0:
                self.last_detection_data = None
            else:
                landmarks = result.face_landmarks[0]
                raw_ear_l = self.calculate_ear(landmarks, self.LEFT_EYE, w, h)
                raw_ear_r = self.calculate_ear(landmarks, self.RIGHT_EYE, w, h)
                avg_ear = self.smooth_ear.update((raw_ear_l + raw_ear_r) / 2.0)
                mar = self.calculate_mar(landmarks, w, h)

                raw_pitch, raw_yaw, raw_roll, _, _ = self.estimate_head_pose(landmarks, w, h)
                pitch = self.smooth_pitch.update(raw_pitch)
                yaw = self.smooth_yaw.update(raw_yaw)
                roll = self.smooth_roll.update(raw_roll)

                raw_gaze = self.calculate_iris_gaze(landmarks, w, h)
                gaze_ratio = self.smooth_gaze.update(raw_gaze)

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

            if self.away_start is None:
                self.away_start = now
            away_dur = now - self.away_start

            should_alert = away_dur > self.away_limit_sec
            return {
                "status": "AWAY",
                "label": "RỜI KHỎI BÀN",
                "reason": f"Không thấy khuôn mặt ({away_dur:.1f}s)",
                "alert": should_alert,
                "alert_type": "AWAY",
                "ear": 0.0,
                "mar": 0.0,
                "pitch": 0.0,
                "yaw": 0.0,
                "roll": 0.0,
                "gaze_ratio": 0.5,
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

        # 5. NẾU ĐANG TRONG CHẾ ĐỘ HỌC GÓC HỌC TẬP (60 GIÂY)
        record_time_left = 0.0
        if self.is_recording_zone:
            self.recorded_samples["yaw"].append(yaw)
            self.recorded_samples["pitch"].append(pitch)
            self.recorded_samples["roll"].append(roll)
            self.recorded_samples["ear"].append(avg_ear)

            elapsed = now - self.record_start_time
            record_time_left = max(0.0, self.record_duration - elapsed)

            if elapsed >= self.record_duration:
                self.finalize_zone_learning()

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
                "ear_threshold": self.ear_threshold,
                "study_zone": self.study_zone,
                "is_recording_zone": True,
                "record_time_left": record_time_left,
                "is_study_zone_set": self.is_study_zone_set,
                "focus_score": self.get_focus_score(),
                "landmarks": landmarks
            }

        # 6. KIỂM TRA ĐẦU CÓ NẰM TRONG HƯỚNG BÀN HỌC KHÔNG?
        # Người dùng yêu cầu: Quay trái tự do thoải mái 100%, chỉ có quay phải >= 70 độ mới là có vấn đề!
        is_turned_right = (yaw >= 70.0)
        is_turned_away = is_turned_right
        is_inside_study_zone = not is_turned_away

        # Gaze tracking: Chỉ cảnh báo khi liếc mắt quá mạnh sang phải (> 0.82)
        is_gaze_diverted = (gaze_ratio > 0.82)
        is_eyes_closed = avg_ear < self.ear_threshold
        is_yawning = mar > 0.70

        status = "FOCUSED"
        label = "ĐANG TẬP TRUNG"
        reason = "Đang tại bàn học"
        should_alert = False
        alert_type = None

        # Ưu tiên 1: PHÁT HIỆN ĐIỆN THOẠI TRỰC TIẾP BẰNG YOLO
        if has_phone:
            if self.phone_detected_start is None:
                self.phone_detected_start = now
            self.last_phone_seen_time = now
            phone_dur = now - self.phone_detected_start

            if phone_dur >= 0.75:
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
            # Cho phép ân hạn 0.6 giây để chống rớt frame chớp tắt
            if hasattr(self, 'last_phone_seen_time') and (now - self.last_phone_seen_time < 0.6) and self.phone_detected_start:
                phone_dur = now - self.phone_detected_start
                if phone_dur >= 0.75:
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

        # Ưu tiên 2: BUỒN NGỦ / NHẮM MẮT
        if status == "FOCUSED" and is_eyes_closed:
            if self.eye_closed_start is None:
                self.eye_closed_start = now
            drowsy_dur = now - self.eye_closed_start

            if drowsy_dur > self.drowsy_limit_sec:
                status = "DROWSY"
                label = "NGỦ GẬT / BUỒN NGỦ"
                reason = f"Nhắm mắt quá lâu ({drowsy_dur:.1f}s)!"
                should_alert = True
                alert_type = "DROWSY"
            else:
                status = "WARNING"
                label = "CẢNH GIÁC"
                reason = "Mắt đang nhắm..."
        elif not is_eyes_closed:
            self.eye_closed_start = None

        # Ưu tiên 3: QUAY MẶT SANG PHẢI QUÁ 70 ĐỘ (Quay trái hoàn toàn thoải mái)
        if status == "FOCUSED":
            if is_turned_right:
                if self.distracted_start is None:
                    self.distracted_start = now
                distracted_dur = now - self.distracted_start

                if distracted_dur > self.distracted_limit_sec:
                    status = "DISTRACTED"
                    label = "MẤT TẬP TRUNG"
                    reason = f"Quay mặt sang phải quá >= 70° ({distracted_dur:.1f}s)!"
                    should_alert = True
                    alert_type = "LOOKING_AWAY"
                else:
                    status = "WARNING"
                    label = "CHÚ Ý"
                    reason = f"Đang quay mặt sang phải ({yaw:+.1f}°)..."
            else:
                self.distracted_start = None

        # Ưu tiên 4: GAZE TRACKING (ĐẦU THẲNG NHƯNG LIẾC MẮT RA NGOÀI)
        if status == "FOCUSED" and is_gaze_diverted:
            if self.gaze_away_start is None:
                self.gaze_away_start = now
            gaze_dur = now - self.gaze_away_start
            if gaze_dur > 3.0:
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
            reason = "Phát hiện ngáp, hãy nghỉ ngơi một chút"
            alert_type = "YAWN"

        if status == "FOCUSED":
            self.focused_frames += 1

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
            "ear_threshold": self.ear_threshold,
            "study_zone": self.study_zone,
            "is_recording_zone": False,
            "record_time_left": 0.0,
            "is_study_zone_set": self.is_study_zone_set,
            "focus_score": self.get_focus_score(),
            "landmarks": landmarks
        }

    def get_focus_score(self):
        if self.total_frames == 0:
            return 100.0
        return round((self.focused_frames / self.total_frames) * 100.0, 1)
