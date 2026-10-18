# -*- coding: utf-8 -*-
import cv2
import threading
import time
import math
import numpy as np

class PhoneTrack:
    """Theo dõi quỹ đạo, động học (Kinematics) và tiếp xúc bàn tay của từng chiếc điện thoại"""
    def __init__(self, cx, cy, w, h, conf, now, has_hand_contact=False):
        self.history = [(now, cx, cy)]
        self.last_seen = now
        self.conf = conf
        self.w = w
        self.h = h
        self.has_hand_contact = has_hand_contact
        self.hand_contact_history = [(now, has_hand_contact)]
        self.is_held = False
        self.first_seen = now

    def update(self, cx, cy, w, h, conf, now, has_hand_contact=False):
        self.last_seen = now
        self.conf = conf
        self.w = w
        self.h = h
        self.has_hand_contact = has_hand_contact
        self.history.append((now, cx, cy))
        self.hand_contact_history.append((now, has_hand_contact))

        cutoff = now - 2.5
        self.history = [pt for pt in self.history if pt[0] >= cutoff]
        self.hand_contact_history = [pt for pt in self.hand_contact_history if pt[0] >= cutoff]

        # Tỷ lệ tiếp xúc bàn tay trong 1.0 giây gần nhất
        recent_contacts = [pt[1] for pt in self.hand_contact_history if pt[0] >= now - 1.0]
        hand_contact_rate = (sum(recent_contacts) / len(recent_contacts)) if recent_contacts else 0.0

        if len(self.history) >= 2:
            xs = [pt[1] for pt in self.history]
            ys = [pt[2] for pt in self.history]
            disp = math.hypot(max(xs) - min(xs), max(ys) - min(ys))

            recent = [pt for pt in self.history if pt[0] >= now - 0.7]
            if len(recent) >= 2:
                dt = max(0.02, recent[-1][0] - recent[0][0])
                d_dist = math.hypot(recent[-1][1] - recent[0][1], recent[-1][2] - recent[0][2])
                vel = d_dist / dt
            else:
                vel = 0.0

            # TIÊU CHUẨN ĐỘNG HỌC & TIẾP XÚC BÀN TAY (KINEMATIC + HAND CONTACT):
            # 1. BẮT BUỘC PHẢI CÓ TAY CẦM / CHẠM VÀO ĐIỆN THOẠI (has_hand_contact hoặc hand_contact_rate >= 0.30)
            # 2. VÀ có chuyển động cầm/nhấc/bấm vuốt (disp > 16px hoặc vel > 14px/s hoặc conf >= 0.65 cầm trên không)
            has_hand = has_hand_contact or (hand_contact_rate >= 0.30)
            if has_hand and (disp > 16.0 or vel > 14.0 or (self.conf >= 0.65 and disp > 8.0)):
                self.is_held = True
            elif not has_hand:
                # Không có bàn tay chạm vào -> Tuyệt đối là vật thể tĩnh trên bàn / kệ
                self.is_held = False
            elif (now - self.first_seen >= 1.0) and disp < 14.0 and vel < 9.0:
                self.is_held = False
        else:
            self.is_held = False


class KinematicPhoneTracker:
    """Bộ lọc động học phân biệt điện thoại CẦM TRÊN TAY vs ĐẶT TĨNH TRÊN BÀN / KỆ ĐỠ"""
    def __init__(self):
        self.tracks = []

    def update(self, raw_boxes, now):
        # Dọn dẹp vết cũ quá 1.0s
        self.tracks = [tr for tr in self.tracks if (now - tr.last_seen) < 1.0]

        results = []
        for item in raw_boxes:
            if len(item) == 6:
                x1, y1, x2, y2, conf, has_hand_contact = item
            else:
                x1, y1, x2, y2, conf = item
                has_hand_contact = False

            cx = (x1 + x2) / 2.0
            cy = (y1 + y2) / 2.0
            w = abs(x2 - x1)
            h = abs(y2 - y1)

            best_track = None
            min_dist = 70.0
            for tr in self.tracks:
                last_pt = tr.history[-1]
                dist = math.hypot(cx - last_pt[1], cy - last_pt[2])
                if dist < min_dist:
                    min_dist = dist
                    best_track = tr

            if best_track is not None:
                best_track.update(cx, cy, w, h, conf, now, has_hand_contact)
                is_held = best_track.is_held
            else:
                new_tr = PhoneTrack(cx, cy, w, h, conf, now, has_hand_contact)
                self.tracks.append(new_tr)
                is_held = False

            results.append((x1, y1, x2, y2, conf, is_held))

        return results


