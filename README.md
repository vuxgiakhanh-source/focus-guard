# 🎯 FocusGuard PRO

<p align="center">
  <b>Hệ thống AI Giám Sát Học Tập & Siêu Kỷ Luật Thời Gian Thực</b><br>
  <i>100% Offline • Chuẩn Tracking Quốc Tế (One-Euro Filter + NHTSA PERCLOS + Kinematics) • Bảo Mật Tuyệt Đối</i>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.10%20%7C%203.11%20%7C%203.12-blue?logo=python" alt="Python">
  <img src="https://img.shields.io/badge/Algorithm-One--Euro%20Filter-teal" alt="1-Euro Filter">
  <img src="https://img.shields.io/badge/DMS%20Standard-NHTSA%20PERCLOS%20P80-red" alt="PERCLOS">
  <img src="https://img.shields.io/badge/MediaPipe-Face%20Landmarks-orange" alt="MediaPipe">
  <img src="https://img.shields.io/badge/YOLOv8-Kinematic%20Phone%20Tracker-brightgreen" alt="YOLOv8">
  <img src="https://img.shields.io/badge/Platform-Windows%2010%20%7C%2011-0078D6?logo=windows" alt="Windows">
  <img src="https://img.shields.io/badge/UI-Cyber%20Glassmorphism-indigo" alt="Glassmorphism UI">
  <img src="https://img.shields.io/badge/License-MIT-green.svg" alt="License">
</p>

---

## 📖 Giới Thiệu (Overview)

**FocusGuard PRO** là hệ thống trợ lý AI giám sát kỷ luật học tập cá nhân bằng thị giác máy tính thế hệ mới, áp dụng các thuật toán chuẩn công nghiệp từ các hệ thống giám sát người lái xe (Driver Monitoring Systems - DMS) cao cấp nhất thế giới (Tesla Autopilot, Comma.ai, Tobii Pro và Apple Screen Time):
* 📱 **Phát hiện điện thoại trên tay bằng AI Động Học (Kinematics):** Phân biệt chính xác giữa điện thoại để tĩnh trên bàn/kệ sạc (an toàn) và điện thoại đang cầm trên tay (cảnh báo).
* 📖 **Chế độ Đọc Sách / Ghi Chép (Desk Reading Mode):** Tự động nhận diện tư thế cúi đầu làm bài, chống 100% tình trạng báo nhầm buồn ngủ khi mắt cụp xuống đọc vở.
* 😴 **Tiêu chuẩn Buồn Ngủ NHTSA PERCLOS (P80) & Micro-sleep:** Không báo nhầm khi chớp mắt chậm; bắt dính ngay lập tức hiện tượng gà gật lờ đờ hoặc ngủ gục.
* 📏 **Bảo Vệ Mắt & Cột Sống (Screen Distance & Posture):** Cảnh báo khi người học ngồi quá gần màn hình (<35cm) hoặc nghiêng cổ tì cằm quá lâu.
* 🌐 **Lọc Xao Nhãng Ứng Dụng Thông Minh:** Phát hiện Facebook, TikTok, Game (Liên Minh, Valorant, Genshin, Roblox...), cho phép xem bài giảng học tập trên YouTube và nghe nhạc Lofi.
* 🔋 **Bình Năng Lượng Tập Trung Động (Attentional Reservoir):** Điểm số 0-100% phản hồi thời gian thực, hồi phục khi chăm chỉ và rút bớt khi xao nhãng.
* 🔥 **Theo Dõi Chuỗi Ngày Học (Daily Streak & Mục Tiêu Ngày):** Gamify hóa quá trình tự học với bảng vàng thành tích xem trực tiếp bằng phím `H`.

> [!IMPORTANT]
> **Cam kết bảo mật 100%:** Toàn bộ mô hình AI chạy trực tiếp trên máy của bạn (Offline hoàn toàn). Webcam không lưu trữ video và không gửi bất kỳ dữ liệu nào ra ngoài Internet.

---

## 🌟 Tính Năng Nổi Bật (Key Features)

1. **🚀 Bộ Lọc One-Euro Filter (CHI 2012 - Triệt Tiêu 87% Rung Lắc, Zero Lag):**
   * Thay thế hoàn toàn bộ lọc EMA truyền thống bằng giải thuật thích ứng tần số cắt theo vận tốc góc. Đứng yên thì số đo ổn định tuyệt đối; quay đầu thì bắt chuyển động tức thì không độ trễ.

