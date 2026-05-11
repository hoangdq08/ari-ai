# Kế hoạch Refactor Backend tuân thủ DDD + Clean Architecture + DI

Tài liệu này xác định các bước để "chữa cháy" cho phần code tạm bợ ở `router.py` của cả 3 module: `Chat`, `Diagnostics` và `Handbook`. Chúng ta sẽ tái cấu trúc lại toàn bộ để tuân thủ nghiêm ngặt 4 lớp của Clean Architecture và ứng dụng Dependency Injection (DI) của FastAPI.

## Vấn đề hiện tại
- Việc đặt trực tiếp logic mock data và xử lý request ngay trong file `presentation/router.py` là **vi phạm nghiêm trọng nguyên tắc SRP (Single Responsibility Principle) và Clean Architecture**. 
- Router chỉ nên làm nhiệm vụ nhận request và trả response, không được chứa Logic nghiệp vụ (Application) hay truy xuất dữ liệu (Infrastructure).

---

## Các bước triển khai

### Bước 1: Refactor Module Chat (Trò chuyện AI)
1. **Lớp Domain (`domain/`)**:
   - Định nghĩa `MessageEntity` và `TranscribeEntity`.
   - Định nghĩa Interface `IChatService` hoặc `IChatRepository` (Xử lý gửi tin nhắn, nhận diện giọng nói).
2. **Lớp Infrastructure (`infrastructure/`)**:
   - Tạo `MockChatProvider` thực thi Interface trên, chứa logic mock text và mock transcribe.
   - Định nghĩa DI trong `di.py`.
3. **Lớp Application (`application/`)**:
   - Tạo `ChatService` điều phối logic giao tiếp AI.
4. **Lớp Presentation (`presentation/`)**:
   - Cập nhật `router.py`: Dùng `Depends` để tiêm `ChatService`.

### Bước 2: Refactor Module Handbook (Cẩm nang)
1. **Lớp Domain (`domain/`)**:
   - Định nghĩa `ArticleEntity`: model cốt lõi chứa cấu trúc bài viết.
   - Định nghĩa Interface (Abstract Base Class) `IHandbookRepository` có phương thức `search_articles`.
2. **Lớp Infrastructure (`infrastructure/`)**:
   - Chuyển toàn bộ mảng `MOCK_ARTICLES` vào file `mock_repository.py`.
   - Tạo class `MockHandbookRepository` kế thừa `IHandbookRepository` và thực thi hàm `search_articles`.
   - Tạo file `di.py` chứa hàm `get_handbook_service` để khởi tạo Service và tiêm (inject) Repository vào.
3. **Lớp Application (`application/`)**:
   - Tạo `HandbookService`. Service này nhận `IHandbookRepository` thông qua hàm khởi tạo (DI).
   - Chứa logic gọi xuống repository.
4. **Lớp Presentation (`presentation/`)**:
   - Cập nhật `router.py`: Dùng `Depends(get_handbook_service)` để lấy instance của Service thay vì tự xử lý logic.

### Bước 3: Refactor Module Diagnostics (Chẩn đoán bệnh)
1. **Lớp Domain (`domain/`)**:
   - Định nghĩa `DiagnosticEntity` và `IDiagnosticsRepository`.
2. **Lớp Infrastructure (`infrastructure/`)**:
   - Tạo `MockDiagnosticsRepository` chứa logic phân tích ảnh giả lập (mock AI).
   - Cấu hình DI trong `di.py`.
3. **Lớp Application (`application/`)**:
   - Tạo `DiagnosticsService` phụ thuộc vào `IDiagnosticsRepository`.
4. **Lớp Presentation (`presentation/`)**:
   - Refactor `router.py` để sử dụng `DiagnosticsService` thông qua DI.

---
### Kết quả mong đợi
- Code backend sẽ cực kỳ dễ mở rộng. Khi chúng ta thay thế Mock Data bằng thao tác truy vấn ChromaDB thật, ta chỉ cần tạo một `ChromaHandbookRepository` và đổi cấu hình ở file DI, file Router và Service sẽ không cần sửa lại 1 dòng code nào.
