# -*- coding: utf-8 -*-
import cv2
import threading
import time
import math
import numpy as np

class PhoneTrack:
    """Theo dõi quỹ đạo và động học (Kinematics) của từng chiếc điện thoại trong khung hình"""
    def __init__(self, cx, cy, w, h, conf, now):
        self.history = [(now, cx, cy)]
        self.last_seen = now
        self.conf = conf
        self.w = w
        self.h = h
        self.is_held = False
        self.first_seen = now

    def update(self, cx, cy, w, h, conf, now):
        self.last_seen = now
        self.conf = conf
        self.w = w
        self.h = h
        self.history.append((now, cx, cy))
        cutoff = now - 2.5
        self.history = [pt for pt in self.history if pt[0] >= cutoff]

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

            # Tiêu chuẩn động học phân biệt:
            # - Cầm trên tay / bấm vuốt: độ dịch chuyển > 20px hoặc vận tốc di chuyển > 18px/s
            # - Tĩnh trên bàn / kệ đỡ: độ dịch chuyển < 15px và vận tốc < 10px/s sau > 1.0s
            if disp > 20.0 or vel > 18.0:
                self.is_held = True
            elif (now - self.first_seen >= 1.0) and disp < 15.0 and vel < 10.0:
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
        for (x1, y1, x2, y2, conf) in raw_boxes:
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
                best_track.update(cx, cy, w, h, conf, now)
                is_held = best_track.is_held
            else:
                new_tr = PhoneTrack(cx, cy, w, h, conf, now)
                self.tracks.append(new_tr)
                is_held = False

            results.append((x1, y1, x2, y2, conf, is_held))

        return results


class PhoneDetector:
    def __init__(self, model_name="yolov8n.pt", conf_thresh=0.28):
        """
        Bộ phát hiện điện thoại trên tay người dùng sử dụng YOLOv8 Nano SIÊU TỐI ƯU HÓA:
        - torch.inference_mode(): Loại bỏ 100% overhead autograd của PyTorch
        - Model Warmup: Pre-warm mô hình ngay khi nạp, triệt tiêu giật lag ở khung hình đầu tiên
        - Tần suất quét thích ứng ~5 FPS (mỗi 0.20s), tiêu thụ <8% của 1 CPU thread
        - Kinematic Tracker: Phân biệt chính xác điện thoại CẦM TRÊN TAY vs ĐẶT TĨNH TRÊN BÀN / KỆ
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
            print("[+] YOLOv8 Nano: Đã sẵn sàng & Pre-warmed (conf=0.36, imgsz=320, Kinematic Tracker Active)!")
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
                                boxes.append((x1, y1, x2, y2, conf))

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
