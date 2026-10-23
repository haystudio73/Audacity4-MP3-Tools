# Import Suno MP3 public direct to → Audacity 4

## Quick Install

Tải repository bằng **Code → Download ZIP** và giải nén (hoặc `git clone`). Trên Windows đã có Audacity 4, mở PowerShell **trong thư mục dự án** rồi chạy:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\install.ps1
```

Script kiểm tra Python 3.10+ có Tkinter, `ffmpeg` và `ffprobe`; cài phần còn thiếu qua WinGet rồi tự chạy `install.py`. Python cài mới dùng nhánh 3.13. Các thành phần đã hoạt động được giữ lại. Cài cho tài khoản Windows hiện tại; mở PowerShell thông thường, không cần chọn Run as administrator. Lệnh trên chỉ áp dụng ExecutionPolicy cho tiến trình đang chạy.

Sau khi báo **Done**, khởi động lại Audacity, mở **Start Suno Helper.vbs**, rồi vào **Tools → Nyquist → Suno Audacity Importer → Suno URL Import** để dán URL.

`Start Suno Helper.vbs` và file plugin `.ny` được tạo khi cài đặt, theo đường dẫn trên máy bạn; repository chỉ chứa template `.ny.in`.

Cần Internet khi tải thành phần còn thiếu. Nếu máy chưa có WinGet, cài/cập nhật [App Installer](https://apps.microsoft.com/detail/9NBLGGH4NNS1), mở lại PowerShell và chạy lại lệnh. Script tự chấp nhận thỏa thuận gói cài đặt của WinGet. Chỉ muốn kiểm tra, thêm `-CheckOnly` vào cuối lệnh.

## Sử dụng

1. Mở `Start Suno Helper.vbs`. Giữ helper chạy; có thể thu nhỏ cửa sổ.
<img width="636" height="294" alt="image" src="https://github.com/user-attachments/assets/3549fa31-05c6-46dc-9cd0-d8ca0bb305e6" />

2. Trong dự án Audacity muốn nhập audio, chọn **Tools → Nyquist → Suno Audacity Importer → Suno URL Import**. Cách nhóm menu có thể khác theo cấu hình plugin.
<img width="1005" height="683" alt="image" src="https://github.com/user-attachments/assets/afe50e93-4e8c-4d13-8ab9-d50f8491b834" />

3. Plugin kiểm tra helper ngay khi chọn menu. Nếu chưa chạy, thông báo yêu cầu mở **Start Suno Helper.vbs**; mở helper rồi chọn lại menu.
4. Trong hộp thoại **Suno URL Import** của helper, dán URL dạng `https://suno.com/song/UUID` hoặc URL MP3 public, nhấn **Import**. Nút **✕ Xóa** xóa toàn bộ URL và đưa con trỏ về ô nhập. **Hủy** hoặc Escape đóng hộp thoại mà không tải audio.
5. Giữ hoặc đưa cửa sổ dự án đó về phía trước khi helper yêu cầu. Helper tự mở hộp thoại Import và nhập audio thành track.

✴️✴️✴️ Nếu Helper báo lỗi không import được MP3 (403): Hãy mở lại link nhạc Suno trong website, nhấn F5 để refresh. Sau đó quay lại mở tools Import lại!

MP3 được giữ trong `downloads/`. Helper không tự lưu dự án Audacity. Nếu dự án bị đóng hoặc cửa sổ đích không sẵn sàng trong 90 giây, thao tác import báo lỗi; MP3 đã tải vẫn còn để nhập thủ công.

## Cài đặt hoặc chuyển thư mục

Yêu cầu Windows, Audacity 4.0.1, Python 3.10+ có Tkinter, và `ffmpeg` cùng `ffprobe` trên PATH để dùng phương án video. Không cần pip package. Có thể chỉ định đường dẫn chương trình bằng biến `SUNO_FFMPEG` và `SUNO_FFPROBE`.

```powershell
python install.py
```

Installer tạo launcher và plugin với đường dẫn tuyệt đối tới thư mục hiện tại, rồi chép plugin vào `%APPDATA%\audacity\Audacity4\Plug-Ins`. Khởi động lại Audacity hoặc quét lại plugin nếu tool chưa xuất hiện. Khi chuyển thư mục dự án hoặc thay Python, chạy installer lại. Đóng rồi mở lại helper sau khi cập nhật mã Python. Bản 0.3.1 sửa hộp thoại Suno URL Import bị Audacity che phía sau; cần mở lại helper để áp dụng.

## Buy me a cup of coffe

❤️❤️❤️ Nếu bạn yêu thích mã nguồn này ❤️❤️❤️ HÃY MỜI TÔI 1 LY CAFE (Momo QR)!

<img width="390" height="422" alt="image" src="https://github.com/user-attachments/assets/8d0590a0-1bf7-4ff8-aed9-b224b0325706" />

Thanks, and good luck!




## Giấy phép

GNU GPL v3, theo [LICENSE](LICENSE) của repository.
