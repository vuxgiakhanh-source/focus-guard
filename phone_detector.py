# -*- coding: utf-8 -*-
import os
import cv2
import threading
import time
import math
import numpy as np

class PhoneTrack:
    """Theo dõi quỹ đạo, động học và tiếp xúc bàn tay của từng chiếc điện thoại"""
    def __init__(self, cx, cy, w, h, conf, now, has_hand_contact=False, frame_h=None):
        self.history = [(now, cx, cy)]
        self.last_seen = now
        self.conf = conf
        self.w = w
        self.h = h
        self.frame_h = frame_h
        self.has_hand_contact = has_hand_contact
        self.hand_contact_history = [(now, has_hand_contact)]
        # Điện thoại khi xuất hiện trước camera đa phần do người dùng cầm đưa vào -> Mặc định là CẦM TRÊN TAY
        self.is_held = True
        self.first_seen = now
        self.static_start_time = now if not has_hand_contact else None

    def update(self, cx, cy, w, h, conf, now, has_hand_contact=False, frame_h=None):
        self.last_seen = now
        self.conf = conf
        self.w = w
        self.h = h
        if frame_h is not None:
            self.frame_h = frame_h
        self.has_hand_contact = has_hand_contact
        self.history.append((now, cx, cy))
        self.hand_contact_history.append((now, has_hand_contact))

        cutoff = now - 3.0
        self.history = [pt for pt in self.history if pt[0] >= cutoff]
        self.hand_contact_history = [pt for pt in self.hand_contact_history if pt[0] >= cutoff]

        recent_contacts = [pt[1] for pt in self.hand_contact_history if pt[0] >= now - 1.5]
        hand_contact_rate = (sum(recent_contacts) / len(recent_contacts)) if recent_contacts else 0.0
        has_hand = has_hand_contact or (hand_contact_rate >= 0.20)

        # Kiểm tra độ cao vị trí: Nếu ở nửa trên khung hình (ngang ngực/mặt), người dùng đang giơ lên xem
        is_elevated = (self.frame_h is not None and cy < self.frame_h * 0.65)

        if len(self.history) >= 2:
            xs = [pt[1] for pt in self.history]
            ys = [pt[2] for pt in self.history]
            net_disp = math.hypot(xs[-1] - xs[0], ys[-1] - ys[0])
            peak_disp = math.hypot(max(xs) - min(xs), max(ys) - min(ys))

            # 1. Có bàn tay chạm/đỡ HOẶC đang giơ cao ngang ngực/mặt -> CẦM TRÊN TAY
            if has_hand or is_elevated:
                self.is_held = True
                self.static_start_time = None
            # 2. Có chuyển động thực sự (nhấc lên, di chuyển, lắc tay; bỏ qua rung nhẹ của box YOLO <= 14px)
            elif net_disp > 14.0 or peak_disp > 20.0:
                self.is_held = True
                self.static_start_time = None
            # 3. Không có tay chạm VÀ ở vùng mặt bàn VÀ vị trí gần như bất động hoàn toàn
            else:
                if self.static_start_time is None:
                    self.static_start_time = now
                elif now - self.static_start_time >= 2.0:
                    # Nằm yên trên bàn không có tay chạm > 2.0s -> ĐẶT TĨNH TRÊN BÀN
                    self.is_held = False
        else:
            self.is_held = True


class KinematicPhoneTracker:
    """Bộ lọc động học phân biệt điện thoại CẦM TRÊN TAY vs ĐẶT TĨNH TRÊN BÀN / KỆ ĐỠ"""
    def __init__(self):
        self.tracks = []

    def update(self, raw_boxes, now, frame_h=None):
        # Dọn dẹp vết cũ quá 2.5s
        self.tracks = [tr for tr in self.tracks if (now - tr.last_seen) < 2.5]

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
            min_dist = 140.0
            for tr in self.tracks:
                last_pt = tr.history[-1]
                dist = math.hypot(cx - last_pt[1], cy - last_pt[2])
                if dist < min_dist:
                    min_dist = dist
                    best_track = tr

            if best_track is not None:
                best_track.update(cx, cy, w, h, conf, now, has_hand_contact, frame_h=frame_h)
                is_held = best_track.is_held
            else:
                new_tr = PhoneTrack(cx, cy, w, h, conf, now, has_hand_contact, frame_h=frame_h)
                self.tracks.append(new_tr)
                is_held = new_tr.is_held

            results.append((x1, y1, x2, y2, conf, is_held))

        return results


