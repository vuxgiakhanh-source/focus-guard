# -*- coding: utf-8 -*-
import os
# GIỚI HẠN TUYỆT ĐỐI 1 THREAD CHO MỌI THƯ VIỆN TOÁN HỌC & AI (Khóa chặt CPU <= 15%)
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"
os.environ["VECLIB_MAXIMUM_THREADS"] = "1"
os.environ["NUMEXPR_NUM_THREADS"] = "1"
os.environ["TORCH_NUM_THREADS"] = "1"

try:
    import torch
    import ultralytics.utils.torch_utils as tu
    tu.NUM_THREADS = 1
    torch.set_num_threads(1)
    torch.set_num_interop_threads(1)
except Exception:
    pass

import cv2
cv2.setNumThreads(1)
import time
import sys
import gc
import ctypes

# Tối ưu Garbage Collector: Giảm tần suất dọn dẹp để triệt tiêu hiện tượng giật khung hình
gc.set_threshold(50000, 15, 15)

# Bật đồng hồ thời gian thực Windows độ chính xác cao 1ms
try:
    ctypes.windll.winmm.timeBeginPeriod(1)
except Exception:
    pass

# Đảm bảo in UTF-8 không lỗi trên Windows
try:
    if sys.stdout and hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass

from detector import FocusDetector
from phone_detector import PhoneDetector
from alert import SoundAlertManager
from ui_utils import HUDRenderer
from pomodoro import PomodoroTimer
from history import SessionHistoryManager
from toast_notifier import WindowsToastManager
from app_monitor import AppDistractionMonitor

WIN_TITLE = "FocusGuard - AI Distraction & Drowsiness Detector"

_instance_mutex = None

def enforce_single_instance():
    """
    Đảm bảo chỉ có duy nhất 1 phiên bản FocusGuard PRO hoạt động cùng lúc.
    Ngăn chặn hoàn toàn tình trạng mở 2 app cùng lúc làm nghẽn webcam dẫn tới màn hình đen
    và liên tục báo sai 'quay lại bàn học'.
    """
    global _instance_mutex
    ERROR_ALREADY_EXISTS = 183
    mutex_name = "FocusGuard_PRO_SingleInstance_Mutex_v2"

    try:
        _instance_mutex = ctypes.windll.kernel32.CreateMutexW(None, False, mutex_name)
        last_error = ctypes.windll.kernel32.GetLastError()
        if last_error == ERROR_ALREADY_EXISTS:
            user32 = ctypes.windll.user32
            hwnd = user32.FindWindowW(None, WIN_TITLE)
            if hwnd:
                user32.ShowWindow(hwnd, 9)  # SW_RESTORE
                user32.SetForegroundWindow(hwnd)
            user32.MessageBoxW(
                0,
                "FocusGuard PRO hiện đang chạy trên máy tính rồi bạn nhé!\n\n"
                "Cửa sổ ứng dụng đã được đưa lên phía trước để bạn tiếp tục buổi học.",
                "FocusGuard PRO - Ứng Dụng Đang Chạy",
                0x40 | 0x00  # MB_ICONINFORMATION | MB_OK
            )
            sys.exit(0)
    except Exception:
        pass

def cleanup_single_instance():
    global _instance_mutex
    if _instance_mutex:
        try:
            ctypes.windll.kernel32.CloseHandle(_instance_mutex)
            _instance_mutex = None
        except Exception:
            pass

