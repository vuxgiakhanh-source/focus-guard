import asyncio
import os
import sys
import edge_tts

# Cấu hình UTF-8 cho console Windows
sys.stdout.reconfigure(encoding='utf-8')

VOICE = "vi-VN-HoaiMyNeural"

PHRASES = {
    "drowsy.mp3": "Bạn ơi! Tỉnh ngủ đi, ngủ gật rồi kìa!",
    "phone.mp3": "Bỏ điện thoại xuống, tập trung học bài nào!",
    "look_away.mp3": "Tập trung nhìn vào màn hình đi bạn ơi!",
    "away.mp3": "Bạn ơi, mau quay lại bàn học thôi nào!",
    "yawn.mp3": "Ngáp rồi kìa! Đi rửa mặt cho tỉnh táo nhé!"
}

async def generate_all():
    os.makedirs("sounds", exist_ok=True)
    print("Dang tao file am thanh giong noi tieng Viet...")
    for filename, text in PHRASES.items():
        path = os.path.join("sounds", filename)
        communicate = edge_tts.Communicate(text, VOICE)
        await communicate.save(path)
        print(f"[+] Da tao: {path}")
    print("Hoan tat 100%!")

if __name__ == "__main__":
    asyncio.run(generate_all())
