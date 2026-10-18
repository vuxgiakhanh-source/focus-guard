import asyncio
import os
import sys
import edge_tts

sys.stdout.reconfigure(encoding='utf-8')
VOICE = "vi-VN-HoaiMyNeural"

EXTRA_PHRASES = {
    "break_start.mp3": "Đã xong 25 phút học tập! Bạn có 5 phút nghỉ ngơi xả hơi nhé!",
    "break_end.mp3": "Hết giờ giải lao rồi! Quay lại bàn học tiếp tục nào!",
    "gaze_away.mp3": "Đừng liếc mắt ra ngoài, tập trung nhìn vào bài học nào!"
}

async def generate_extra():
    os.makedirs("sounds", exist_ok=True)
    print("Dang tao them cac file giong noi cho Pomodoro & Gaze Tracking...")
    for filename, text in EXTRA_PHRASES.items():
        path = os.path.join("sounds", filename)
        communicate = edge_tts.Communicate(text, VOICE)
        await communicate.save(path)
        print(f"[+] Da tao: {path}")
    print("Hoan tat tao file bo sung!")

if __name__ == "__main__":
    asyncio.run(generate_extra())
