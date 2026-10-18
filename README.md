# 🎯 FocusGuard PRO

<p align="center">
  <b>Hệ thống AI Giám Sát Học Tập & Siêu Kỷ Luật Thời Gian Thực</b><br>
  <i>100% Offline • Siêu Tiết Kiệm CPU (~11.8ms/frame) • Tự Do Mọi Góc Camera • Bảo Mật Tuyệt Đối</i>
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

**FocusGuard PRO** là công cụ AI giám sát kỷ luật học tập cá nhân bằng thị giác máy tính (Computer Vision), được thiết kế để giải quyết dứt điểm các thói quen gây mất tập trung:
* 📱 **Cầm điện thoại bấm lén** trong giờ học.
* 😴 **Ngủ gật, nhắm mắt, ngáp ngủ**.
* 🌐 **Sa đà lướt mạng xã hội** (Facebook, YouTube, TikTok...) trên máy tính.
* 👀 **Ngoảnh mặt ra ngoài, bỏ bàn học đi nơi khác**.

> [!IMPORTANT]
> **Cam kết bảo mật 100%:** Toàn bộ mô hình AI chạy trực tiếp trên máy của bạn (Offline hoàn toàn). Webcam không lưu trữ video và không gửi bất kỳ hình ảnh nào ra Internet.

---

## 🌟 Tính Năng Nổi Bật (Key Features)

1. **📐 Tự Do Mọi Góc Camera (Face-Centric Adaptive Mode):**
   * Không ép bạn phải ngồi cứng đờ hay đặt camera thẳng mặt. Bạn có thể gập mở màn hình laptop, nâng đế tản nhiệt, hay đặt máy ở góc chéo tùy thích.
   * **Quy tắc vàng:** Chỉ cần camera nhìn thấy khuôn mặt bạn $\rightarrow$ AI tính là đang tập trung học!
   * **Quay trái thoải mái vô hạn (180°):** Thoải mái nhìn sang sách vở hoặc màn hình phụ bên trái.
   * **Cảnh báo quay phải > 70°:** Chỉ nhắc nhở khi bạn quay hẳn đầu đi nơi khác xa khỏi bàn học.

2. **📱 Bắt Quả Tang Cầm Điện Thoại (YOLOv8 Nano):**
   * Quét và khoanh khung đỏ kèm tỷ lệ % tin cậy ngay khi phát hiện điện thoại trên tay.
   * Tự động tắt quét trong giờ giải lao Pomodoro để máy luôn mát rượi.

3. **🌐 Giám Sát Mạng Xã Hội Thông Minh (Facebook / YouTube Active Monitor):**
   * **Mở tab để đó nghe nhạc Lofi / Study Music:** Hoàn toàn **KHÔNG** bị báo động.
   * **Thực sự dùng (cuộn feed, click chuột, gõ phím/chat) > 2.5s:** AI phát cảnh báo giọng nói riêng, trừ điểm tập trung và bắn popup thông báo.

4. **⏱ Tích Hợp Đồng Hồ Pomodoro (25 phút học / 5 phút nghỉ):**
   * Bấm **`P`** hoặc click chuột trên màn hình để bật/tắt.
   * Hết giờ học có giọng nói nhắc nghỉ ngơi; hết giờ giải lao có chuông gọi quay lại học.

5. **👓 Tự Đo Độ Mở Mắt Cho Người Đeo Kính & Mắt Híp:**
   * Trong lúc học góc 60s, AI tự đo độ mở mắt tự nhiên của bạn để thiết lập ngưỡng `ear_threshold` tối ưu riêng, triệt tiêu 100% việc báo nhầm buồn ngủ khi đeo kính phản quang.

6. **📈 Biểu Đồ Sparkline Mini Thời Gian Thực:**
   * Hiển thị đường dao động độ tập trung 20 giây gần nhất ngay trong thẻ Focus Score.

7. **🔔 Thông Báo Đa Tầng (Windows Toast & Voice Alerts):**
   * Ngay cả khi thu nhỏ cửa sổ để làm bài tập trên Word hay trình duyệt, popup thông báo Windows Toast vẫn bật lên nhắc nhở kịp thời.

