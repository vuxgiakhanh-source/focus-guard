# -*- coding: utf-8 -*-
import os
import threading
import time
import winsound
import ctypes
import subprocess

USE_PYGAME = False
try:
    import pygame
    pygame.mixer.init()
    USE_PYGAME = True
except Exception:
    USE_PYGAME = False

VOICE_TEXTS = {
    "DROWSY": "Cảnh báo buồn ngủ! Hãy rửa mặt và vận động nhẹ!",
    "PHONE": "Bỏ điện thoại xuống và tập trung học bài!",
    "LOOKING_AWAY": "Bạn đang quay mặt đi đâu đấy? Tập trung nhìn vào màn hình!",
    "GAZE_AWAY": "Hãy tập trung ánh mắt vào bài học!",
    "AWAY": "Bạn đã rời khỏi bàn học quá lâu!",
    "YAWN": "Bạn đang ngáp và có dấu hiệu mệt mỏi!",
    "BREAK_START": "Đã hết giờ học, bắt đầu giờ giải lao!",
    "BREAK_END": "Hết giờ giải lao, hãy quay lại học tiếp!",
    "FACEBOOK": "Tắt Facebook đi và tập trung học bài!",
    "YOUTUBE": "Tắt video giải trí đi, hãy tập trung vào bài học!",
    "WEB_DISTRACT": "Đang mở trang web gây xao nhãng! Hãy quay lại học bài!"
}

