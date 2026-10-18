# 🎯 FocusGuard PRO

<p align="center">
  <b>Hệ thống AI Giám Sát Học Tập & Nâng Cao Tập Trung Thời Gian Thực</b><br>
  <i>100% Offline • Siêu Tiết Kiệm CPU (~4.8ms/frame) • Tự Do Mọi Góc Camera • Bảo Mật Tuyệt Đối</i>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.10%20%7C%203.11%20%7C%203.12-blue?logo=python" alt="Python">
  <img src="https://img.shields.io/badge/MediaPipe-Face%20Landmarks-orange" alt="MediaPipe">
  <img src="https://img.shields.io/badge/YOLOv8-Nano%20Phone%20Detect-brightgreen" alt="YOLOv8">
  <img src="https://img.shields.io/badge/Platform-Windows%2010%20%7C%2011-0078D6?logo=windows" alt="Windows">
  <img src="https://img.shields.io/badge/License-MIT-green.svg" alt="License">
</p>

---

## 📖 Giới Thiệu (Overview)

**FocusGuard PRO** là trợ lý học tập cá nhân bằng thị giác máy tính (AI Computer Vision) thế hệ mới, được thiết kế để giải quyết bài toán mất tập trung, dùng điện thoại lén lút, ngủ gật và sa đà lướt mạng xã hội (Facebook / YouTube) trong giờ học.

Toàn bộ mô hình AI xử lý **100% trên thiết bị (Offline)** — webcam không truyền bất kỳ hình ảnh hay dữ liệu nào ra Internet, đảm bảo tính riêng tư tuyệt đối cho người dùng.

---

## 🌟 Tính Năng Nổi Bật (Key Features)

### 1. 📐 Face-Centric Adaptive Camera (Tự Do Mọi Góc Đặt Máy)
* **Không ép buộc vị trí camera:** Bạn có thể nâng cao laptop, đặt máy chéo bên trái hay gập mở màn hình tùy ý.
* **Cơ chế linh hoạt:** Chỉ cần camera nhìn thấy khuôn mặt bạn là hệ thống tính đang tập trung học.
* **Tự do quay trái:** Góc quay trái mở rộng tối đa 180° (thoải mái nhìn sang sách vở hoặc màn hình phụ bên trái).
* **Cảnh báo quay phải > 70°:** Chỉ kích hoạt khi bạn ngoảnh hẳn đầu ra xa khỏi bàn học.

### 2. 📱 Phát Hiện Cầm Điện Thoại Thời Gian Thực (YOLOv8 Nano)
* Sử dụng mô hình nhận diện vật thể YOLOv8n siêu nhẹ chạy luồng riêng biệt (~5 FPS).
* Nhận diện chính xác khi bạn cầm điện thoại trong vùng bàn học và lập tức phát cảnh báo bằng giọng nói & khung đỏ trực quan.
* Tự động tạm dừng quét điện thoại trong 5 phút giải lao Pomodoro.

### 3. 🌐 Giám Sát Thao Tác Facebook & YouTube Thông Minh (Active Tracking Only)
* **Nghe nhạc Lofi / Study Music trên YouTube hoặc để mở tab:** Hoàn toàn **KHÔNG** bị báo động.
* **Thực sự đang dùng (cuộn feed, click chuột, gõ phím/chat) > 2.5 giây:** AI lập tức kích hoạt cảnh báo giọng nói riêng, popup Windows Toast và trừ điểm tập trung.

### 4. ⏱ Tích Hợp Chu Kỳ Pomodoro (25 Phút Học / 5 Phút Nghỉ)
* Bấm **`P`** hoặc click chuột vào nút `[⏱ Pomodoro]` trên màn hình.
* **Trong 25 phút học:** Giám sát nghiêm ngặt, giữ kỷ luật tối đa.
* **Trong 5 phút nghỉ:** Màn hình chuyển tông màu tím hồng thư giãn, tự động ngắt toàn bộ cảnh báo để bạn giải lao, lướt điện thoại thoải mái. Có giọng nói nhắc nhở khi hết giờ nghỉ!

### 5. 👁 Iris Gaze Tracking & Tự Cân Chỉnh EAR
* Theo dõi tỷ lệ dịch chuyển con ngươi (Iris) thời gian thực.
* Tự động học dáng mắt và tính toán `ear_threshold` riêng cho từng người (chống báo nhầm buồn ngủ đối với người đeo kính hoặc mắt híp).

### 6. 🔔 Thông Báo Đa Tầng (Windows Toast & Voice Alerts)
* Cảnh báo bằng giọng nói tiếng Việt tự nhiên phát sinh từ Edge TTS.
* Khi FocusGuard bị che hoặc thu nhỏ dưới thanh Taskbar, Windows Toast Notification ở góc dưới màn hình vẫn gửi thông báo kịp thời.

### 7. 📊 Thống Kê & Lưu Lịch Sử Phiên Học
* Tự động lưu toàn bộ thời gian học, điểm tập trung trung bình, chuỗi phiên học (streak) vào file cục bộ.
* Bảng tổng kết chi tiết hiển thị ngay khi kết thúc phiên.

---

## ⚡ Kiến Trúc Tối Ưu Hiệu Năng (~4.8ms/frame - 0% Nóng Máy)

