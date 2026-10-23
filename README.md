# Suno → Audacity 4 — phiên bản 0.3.0

## Quick Install

Tải repository bằng **Code → Download ZIP** và giải nén (hoặc `git clone`). Trên Windows đã có Audacity 4, mở PowerShell **trong thư mục dự án** rồi chạy:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\install.ps1
```

Script kiểm tra Python 3.10+ có Tkinter, `ffmpeg` và `ffprobe`; cài phần còn thiếu qua WinGet rồi tự chạy `install.py`. Python cài mới dùng nhánh 3.13. Các thành phần đã hoạt động được giữ lại. Cài cho tài khoản Windows hiện tại; mở PowerShell thông thường, không cần chọn Run as administrator. Lệnh trên chỉ áp dụng ExecutionPolicy cho tiến trình đang chạy.

Sau khi báo **Done**, khởi động lại Audacity, mở **Start Suno Helper.vbs**, rồi vào **Tools → Nyquist → Suno Audacity Importer → Suno URL Import** để dán URL.

`Start Suno Helper.vbs` và file plugin `.ny` được tạo khi cài đặt, theo đường dẫn trên máy bạn; repository chỉ chứa template `.ny.in`.

Cần Internet khi tải thành phần còn thiếu. Nếu máy chưa có WinGet, cài/cập nhật [App Installer](https://apps.microsoft.com/detail/9NBLGGH4NNS1), mở lại PowerShell và chạy lại lệnh. Script tự chấp nhận thỏa thuận gói cài đặt của WinGet. Chỉ muốn kiểm tra, thêm `-CheckOnly` vào cuối lệnh.

Nyquist tool nhận URL Suno, gửi cho helper Windows tải MP3 rồi nhập vào cửa sổ dự án Audacity đã gọi tool. Đã cài và kiểm thử trực tiếp trên Audacity 4.0.1, Windows, ngày 22/10/2026.

Audacity 4.0.1 chặn `SYSTEM` của Nyquist; cầu nối `AUD-DO` của AU3 không được thấy đăng ký ở phần AU4. Một `.ny` độc lập không thực hiện được đầy đủ quy trình tải URL rồi import. Chi tiết và nguồn: [research/COMPATIBILITY.md](research/COMPATIBILITY.md).

## Sử dụng

1. Mở `Start Suno Helper.vbs`. Giữ helper chạy; có thể thu nhỏ cửa sổ.
2. Trong dự án Audacity muốn nhập audio, chọn **Tools → Nyquist → Suno Audacity Importer → Suno URL Import**. Cách nhóm menu có thể khác theo cấu hình plugin.
3. Plugin kiểm tra helper ngay khi chọn menu. Nếu chưa chạy, thông báo yêu cầu mở **Start Suno Helper.vbs**; mở helper rồi chọn lại menu.
4. Trong hộp thoại **Suno URL Import** của helper, dán URL dạng `https://suno.com/song/UUID` hoặc URL MP3 public, nhấn **Import**. Nút **✕ Xóa** xóa toàn bộ URL và đưa con trỏ về ô nhập. **Hủy** hoặc Escape đóng hộp thoại mà không tải audio.
5. Giữ hoặc đưa cửa sổ dự án đó về phía trước khi helper yêu cầu. Helper tự mở hộp thoại Import và nhập audio thành track. Theo dõi tiến trình/lỗi trong cửa sổ helper.

MP3 được giữ trong `downloads/`. Helper không tự lưu dự án Audacity. Nếu dự án bị đóng hoặc cửa sổ đích không sẵn sàng trong 90 giây, thao tác import báo lỗi; MP3 đã tải vẫn còn để nhập thủ công.

Nếu Suno trả 403/404 cho MP3, tool thử video MP4 public của cùng bài và chuyển audio sang MP3 256 kbps bằng FFmpeg. Đây là chuyển mã từ audio của video, không phải MP3 gốc do Suno xuất. Bài không có cả MP3 và video public sẽ không tải được. Không hỗ trợ playlist hoặc bài cần đăng nhập; link `/s/...` cần chuyển hướng được đến bài hát.

