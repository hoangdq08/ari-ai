# Kế hoạch Xử lý Lỗi 404 (Not Found) Toàn hệ thống

Tài liệu này xác định các bước để chặn và xử lý triệt để các trường hợp người dùng (hoặc ứng dụng) truy cập vào những đường dẫn không tồn tại trên cả Frontend và Backend.

## Mục tiêu
Thay vì để hệ thống quăng ra những trang lỗi trắng bóc hoặc lỗi JSON mặc định của Framework, chúng ta sẽ "tút tát" lại để mọi thông báo lỗi đều đẹp mắt, đồng nhất và có cấu trúc chuẩn.

---

### Bước 1: Xử lý 404 tại Frontend (Giao diện)
- **Công cụ sử dụng**: Cơ chế `not-found.tsx` của Next.js App Router.
- **File tạo mới**: `frontend/src/app/not-found.tsx`
- **Công việc**:
  - Tạo một component hiển thị màn hình báo lỗi 404 ("Lạc đường").
  - Kế thừa giao diện khung Mobile của ứng dụng (có Header, Navigation Bottom).
  - Có icon cảnh báo, câu thông báo thân thiện bằng tiếng Việt và nút bấm "Trở về Trang chủ".
- **Kết quả**: Khi user gõ bừa 1 URL (vd: `localhost:8080/he-he`), họ sẽ thấy màn hình báo lỗi chuẩn thay vì trang báo lỗi mặc định của Next.js.

### Bước 2: Xử lý 404 tại Backend (API)
- **Công cụ sử dụng**: Cơ chế `exception_handler` của FastAPI.
- **File ảnh hưởng**: `backend/app/main.py`
- **Công việc**:
  - Import `StarletteHTTPException` và `JSONResponse`.
  - Khai báo `@app.exception_handler(StarletteHTTPException)` để "chộp" (catch) tất cả các lỗi HTTP.
  - Nếu mã lỗi là `404`, trả về cấu trúc JSON thống nhất:
    ```json
    {
      "status": "error",
      "message": "Endpoint không tồn tại hoặc đã bị di dời.",
      "data": null
    }
    ```
- **Kết quả**: Bất kỳ Frontend hay bên thứ 3 nào vô tình gọi sai link API (vd: `/api/v1/abcd`) cũng sẽ nhận được một chuỗi JSON có chuẩn mực thay vì chữ `{"detail": "Not Found"}` khô khan.

### Bước 3: Triển khai và Kiểm tra
- **Thực thi mã nguồn**: Viết code cho cả 2 tệp.
- **Kiểm tra Frontend**: Mở trình duyệt gõ `http://localhost:8080/duong-dan-sai`.
- **Kiểm tra Backend**: Dùng Postman hoặc Terminal gọi `curl http://localhost:8081/api/v1/api-ma`.
