# 🎯 FocusGuard PRO

<p align="center">
  <b>Hệ thống AI Giám Sát Học Tập & Siêu Kỷ Luật Thời Gian Thực</b><br>
  <i>100% Offline • Siêu Tiết Kiệm CPU (~10.1ms/frame) • Thích Ứng Mọi Setup Bàn Học • Bảo Mật Tuyệt Đối</i>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.10%20%7C%203.11%20%7C%203.12-blue?logo=python" alt="Python">
  <img src="https://img.shields.io/badge/MediaPipe-Face%20Landmarks-orange" alt="MediaPipe">
  <img src="https://img.shields.io/badge/YOLOv8-Nano%20Phone%20Detect-brightgreen" alt="YOLOv8">
  <img src="https://img.shields.io/badge/Platform-Windows%2010%20%7C%2011-0078D6?logo=windows" alt="Windows">
  <img src="https://img.shields.io/badge/UI-Cyber%20Glassmorphism-indigo" alt="Glassmorphism UI">
  <img src="https://img.shields.io/badge/License-MIT-green.svg" alt="License">
</p>

---

## 📖 Giới Thiệu (Overview)

**FocusGuard PRO** là trợ lý công nghệ AI giám sát kỷ luật học tập cá nhân bằng thị giác máy tính (Computer Vision), được thiết kế chuyên sâu để giải quyết dứt điểm các thói quen gây xao nhãng và lười biếng khi ngồi học một mình:
* 📱 **Cầm điện thoại bấm lén** trong giờ học.
* 😴 **Ngủ gật, nhắm mắt, ngáp dài**.
* 🌐 **Sa đà lướt mạng xã hội** (Facebook, YouTube, TikTok...) trên máy tính.
* 👀 **Ngoảnh mặt ra ngoài, đảo mắt đọc phao, bỏ bàn học đi nơi khác**.

> [!IMPORTANT]
> **Cam kết bảo mật 100%:** Toàn bộ mô hình AI chạy trực tiếp trên máy của bạn (Offline hoàn toàn). Webcam không lưu trữ video và không gửi bất kỳ dữ liệu nào ra ngoài Internet.

---

## 🌟 Tính Năng Nổi Bật (Key Features)

1. **📐 Tự Động Thích Ứng Mọi Setup Bàn Học (Adaptive Study Envelope):**
   * **Không ép buộc tư thế cứng nhắc:** Cho dù bạn đặt sách vở/màn hình phụ ở **bên trái, bên phải hay cả hai bên**, AI sẽ tự động học và thích ứng với không gian bàn học của riêng bạn.
   * **Khoảng thời gian vàng 2 phút:** Trong 2 phút khởi tạo, AI sẽ đo chính xác biên độ góc quay tự nhiên của bạn và cấp thêm đệm tự do 15° để bạn cử động thoải mái mà không bao giờ bị báo nhầm!

2. **📱 Bắt Quả Tang Cầm Điện Thoại (YOLOv8 Nano):**
   * Khóa mục tiêu và đóng khung đỏ kèm tỷ lệ % tin cậy ngay khi phát hiện điện thoại trên tay.
   * Tự động tắt quét trong giờ giải lao Pomodoro để máy luôn mát rượi.

3. **🌐 Giám Sát Mạng Xã Hội Thông Minh (Facebook / YouTube Active Monitor):**
   * **Mở tab để đó nghe nhạc Lofi / Study Music:** Hoàn toàn **KHÔNG** bị báo động.
   * **Thực sự dùng (cuộn feed, click chuột, gõ phím/chat) > 2.5s:** AI phát cảnh báo giọng nói riêng, trừ điểm tập trung và bật thông báo Windows Toast.

4. **⏱ Tích Hợp Đồng Hồ Pomodoro (25 phút học / 5 phút nghỉ):**
   * Bấm nút **`[⏱ Pomodoro]`** trên dock hoặc phím **`P`** để bật/tắt.
   * Đóng băng thời gian chính xác khi tạm dừng. Hết giờ học có chuông nhắc nghỉ; hết giờ nghỉ có chuông gọi học bài.