def run_focus_guard():
    print("=" * 65)
    print("        FOCUSGUARD PRO - HỆ THỐNG TRỢ LÝ HỌC TẬP THỊ GIÁC AI")
    print("    (EMA FILTER + IRIS GAZE + POMODORO + TOAST + TỰ CÂN CHỈNH MẮT)")
    print("=" * 65)

    history_mgr = SessionHistoryManager()
    toast_mgr = WindowsToastManager()

    # In thống kê lịch sử tích lũy khi khởi động
    summary = history_mgr.get_summary_stats()
    print(f"[*] Lịch sử học tập tích lũy: {summary['total_minutes']} phút ({summary['total_sessions']} phiên)")
    if summary['today_sessions'] > 0:
        print(f"[*] Hôm nay bạn đã học     : {summary['today_minutes']} phút (Điểm trung bình: {summary['today_avg_score']}%)")

    print("[*] Đang khởi tạo các mô hình AI và camera...")

    try:
        detector = FocusDetector(model_path="face_landmarker.task")
    except Exception as e:
        print(f"[-] Lỗi khởi tạo mô hình FaceMesh: {e}")
        return

    phone_detector = PhoneDetector(model_name="yolov8n.pt", conf_thresh=0.40)
    alert_mgr = SoundAlertManager()
    hud = HUDRenderer()
    pomodoro = PomodoroTimer(work_min=25, break_min=5)
    app_monitor = AppDistractionMonitor(active_operate_thresh_sec=6.0, idle_timeout_sec=2.0)

    # Khởi tạo camera với DirectShow (mở cực nhanh <0.2s trên Windows) và tự động thử camera 1 nếu camera 0 bận
    cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
    if not cap.isOpened():
        cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        cap = cv2.VideoCapture(1, cv2.CAP_DSHOW)
    if not cap.isOpened():
        cap = cv2.VideoCapture(1)

    if not cap.isOpened():
        print("[-] Không thể mở Webcam. Vui lòng kiểm tra quyền camera hoặc cắm webcam!")
        try:
            import ctypes
            ctypes.windll.user32.MessageBoxW(
                0,
                "Không thể kết nối với Webcam!\n\n"
                "Vui lòng kiểm tra:\n"
                "1. Webcam có đang bị ứng dụng khác (Zoom, Teams, Discord, Chrome...) chiếm dụng không?\n"
                "2. Kiểm tra quyền truy cập Camera trong Windows Settings -> Privacy -> Camera.",
                "FocusGuard PRO - Lỗi Camera",
                0x10 | 0x00
            )
        except Exception:
            pass
        phone_detector.stop()
        return

    # Cài đặt độ phân giải chuẩn 640x480 và triệt tiêu độ trễ bộ đệm (Zero Buffer Delay)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
    cap.set(cv2.CAP_PROP_FPS, 20)

    # Đăng ký sự kiện Click chuột lên các nút giao diện
    mouse_click_action = None
    def on_mouse_event(event, x, y, flags, param):
        nonlocal mouse_click_action
        if event == cv2.EVENT_LBUTTONDOWN:
            btn_clicked = hud.get_clicked_button(x, y)
            if btn_clicked:
                mouse_click_action = btn_clicked

    cv2.namedWindow(WIN_TITLE)
    cv2.setMouseCallback(WIN_TITLE, on_mouse_event)

    print("[+] Camera đã sẵn sàng!")
    print("    - [Click / C] : XÁC ĐỊNH KHUNG HỌC (10s thu thập góc quay bàn học & mắt, bấm C chốt sớm).")
    print("    - [Click / P] : BẬT / TẮT đồng hồ Pomodoro (25p học / 5p nghỉ / 15p nghỉ dài sau 4 hiệp).")
    print("    - [Click / H] : BẬT / TẮT bảng THỐNG KÊ & CHUỖI HỌC TẬP (Daily Streak).")
    print("    - [Click / M] : BẬT / TẮT âm thanh cảnh báo.")
    print("    - [Click / R] : RESET điểm tập trung.")
    print("    - [Click / Q] : THOÁT ứng dụng & Lưu lịch sử học tập.")
    print("=" * 65)

    streak_days, _ = history_mgr.calculate_streak()
    streak_msg = f"🔥 Chuỗi học tập hiện tại: {streak_days} ngày! Chúc bạn học tốt!" if streak_days > 0 else "Hệ thống giám sát tập trung đã sẵn sàng! Chúc bạn học tốt!"
    print(f"[*] {streak_msg}")

    start_time = time.time()
    is_muted = False
    show_stats = False
    stats_data = None
    distraction_events = 0
    drowsy_events = 0
    phone_events = 0
    web_events = 0
    last_alert_state = False
    last_web_alerting = False

    alert_msg = ""
    alert_msg_time = 0
    last_recording_state = False

    TARGET_FPS = 20
    FRAME_INTERVAL = 1.0 / TARGET_FPS  # 0.050 giây (20 FPS mượt mà chuẩn công thái học)

    failed_frames_count = 0
    while True:
        loop_start = time.perf_counter()
        ret, frame = cap.read()
        if not ret:
            failed_frames_count += 1
            if failed_frames_count > 10:
                print("[-] Không đọc được frame từ webcam (mất tín hiệu camera).")
                break
            time.sleep(0.03)
            continue
        failed_frames_count = 0

        # Đảm bảo độ phân giải luôn chuẩn xác 640x480 trên mọi loại webcam (tránh giật lag do webcam 1080p/4K)
        if frame.shape[1] != 640 or frame.shape[0] != 480:
            frame = cv2.resize(frame, (640, 480), interpolation=cv2.INTER_LINEAR)

        cv2.flip(frame, 1, dst=frame)

        # 1. Cập nhật đồng hồ Pomodoro (hỗ trợ Nghỉ Dài sau 4 hiệp)
        pomo_state, pomo_time_left, pomo_event = pomodoro.update()
        if pomo_event == "LONG_BREAK_START":
            alert_mgr.play_voice("BREAK_START", force=True)
            print("[*] POMODORO: 4 chu kỳ học hoàn thành! Bắt đầu NGHỈ DÀI 15 PHÚT!")
        elif pomo_event == "BREAK_START":
            alert_mgr.play_voice("BREAK_START", force=True)
            print("[*] POMODORO: Hết 25 phút học! Nghỉ giải lao 5 phút thoải mái!")
        elif pomo_event == "BREAK_END":
            alert_mgr.play_voice("BREAK_END", force=True)
            print("[*] POMODORO: Hết giờ nghỉ! Bắt đầu buổi học tiếp theo!")

        is_break = (pomo_state == "BREAK")

        # 2. Quét điện thoại ngầm bằng YOLOv8 (Tự động ngủ 100% trong giờ giải lao để làm mát máy)
        if not is_break:
            phone_detector.update_frame(frame)
            detected_phones = phone_detector.get_detected_phones()
        else:
            detected_phones = []

        # 3. Chạy AI phân tích (EMA, Gaze, HeadPose, Adaptive EAR)
        result = detector.process_frame(frame, detected_phones=detected_phones, is_pomodoro_break=is_break)

        # 3.5 Giám sát thao tác trên Facebook / YouTube / Mạng xã hội trên máy tính
        web_distract = app_monitor.check_distraction(is_pomodoro_break=is_break)
        is_web_alerting = bool(web_distract and web_distract["should_alert"])

        # Nếu người dùng vừa tắt Facebook/YouTube -> Dừng cảnh báo giọng nói NGAY LẬP TỨC (Zero Lag)!
        if last_web_alerting and not is_web_alerting:
            alert_mgr.stop(min_play_sec=0, fade_ms=150)

        last_web_alerting = is_web_alerting

        if is_web_alerting:
            detector._update_energy("DISTRACTED", time.time())
            result["focus_score"] = detector.get_focus_score()
            result["status"] = "DISTRACTED"
            result["label"] = f"PHÁT HIỆN ĐANG DÙNG {web_distract['label'].upper()}!"
            result["reason"] = f"Đang thao tác trên {web_distract['label']} ({web_distract['duration']:.1f}s)!"
            result["alert"] = True
            result["alert_type"] = web_distract["alert_type"]
        elif web_distract and web_distract["is_distracted"]:
            result["label"] = f"CHẠM VÀO {web_distract['label'].upper()}"
            result["reason"] = f"Đang tương tác ({web_distract['duration']:.1f}s)..."


        # Theo dõi chuyển trạng thái của quá trình xác định khung học
        is_rec = result.get("is_recording_zone", False)
        if last_recording_state and not is_rec:
            calib_summary = result.get("calib_result_msg") or detector.last_calib_msg or "ĐÃ XÁC ĐỊNH XONG KHUNG HỌC TỰ NHIÊN! ✓"
            alert_msg = calib_summary
            alert_msg_time = time.time()
        last_recording_state = is_rec

        # Theo dõi tự động thích ứng góc học tập mới (Autonomous Zone Adaptation)
        auto_msg = result.get("auto_adapted_zone")
        if auto_msg and alert_msg != auto_msg:
            alert_msg = auto_msg
            alert_msg_time = time.time()

        # 4. Vẽ hộp nhận diện điện thoại (Đỏ nếu đang CẦM TRÊN TAY, Lam nếu ĐẶT TĨNH TRÊN BÀN)
        if detected_phones and not is_break:
            for item in detected_phones:
                if len(item) == 6:
                    x1, y1, x2, y2, conf, is_held = item
                else:
                    x1, y1, x2, y2, conf = item
                    is_held = True

                if is_held:
                    # Điện thoại đang cầm trên tay: Hộp đỏ cảnh báo
                    cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 0, 255), 3)
                    top_y = max(0, y1 - 28)
                    cv2.rectangle(frame, (x1, top_y), (min(frame.shape[1], x1 + 205), y1), (0, 0, 255), -1)
                    cv2.putText(frame, f"DIEN THOAI TREN TAY {int(conf*100)}%", (x1 + 6, max(18, y1 - 8)),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.46, (255, 255, 255), 1, cv2.LINE_AA)
                elif conf >= 0.52:
                    # Điện thoại đặt trên bàn / kệ: Chỉ hiển thị nếu độ tin cậy >= 52% (chống vẽ nhầm lên sách vở)
                    cv2.rectangle(frame, (x1, y1), (x2, y2), (210, 180, 0), 2)
                    top_y = max(0, y1 - 24)
                    cv2.rectangle(frame, (x1, top_y), (min(frame.shape[1], x1 + 195), y1), (180, 130, 20), -1)
                    cv2.putText(frame, "DIEN THOAI (TREN BAN)", (x1 + 6, max(16, y1 - 7)),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.44, (255, 255, 255), 1, cv2.LINE_AA)

        if result["alert"] and not is_break:
            if not last_alert_state:
                alert_type = result.get("alert_type")
                if alert_type in ["FACEBOOK", "YOUTUBE", "WEB_DISTRACT"]:
                    web_events += 1
                elif alert_type == "PHONE":
                    phone_events += 1
                elif result["status"] == "DROWSY":
                    drowsy_events += 1
                elif result["status"] in ["DISTRACTED", "AWAY"]:
                    distraction_events += 1
                last_alert_state = True

            if not is_muted and result.get("alert_type"):
                # Giãn cách thông minh: Không bao giờ nói lặp đi lặp lại quấy rầy người học
                if result["alert_type"] == "AWAY":
                    voice_cd = 60.0    # Rời bàn chỉ nhắc 1 lần, 60s sau mới nhắc lại nếu vẫn chưa về
                elif result["alert_type"] in ["FACEBOOK", "YOUTUBE", "WEB_DISTRACT"]:
                    voice_cd = 20.0    # Mạng xã hội giãn cách 20s
                elif result["alert_type"] == "PHONE":
                    voice_cd = 16.0    # Điện thoại giãn cách 16s
                elif result["alert_type"] == "DROWSY":
                    voice_cd = 15.0    # Buồn ngủ giãn cách 15s
                else:
                    voice_cd = 18.0    # Quay mặt đi giãn cách 18s (triệt tiêu nói lặp 3.5s)
                alert_mgr.play_voice(result["alert_type"], cooldown=voice_cd)
        else:
            # Ngay khi quay lại tập trung: Dừng âm thanh nếu đã phát xong câu cảnh báo (chống ngắt ngang ngắp ngứ)
            if last_alert_state:
                alert_mgr.stop(min_play_sec=1.4, fade_ms=250)
            last_alert_state = False

        # 6. Quản lý thông báo nổi
        active_msg = ""
        if time.time() - alert_msg_time < 2.5:
            active_msg = alert_msg

        # 7. Vẽ giao diện HUD chuyên nghiệp
        elapsed_sec = time.time() - start_time
        pomodoro_info = (pomo_state, pomo_time_left) if pomodoro.is_active else None
        frame = hud.draw_hud(
            frame,
            result,
            elapsed_sec,
            pomodoro_info=pomodoro_info,
            is_muted=is_muted,
            alert_msg=active_msg,
            show_stats=show_stats,
            stats_data=stats_data
        )

        # 8. Hiển thị
        cv2.imshow(WIN_TITLE, frame)

        # 9. Bắt phím bấm và kiểm tra đóng cửa sổ (bấm nút X)
        if cv2.getWindowProperty(WIN_TITLE, cv2.WND_PROP_VISIBLE) < 1:
            print("[*] Đóng cửa sổ ứng dụng.")
            break

        # Precision Frame Pacer (Khóa chặt CPU <= 15%, ngủ đúng thời gian còn lại của frame 50ms)
        loop_elapsed = time.perf_counter() - loop_start
        remaining = FRAME_INTERVAL - loop_elapsed
        wait_ms = max(1, int(remaining * 1000)) if remaining > 0 else 1
        key = cv2.waitKey(wait_ms) & 0xFF

        # Xử lý hành động từ Click chuột hoặc Phím tắt bàn phím
        action = None
        if mouse_click_action:
            action = mouse_click_action
            mouse_click_action = None
            if show_stats and action != "STATS":
                show_stats = False
        elif key == ord('q') or key == ord('Q') or key == 27:
            action = "QUIT"
        elif key == ord('c') or key == ord('C'):
            action = "CALIBRATE"
        elif key == ord('p') or key == ord('P'):
            action = "POMODORO"
        elif key == ord('h') or key == ord('H'):
            action = "STATS"
        elif key == ord('r') or key == ord('R'):
            action = "RESET"
        elif key == ord('m') or key == ord('M'):
            action = "MUTE"
        elif key != 255 and show_stats:
            # Nhấn bất kỳ phím nào khác để đóng bảng thống kê
            show_stats = False

        if action == "QUIT":
            break
        elif action == "CALIBRATE":
            if detector.is_recording_zone:
                msg = detector.finalize_zone_learning()
            else:
                msg = detector.start_zone_learning(duration=10.0)
            alert_msg = msg
            alert_msg_time = time.time()
        elif action == "POMODORO":
            state_active = pomodoro.toggle()
            print(f"[*] Chế độ Pomodoro: {'BẬT' if state_active else 'TẮT'}")
        elif action == "STATS":
            show_stats = not show_stats
            if show_stats:
                stats_data = history_mgr.get_summary_stats()
            print(f"[*] Bảng thống kê học tập: {'MỞ' if show_stats else 'ĐÓNG'}")
        elif action == "RESET":
            detector.reset_focus_score()
            hud.score_history = [100.0, 100.0]
            start_time = time.time()
            pomodoro.reset()
            print("[*] Đã reset điểm tập trung và đồng hồ Pomodoro.")
        elif action == "MUTE":
            is_muted = not is_muted
            if is_muted:
                alert_mgr.stop(min_play_sec=0, fade_ms=100)
            state_str = "TẮT" if is_muted else "BẬT"
            print(f"[*] Âm thanh cảnh báo: {state_str}")

    alert_mgr.stop(min_play_sec=0, fade_ms=100)
    phone_detector.stop()
    cap.release()
    cv2.destroyAllWindows()

    try:
        ctypes.windll.winmm.timeEndPeriod(1)
    except Exception:
        pass

    final_score = detector.get_focus_score()

    # 10. Tự động lưu phiên học vào focus_history.json và in báo cáo chi tiết
    saved_session = history_mgr.save_session(
        start_time=start_time,
        end_time=time.time(),
        focus_score=final_score,
        phone_events=phone_events,
        distraction_events=distraction_events,
        drowsy_events=drowsy_events,
        pomo_cycles=pomodoro.completed_cycles,
        web_events=web_events
    )

    history_mgr.print_report(saved_session)

if __name__ == "__main__":
    enforce_single_instance()
    try:
        run_focus_guard()
    except Exception as e:
        import traceback
        err_msg = traceback.format_exc()
        try:
            import ctypes
            ctypes.windll.user32.MessageBoxW(
                0,
                f"Đã xảy ra lỗi khi chạy FocusGuard PRO:\n\n{err_msg}",
                "FocusGuard PRO - Lỗi Khởi Chạy",
                0x10 | 0x00
            )
        except Exception:
            pass
    finally:
        cleanup_single_instance()