FocusGuard PRO được tối ưu chuyên sâu ở cấp độ hệ thống và C-Level:
* **Zero-Allocation Memory Buffers:** Tái sử dụng vùng nhớ đệm RGB và Landmark points, loại trừ hoàn toàn việc cấp phát bộ nhớ liên tục.
* **Windows Native Multimedia 1ms Timer:** Kích hoạt `timeBeginPeriod(1)` đảm bảo chu kỳ khung hình chính xác, không giật lag.
* **Cadence Text Caching:** Chỉ rasterize chữ FreeType ở tần suất 15 FPS và cache kết quả, giảm 90% tải vẽ giao diện.
* **Single-Thread Isolated Torch Engine:** Khóa YOLOv8 chạy đơn luồng độc lập, triệt tiêu xung đột CPU và kiểm soát nhiệt độ máy luôn mát mẻ.
* **Garbage Collection Throttling:** Tinh chỉnh ngưỡng dọn rác GC tránh hiện tượng drop frame định kỳ.

---

## 🛠 Hướng Dẫn Cài Đặt (Installation)

### 1. Yêu Cầu Hệ Thống
* Hệ điều hành: Windows 10 / 11 (64-bit).
* Python 3.10, 3.11 hoặc 3.12.
* Webcam hoạt động bình thường.

### 2. Tải Mã Nguồn & Cài Đặt Thư Viện

```powershell
# Clone kho lưu trữ
git clone https://github.com/vuxgiakhanh/focus-guard.git
cd focus-guard

# Khuyến nghị: Tạo môi trường ảo (Virtual Environment)
python -m venv venv
.\venv\Scripts\activate

# Cài đặt các thư viện cần thiết
pip install -r requirements.txt
```

> **Ghi chú:** Các file weights (`face_landmarker.task` 3.7MB và `yolov8n.pt` 6.5MB) cùng âm thanh cảnh báo đã được đính kèm sẵn trong kho lưu trữ — bạn không cần phải tải thêm gì từ bên ngoài!

---

## 🚀 Hướng Dẫn Sử Dụng (Quick Start)

### Cách 1: Khởi Chạy Nhanh Từ Màn Hình (Tạo Desktop Icon)
Chạy script tự động tạo shortcut FocusGuard PRO ra ngoài Desktop (chỉ cần chạy 1 lần):
```powershell
powershell -ExecutionPolicy Bypass -File install_shortcut.ps1
```
Sau đó, bạn chỉ cần ra ngoài Desktop và **nhấp đúp chuột vào icon FocusGuard PRO** để học bài!

### Cách 2: Khởi Chạy Bằng Lệnh
```powershell
python main.py
```

### ⌨️ Phím Tắt & Nút Bấm Chuột

| Thao Tác Chuột | Phím Tắt | Chức Năng |
| :---: | :---: | :--- |
| Click **`[C] Dạy góc học`** | **`C`** | Cân chỉnh góc học tập & tự đo dáng mắt trong 60 giây |
| Click **`[P] Pomodoro`** | **`P`** | Bật / Tắt chu kỳ Pomodoro (25 phút học - 5 phút nghỉ) |
| Click **`[M] Âm thanh`** | **`M`** | Bật / Tắt âm thanh giọng nói nhắc nhở (Mute/Unmute) |
| Click **`[R] Reset`** | **`R`** | Đặt lại điểm tập trung và đồng hồ học tập |
| Click **`[Q] Thoát`** | **`Q`** / **`Esc`** | Thoát ứng dụng, tự lưu lịch sử và hiển thị báo cáo |

---

## 📂 Cấu Trúc Dự Án (Project Structure)

```text
focus-guard/
├── main.py                   # Điểm khởi chạy chính & vòng lặp video 30 FPS
├── detector.py               # Xử lý MediaPipe, Iris, Head Pose, Blinking, CLAHE
├── phone_detector.py         # Nhận diện điện thoại bằng YOLOv8 Nano đa luồng
├── app_monitor.py            # Giám sát thao tác người dùng trên Facebook/YouTube
├── pomodoro.py               # Quản lý chu kỳ Pomodoro 25/5
├── ui_utils.py               # Giao diện HUD bán trong suốt, Sparkline, bảng nút bấm
├── alert.py                  # Quản lý phát âm thanh cảnh báo đa luồng
├── toast_notifier.py         # Bắn thông báo Windows Native Toast
├── history.py                # Quản lý lịch sử và thống kê chuỗi học tập
├── requirements.txt          # Danh sách thư viện Python
├── sounds/                   # Thư mục âm thanh cảnh báo tiếng Việt
├── face_landmarker.task      # Trọng số MediaPipe Face Landmark
├── yolov8n.pt                # Trọng số YOLOv8 Nano
├── FocusGuard.bat            # File khởi chạy ngầm (không hiện cửa sổ cmd)
├── FocusGuard_Console.bat    # File khởi chạy có console (để debug)
├── install_shortcut.ps1      # Script tạo icon ra màn hình Desktop
├── LICENSE                   # Giấy phép MIT
└── README.md                 # Tài liệu hướng dẫn sử dụng
```

---

## 📄 Bản Quyền & Giấy Phép (License)

Dự án được phân phối dưới giấy phép [MIT License](LICENSE). Bạn hoàn toàn tự do sử dụng, chỉnh sửa và chia sẻ cho cộng đồng.

Tác giả: **Vũ Gia Khánh**  
Email: [vuxgiakhanh@gmail.com](mailto:vuxgiakhanh@gmail.com)
