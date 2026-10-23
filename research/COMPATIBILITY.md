# Đánh giá khả năng tích hợp Suno vào Audacity

Ngày kiểm tra: 21/10/2026. Máy hiện có `C:\Program Files\Audacity 4\bin\Audacity4.exe`, ProductVersion 4.0.1.

Đã đọc cả 4 trang PDF người dùng cung cấp và render trang 4. “Phương pháp 2” là viết Nyquist `.ny`, không phải iPlug2 trong bảng framework. Tài liệu mô tả plugin xử lý âm thanh; không chứng minh khả năng tải HTTP hoặc điều khiển import của Nyquist trong Audacity 4.

## Kết quả kiểm tra mã nguồn

Tag chính thức `Audacity-4.0.1`, commit `d82386ce31175f1641d0450566a73a993c635a75`.

1. `src/effects/nyquist/libnyquist/nyx.c`, hàm `xsystem()` dòng 1397: chỉ in `Will not execute system command` rồi trả `s_true`; không chạy lệnh. Vì thế `(system "curl ...")` hoặc `(system "powershell ...")` không tải được file, dù có thể trả về true.
2. `au3/libraries/au3-nyquist-effects/NyquistBase.cpp` dòng 2746: `AUD-DO` gọi `ExecFromMainHook`. Phần triển khai hook được thấy trong giao diện AU3 `au3/src/effects/nyquist/Nyquist.cpp` dòng 850. Không thấy đăng ký hook tương ứng khi tìm toàn bộ `src/` của AU4. Do đó không thể coi ví dụ `(aud-do "Import: ...")` của AU3 là API import đã hoạt động trên AU4. Chưa chạy phép thử runtime AUD-DO.
3. Ghi chú phát hành Audacity 4.0.0 xác nhận scripting pipe và Macro Manager chưa có. Không chọn `mod-script-pipe` làm giải pháp cho 4.0.1.

Nguồn:
- https://github.com/audacity/audacity/blob/Audacity-4.0.1/src/effects/nyquist/libnyquist/nyx.c#L1397
- https://github.com/audacity/audacity/blob/Audacity-4.0.1/au3/libraries/au3-nyquist-effects/NyquistBase.cpp#L2741
- https://github.com/audacity/audacity/blob/Audacity-4.0.1/au3/src/effects/nyquist/Nyquist.cpp#L850
- https://github.com/audacity/audacity/discussions/11904
- https://www.audacityteam.org/manual/tools/nyquist/
- https://github.com/yt-dlp/yt-dlp/issues/10368 (tham khảo vấn đề Suno trả file silence.mp3; không sao chép code)

## Phương án đã triển khai

Người dùng đã đồng ý `.ny` kèm helper Windows. Plugin ghi yêu cầu vào file nội bộ; helper nhận yêu cầu, tải MP3 và nhập vào cửa sổ dự án đã xác định bằng hộp thoại Import Audio. Không dùng SYSTEM, AUD-DO hoặc scripting pipe. Đã cài và kiểm thử đầu-cuối trên Audacity 4.0.1 ngày 22/10/2026. Tình huống nhiều dự án mở đồng thời và thêm vào dự án đã có nhiều track chưa được kiểm thử trực tiếp.

Từ bản 0.3.0 (23/10/2026), người dùng chọn hộp thoại URL do helper tạo để có nút xóa. `.ny` không khai báo control: khi chọn menu, mã kiểm tra session/heartbeat chạy ngay rồi yêu cầu helper mở hộp thoại. Nyquist không cung cấp callback nút tùy chỉnh trong [các widget hỗ trợ](https://plugins.audacityteam.org/contributing/developing-your-own-plugins-and-scripts/creating-your-own-nyquist-plugins/widgets-reference); mã nguồn AU4 `nyquistparameterextractorservice.cpp` và `ParameterControl.qml` cũng dựng string control cố định. Không sửa bản cài Audacity. Timestamp dùng `get-real-time` theo [tài liệu Nyquist](https://www.cs.cmu.edu/~rbd/doc/nyquist/part19.html), đối chiếu với heartbeat của Python mỗi giây, ngưỡng quá hạn bốn giây.

## Phần đã viết

`suno_importer/downloader.py`: downloader Python không cần thư viện ngoài; hỗ trợ MP3 trực tiếp, trang `/song/UUID`, link chia sẻ chuyển hướng về trang bài hát; chỉ URL HTTPS Suno/CDN Suno. Giới hạn trang 4 MiB, audio 200 MiB, socket timeout 20s, kiểm tra deadline giữa các lần đọc. Không đăng nhập hay sử dụng cookie. Không thực thi nội dung URL/trang web.

Kiểm thử offline kiểm tra allowlist URL/chuyển hướng, metadata HTML, tránh silence.mp3, lỗi nội dung, file thiếu, giới hạn dung lượng, tên Windows và không ghi đè. Kiểm tra header MP3 là bước kiểm tra nhanh, không thay cho giải mã toàn bộ MP3.

## Video public và kiểm thử thực tế — 22/10/2026

Tham khảo ý tưởng lấy audio từ video public trong [suno-music-downloader](https://github.com/cs-eliseev/suno-music-downloader) (MIT); không sao chép mã nguồn. Với hai bài người dùng gửi, MP3 CDN trả 403 nhưng MP4 public tại `https://cdn1.suno.ai/UUID.mp4` tải được và chứa audio AAC không mã hóa. Downloader thử phương án này khi MP3 trả 403/404 và xác định được UUID bài hát, dùng FFmpeg chuyển thành MP3 256 kbps. FFprobe kiểm tra có audio và thời lượng khớp trong sai số một giây. Không dùng cookie, khóa stream hoặc giải mã DRM.

- `3603f35f-f31c-4930-adcb-f05e58b4239b` (Pentatonic Echoes): tải/chuyển mã thành công; audio nguồn stereo, 48 kHz, khoảng 219,605 giây.
- `52e94026-fa85-4779-b54e-da4d8df58d62`: kiểm thử qua menu plugin, tải/chuyển mã và nhập thành công; cùng cửa sổ Audacity xuất hiện waveform stereo và thao tác Undo Import.
- 17 kiểm thử tự động đạt sau sửa bản 0.2.1.

Lỗi “Applying effect failed” do tool trả `nil`, được Nyquist phân loại thành lỗi; trả chuỗi rỗng là kết quả thành công không chỉnh audio trực tiếp. Lỗi helper không điền được tên file do dùng `GetWindowTextW` để đọc Edit thuộc tiến trình khác; đã sửa bằng `SendMessageTimeoutW` với `WM_GETTEXT`. Đã xác nhận cả hai sửa đổi bằng lần import thực tế nêu trên.