class SoundAlertManager:
    def __init__(self, sounds_dir="sounds", volume=0.85):
        if sounds_dir == "sounds":
            base_dir = os.path.dirname(os.path.abspath(__file__))
            self.sounds_dir = os.path.join(base_dir, "sounds")
        else:
            self.sounds_dir = os.path.abspath(sounds_dir)

        self.volume = max(0.0, min(1.0, volume))
        self.is_playing = False
        self.last_alert_time = 0.0
        self.lock = threading.Lock()
        self._current_worker = None
        self._stop_requested = False

        if USE_PYGAME:
            try:
                pygame.mixer.music.set_volume(self.volume)
            except Exception:
                pass

        # Ánh xạ đầy đủ các loại cảnh báo và thông báo Pomodoro
        self.voice_map = {
            "DROWSY": os.path.join(self.sounds_dir, "drowsy.mp3"),
            "PHONE": os.path.join(self.sounds_dir, "phone.mp3"),
            "LOOKING_AWAY": os.path.join(self.sounds_dir, "look_away.mp3"),
            "GAZE_AWAY": os.path.join(self.sounds_dir, "gaze_away.mp3"),
            "AWAY": os.path.join(self.sounds_dir, "away.mp3"),
            "YAWN": os.path.join(self.sounds_dir, "yawn.mp3"),
            "BREAK_START": os.path.join(self.sounds_dir, "break_start.mp3"),
            "BREAK_END": os.path.join(self.sounds_dir, "break_end.mp3"),
            "FACEBOOK": os.path.join(self.sounds_dir, "facebook.mp3"),
            "YOUTUBE": os.path.join(self.sounds_dir, "youtube.mp3"),
            "WEB_DISTRACT": os.path.join(self.sounds_dir, "web_distract.mp3")
        }

    def get_backend_status(self):
        """Trả về 'PYGAME', 'MCI' hoặc 'BEEP'"""
        if USE_PYGAME:
            return "PYGAME"
        try:
            if hasattr(ctypes.windll, 'winmm'):
                return "MCI"
        except Exception:
            pass
        return "BEEP"

    def set_volume(self, volume):
        """Điều chỉnh âm lượng thông báo (0.0 đến 1.0)"""
        self.volume = max(0.0, min(1.0, float(volume)))
        if USE_PYGAME:
            try:
                pygame.mixer.music.set_volume(self.volume)
            except Exception:
                pass

    def play_voice(self, alert_type, cooldown=3.5, force=False):
        """Phát giọng nói cảnh báo trên luồng nền, đảm bảo an toàn đa luồng không chồng lấn"""
        now = time.monotonic()
        if not force and (now - self.last_alert_time < cooldown):
            return

        with self.lock:
            if self.is_playing and not force:
                return

            self._stop_requested = True
            if USE_PYGAME:
                try:
                    pygame.mixer.music.stop()
                except Exception:
                    pass
            try:
                ctypes.windll.winmm.mciSendStringW("stop fg_alert", None, 0, 0)
                ctypes.windll.winmm.mciSendStringW("close fg_alert", None, 0, 0)
            except Exception:
                pass

            prev_worker = self._current_worker
            self.is_playing = True
            self._stop_requested = False
            self.last_alert_time = now

        # Nếu có luồng cũ đang chạy, đợi luồng cũ dừng hẳn trước khi nạp bài mới
        if prev_worker and prev_worker.is_alive() and prev_worker != threading.current_thread():
            prev_worker.join(timeout=0.15)

        def _worker():
            try:
                audio_path = self.voice_map.get(alert_type)
                played = False

                # 1. Ưu tiên phát bằng Pygame (nếu có thư viện và tệp âm thanh tồn tại)
                if USE_PYGAME and audio_path and os.path.exists(audio_path):
                    try:
                        with self.lock:
                            if self._stop_requested:
                                return
                            pygame.mixer.music.load(audio_path)
                            pygame.mixer.music.set_volume(self.volume)
                            pygame.mixer.music.play()

                        while True:
                            with self.lock:
                                if self._stop_requested:
                                    break
                                busy = pygame.mixer.music.get_busy()
                            if not busy:
                                break
                            time.sleep(0.05)
                        played = True
                    except Exception:
                        played = False

                # 2. Dự phòng 1: Nếu Pygame lỗi / không có, dùng Windows MCI phát file MP3 trực tiếp (Không cần thư viện ngoài)
                if not played and audio_path and os.path.exists(audio_path):
                    try:
                        mci = ctypes.windll.winmm.mciSendStringW
                        mci("close fg_alert", None, 0, 0)
                        err = mci(f'open "{audio_path}" type mpegvideo alias fg_alert', None, 0, 0)
                        if err == 0:
                            vol = max(0, min(1000, int(self.volume * 1000)))
                            mci(f"setaudio fg_alert volume to {vol}", None, 0, 0)
                            mci("play fg_alert", None, 0, 0)

                            status_buf = ctypes.create_unicode_buffer(64)
                            # Đợi tối đa 12.0 giây (240 * 0.05s) để các câu thoại dài (youtube 6.4s, facebook 5.4s) phát trọn vẹn;
                            # tự động thoát ngay khi trạng thái chuyển sang 'stopped'
                            for _ in range(240):
                                with self.lock:
                                    if self._stop_requested:
                                        break
                                mci("status fg_alert mode", status_buf, 64, 0)
                                if status_buf.value not in ("playing", ""):
                                    break
                                time.sleep(0.05)

                            mci("stop fg_alert", None, 0, 0)
                            mci("close fg_alert", None, 0, 0)
                            played = True
                    except Exception:
                        played = False

                # 3. Dự phòng 2: Nếu file âm thanh bị thiếu, dùng Windows SAPI TTS đọc to tiếng Việt
                if not played:
                    text_prompt = VOICE_TEXTS.get(alert_type)
                    if text_prompt:
                        try:
                            ps_cmd = f"$v = New-Object -ComObject SAPI.SpVoice; $v.Volume = {int(self.volume * 100)}; $v.Speak('{text_prompt}')"
                            subprocess.run(["powershell", "-NoProfile", "-WindowStyle", "Hidden", "-Command", ps_cmd], timeout=3.5, capture_output=True)
                            played = True
                        except Exception:
                            played = False

                # 4. Dự phòng cuối cùng: Tiếng bíp chuẩn Windows
                if not played:
                    freq = 1600 if alert_type == "DROWSY" else 1100
                    winsound.Beep(freq, 400)
            except Exception:
                try:
                    winsound.MessageBeep(winsound.MB_ICONEXCLAMATION)
                except Exception:
                    pass
            finally:
                with self.lock:
                    if self._current_worker == threading.current_thread():
                        self.is_playing = False

        worker = threading.Thread(target=_worker, name="FocusGuard-AudioWorker", daemon=True)
        with self.lock:
            self._current_worker = worker
        worker.start()

    def stop(self, min_play_sec=1.2, fade_ms=250):
        """
        Dừng âm thanh mượt mà, chống hiện tượng ngắt ngang câu nói (ngắp ngứ / stuttering):
        Nếu âm thanh mới bắt đầu phát chưa đủ min_play_sec (ví dụ câu nhắc 1.2s),
        cho phép câu nói hoàn tất tự nhiên thay vì bị giật tắt giữa chừng.
        """
        now = time.monotonic()
        with self.lock:
            if not self.is_playing:
                return
            if min_play_sec > 0 and (now - self.last_alert_time < min_play_sec):
                # Đang phát câu thoại ngắn, cho phép phát trọn vẹn không bị ngắp ngứ
                return
            self._stop_requested = True
            self.is_playing = False

        if USE_PYGAME:
            try:
                if fade_ms > 0:
                    pygame.mixer.music.fadeout(fade_ms)
                else:
                    pygame.mixer.music.stop()
            except Exception:
                pass

        try:
            ctypes.windll.winmm.mciSendStringW("stop fg_alert", None, 0, 0)
            ctypes.windll.winmm.mciSendStringW("close fg_alert", None, 0, 0)
        except Exception:
            pass