2. **📱 Kinematic Phone Tracker (Phân Biệt Cầm Trên Tay vs Để Trên Bàn):**
   * Điện thoại dựng trên kệ sạc hoặc nằm yên trên bàn: Hiện hộp màu vàng lam `DIEN THOAI (TREN BAN)`, **không báo động, không trừ điểm**.
   * Chỉ khi nhấc điện thoại lên tay hoặc vuốt màn hình: Hộp đỏ cảnh báo lập tức xuất hiện và nhắc nhở.

3. **📚 Chế Độ Đọc Sách / Viết Bài (Desk Reading Mode):**
   * Khi cúi đầu nhìn vở trên bàn ($-38° \le \text{pitch} \le -8°$), AI chuyển sang chế độ `● ĐANG ĐỌC / VIẾT BÀI`, tự động hạ ngưỡng EAR và bỏ qua đảo mắt để bạn tập trung làm bài thi mà không bao giờ bị làm phiền.

4. **👁 Đo Độ Nhắm Mắt Chuẩn NHTSA PERCLOS & Micro-sleep:**
   * Tính toán tỷ lệ mắt nhắm trong cửa sổ trượt 12 giây kết hợp bộ đếm vi giấc ngủ (Micro-sleep > 2.6s). Người đeo kính gọng dày hay mắt híp đều được cân chỉnh riêng biệt.

5. **👀 Cảnh Báo Khoảng Cách Mắt & Tư Thế Cổ (Screen Distance):**
   * Tự động đo khoảng cách giữa 2 mắt đến camera. Ngồi quá sát màn hình (<35cm) sẽ có thông báo nhắc lùi xa $\ge 50\text{cm}$ để chống cận thị và gù lưng.

6. **⏱ Pomodoro Chuẩn Quốc Tế Có Nghỉ Dài (25p học / 5p nghỉ / 15p nghỉ sâu):**
   * Cứ sau mỗi 4 chu kỳ học tập trung liên tiếp, hệ thống tự động thưởng phiên **Nghỉ Dài 15 phút** để não bộ tái tạo năng lượng.

7. **📊 Bảng Vàng Thống Kê & Chuỗi Học Tập (Daily Streak Modal):**
   * Bấm phím **`H`** hoặc click nút `[H] Thống kê` trên dock để mở ngay bảng tổng kết: chuỗi ngày học liên tục (Streak), tiến độ mục tiêu 120 phút/ngày và số lần vượt qua cám dỗ.

8. **🌐 Nhận Diện Game & Mạng Xã Hội (Facebook, YouTube Học Tập, Game):**
   * Tự động nhận diện khi mở game hoặc mạng xã hội. Nếu đang xem video bài giảng (IELTS, Toán, Lập trình, Lofi...) trên YouTube, AI nhận biết đó là học tập và không báo động.

9. **🔇 Ngắt Âm Thanh Tức Thì (Zero Audio Delay):**
   * Ngay khoảnh khắc bạn quay lại bài học hoặc đặt điện thoại xuống, âm thanh cảnh báo lập tức dừng ngay mà không phát rền rĩ thêm một giây nào.

---

## 🛠 Hướng Dẫn Cài Đặt (Installation)

### 1. Yêu Cầu Hệ Thống
* Hệ điều hành: Windows 10 / 11 (64-bit).
* Python 3.10, 3.11 hoặc 3.12.
* Webcam đang hoạt động bình thường.

### 2. Tải Mã Nguồn & Cài Thư Viện

```powershell
# Clone kho mã nguồn về máy qua SSH hoặc HTTPS
git clone git@github.com:vuxgiakhanh-source/focus-guard.git
cd focus-guard

# Khuyến nghị: Tạo môi trường ảo
python -m venv venv
.\venv\Scripts\activate

# Cài đặt toàn bộ thư viện phụ thuộc
pip install -r requirements.txt
```

> **Ghi chú:** Trọng số AI (`face_landmarker.task`, `yolov8n.pt`) và toàn bộ âm thanh cảnh báo đã đính kèm sẵn trong kho lưu trữ — bạn không cần tải thêm bất kỳ file nào từ bên ngoài!

---

## 🚀 Hướng Dẫn Khởi Chạy (Quick Start)

