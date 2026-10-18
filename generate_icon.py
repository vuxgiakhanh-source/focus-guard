import sys
if sys.stdout and hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
from PIL import Image, ImageDraw
import math

def create_focusguard_icon(size=256):
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    center = size / 2.0
    radius = size * 0.44

    # 1. Nền tròn tối sang trọng với viền gradient nhẹ
    bg_color = (15, 23, 42, 255)       # Slate 900
    border_color = (16, 185, 129, 255)  # Emerald 500
    cyan_color = (6, 182, 212, 255)     # Cyan 500
    white_color = (248, 250, 252, 255)

    # Đổ bóng nền mờ
    for i in range(4):
        pad = i * 2
        alpha = int(60 / (i + 1))
        draw.ellipse([center - radius - 4 + pad, center - radius - 4 + pad,
                      center + radius + 4 - pad, center + radius + 4 - pad],
                     fill=(0, 0, 0, alpha))

    # Vòng tròn nền chính
    draw.ellipse([center - radius, center - radius, center + radius, center + radius],
                 fill=bg_color, outline=border_color, width=max(2, int(size * 0.035)))

    # 2. Vòng tròn ngắm bắn (Reticle Outer Ring)
    reticle_r = radius * 0.72
    draw.ellipse([center - reticle_r, center - reticle_r, center + reticle_r, center + reticle_r],
                 outline=(6, 182, 212, 180), width=max(1, int(size * 0.02)))

    # 4 vạch ngắm bắn Focus Reticle (Trên, Dưới, Trái, Phải)
    tick_len = radius * 0.22
    tick_w = max(2, int(size * 0.028))
    # Top
    draw.line([center, center - reticle_r - tick_len * 0.5, center, center - reticle_r + tick_len * 0.5], fill=cyan_color, width=tick_w)
    # Bottom
    draw.line([center, center + reticle_r - tick_len * 0.5, center, center + reticle_r + tick_len * 0.5], fill=cyan_color, width=tick_w)
    # Left
    draw.line([center - reticle_r - tick_len * 0.5, center, center - reticle_r + tick_len * 0.5, center], fill=cyan_color, width=tick_w)
    # Right
    draw.line([center + reticle_r - tick_len * 0.5, center, center + reticle_r + tick_len * 0.5, center], fill=cyan_color, width=tick_w)

    # 3. Biểu tượng Con Mắt Tập Trung (Focus Eye Shape)
    # Vẽ mí mắt trên và dưới bằng cung elip
    eye_w = radius * 0.95
    eye_h = radius * 0.48
    bbox = [center - eye_w, center - eye_h, center + eye_w, center + eye_h]

    # Cung mắt
    eye_thickness = max(2, int(size * 0.03))
    draw.arc(bbox, start=25, end=155, fill=(16, 185, 129, 230), width=eye_thickness)
    draw.arc(bbox, start=205, end=335, fill=(16, 185, 129, 230), width=eye_thickness)

    # 4. Tròng mắt / Con ngươi (Pupil & Iris)
    iris_r = radius * 0.35
    draw.ellipse([center - iris_r, center - iris_r, center + iris_r, center + iris_r],
                 fill=(6, 182, 212, 220), outline=border_color, width=max(2, int(size * 0.025)))

    # Tâm phát sáng (Lõi trắng & xanh lá AI)
    pupil_r = iris_r * 0.48
    draw.ellipse([center - pupil_r, center - pupil_r, center + pupil_r, center + pupil_r],
                 fill=(16, 185, 129, 255))

    core_r = pupil_r * 0.45
    draw.ellipse([center - core_r - 2, center - core_r - 2, center + core_r - 2, center + core_r - 2],
                 fill=white_color)

    return img

def main():
    base_img = create_focusguard_icon(256)
    base_img.save("app_icon.png")
    
    # Xuất ra file .ico đa kích cỡ (Windows icon chuẩn)
    sizes = [(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]
    base_img.save("app_icon.ico", format="ICO", sizes=sizes)
    print("[+] Đã tạo icon thành công: app_icon.ico và app_icon.png")

if __name__ == "__main__":
    main()