5. **👓 Tự Đo Độ Mở Mắt Cho Người Đeo Kính & Mắt Híp:**
   * Trong 2 phút đo ban đầu, AI tự đo kích thước độ mở mí mắt tự nhiên của bạn để thiết lập ngưỡng `ear_threshold` tối ưu riêng, triệt tiêu 100% việc báo nhầm buồn ngủ khi đeo kính phản quang.

6. **👁 Iris Gaze Tracking Chuẩn Xác Cao:**
   * Theo dõi tâm con ngươi thời gian thực. Chỉ kích hoạt cảnh báo liếc mắt khi đầu hướng thẳng về phía trước (`|yaw| < 25°`) mà mắt liếc trộm sang bên cạnh.

7. **📊 Giao Diện Kính Mờ Cyber-Glassmorphism & Biểu Đồ Sparkline:**
   * Không gian nhìn siêu thoáng (> 82% camera), hiển thị đường biểu đồ Sparkline mini dao động thời gian thực cùng thanh dock nút bấm bo tròn phong cách hiện đại.

8. **🔔 Thông Báo Đa Tầng (Windows Toast & Voice Alerts):**
   * Ngay cả khi thu nhỏ cửa sổ FocusGuard để làm bài trên Word hay trình duyệt, popup thông báo Windows Toast vẫn bật lên kịp thời ở góc phải màn hình.

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

> **Ghi chú:** Trọng số AI (`face_landmarker.task` 3.7MB, `yolov8n.pt` 6.5MB) và toàn bộ âm thanh cảnh báo đã đính kèm sẵn trong kho lưu trữ — bạn không cần tải thêm bất kỳ file nào từ bên ngoài!

---

## 🚀 Hướng Dẫn Khởi Chạy (Quick Start)

### Cách 1: Bấm Icon Từ Desktop (Khuyên Dùng)
Chạy script tự động tạo shortcut FocusGuard PRO ra ngoài Desktop (chỉ cần chạy 1 lần):
```powershell
powershell -ExecutionPolicy Bypass -File install_shortcut.ps1
```
Sau đó ra ngoài Desktop, nhấp đúp vào biểu tượng **FocusGuard PRO** (khởi động êm ái trong 1.5s, không hiện cửa sổ cmd đen).

### Cách 2: Khởi Chạy Bằng File Batch
* Nhấp đúp vào file `FocusGuard.bat` trong thư mục.

### Cách 3: Khởi Chạy Bằng Lệnh
```powershell
python main.py
```

---

## 📘 HƯỚNG DẪN SỬ DỤNG CHI TIẾT TỪ A - Z (User Guide)

### 🎯 Quy trình 1 buổi học chuẩn:

#### Bước 1: Khởi động & Cân chỉnh camera
* Mở app lên. Đặt laptop hoặc webcam ở góc bạn thấy thoải mái nhất (thẳng mặt hoặc chéo bên đều được, chỉ cần camera nhìn thấy khuôn mặt bạn).

#### Bước 2: Dạy AI góc học tập & Dáng mắt (⭐ ĐẶC BIỆT DÀNH CHO LẦN ĐẦU)
> [!IMPORTANT]
> **Khoảng thời gian vàng 2 phút (First-Time Calibration):**  
> Khi khởi chạy lần đầu tiên, FocusGuard sẽ **tự động kích hoạt chế độ học góc 2 phút** (hoặc bạn có thể bấm nút **`[🎯 Dạy góc (2p)]`**).  
> **Bạn hãy cố gắng ngồi học tập trung cao độ nhất có thể trong đúng 2 phút này** (ngồi thẳng lưng, đọc sách, nhìn bài nghiêm túc, không bấm điện thoại hay quay ngang ngửa).
> 
> 👉 **Tại sao 2 phút này lại quyết định tất cả?**
> 1. **Ghi nhớ góc học tập cá nhân:** AI lấy mẫu hàng trăm khung hình tư thế nghiêm túc của bạn (dù bạn để sách bên trái hay bên phải) để làm thước đo chuẩn riêng cho bàn học của bạn.
> 2. **Cân chỉnh mắt cho người đeo kính:** AI tự đo kích thước con ngươi và độ mở mí mắt tự nhiên của bạn để tính ra ngưỡng nhắm mắt `ear_threshold` chuẩn xác 100%, chống báo nhầm buồn ngủ.
> 3. **Lưu vĩnh viễn:** Sau 2 phút, AI sẽ tự động lưu cấu hình vào máy. Từ các buổi học sau trở đi, bạn mở app lên là học ngay lập tức!

