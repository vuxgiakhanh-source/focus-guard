# -*- coding: utf-8 -*-
"""
FocusGuard - Công cụ chẩn đoán cài đặt.

Cách dùng (mở CMD trong thư mục dự án):
    python diagnose.py              # kiểm tra file, thư viện, âm thanh, mô hình mặt, YOLO
    python diagnose.py --camera     # kiểm tra thêm webcam
    python diagnose.py --titles 20  # 20 giây: in tiêu đề cửa sổ đang mở + app đánh giá nó là gì
                                    # (mở Facebook / Edge / Chrome ngay lúc đó để xem app có bắt được không)
    python diagnose.py --play       # phát thử một câu cảnh báo bằng đúng cách app đang phát

Gửi toàn bộ kết quả in ra cho người hỗ trợ khi app "không báo gì".
"""
import importlib
import os
import platform
import sys
import time

try:
    if sys.stdout and hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    if sys.stderr and hasattr(sys.stderr, 'reconfigure'):
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass

BASE = os.path.dirname(os.path.abspath(__file__))
if not os.path.exists(os.path.join(BASE, "face_landmarker.task")):
    for cd in [os.getcwd(), r"D:\focus-guard", r"D:/focus-guard"]:
        if os.path.exists(os.path.join(cd, "face_landmarker.task")):
            BASE = os.path.abspath(cd)
            break

SOUNDS = ["away", "break_end", "break_start", "drowsy", "facebook", "gaze_away",
          "look_away", "phone", "web_distract", "yawn", "youtube"]
problems = []


def say(level, name, detail=""):
    tag = {"ok": "[ OK ]", "warn": "[CHÚ Ý]", "fail": "[LỖI ]", "info": "[ .. ]"}[level]
    print(f"{tag} {name}" + (f" -> {detail}" if detail else ""))
    if level in ("warn", "fail"):
        problems.append((level, name, detail))


def check_environment():
    v = sys.version_info
    ver = f"{v.major}.{v.minor}.{v.micro}"
    if (3, 10) <= (v.major, v.minor) <= (3, 12):
        say("ok", f"Python {ver}")
    else:
        say("warn", f"Python {ver}", "README khuyên dùng 3.10-3.12. Bản mới hơn có thể thiếu gói cài sẵn "
            "(ví dụ pygame chưa có wheel Windows cho 3.14) -> cài lỗi hoặc mất âm thanh giọng nói.")
    if platform.system() == "Windows":
        say("ok", "Hệ điều hành", platform.platform())
    else:
        say("warn", "Hệ điều hành", f"{platform.system()} - app dùng winsound / user32 nên chỉ chạy đầy đủ trên Windows.")
    if os.path.normcase(os.getcwd()) != os.path.normcase(BASE):
        say("ok", "Thư mục dự án", f"Đã định vị tại {BASE}")
    else:
        say("ok", "Thư mục đang chạy", "đúng thư mục dự án")
    exe = os.path.basename(sys.executable).lower()
    if exe.startswith("pythonw"):
        say("warn", "Đang chạy bằng pythonw", "không có cửa sổ lệnh nên mọi thông báo lỗi bị ẩn; dùng FocusGuard_Console.bat để thấy lỗi.")


def check_files():
    def size(p):
        return os.path.getsize(os.path.join(BASE, p)) if os.path.exists(os.path.join(BASE, p)) else None

    s = size("face_landmarker.task")
    say("ok" if s and s > 1_000_000 else "fail", "face_landmarker.task", f"{s} byte" if s else "THIẾU hoặc rỗng")
    s = size("yolov8n.pt")
    if not s or s < 1_000_000:
        say("fail", "yolov8n.pt", "THIẾU hoặc rỗng (có thể git clone lỗi / tải thiếu file)")
    else:
        with open(os.path.join(BASE, "yolov8n.pt"), "rb") as f:
            magic = f.read(2)
        say("ok" if magic == b"PK" else "fail", "yolov8n.pt", f"{s} byte" + ("" if magic == b"PK" else " - KHÔNG phải file model hợp lệ (có thể là file LFS/HTML)"))
    missing = [n for n in SOUNDS if not size(os.path.join("sounds", n + ".mp3"))]
    say("ok" if not missing else "fail", "Thư mục sounds/", "đủ 11 file" if not missing else "thiếu: " + ", ".join(missing))