### Cách 1: Bấm Icon Từ Desktop (Khuyên Dùng)
Chạy script tự động tạo shortcut FocusGuard PRO ra ngoài Desktop (chỉ cần chạy 1 lần):
```powershell
powershell -ExecutionPolicy Bypass -File install_shortcut.ps1
```
Sau đó ra ngoài Desktop, nhấp đúp vào biểu tượng **FocusGuard PRO** (khởi động êm ái trong 1.5s, không hiện cửa sổ cmd đen).

### Cách 2: Khởi Chạy Bằng Lệnh
```powershell
python main.py
```

---

## ⌨️ Bảng Phím Tắt & Nút Bấm Điều Khiển

Tất cả các chức năng đều hỗ trợ **Click chuột trực tiếp** lên thanh Dock bo tròn ở đáy cửa sổ hoặc bấm phím tắt:

| Nút Bấm Trên Dock | Phím Tắt | Chức Năng |
| :---: | :---: | :--- |
| **`[C] Dạy góc`** | **`C`** | Bắt đầu đo góc ngồi học và dáng mắt trong 2 phút (bấm lại để hoàn tất sớm) |
| **`[P] Pomodoro`** | **`P`** | Bật / Tắt chu kỳ đếm giờ Pomodoro (25p học / 5p nghỉ / 15p nghỉ dài sau 4 hiệp) |
| **`[H] Thống kê`** | **`H`** | Bật / Tắt bảng vàng thống kê thành tích, chuỗi ngày học (Daily Streak) |
| **`[M] Âm thanh`** | **`M`** | Tắt / Mở âm thanh giọng nói cảnh báo (hữu ích khi ngồi thư viện) |
| **`[R] Đặt lại`** | **`R`** | Đặt lại điểm tập trung 100% và đồng hồ thời gian học |
| **`[Q] Thoát`** | **`Q`** / **`Esc`** | Thoát ứng dụng an toàn, lưu lịch sử và hiển thị báo cáo tổng kết |

---

## ❓ Câu Hỏi Thường Gặp (FAQ)

**Q1: Điện thoại để trên giá đỡ trên bàn có bị kêu chuông không?**  
* **A:** Hoàn toàn không! Bộ lọc động học Kinematic Tracker sẽ nhận diện điện thoại đứng yên trên bàn và hiển thị nhãn màu vàng lam an toàn `DIEN THOAI (TREN BAN)`. Chỉ khi bạn cầm lên tay sử dụng thì mới cảnh báo.

**Q2: Khi cúi đầu đọc sách hoặc ghi chép có bị báo buồn ngủ oan không?**  
* **A:** Hoàn toàn không! Chế độ Desk Reading Mode tự động phát hiện góc cúi làm bài, nới lỏng góc nhìn mí mắt và cộng điểm tập trung tối đa cho bạn.

**Q3: Tôi xem video bài giảng hoặc giải toán trên YouTube có bị phạt không?**  
* **A:** FocusGuard PRO trang bị bộ lọc từ khóa giáo dục thông minh (IELTS, Toán, Văn, Tutorial, Lập trình, Lofi study...). Nếu xem video học tập, AI nhận biết đó là học và không phạt điểm.

**Q4: Nếu tôi mở 2 ứng dụng cùng lúc thì sao?**  
* **A:** Ứng dụng tích hợp khóa đơn **Windows Named Mutex**. Nếu có phiên bản đang chạy ngầm, cửa sổ thứ 2 sẽ tự động nhận diện và đưa cửa sổ đang học lên phía trước màn hình, chống nghẽn webcam.

**Q5: Nếu phòng học tối hoặc chỉ bật đèn bàn thì AI có nhận được không?**  
* **A:** FocusGuard tích hợp bộ xử lý kép Gamma LUT Correction kết hợp thuật toán thích ứng ánh sáng CLAHE, tự động nâng sáng vùng tối vi mô mà không làm nhiễu hình ảnh, giúp MediaPipe nhận diện chính xác ngay cả trong phòng tối.

---

## 📄 Bản Quyền & Giấy Phép (License)

Dự án được phân phối dưới giấy phép mã nguồn mở [MIT License](LICENSE).

Tác giả: **Vũ Gia Khánh**  
Email: [vuxgiakhanh@gmail.com](mailto:vuxgiakhanh@gmail.com)  
GitHub: [@vuxgiakhanh-source](https://github.com/vuxgiakhanh-source)