#### Bước 3: Học bài & Kỷ luật tự giác
Trong quá trình học, AI sẽ âm thầm giám sát:
* 😴 **Nếu bạn nhắm mắt quá 2 giây:** Giọng nói tiếng Việt sẽ nhắc *"Bạn đang buồn ngủ, hãy tập trung!"* và viền đỏ màn hình nhấp nháy.
* 📱 **Nếu bạn nhấc điện thoại lên tay:** Khung màu đỏ lập tức khóa chặt vị trí chiếc điện thoại và phát loa cảnh báo.
* 🌐 **Nếu bạn mở Facebook/YouTube lướt:** Sau 2.5 giây thao tác chuột/phím liên tục, AI sẽ lên tiếng nhắc nhở quay lại học và trừ điểm tập trung.
* ☕ **Bật Pomodoro:** Bấm **`[⏱ Pomodoro]`** để vào chu kỳ chuẩn 25 phút học tập trung cao độ.

#### Bước 4: Nghỉ giải lao (Pomodoro Break)
* Khi hết 25 phút học, chuông báo sẽ reo và màn hình chuyển sang tông **màu tím hồng thư giãn**.
* Trong 5 phút này: Toàn bộ cảnh báo camera, điện thoại và lướt web sẽ **tự động tắt 100%**. Bạn có thể thoải mái bấm điện thoại, nghe nhạc, giải trí.
* Khi hết 5 phút nghỉ: Giọng nói sẽ thông báo hết giờ nghỉ để bạn quay lại bàn học!

#### Bước 5: Kết thúc phiên học & Xem báo cáo
* Khi học xong: Bấm nút **`[✕ Thoát & Lưu]`** (hoặc nhấn phím **`Q`** / nút **`X`** cửa sổ).
* Hệ thống sẽ tự động:
  1. Bắn thông báo Windows Toast tổng kết thời gian học và điểm tập trung.
  2. In bảng báo cáo chi tiết ra màn hình (số lần cầm điện thoại, số lần lướt mạng xã hội, chu kỳ Pomodoro).
  3. Tự động cộng dồn vào lịch sử học tập tích lũy (`focus_history.json`).

---

## ⌨️ Bảng Phím Tắt & Nút Bấm Điều Khiển

Tất cả các chức năng đều hỗ trợ **Click chuột trực tiếp** lên thanh Dock bo tròn ở đáy cửa sổ hoặc bấm phím tắt:

| Nút Bấm Trên Dock | Phím Tắt | Chức Năng |
| :---: | :---: | :--- |
| **`[C] Dạy góc 2p`** | **`C`** | Bắt đầu đo góc ngồi học và dáng mắt trong 2 phút (bấm lại lần nữa để hoàn tất sớm) |
| **`[P] Pomodoro`** | **`P`** | Bật / Tắt chu kỳ đếm giờ Pomodoro (25 phút học / 5 phút nghỉ) |
| **`[M] Âm thanh`** | **`M`** | Tắt / Mở âm thanh giọng nói cảnh báo (hữu ích khi ngồi thư viện) |
| **`[R] Đặt lại`** | **`R`** | Đặt lại điểm tập trung 100% và đồng hồ thời gian học |
| **`[Q] Thoát`** | **`Q`** / **`Esc`** | Thoát ứng dụng an toàn, lưu lịch sử và hiển thị báo cáo tổng kết |

---

## ❓ Câu Hỏi Thường Gặp (FAQ)