## Cài đặt hoặc chuyển thư mục

Yêu cầu Windows, Audacity 4.0.1, Python 3.10+ có Tkinter, và `ffmpeg` cùng `ffprobe` trên PATH để dùng phương án video. Không cần pip package. Có thể chỉ định đường dẫn chương trình bằng biến `SUNO_FFMPEG` và `SUNO_FFPROBE`.

```powershell
python install.py
```

Installer tạo launcher và plugin với đường dẫn tuyệt đối tới thư mục hiện tại, rồi chép plugin vào `%APPDATA%\audacity\Audacity4\Plug-Ins`. Khởi động lại Audacity hoặc quét lại plugin nếu tool chưa xuất hiện. Khi chuyển thư mục dự án hoặc thay Python, chạy installer lại. Đóng rồi mở lại helper sau khi cập nhật mã Python.

## Bản 0.3.0 và kiểm chứng

- Menu Nyquist mở hộp thoại URL của helper, có nút **✕ Xóa**, **Import** và **Hủy**. Hộp thoại hiển thị dự án đích đã ghi nhận khi chọn menu.
- Kiểm tra phiên helper và tín hiệu hoạt động cập nhật mỗi giây. Nếu file còn sót sau khi helper bị tắt đột ngột, tín hiệu quá hạn bốn giây sẽ bị từ chối và yêu cầu mở lại helper.
- Đã kiểm thử trực tiếp trên Audacity 4.0.1 ngày 23/10/2026: cảnh báo khi chưa có helper, xóa hết URL, nhập lại và import thành công bài `52e94026-fa85-4779-b54e-da4d8df58d62` vào đúng cửa sổ dự án. 19 kiểm thử tự động đạt.
- Khi nâng cấp từ 0.2.1, chạy lại `install.ps1`, đóng/mở lại helper và khởi động lại Audacity hoặc quét lại plugin.

## Bản sửa 0.2.1 trước đó

- Sửa giá trị trả về của Nyquist tool để yêu cầu hợp lệ không gây thông báo **Applying effect failed**.
- Sửa cách đọc ô tên file thuộc tiến trình Audacity, giúp helper xác nhận đường dẫn và hoàn tất Import.
- Đã kiểm thử đầu-cuối qua menu plugin với bài `52e94026-fa85-4779-b54e-da4d8df58d62`: tải/chuyển mã thành công, waveform stereo xuất hiện trong cùng cửa sổ dự án. Bài `3603f35f-f31c-4930-adcb-f05e58b4239b` cũng đã tải/chuyển mã thành công.
- 17 kiểm thử tự động đã đạt. Chưa xác minh trực tiếp tình huống nhiều dự án mở đồng thời hoặc dự án đã có nhiều track; helper có kiểm tra HWND, PID và thời điểm tạo tiến trình để ràng buộc cửa sổ đích.

Thông tin trạng thái ở `runtime/status.json`; lỗi chi tiết ở `runtime/errors.log` (có thể chứa lỗi cũ từ những lần chạy trước).

## Chạy riêng downloader

Chạy trong thư mục dự án:

```powershell
python -m suno_importer "https://cdn1.suno.ai/ID-BAI-HAT.mp3" --output downloads
```

Thay bằng URL thật. Lệnh trên chỉ tải file, chưa nhập vào Audacity. Có thể dùng URL `https://suno.com/song/...` hoặc link chia sẻ `https://suno.com/s/...` nếu trang public cung cấp metadata/chuyển hướng phù hợp. Không hỗ trợ playlist hoặc bài yêu cầu đăng nhập.

## Kiểm thử offline

```powershell
python -m unittest discover -s tests -v
```

Trong môi trường sandbox hạn chế thư mục tạm, đặt `TEMP` và `TMP` vào thư mục `tmp` của dự án trước khi chạy test.

## Giấy phép

GNU GPL v3, theo [LICENSE](LICENSE) của repository.
