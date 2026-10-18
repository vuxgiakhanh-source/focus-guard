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

cap = cv2.VideoCapture(0)
if not cap.isOpened():
    print('Khong mo duoc camera')
    exit(1)
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

detector = FocusDetector('face_landmarker.task')
phone_det = PhoneDetector('yolov8n.pt', conf_thresh=0.45)
hud = HUDRenderer()
pomo = PomodoroTimer()

# Warmup 30 frames (cho YOLO load xong, camera on dinh)
print('\nWarmup 30 frames...')
for _ in range(30):
    ret, frame = cap.read()
    if ret:
        frame = cv2.flip(frame, 1)
        phone_det.update_frame(frame)
        detector.process_frame(frame)
time.sleep(1.0)  # Cho YOLO warmup xong
print('Warmup xong!\n')

# Benchmark 300 frames - TACH RIENG thoi gian doc camera va thoi gian xu ly AI
proc = psutil.Process(os.getpid())
_ = proc.cpu_percent(interval=None)

cam_times = []
ai_times = []
analysis_interval_sec = 0.1
last_analysis_time = 0.0
cached_result = None
hud_times = []
total_times = []
benchmark_started = time.perf_counter()

for i in range(300):
    # Do thoi gian doc camera (I/O hardware, khong phai loi code)
    tc0 = time.perf_counter()
    ret, frame = cap.read()
    tc1 = time.perf_counter()
    if not ret:
        break
    frame = cv2.flip(frame, 1)
    cam_times.append((tc1 - tc0) * 1000)

    # Do overhead luong chinh; suy luan MediaPipe/YOLO chay o worker nen
    ta0 = time.perf_counter()
    pomo_state, pomo_time, _ = pomo.update()
    phone_det.update_frame(frame)
    phones = phone_det.get_detected_phones()
    now = time.monotonic()
    if cached_result is None or now - last_analysis_time >= analysis_interval_sec:
        cached_result = detector.process_frame(frame, detected_phones=phones)
        last_analysis_time = now
    result = dict(cached_result)
    ta1 = time.perf_counter()
    ai_times.append((ta1 - ta0) * 1000)

    # Do thoi gian ve HUD
    th0 = time.perf_counter()
    frame_out = hud.draw_hud(frame, result, float(i), pomodoro_info=(pomo_state, pomo_time))
    th1 = time.perf_counter()
    hud_times.append((th1 - th0) * 1000)

    total_times.append(cam_times[-1] + ai_times[-1] + hud_times[-1])

benchmark_elapsed = time.perf_counter() - benchmark_started
measured_fps = len(cam_times) / max(benchmark_elapsed, 1e-9)
cpu_usage = proc.cpu_percent(interval=None)
cap.release()
phone_det.stop()
detector.stop()

print('KET QUA CHI TIET (300 frames sau warmup):')
print('-' * 60)
print(f'  Throughput: {measured_fps:.1f} FPS ({len(cam_times)} frames / {benchmark_elapsed:.1f}s)')
print(f'  Camera I/O (hardware):')
print(f'    Trung binh: {np.mean(cam_times):.2f} ms | Max: {np.max(cam_times):.2f} ms')
print(f'  AI main-thread overhead (queue + face-state):')
print(f'    Trung binh: {np.mean(ai_times):.2f} ms | Max: {np.max(ai_times):.2f} ms')
print(f'  HUD Rendering (giao dien):')
print(f'    Trung binh: {np.mean(hud_times):.2f} ms | Max: {np.max(hud_times):.2f} ms')
print('-' * 60)
code_avg = np.mean(ai_times) + np.mean(hud_times)
print(f'  => Main-thread work (analysis enqueue + HUD): {code_avg:.2f} ms/frame')
print(f'  => Camera I/O (khong phai loi code): {np.mean(cam_times):.2f} ms/frame')
print(f'  => CPU process usage: {cpu_usage:.1f}%')
print()

# Tinh CPU% thuc te cua code (khong tinh cam wait)
cam_pct = np.mean(cam_times) / (np.mean(cam_times) + code_avg) * 100
target_fps = 30
frame_budget_ms = 1000.0 / target_fps
code_pct = code_avg / frame_budget_ms * 100
print(f'  Main thread chiem {code_pct:.1f}% budget moi frame ({target_fps} FPS)')
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