def check_imports():
    mods = [("cv2", "opencv-python"), ("numpy", "numpy"), ("mediapipe", "mediapipe"), ("pygame", "pygame"),
            ("ultralytics", "ultralytics"), ("torch", "torch"), ("psutil", "psutil"), ("PIL", "pillow")]
    loaded = {}
    for mod, pipname in mods:
        try:
            m = importlib.import_module(mod)
            loaded[mod] = m
            say("ok", f"import {mod}", getattr(m, "__version__", ""))
        except Exception as e:
            hint = f"pip install {pipname}"
            extra = ""
            if mod == "pygame":
                extra = "  => KHÔNG có pygame thì mọi cảnh báo chỉ còn tiếng 'tít' (không có giọng nói)."
            if mod in ("ultralytics", "torch"):
                extra = "  => KHÔNG có thì tắt hoàn toàn nhận diện điện thoại."
            say("fail", f"import {mod}", f"{type(e).__name__}: {str(e)[:120]} | thử: {hint}{extra}")
    try:
        from importlib import metadata
        cv_pk = sorted({d.metadata["Name"] for d in metadata.distributions()
                        if d.metadata["Name"] and d.metadata["Name"].lower().startswith("opencv-")})
        if len(cv_pk) > 1:
            say("warn", "Nhiều gói OpenCV cùng cài", ", ".join(cv_pk) + " (cùng ghi đè module cv2; nếu lỗi imshow/crash hãy gỡ bớt, chỉ giữ 1)")
    except Exception:
        pass
    return loaded


def check_audio(loaded, play=False):
    pg = loaded.get("pygame")
    if not pg:
        say("fail", "Âm thanh giọng nói", "pygame không dùng được -> app sẽ chỉ phát tiếng 'tít' (winsound.Beep)")
        return
    try:
        pg.mixer.init()
        say("ok", "pygame.mixer.init", str(pg.mixer.get_init()))
    except Exception as e:
        say("fail", "pygame.mixer.init", f"{type(e).__name__}: {e} (không có thiết bị âm thanh / bị app khác giữ?) -> app chỉ phát 'tít'")
        return
    bad = []
    for n in SOUNDS:
        p = os.path.join(BASE, "sounds", n + ".mp3")
        if not os.path.exists(p):
            continue
        try:
            pg.mixer.music.load(p)
        except Exception as e:
            bad.append(f"{n}: {str(e)[:50]}")
    say("ok" if not bad else "fail", "Giải mã các file mp3", "tất cả nạp được" if not bad else "; ".join(bad))
    if play:
        try:
            pg.mixer.music.load(os.path.join(BASE, "sounds", "away.mp3"))
            pg.mixer.music.play()
            say("info", "Đang phát away.mp3...", "bạn có nghe giọng nói không? (nếu chỉ im lặng: kiểm tra loa/âm lượng Windows)")
            t0 = time.time()
            while pg.mixer.music.get_busy() and time.time() - t0 < 6:
                time.sleep(0.1)
        except Exception as e:
            say("fail", "Phát thử", str(e))


def check_face_model():
    try:
        from mediapipe.tasks import python as mp_python
        from mediapipe.tasks.python import vision
        import mediapipe as mp
        import numpy as np
        opts = vision.FaceLandmarkerOptions(
            base_options=mp_python.BaseOptions(model_asset_path=os.path.join(BASE, "face_landmarker.task")),
            running_mode=vision.RunningMode.IMAGE, num_faces=1)
        lm = vision.FaceLandmarker.create_from_options(opts)
        img = mp.Image(image_format=mp.ImageFormat.SRGB, data=np.zeros((240, 320, 3), np.uint8))
        lm.detect(img)
        say("ok", "MediaPipe FaceLandmarker", "nạp model và chạy được")
    except Exception as e:
        say("fail", "MediaPipe FaceLandmarker", f"{type(e).__name__}: {str(e)[:150]}")