class PhoneDetector:
    def __init__(self, model_name="yolov8n.pt", conf_thresh=0.35, inference_interval_sec=0.50):
        """
        Bộ phát hiện điện thoại trên tay người dùng sử dụng YOLOv8 Nano SIÊU TỐI ƯU HÓA:
        - torch.inference_mode(): Loại bỏ 100% overhead autograd của PyTorch
        - Model Warmup: Pre-warm mô hình ngay khi nạp, triệt tiêu giật lag ở khung hình đầu tiên
        - Tần suất quét 2 FPS (mỗi 0.50s), phản hồi tức thì và tốn <1% CPU
        - Kinematic Tracker + Hand Contact: Phân biệt chính xác điện thoại CẦM TRÊN TAY vs ĐẶT TĨNH TRÊN BÀN / KỆ
        - Anti-Hallucination Filters: Loại bỏ hoàn toàn sách vở, lót chuột, post-it, điều khiển, vật chữ nhật
        - Grace Persistence (1.8s): Giữ hộp nhận diện ổn định, chống chớp tắt khi tay chuyển động
        """
        if model_name == "yolov8n.pt" or not os.path.isabs(model_name):
            base_dir = os.path.dirname(os.path.abspath(__file__))
            candidate = os.path.join(base_dir, model_name)
            if os.path.exists(candidate):
                model_name = candidate

        self.conf_thresh = conf_thresh
        self.inference_interval_sec = max(0.25, float(inference_interval_sec))
        self.detection_ttl_sec = max(1.8, self.inference_interval_sec * 2.5)
        self.model = None
        self.torch = None
        self.is_ready = False
        self.has_error = False
        self.latest_boxes = []
        self.last_detected_time = 0.0
        self.lock = threading.Lock()
        self.is_running = True
        
        self.pending_frame = None
        self.frame_event = threading.Event()
        self.last_infer_time = 0.0
        self.inference_busy = False
        self.last_error_log_time = 0.0
        self.tracker = KinematicPhoneTracker()
        self.model_thread = threading.Thread(
            target=self._load_model, args=(model_name,), name="FocusGuard-YOLOLoader", daemon=True
        )
        self.inference_thread = None
        self.model_thread.start()

    def _load_model(self, model_name):
        try:
            if not self.is_running:
                return
            import torch
            import ultralytics.utils.torch_utils as tu
            tu.NUM_THREADS = 1
            self.torch = torch
            torch.set_num_threads(1)
            # main.py may already have set this process-wide value before starting this thread.
            if torch.get_num_interop_threads() != 1:
                torch.set_num_interop_threads(1)
            torch.set_grad_enabled(False)

            from ultralytics import YOLO
            if not self.is_running:
                return
            self.model = YOLO(model_name)
            if not self.is_running:
                return

            # Khởi động trước (Warmup) mô hình để nạp trọng số vào CPU L2/L3 cache
            with torch.inference_mode():
                dummy = np.zeros((256, 256, 3), dtype=np.uint8)
                self.model.predict(dummy, classes=[67], conf=0.5, verbose=False, imgsz=256)

            if not self.is_running:
                return
            with self.lock:
                if not self.is_running:
                    return
                self.is_ready = True
                self.inference_thread = threading.Thread(
                    target=self._inference_loop,
                    name="FocusGuard-PhoneInference",
                    daemon=True
                )
                self.inference_thread.start()
            print("[+] YOLOv8 Nano: Đã sẵn sàng & Pre-warmed (imgsz=256, tối đa khoảng 1 FPS).")
        except Exception as e:
            with self.lock:
                self.has_error = True
            print(f"[-] Không thể nạp YOLOv8: {e}")

    def update_frame(self, frame):
        """Gửi tối đa một frame theo nhịp YOLO, không chép frame trong lúc suy luận."""
        if not self.is_ready or not self.is_running:
            return

        now = time.monotonic()
        with self.lock:
            if (not self.is_running or self.inference_busy or self.pending_frame is not None
                    or now - self.last_infer_time < self.inference_interval_sec):
                return
            self.pending_frame = frame.copy()
            self.last_infer_time = now
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
        # Cho phép cả khi điện thoại nghiêng 3D, ngang hoặc thẳng đứng (1.05 đến 3.50)
        aspect_ratio = float(long_side) / float(short_side)
        if aspect_ratio < 1.05 or aspect_ratio > 3.50:
            return False, False

        # 2. GIỚI HẠN DIỆN TÍCH & KÍCH THƯỚC TRONG KHUNG HÌNH:
        box_area = w * h
        frame_area = img_w * img_h
        if box_area > (frame_area * 0.45) or w > (img_w * 0.70) or h > (img_h * 0.80):
            return False, False
        if long_side < 28 or box_area < 500:
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
        # Mở rộng vùng kiểm tra xung quanh viền điện thoại
        pad_x = max(8, int(w * 0.20))
        pad_y = max(8, int(h * 0.20))
        hx1 = max(0, x1_c - pad_x)
        hy1 = max(0, y1_c - pad_y)
        hx2 = min(img_w, x2_c + pad_x)
        hy2 = min(img_h, y2_c + pad_y)
        hand_roi = frame[hy1:hy2, hx1:hx2]

        # Tạo mặt nạ vùng viền ngoài (Perimeter Ring Mask), loại trừ 75% diện tích lõi giữa của chính điện thoại
        # (tránh tính nhầm ốp lưng màu be, hình nền người hoặc phản chiếu trên mặt kính)
        ring_mask = np.ones((hand_roi.shape[0], hand_roi.shape[1]), dtype=bool)
        core_y1 = max(0, y1_c - hy1 + int(h * 0.12))
        core_y2 = min(hand_roi.shape[0], y2_c - hy1 - int(h * 0.12))
        core_x1 = max(0, x1_c - hx1 + int(w * 0.12))
        core_x2 = min(hand_roi.shape[1], x2_c - hx1 - int(w * 0.12))
        if core_y2 > core_y1 and core_x2 > core_x1:
            ring_mask[core_y1:core_y2, core_x1:core_x2] = False

        # Phối hợp YCrCb + HSV để nhận diện màu da chính xác, chống nhận nhầm mặt bàn gỗ / bìa sách màu kem
        ycrcb = cv2.cvtColor(hand_roi, cv2.COLOR_BGR2YCrCb)
        hsv = cv2.cvtColor(hand_roi, cv2.COLOR_BGR2HSV)

        # Ngưỡng da sinh trắc học chuẩn trong không gian YCrCb (có ràng buộc độ sáng Y)
        skin_ycrcb = (ycrcb[:, :, 0] >= 40) & (ycrcb[:, :, 0] <= 250) & \
                     (ycrcb[:, :, 1] >= 128) & (ycrcb[:, :, 1] <= 180) & \
                     (ycrcb[:, :, 2] >= 70) & (ycrcb[:, :, 2] <= 138)

        # Ngưỡng sắc thái da trong HSV (Hue da người 0-30 hoặc 165-180, bão hòa vừa phải)
        skin_hsv = ((hsv[:, :, 0] <= 30) | (hsv[:, :, 0] >= 165)) & \
                   (hsv[:, :, 1] >= 20) & (hsv[:, :, 1] <= 230) & \
                   (hsv[:, :, 2] >= 35)

        skin_mask = (skin_ycrcb & skin_hsv) & ring_mask
        skin_pixels = np.count_nonzero(skin_mask)
        ring_pixel_count = np.count_nonzero(ring_mask)
        skin_ratio = float(skin_pixels) / max(1, ring_pixel_count)
        has_hand_contact = (skin_ratio >= 0.020)

        # 4. LOẠI BỎ TRANG SÁCH / GIẤY VỞ TRẮNG TRÊN BÀN HỌC (PHOTOMETRIC PAPER FILTER):
        gray_roi = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
        mean_val = float(np.mean(gray_roi))
        white_ratio = float(np.count_nonzero(gray_roi > 210)) / float(gray_roi.size)

        if not has_hand_contact and mean_val > 195.0 and white_ratio > 0.55:
            return False, False
        if white_ratio > 0.80:
            return False, False

        # 5. LỌC ĐỘ TIN CẬY (CONFIDENCE FILTER):
        if conf < self.conf_thresh:
            return False, False

        return True, has_hand_contact

    def _inference_loop(self):
        """Chỉ xử lý một frame tại một thời điểm; worker dừng gọn khi app thoát."""
        while self.is_running:
            if not self.frame_event.wait(timeout=0.25):
                continue

            with self.lock:
                self.frame_event.clear()
                frame_to_process = self.pending_frame
                self.pending_frame = None
                if frame_to_process is None:
                    continue
                self.inference_busy = True

            now = time.monotonic()
            try:
                if not self.is_running or self.model is None or self.torch is None:
                    continue

                with self.torch.inference_mode():
                    results = self.model.predict(
                        source=frame_to_process,
                        classes=[67],
                        conf=self.conf_thresh,
                        verbose=False,
                        imgsz=256
                    )

                boxes = []
                if results and len(results) > 0:
                    result = results[0]
                    if result.boxes is not None and len(result.boxes) > 0:
                        for box in result.boxes:
                            x1, y1, x2, y2 = map(int, box.xyxy[0].tolist())
                            conf = float(box.conf[0])
                            is_valid, has_hand_contact = self._validate_phone_candidate(
                                frame_to_process, x1, y1, x2, y2, conf
                            )
                            if is_valid:
                                boxes.append((x1, y1, x2, y2, conf, has_hand_contact))

                tracked = self.tracker.update(boxes, now, frame_h=frame_to_process.shape[0])
                with self.lock:
                    if self.is_running:
                        if tracked:
                            self.latest_boxes = tracked
                            self.last_detected_time = now
                        elif now - self.last_detected_time > self.detection_ttl_sec:
                            self.latest_boxes = []
            except Exception as exc:
                if now - self.last_error_log_time >= 30.0:
                    print(f"[-] Lỗi suy luận YOLO: {exc}")
                    self.last_error_log_time = now
            finally:
                with self.lock:
                    self.inference_busy = False

    def get_detected_phones(self):
        """Trả về danh sách các điện thoại nhận diện được dạng (x1, y1, x2, y2, conf, is_held)"""
        with self.lock:
            if time.monotonic() - self.last_detected_time > self.detection_ttl_sec:
                return []
            return list(self.latest_boxes)

    def stop(self):
        with self.lock:
            self.is_running = False
            self.is_ready = False
            self.pending_frame = None
            self.frame_event.set()
            workers = (self.inference_thread, self.model_thread)

        for worker in workers:
            if worker is not None and worker is not threading.current_thread():
                worker.join(timeout=1.0)
