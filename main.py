# -*- coding: utf-8 -*-
import cv2
import time
import sys
import os

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

    phone_detector = PhoneDetector(model_name="yolov8n.pt", conf_thresh=0.28)
    alert_mgr = SoundAlertManager()
    hud = HUDRenderer()
    pomodoro = PomodoroTimer(work_min=25, break_min=5)
    app_monitor = AppDistractionMonitor(active_operate_thresh_sec=2.5, idle_timeout_sec=2.0)

    cap = cv2.VideoCapture(0)
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
    print("    - [Click / C] : DẠY AI GÓC HỌC TẬP (60 giây, tự đo độ mở mắt cho kính).")
    print("    - [Click / P] : BẬT / TẮT đồng hồ Pomodoro (25p học / 5p nghỉ).")
    print("    - [Click / M] : BẬT / TẮT âm thanh cảnh báo.")
    print("    - [Click / R] : RESET điểm tập trung.")
    print("    - [Click / Q] : THOÁT ứng dụng & Lưu lịch sử học tập.")
    print("=" * 65)

    # Bật thông báo Toast chào mừng
    toast_mgr.show_toast("FocusGuard AI", "Hệ thống giám sát tập trung đã sẵn sàng! Chúc bạn học tốt!", "welcome", cooldown=1.0)

    start_time = time.time()
    is_muted = False
    distraction_events = 0
    drowsy_events = 0
    phone_events = 0
    web_events = 0
    last_alert_state = False

    alert_msg = ""
    alert_msg_time = 0
    last_recording_state = False

    # Tự động bật học góc học tập 60s lần đầu tiên nếu chưa có file
    auto_started_learning = False

    failed_frames_count = 0
    while True:
        ret, frame = cap.read()
        if not ret:
            failed_frames_count += 1
            if failed_frames_count > 10:
                print("[-] Không đọc được frame từ webcam (mất tín hiệu camera).")
                break
            time.sleep(0.03)
            continue
        failed_frames_count = 0

        cv2.flip(frame, 1, dst=frame)

        # 1. Cập nhật đồng hồ Pomodoro
        pomo_state, pomo_time_left, pomo_event = pomodoro.update()
        if pomo_event == "BREAK_START":
            alert_mgr.play_voice("BREAK_START", force=True)
            toast_mgr.show_toast("FocusGuard Pomodoro", "☕ Hết 25 phút học! Nghỉ giải lao 5 phút thoải mái nhé!", "pomo_break", cooldown=5.0)
            print("[*] POMODORO: Hết 25 phút học! Nghỉ giải lao 5 phút thoải mái!")
        elif pomo_event == "BREAK_END":
            alert_mgr.play_voice("BREAK_END", force=True)
            toast_mgr.show_toast("FocusGuard Pomodoro", "📚 Hết 5 phút nghỉ! Bắt đầu chu kỳ học 25 phút tiếp theo!", "pomo_work", cooldown=5.0)
            print("[*] POMODORO: Hết 5 phút nghỉ! Bắt đầu buổi học tiếp theo!")

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
        if web_distract and web_distract["should_alert"]:
            if result.get("status") == "FOCUSED":
                detector.focused_frames = max(0, detector.focused_frames - 1)
                result["focus_score"] = detector.get_focus_score()
            result["status"] = "DISTRACTED"
            result["label"] = f"PHÁT HIỆN ĐANG DÙNG {web_distract['label'].upper()}!"
            result["reason"] = f"Đang thao tác trên {web_distract['label']} ({web_distract['duration']:.1f}s)!"
            result["alert"] = True
            result["alert_type"] = web_distract["alert_type"]
        elif web_distract and web_distract["is_distracted"]:
            result["label"] = f"CHẠM VÀO {web_distract['label'].upper()}"
            result["reason"] = f"Đang tương tác ({web_distract['duration']:.1f}s)..."


        # Theo dõi khi phiên học góc kết thúc
        is_rec = result.get("is_recording_zone", False)
        if last_recording_state and not is_rec:
            alert_msg = "ĐÃ GHI NHỚ VÙNG HỌC & ĐO MẮT XONG!"
            alert_msg_time = time.time()
            toast_mgr.show_toast("FocusGuard AI", f"Đã ghi nhớ vùng học tập & cân chỉnh EAR ({detector.ear_threshold:.2f}) thành công! ✓", "zone_done", cooldown=2.0)
            print(f"[+] Hoàn tất học góc học tập! Ngưỡng EAR: {detector.ear_threshold}")
        last_recording_state = is_rec

        # 4. Vẽ hộp đỏ quanh chiếc điện thoại (chỉ khi trong giờ học)
        if detected_phones and not is_break:
            for (x1, y1, x2, y2, conf) in detected_phones:
                cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 0, 255), 3)
                top_y = max(0, y1 - 28)
                cv2.rectangle(frame, (x1, top_y), (min(frame.shape[1], x1 + 180), y1), (0, 0, 255), -1)
                cv2.putText(frame, f"DIEN THOAI {int(conf*100)}%", (x1 + 6, max(18, y1 - 8)),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 2)

        # 5. Xử lý cảnh báo (Giọng nói + Windows Toast)
        if result["alert"] and not is_break:
            if not last_alert_state:
                alert_type = result.get("alert_type")
                if alert_type in ["FACEBOOK", "YOUTUBE", "WEB_DISTRACT"]:
                    web_events += 1
                    target_name = web_distract['label'] if web_distract else "mạng xã hội"
                    toast_mgr.show_toast("FocusGuard Cảnh Báo", f"⚠️ Bạn đang thao tác trên {target_name} trong giờ học! Hãy quay lại bài nhé!", "web_alert", cooldown=8.0)
                elif alert_type == "PHONE":
                    phone_events += 1
                    toast_mgr.show_toast("FocusGuard Cảnh Báo", "⚠️ Phát hiện bạn đang cầm điện thoại trên tay!", "phone_alert", cooldown=10.0)
                elif result["status"] == "DROWSY":
                    drowsy_events += 1
                    toast_mgr.show_toast("FocusGuard Cảnh Báo", "😴 Cảnh báo buồn ngủ! Hãy đứng dậy vận động hoặc rửa mặt!", "drowsy_alert", cooldown=10.0)
                elif result["status"] in ["DISTRACTED", "AWAY"]:
                    distraction_events += 1
                    toast_mgr.show_toast("FocusGuard Cảnh Báo", f"👀 {result['reason']}", "distract_alert", cooldown=10.0)
                last_alert_state = True

            if not is_muted and result.get("alert_type"):
                alert_mgr.play_voice(result["alert_type"], cooldown=3.5)
        else:
            last_alert_state = False

        # 6. Quản lý thông báo nổi
        active_msg = ""
        if time.time() - alert_msg_time < 2.5:
            active_msg = alert_msg

        # 7. Vẽ giao diện HUD chuyên nghiệp
        elapsed_sec = time.time() - start_time
        pomodoro_info = (pomo_state, pomo_time_left) if pomodoro.is_active else None
        frame = hud.draw_hud(frame, result, elapsed_sec, pomodoro_info=pomodoro_info, is_muted=is_muted, alert_msg=active_msg)

        # 8. Hiển thị
        cv2.imshow(WIN_TITLE, frame)

        # 9. Bắt phím bấm và kiểm tra đóng cửa sổ (bấm nút X)
        if cv2.getWindowProperty(WIN_TITLE, cv2.WND_PROP_VISIBLE) < 1:
            print("[*] Đóng cửa sổ ứng dụng.")
            break

        key = cv2.waitKey(1) & 0xFF

        # Xử lý hành động từ Click chuột hoặc Phím tắt bàn phím
        action = None
        if mouse_click_action:
            action = mouse_click_action
            mouse_click_action = None
        elif key == ord('q') or key == ord('Q') or key == 27:
            action = "QUIT"
        elif key == ord('c') or key == ord('C'):
            action = "CALIBRATE"
        elif key == ord('p') or key == ord('P'):
            action = "POMODORO"
        elif key == ord('r') or key == ord('R'):
            action = "RESET"
        elif key == ord('m') or key == ord('M'):
            action = "MUTE"

        if action == "QUIT":
            break
        elif action == "CALIBRATE":
            detector.start_zone_learning(60.0)
            print("[*] Bắt đầu phiên học góc học tập & đo mắt 60 giây...")
        elif action == "POMODORO":
            state_active = pomodoro.toggle()
            print(f"[*] Chế độ Pomodoro: {'BẬT' if state_active else 'TẮT'}")
        elif action == "RESET":
            detector.total_frames = 0
            detector.focused_frames = 0
            start_time = time.time()
            pomodoro.reset()
            print("[*] Đã reset điểm tập trung và đồng hồ Pomodoro.")
        elif action == "MUTE":
            is_muted = not is_muted
            state_str = "TẮT" if is_muted else "BẬT"
            print(f"[*] Âm thanh cảnh báo: {state_str}")

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

    try:
        dur_mins, dur_secs = divmod(int(time.time() - start_time), 60)
        toast_mgr.show_toast(
            "FocusGuard PRO",
            f"🎉 Phiên học kết thúc! Thời gian: {dur_mins}p {dur_secs}s | Tập trung: {final_score:.0f}%\nĐã lưu vào lịch sử học tập!",
            toast_key="session_done",
            cooldown=0.0
        )
        time.sleep(0.4)
    except Exception:
        pass

    history_mgr.print_report(saved_session)

if __name__ == "__main__":
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