---

## 🛠 Hướng Dẫn Cài Đặt (Installation)

### 1. Yêu Cầu Hệ Thống
* Hệ điều hành: Windows 10 / 11 (64-bit).
* Python 3.10, 3.11 hoặc 3.12.
* Webcam đang hoạt động bình thường.

### 2. Tải Mã Nguồn & Cài Thư Viện

```powershell
# Clone kho mã nguồn về máy
git clone git@github.com:vuxgiakhanh-source/focus-guard.git
cd focus-guard

# Khuyến nghị: Tạo môi trường ảo
python -m venv venv
.\venv\Scripts\activate

# Cài đặt thư viện phụ thuộc
pip install -r requirements.txt
```

> **Ghi chú:** Trọng số AI (`face_landmarker.task` 3.7MB, `yolov8n.pt` 6.5MB) và toàn bộ âm thanh cảnh báo đã đính kèm sẵn trong kho lưu trữ — bạn không cần tải thêm bất kỳ file nào từ bên ngoài!

---

## 🚀 Hướng Dẫn Khởi Chạy (Quick Start)

### Cách 1: Bấm Icon Từ Desktop (Khuyên Dùng)
Chạy lệnh này một lần duy nhất để tạo icon ra ngoài màn hình chính:
```powershell
powershell -ExecutionPolicy Bypass -File install_shortcut.ps1
```
Sau đó ra ngoài Desktop, nhấp đúp vào biểu tượng **FocusGuard PRO** (khởi động êm ái, không hiện cửa sổ cmd đen).

### Cách 2: Khởi Chạy Bằng Lệnh
```powershell
python main.py
```

---

## 📘 HƯỚNG DẪN SỬ DỤNG CHI TIẾT TỪ A - Z (User Guide)

### 🎯 Quy trình 1 buổi học chuẩn:

#### Bước 1: Khởi động & Cân chỉnh camera
* Mở app lên. Đặt laptop hoặc webcam ở góc bạn thấy thoải mái nhất (thẳng mặt hoặc chéo bên đều được).
* Đảm bảo khung camera có nhìn thấy mặt bạn.

#### Bước 2: Dạy AI góc học tập & Dáng mắt (Khuyên dùng khi bắt đầu)
* Bấm nút **`[C] Dạy góc học`** trên màn hình (hoặc nhấn phím **`C`**).
* Màn hình sẽ hiện thanh tiến trình đếm ngược 60 giây.
* Trong 60 giây này, bạn chỉ cần ngồi học bình thường (đọc sách, nhìn màn hình, viết bài...).
* 👉 **AI sẽ tự động:**
  1. Ghi nhớ góc ngồi học tự nhiên của bạn.
  2. Đo độ mở mắt của bạn (đặc biệt hữu ích nếu bạn **đeo kính cận** hoặc có **dáng mắt híp**) để không bao giờ bị báo nhầm buồn ngủ!

#### Bước 3: Học bài & Kỷ luật tự giác
Trong quá trình học, AI sẽ âm thầm giám sát:
* 😴 **Nếu bạn nhắm mắt quá 2 giây:** Giọng nói tiếng Việt sẽ nhắc *"Bạn đang buồn ngủ, hãy tập trung!"* và viền đỏ màn hình nhấp nháy.
* 📱 **Nếu bạn nhấc điện thoại lên tay:** Khung màu đỏ lập tức khóa chặt vị trí chiếc điện thoại và phát loa cảnh báo.
* 🌐 **Nếu bạn mở Facebook/YouTube lướt:** Sau 2.5 giây thao tác chuột/phím liên tục, AI sẽ lên tiếng nhắc nhở quay lại học và trừ điểm tập trung.
* ☕ **Bật Pomodoro:** Bấm **`P`** để vào chu kỳ chuẩn 25 phút học tập trung cao độ.

