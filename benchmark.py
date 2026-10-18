# -*- coding: utf-8 -*-
import cv2, time, numpy as np, psutil, os, sys
sys.stdout.reconfigure(encoding='utf-8')

print('=' * 60)
print('   FOCUSGUARD - BENCHMARK CHINH XAC (TACH CAMERA I/O)')
print('=' * 60)

from detector import FocusDetector
from phone_detector import PhoneDetector
from alert import SoundAlertManager
from ui_utils import HUDRenderer
from pomodoro import PomodoroTimer

detector = FocusDetector('face_landmarker.task')
phone_det = PhoneDetector('yolov8n.pt', conf_thresh=0.45)
hud = HUDRenderer()
pomo = PomodoroTimer()

cap = cv2.VideoCapture(0)
if not cap.isOpened():
    print('Khong mo duoc camera')
    exit(1)
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

# Warmup 10 frames (cho YOLO load xong, camera on dinh)
print('\nWarmup 10 frames...')
for _ in range(10):
    ret, frame = cap.read()
    if ret:
        frame = cv2.flip(frame, 1)
        phone_det.update_frame(frame)
        detector.process_frame(frame)
time.sleep(1.0)  # Cho YOLO warmup xong
print('Warmup xong!\n')

# Benchmark 60 frames - TACH RIENG thoi gian doc camera va thoi gian xu ly AI
proc = psutil.Process(os.getpid())
_ = proc.cpu_percent(interval=None)

cam_times = []
ai_times = []
hud_times = []
total_times = []

for i in range(60):
    # Do thoi gian doc camera (I/O hardware, khong phai loi code)
    tc0 = time.perf_counter()
    ret, frame = cap.read()
    tc1 = time.perf_counter()
    if not ret:
        break
    frame = cv2.flip(frame, 1)
    cam_times.append((tc1 - tc0) * 1000)

    # Do thoi gian xu ly AI (MediaPipe + EAR + HeadPose + Gaze + Phone)
    ta0 = time.perf_counter()
    pomo_state, pomo_time, _ = pomo.update()
    phone_det.update_frame(frame)
    phones = phone_det.get_detected_phones()
    result = detector.process_frame(frame, detected_phones=phones)
    ta1 = time.perf_counter()
    ai_times.append((ta1 - ta0) * 1000)

    # Do thoi gian ve HUD
    th0 = time.perf_counter()
    frame_out = hud.draw_hud(frame, result, float(i), pomodoro_info=(pomo_state, pomo_time))
    th1 = time.perf_counter()
    hud_times.append((th1 - th0) * 1000)

    total_times.append(cam_times[-1] + ai_times[-1] + hud_times[-1])

cpu_usage = proc.cpu_percent(interval=0.5)
cap.release()
phone_det.stop()

print('KET QUA CHI TIET (60 frames sau warmup):')
print('-' * 60)
print(f'  Camera I/O (hardware):')
print(f'    Trung binh: {np.mean(cam_times):.2f} ms | Max: {np.max(cam_times):.2f} ms')
print(f'  AI Processing (MediaPipe + HeadPose + EAR + Gaze):')
print(f'    Trung binh: {np.mean(ai_times):.2f} ms | Max: {np.max(ai_times):.2f} ms')
print(f'  HUD Rendering (giao dien):')
print(f'    Trung binh: {np.mean(hud_times):.2f} ms | Max: {np.max(hud_times):.2f} ms')
print('-' * 60)
code_avg = np.mean(ai_times) + np.mean(hud_times)
print(f'  => CODE XU LY THUC (AI + HUD): {code_avg:.2f} ms/frame')
print(f'  => Camera I/O (khong phai loi code): {np.mean(cam_times):.2f} ms/frame')
print(f'  => CPU process usage: {cpu_usage:.1f}%')
print()

# Tinh CPU% thuc te cua code (khong tinh cam wait)
cam_pct = np.mean(cam_times) / (np.mean(cam_times) + code_avg) * 100
target_fps = 6
frame_budget_ms = 1000.0 / target_fps
code_pct = code_avg / frame_budget_ms * 100
print(f'  Code chiem {code_pct:.1f}% ngan sach xu ly moi frame ({target_fps} FPS)')
print(f'  Camera I/O chiem {cam_pct:.0f}% tong frame time')

if code_avg < 8:
    grade = 'S+ (CUC KY NHE - duoi 8ms)'
elif code_avg < 15:
    grade = 'A (RAT NHE - duoi 15ms)'
elif code_avg < 25:
    grade = 'B (NHE - duoi 25ms)'
else:
    grade = 'C (CAN TOI UU)'

print(f'\n  >>> XEP HANG CODE: {grade}')
print('=' * 60)