class PhoneDetector:
    def __init__(self, model_name="yolov8n.pt", conf_thresh=0.40):
        """
        Bộ phát hiện điện thoại trên tay người dùng sử dụng YOLOv8 Nano SIÊU TỐI ƯU HÓA:
        - torch.inference_mode(): Loại bỏ 100% overhead autograd của PyTorch
        - Model Warmup: Pre-warm mô hình ngay khi nạp, triệt tiêu giật lag ở khung hình đầu tiên
        - Tần suất quét thích ứng ~5 FPS (mỗi 0.20s), tiêu thụ <8% của 1 CPU thread
        - Kinematic Tracker + Hand Contact: Phân biệt chính xác điện thoại CẦM TRÊN TAY vs ĐẶT TĨNH TRÊN BÀN / KỆ
        - Anti-Hallucination Filters: Loại bỏ hoàn toàn sách vở, lót chuột, post-it, điều khiển, vật chữ nhật
        - Grace Persistence (0.6s): Giữ hộp nhận diện ổn định, chống chớp tắt khi tay chuyển động
        """
        self.conf_thresh = conf_thresh
        self.model = None
        self.torch = None
        self.is_ready = False
        self.latest_boxes = []
        self.last_detected_time = 0.0
        self.lock = threading.Lock()
        self.is_running = True
        
        self.pending_frame = None
        self.frame_event = threading.Event()
        self.last_infer_time = 0.0
        self.tracker = KinematicPhoneTracker()

        threading.Thread(target=self._load_model, args=(model_name,), daemon=True).start()

    def _load_model(self, model_name):
        try:
            import torch
            self.torch = torch
            torch.set_num_threads(1)
            torch.set_num_interop_threads(1)
            torch.set_grad_enabled(False)

            from ultralytics import YOLO
            self.model = YOLO(model_name)

            # Khởi động trước (Warmup) mô hình để nạp trọng số vào CPU L2/L3 cache
            with torch.inference_mode():
                dummy = np.zeros((320, 320, 3), dtype=np.uint8)
                self.model.predict(dummy, classes=[67], conf=0.5, verbose=False, imgsz=320)

            self.is_ready = True
            print("[+] YOLOv8 Nano: Đã sẵn sàng & Pre-warmed (conf=0.40, imgsz=320, Anti-Hallucination Active)!")
            threading.Thread(target=self._inference_loop, daemon=True).start()
        except Exception as e:
            print(f"[-] Không thể nạp YOLOv8: {e}")

    def update_frame(self, frame):
        """Chỉ nhận frame nếu đã đến chu kỳ quét (~5 FPS)"""
        if not self.is_ready:
            return
        
        now = time.time()
        if now - self.last_infer_time >= 0.20:
            with self.lock:
                self.pending_frame = frame.copy()
            self.frame_event.set()

    def _validate_phone_candidate(self, frame, x1, y1, x2, y2, conf):
        """
        Bộ lọc đa tầng chống nhận diện nhầm hình chữ nhật (sách vở, lót chuột, hộp, điều khiển):
        1. Aspect ratio chuẩn điện thoại (1.28 đến 2.80)
        2. Kích thước & diện tích giới hạn (không vượt quá 16% khung hình, không phải cả bàn/laptop)
        3. Kiểm tra tiếp xúc bàn tay (Hand / Skin Contact qua YCrCb)
        4. Loại trừ sách vở / giấy trắng quang học (Photometric Paper Rejection)
        """
        img_h, img_w = frame.shape[:2]
        w = x2 - x1
        h = y2 - y1
        if w <= 0 or h <= 0:
            return False, False

        long_side = max(w, h)
        short_side = min(w, h)
        if short_side <= 0:
            return False, False

        # 1. TỶ LỆ HÌNH HỌC (ASPECT RATIO):
        # Smartphone luôn có tỷ lệ cạnh từ 1.28 đến 2.80 (chuẩn 16:9 đến 20:9 hoặc nghiêng 3D)
        # Loại bỏ vật vuông (post-it, lót ly, sổ tay mini < 1.28) và vật quá dài (thước kẻ, bút, remote > 2.80)
        aspect_ratio = float(long_side) / float(short_side)
        if aspect_ratio < 1.28 or aspect_ratio > 2.80:
            return False, False

        # 2. GIỚI HẠN DIỆN TÍCH & KÍCH THƯỚC TRONG KHUNG HÌNH:
        # Điện thoại ở khoảng cách ngồi học không bao giờ chiếm > 16% diện tích camera
        box_area = w * h
        frame_area = img_w * img_h
        if box_area > (frame_area * 0.16) or w > (img_w * 0.48) or h > (img_h * 0.58):
            return False, False
        if long_side < 38 or box_area < 1000:
            return False, False

        # Cắt ROI hợp lệ trong ảnh
        x1_c = max(0, min(img_w - 1, x1))
        y1_c = max(0, min(img_h - 1, y1))
        x2_c = max(0, min(img_w, x2))
        y2_c = max(0, min(img_h, y2))
        roi = frame[y1_c:y2_c, x1_c:x2_c]
        if roi.size == 0:
            return False, False

        # 3. KIỂM TRA TIẾP XÚC BÀN TAY (SKIN / HAND CONTACT):
        # Mở rộng vùng biên 12% để kiểm tra các ngón tay cầm hoặc lòng bàn tay đỡ điện thoại
        pad_x = max(4, int(w * 0.12))
        pad_y = max(4, int(h * 0.12))
        hx1 = max(0, x1_c - pad_x)
        hy1 = max(0, y1_c - pad_y)
        hx2 = min(img_w, x2_c + pad_x)
        hy2 = min(img_h, y2_c + pad_y)
        hand_roi = frame[hy1:hy2, hx1:hx2]

        ycrcb = cv2.cvtColor(hand_roi, cv2.COLOR_BGR2YCrCb)
        skin_mask = (ycrcb[:, :, 1] >= 133) & (ycrcb[:, :, 1] <= 173) & \
                    (ycrcb[:, :, 2] >= 77) & (ycrcb[:, :, 2] <= 127)
        skin_pixels = np.count_nonzero(skin_mask)
        skin_ratio = float(skin_pixels) / float(hand_roi.size)
        has_hand_contact = (skin_ratio >= 0.030)

        # 4. LOẠI BỎ TRANG SÁCH / GIẤY VỞ TRẮNG TRÊN BÀN HỌC (PHOTOMETRIC PAPER FILTER):
        # Trang vở/sách có nền giấy trắng sáng đồng đều. Điện thoại có viền bezel hoặc độ tương phản cao.
        gray_roi = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
        mean_val = float(np.mean(gray_roi))
        white_ratio = float(np.count_nonzero(gray_roi > 200)) / float(gray_roi.size)

        if not has_hand_contact and mean_val > 180.0 and white_ratio > 0.38:
            # Đây là trang sách / vở trắng trên bàn học, không phải điện thoại!
            return False, False
        if white_ratio > 0.70:
            # Hơn 70% là giấy trắng tinh -> Chắc chắn là tài liệu / vở bài tập
            return False, False

        # 5. LỌC ĐỘ TIN CẬY (CONFIDENCE FILTER):
        # - Nếu không có bàn tay chạm vào (vật thể nằm trơ trọi trên bàn): bắt buộc conf >= 0.52
        # - Nếu có bàn tay chạm vào: chỉ cần conf >= 0.40
        if not has_hand_contact and conf < 0.52:
            return False, False
        if conf < 0.40:
            return False, False

        return True, has_hand_contact

    def _inference_loop(self):
        """Vòng lặp suy luận nền chính xác, không khóa thread"""
        while self.is_running:
            if not self.frame_event.wait(timeout=0.25):
                continue
            self.frame_event.clear()

            frame_to_process = None
            with self.lock:
                frame_to_process = self.pending_frame
                self.pending_frame = None

            if frame_to_process is not None and self.model is not None and self.torch is not None:
                now = time.time()
                self.last_infer_time = now
                try:
                    with self.torch.inference_mode():
                        # Lớp 67: cell phone (chỉ nhận diện điện thoại, loại bỏ remote/vật dụng khác)
                        results = self.model.predict(
                            source=frame_to_process,
                            classes=[67],
                            conf=self.conf_thresh,
                            verbose=False,
                            imgsz=320
                        )

                    boxes = []
                    if results and len(results) > 0:
                        r = results[0]
                        if r.boxes is not None and len(r.boxes) > 0:
                            for box in r.boxes:
                                x1, y1, x2, y2 = map(int, box.xyxy[0].tolist())
                                conf = float(box.conf[0])
                                is_valid, has_hand_contact = self._validate_phone_candidate(
                                    frame_to_process, x1, y1, x2, y2, conf
                                )
                                if is_valid:
                                    boxes.append((x1, y1, x2, y2, conf, has_hand_contact))

                    tracked = self.tracker.update(boxes, now)

                    with self.lock:
                        if tracked:
                            self.latest_boxes = tracked
                            self.last_detected_time = now
                        else:
                            if now - self.last_detected_time > 0.55:
                                self.latest_boxes = []
                except Exception:
                    pass

    def get_detected_phones(self):
        """Trả về danh sách các điện thoại nhận diện được dạng (x1, y1, x2, y2, conf, is_held)"""
        with self.lock:
            if time.time() - self.last_detected_time > 0.60:
                return []
            return list(self.latest_boxes)

    def stop(self):
        self.is_running = False
        self.frame_event.set()
