import os
import threading
import time
import winsound

USE_PYGAME = False
try:
    import pygame
    pygame.mixer.init()
    USE_PYGAME = True
except Exception:
    USE_PYGAME = False

class SoundAlertManager:
    def __init__(self, sounds_dir="sounds"):
        self.sounds_dir = sounds_dir
        self.is_playing = False
        self.last_alert_time = 0
        self.lock = threading.Lock()

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

    def play_voice(self, alert_type, cooldown=3.5, force=False):
        """Phát giọng nói cảnh báo trên luồng nền"""
        now = time.time()
        if not force and (now - self.last_alert_time < cooldown):
            return

        with self.lock:
            if self.is_playing and not force:
                return
            self.is_playing = True
            self.last_alert_time = now

        def _worker():
            try:
                audio_path = self.voice_map.get(alert_type)
                if USE_PYGAME and audio_path and os.path.exists(audio_path):
                    pygame.mixer.music.load(audio_path)
                    pygame.mixer.music.play()
                    while pygame.mixer.music.get_busy():
                        time.sleep(0.08)
                else:
                    freq = 1600 if alert_type == "DROWSY" else 1100
                    winsound.Beep(freq, 400)
            except Exception:
                try:
                    winsound.MessageBeep(winsound.MB_ICONEXCLAMATION)
                except Exception:
                    pass
            finally:
                with self.lock:
                    self.is_playing = False

        threading.Thread(target=_worker, daemon=True).start()