def check_yolo():
    try:
        import numpy as np
        from ultralytics import YOLO
        t0 = time.time()
        model = YOLO(os.path.join(BASE, "yolov8n.pt"))
        names = getattr(model, "names", {})
        cls = names.get(67) if isinstance(names, dict) else None
        res = model.predict(np.zeros((256, 256, 3), np.uint8), classes=[67], conf=0.5, verbose=False, imgsz=256)
        say("ok" if cls == "cell phone" else "fail", "YOLOv8n", f"nạp + chạy được trong {time.time() - t0:.1f}s; lớp 67 = {cls!r}")
    except Exception as e:
        say("fail", "YOLOv8n", f"{type(e).__name__}: {str(e)[:150]} -> app sẽ KHÔNG nhận diện được điện thoại (chỉ in lỗi ra console)")


def check_camera():
    try:
        import cv2
        backend = cv2.CAP_DSHOW if platform.system() == "Windows" else 0
        cap = cv2.VideoCapture(0, backend) if backend else cv2.VideoCapture(0)
        ok, frame = cap.read() if cap.isOpened() else (False, None)
        cap.release()
        if ok:
            say("ok", "Webcam 0", f"đọc được khung {frame.shape[1]}x{frame.shape[0]}")
        else:
            say("fail", "Webcam 0", "không mở/đọc được (app khác đang dùng camera? quyền camera trong Windows?)")
    except Exception as e:
        say("fail", "Webcam", str(e))


def watch_titles(seconds):
    if platform.system() != "Windows":
        say("warn", "--titles", "chỉ chạy trên Windows")
        return
    sys.path.insert(0, BASE)
    from app_monitor import AppDistractionMonitor
    mon = AppDistractionMonitor()
    print(f"\nTrong {seconds}s: hãy bấm sang Facebook / YouTube / trang bạn muốn thử rồi cuộn trang liên tục.\n")
    t_end = time.time() + seconds
    last = None
    while time.time() < t_end:
        r = mon.check_distraction()
        title = mon.get_foreground_title()
        idle = mon.get_system_idle_seconds()
        verdict = "không coi là xao nhãng"
        if r:
            verdict = f"{r['label']} | thao tác {r['duration']}s/6s | {'>>> SẼ BÁO <<<' if r['should_alert'] else 'chưa đủ'}"
        line = f"idle={idle:4.1f}s | {verdict} | tiêu đề: {title[:70]}"
        if line != last:
            print(line)
            last = line
        time.sleep(0.25)


def main():
    args = sys.argv[1:]
    print("=" * 70)
    print(" FOCUSGUARD - CHẨN ĐOÁN CÀI ĐẶT")
    print("=" * 70)
    check_environment()
    check_files()
    loaded = check_imports()
    check_audio(loaded, play="--play" in args)
    if "mediapipe" in loaded:
        check_face_model()
    if "ultralytics" in loaded and "torch" in loaded:
        check_yolo()
    if "--camera" in args:
        check_camera()
    if "--titles" in args:
        i = args.index("--titles")
        secs = int(args[i + 1]) if i + 1 < len(args) and args[i + 1].isdigit() else 15
        watch_titles(secs)
    print("=" * 70)
    fails = [p for p in problems if p[0] == "fail"]
    warns = [p for p in problems if p[0] == "warn"]
    print(f" KẾT QUẢ: {len(fails)} lỗi, {len(warns)} chú ý.")
    for lvl, name, detail in problems:
        print(f"   - [{'LỖI' if lvl == 'fail' else 'CHÚ Ý'}] {name}")
    print("=" * 70)


if __name__ == "__main__":
    main()