#### Bước 4: Nghỉ giải lao (Pomodoro Break)
* Khi hết 25 phút học, chuông báo sẽ reo và màn hình chuyển sang tông **màu tím hồng thư giãn**.
* Trong 5 phút này: Toàn bộ cảnh báo camera, điện thoại và lướt web sẽ **tự động tắt 100%**. Bạn có thể thoải mái bấm điện thoại, nghe nhạc, giải trí.
* Khi hết 5 phút nghỉ: Giọng nói sẽ thông báo hết giờ nghỉ để bạn quay lại bàn học!

#### Bước 5: Kết thúc phiên học & Xem báo cáo
* Khi học xong: Bấm nút **`[Q] Thoát`** (hoặc nhấn phím **`Q`** / nút **`X`** cửa sổ).
* Hệ thống sẽ tự động:
  1. Bắn thông báo Windows Toast tổng kết thời gian học và điểm tập trung.
  2. In bảng báo cáo chi tiết ra màn hình (số lần cầm điện thoại, số lần lướt mạng xã hội, chu kỳ Pomodoro).
  3. Tự động cộng dồn vào lịch sử học tập tích lũy.

---

## ⌨️ Bảng Phím Tắt & Nút Bấm Điều Khiển

Tất cả các chức năng đều hỗ trợ **Click chuột trực tiếp** lên thanh điều khiển ở đáy cửa sổ hoặc bấm phím tắt:

| Nút Bấm Chuột | Phím Tắt | Chức Năng |
| :---: | :---: | :--- |
| **`[C] Dạy góc học`** | **`C`** | Bắt đầu đo góc ngồi học và dáng mắt trong 60 giây |
| **`[P] Pomodoro`** | **`P`** | Bật / Tắt chu kỳ đếm giờ Pomodoro (25 phút học / 5 phút nghỉ) |
| **`[M] Âm thanh`** | **`M`** | Tắt / Mở âm thanh giọng nói cảnh báo (hữu ích khi ngồi thư viện) |
| **`[R] Reset`** | **`R`** | Đặt lại điểm tập trung 100% và đồng hồ thời gian học |
| **`[Q] Thoát`** | **`Q`** / **`Esc`** | Thoát ứng dụng an toàn, lưu lịch sử và hiển thị báo cáo |

---

## ❓ Câu Hỏi Thường Gặp (FAQ)

**Q1: Ứng dụng có làm nóng máy hay tốn pin khi chạy lâu không?**  
* **A:** Hoàn toàn không! FocusGuard PRO chạy với tần suất xử lý tối ưu ~11.8ms/frame (chỉ tốn ~35% chu kỳ một luồng CPU), các luồng AI chạy đơn luồng độc lập, đảm bảo máy luôn êm mát và tiết kiệm pin.

**Q2: Nếu tôi ngồi học ở thư viện hoặc quán cà phê thì làm sao?**  
* **A:** Bạn chỉ cần click nút **`[M] Âm thanh`** (hoặc nhấn phím **`M`**) để chuyển sang chế độ im lặng `[MUTE]`. Mọi cảnh báo sẽ chuyển sang dạng viền đỏ trực quan trên màn hình và popup Windows Toast, không gây ồn ào xung quanh.

**Q3: Tôi đeo kính gọng dày hay bị báo buồn ngủ oan thì chỉnh thế nào?**  
* **A:** Bạn chỉ cần bấm phím **`C`** một lần. AI sẽ đo mức độ mở mắt xuyên qua tròng kính của bạn trong 60s và tự động hạ ngưỡng phát hiện nhắm mắt về mức chuẩn xác riêng cho bạn.

**Q4: Dữ liệu học tập được lưu ở đâu?**  
* **A:** Lịch sử học tập được lưu cục bộ ngay trong thư mục app (file `focus_history.json`). File này đã được thêm vào `.gitignore` để đảm bảo dữ liệu riêng tư của bạn không bao giờ bị lộ lên GitHub.

---

## 📄 Bản Quyền & Giấy Phép (License)

Dự án được phân phối dưới giấy phép mã nguồn mở [MIT License](LICENSE).

Tác giả: **Vũ Gia Khánh**  
Email: [vuxgiakhanh@gmail.com](mailto:vuxgiakhanh@gmail.com)  
GitHub: [@vuxgiakhanh-source](https://github.com/vuxgiakhanh-source)