**Q1: Ứng dụng có làm nóng máy hay tốn pin khi chạy lâu không?**  
* **A:** Hoàn toàn không! FocusGuard PRO chạy với tần suất xử lý tối ưu ~10.1ms/frame (chỉ tốn ~30% chu kỳ một luồng CPU), các luồng AI chạy đơn luồng độc lập, đảm bảo máy luôn êm mát, không hú quạt và tiết kiệm pin tối đa.

**Q2: Nếu tôi lỡ tay click mở shortcut nhiều lần thì sao?**  
* **A:** Ứng dụng tích hợp khóa đơn **Windows Named Mutex**. Nếu có phiên bản đang chạy ngầm, cửa sổ thứ 2 sẽ tự động nhận diện, đưa cửa sổ đang học lên phía trước màn hình và tự đóng ngay lập tức, ngăn chặn 100% tình trạng nghẽn webcam hay mở trùng lặp.

**Q3: Nếu tôi đóng nắp che camera (E-Shutter) hoặc phòng tối thì app xử lý thế nào?**  
* **A:** AI tích hợp cảm biến phát hiện màn hình tối đen. Nếu nắp camera đóng, app sẽ hiện cảnh báo vàng thân thiện nhắc bạn gạt mở nắp camera và tắt hoàn toàn giọng nói giục quay lại bàn học để không làm phiền bạn.

**Q4: Nếu tôi ngồi học ở thư viện hoặc quán cà phê thì làm sao?**  
* **A:** Bạn chỉ cần click nút **`[M] Âm thanh`** (hoặc nhấn phím **`M`**) để chuyển sang chế độ im lặng `[MUTE]`. Mọi cảnh báo sẽ chuyển sang dạng viền đỏ trực quan trên màn hình và popup Windows Toast, không gây ồn ào xung quanh.

**Q5: Tôi đeo kính gọng dày hay bị báo buồn ngủ oan thì chỉnh thế nào?**  
* **A:** Bạn chỉ cần bấm nút **`[C] Dạy góc 2p`** (hoặc phím **`C`**). AI sẽ đo độ mở mắt xuyên qua tròng kính của bạn trong lúc học và tự động tính toán ngưỡng nhắm mắt chuẩn xác riêng cho bạn.

**Q6: Dữ liệu học tập được lưu ở đâu?**  
* **A:** Lịch sử học tập được lưu cục bộ ngay trong máy (file `focus_history.json`). File này đã được thêm vào `.gitignore` để đảm bảo dữ liệu riêng tư của bạn không bao giờ bị lộ lên GitHub.

**Q7: Nếu tôi đổi góc học tập, chuyển bàn học, hoặc đổi chỗ ngồi thì làm sao?**  
* **A:** Cực kỳ đơn giản! Bạn chỉ cần ngồi vào chỗ mới và bấm nút **`[C] Dạy góc 2p`** (hoặc nhấn phím **`C`**). AI sẽ ngay lập tức đo lại góc ngồi mới và tự động lưu đè cấu hình mới vào máy.  
* *Mẹo:* Nếu không muốn đợi hết 2 phút, chỉ cần ngồi học theo góc mới khoảng 15-20 giây rồi **bấm lại phím `C` một lần nữa** là hệ thống sẽ lưu và hoàn tất ngay tức thì!

**Q8: Bàn học của tôi để sách bên phải hoặc dùng 2 màn hình thì AI có hiểu không?**  
* **A:** Hiểu 100%! Trong 2 phút đo góc ban đầu, bất kể bạn quay sang đâu để đọc bài, AI đều ghi nhận và tự động mở rộng vùng học tập sang phía đó kèm 15° đệm an toàn, không bao giờ ép bạn phải để sách ở một bên cố định.

---

## 📄 Bản Quyền & Giấy Phép (License)

Dự án được phân phối dưới giấy phép mã nguồn mở [MIT License](LICENSE).

Tác giả: **Vũ Gia Khánh**  
Email: [vuxgiakhanh@gmail.com](mailto:vuxgiakhanh@gmail.com)  
GitHub: [@vuxgiakhanh-source](https://github.com/vuxgiakhanh-source)
