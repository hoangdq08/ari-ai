# Kế Hoạch Quy Hoạch Biến Môi Trường (Environment Unification)

Tài liệu này xác định các bước để thống nhất toàn bộ cấu hình môi trường (.env) của dự án về một file duy nhất tại thư mục gốc, giúp dễ dàng quản lý và tăng cường bảo mật thông qua `.gitignore`.

## 1. Mục Tiêu
- Xóa bỏ các file `.env`, `.env.example`, `.env.local` rải rác ở thư mục `frontend/` và `backend/`.
- Tạo một file `.env` duy nhất ở thư mục gốc (`ArgiAI/.env`).
- Tạo một file `.env.example` ở thư mục gốc để các lập trình viên khác biết cần điền biến gì.
- Cấu hình lại `docker-compose.yml` và Next.js để đọc biến môi trường từ thư mục gốc.
- Cập nhật `.gitignore` toàn cục để ngăn chặn việc commit nhầm file nhạy cảm.

---

## 2. Các Bước Triển Khai

### Bước 1: Dọn dẹp file cũ
- Xóa `frontend/.env.local`.
- Xóa `backend/.env` (nếu có) và `backend/.env.example`.

### Bước 2: Tạo File Môi Trường Gốc
- **File `/.env`** (Thư mục gốc):
  ```env
  # --- CẤU HÌNH FRONTEND ---
  FRONTEND_PORT=8080
  NEXT_PUBLIC_API_URL=http://localhost:8081/api/v1

  # --- CẤU HÌNH BACKEND ---
  BACKEND_PORT=8081
  BACKEND_CORS_ORIGINS=["http://localhost:8080"]
  GEMINI_API_KEY=your_gemini_api_key_here
  
  # --- CẤU HÌNH VECTOR DB (CHROMA) ---
  CHROMA_DB_URL=http://chromadb:8000
  ```
- **File `/.env.example`** (Thư mục gốc): Tạo nội dung tương tự nhưng để trống Key.

### Bước 3: Cập nhật Docker Compose
- Đảm bảo `docker-compose.yml` trỏ đúng `env_file: .env`.
- Sửa mục `ports` của các service để map cổng host -> container chuẩn xác:
  - Frontend: `"${FRONTEND_PORT:-8080}:3000"` (Ánh xạ cổng 8080 của máy thật vào cổng 3000 mặc định của Next.js).
  - Backend: `"${BACKEND_PORT:-8081}:8000"` (Ánh xạ cổng 8081 của máy thật vào cổng 8000 mặc định của FastAPI).
- Bổ sung truyền biến `NEXT_PUBLIC_API_URL` vào môi trường của service `frontend`.
- Thêm service `chromadb` chạy image `chromadb/chroma:latest` (port `8000:8000`).
- Map volume cho `chromadb` để lưu data thực tế: `- ./data/chromadb:/chroma/chroma`.

### Bước 4: Thiết lập Môi trường Local Dev (Đọc .env gốc)
- **Frontend**: 
  - Cài đặt `dotenv-cli`: `npm i -D dotenv-cli`.
  - Cập nhật `package.json` lệnh dev để tự nhận Port: `"dev": "dotenv -e ../.env -- next dev -p $FRONTEND_PORT"`.
- **Backend**:
  - Giao diện khởi chạy uvicorn cũng cần ăn theo biến môi trường: `uvicorn app.main:app --reload --host 0.0.0.0 --port $BACKEND_PORT`.

### Bước 5: Cập nhật `.gitignore` gốc
Đảm bảo file `.gitignore` ở thư mục gốc chặn đứng các thành phần sau:
- Các file môi trường: `.env`, `.env.local`, `.env.*.local`
- Các thư mục build: `frontend/.next/`, `frontend/out/`, `backend/__pycache__/`
- Thư viện: `node_modules/`, `venv/`, `env/`
- Rác hệ điều hành: `.DS_Store`, `Thumbs.db`
- Dữ liệu Database cục bộ: `data/chromadb/`

### Bước 6: Khởi tạo cấu trúc Vector DB (Backend Core - HttpClient)
Để tận dụng kiến trúc Microservice, Backend sẽ kết nối với ChromaDB qua mạng lưới Docker:
- Đảm bảo có thư viện `chromadb` trong `backend/requirements.txt`.
- Tạo file `backend/app/core/database.py` (hoặc `backend/app/shared/infrastructure/chroma_db.py`).
- Viết logic khởi tạo kết nối thông qua HTTP Client: `chromadb.HttpClient(host="chromadb", port=8000)` và tạo sẵn Collection cốt lõi `agricultural_handbook`.

---
*Chờ bạn phê duyệt kế hoạch này để tôi tiến hành xóa file, thiết lập và cập nhật mã nguồn (KHÔNG chạy lệnh commit).*
