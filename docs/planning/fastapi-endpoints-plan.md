# Kế Hoạch Cài Đặt FastAPI Endpoints (Phân hệ Backend)

Tài liệu này xác định các giao diện API (Endpoints) cần thiết cho Backend của Nông Trí AI, tuân thủ nguyên tắc **Domain-Driven Design (DDD)** và chuẩn giao tiếp RESTful.

## 1. Mục Tiêu
- Khởi tạo tất cả các Routers cho 3 module chính: `chat`, `diagnostics`, và `handbook`.
- Khai báo các Pydantic Schemas (DTOs) để validation dữ liệu đầu vào/đầu ra.
- Kết nối các Routers vào `app/main.py`.
- Ở giai đoạn này, các endpoint sẽ trả về **dữ liệu giả lập (Mock Data)** trước. Việc tích hợp logic xử lý AI (Whisper, Gemini, ChromaDB) sẽ được thực hiện ở các bước sau.

---

## 2. Thiết Kế API Endpoints

### 2.1. Module Chat (Trợ lý Nông Nghiệp)
*Vị trí file: `app/modules/chat/presentation/router.py`*

| Method | Endpoint | Mô tả | Đầu vào (Input) | Đầu ra (Output) |
| :--- | :--- | :--- | :--- | :--- |
| `POST` | `/api/v1/chat/transcribe` | Chuyển đổi file âm thanh (giọng nói) thành văn bản (Speech-to-Text). | `multipart/form-data`: `file` (Audio) | `{"text": "văn bản đã dịch"}` |
| `POST` | `/api/v1/chat/message` | Gửi tin nhắn text (hoặc audio text) lên trợ lý AI và nhận phản hồi. | JSON: `{"message": "string", "session_id": "string"}` | `{"reply": "string", "sources": [...]}` |

### 2.2. Module Diagnostics (Chẩn Đoán Hình Ảnh)
*Vị trí file: `app/modules/diagnostics/presentation/router.py`*

| Method | Endpoint | Mô tả | Đầu vào (Input) | Đầu ra (Output) |
| :--- | :--- | :--- | :--- | :--- |
| `POST` | `/api/v1/diagnostics/analyze` | Phân tích hình ảnh bệnh cây bằng AI Vision. | `multipart/form-data`: `image` (File) | `{"disease_name": "...", "confidence": 0.9, "treatment": "..."}` |

### 2.3. Module Handbook (Cẩm Nang RAG)
*Vị trí file: `app/modules/handbook/presentation/router.py`*

| Method | Endpoint | Mô tả | Đầu vào (Input) | Đầu ra (Output) |
| :--- | :--- | :--- | :--- | :--- |
| `GET` | `/api/v1/handbook/search` | Tra cứu kiến thức từ Cẩm nang Nông nghiệp (Vector DB). | Query: `?q="từ khóa"&limit=5` | `{"results": [{"title": "...", "content": "..."}]}` |

---

## 3. Các Bước Triển Khai (Implementation Steps)

### Bước 1: Khởi tạo DTOs (Data Transfer Objects)
- Tạo các file `schemas.py` trong thư mục `presentation/` của từng module.
- Sử dụng `Pydantic BaseModel` để định nghĩa cấu trúc Request và Response.

### Bước 2: Tạo FastAPI Routers
- Tạo các file `router.py` trong thư mục `presentation/`.
- Viết các hàm (endpoints) tương ứng với bảng thiết kế ở trên, trả về dữ liệu Mock (Fake Data).

### Bước 3: Tích hợp vào `main.py`
- Import các routers vào `app/main.py`.
- Khai báo `app.include_router()` với `prefix` tương ứng (ví dụ: `prefix="/api/v1/chat"`).

### Bước 4: Kiểm tra Swagger UI
- Mở [http://localhost:8000/docs](http://localhost:8000/docs).
- Đảm bảo tất cả các API đều xuất hiện đúng Document và có thể test thử thành công.

---
*Tiếp theo: Sau khi thống nhất Kế hoạch này, AI sẽ bắt đầu code ngay các Routers và Schemas theo đúng thứ tự 4 bước trên.*
