# Kế hoạch Tái cấu trúc Backend - Strict Clean Architecture & DDD

## Mục tiêu
Loại bỏ hoàn toàn các vi phạm rò rỉ Dependency (Dependency Leakage) trong hệ thống Backend hiện tại, đảm bảo tuân thủ tuyệt đối nguyên tắc Dependency Inversion (DIP) của Clean Architecture.

## 1. Vấn đề hiện tại
- **Dependency Leakage ở Presentation:** Tầng `presentation` (trong `router.py`) đang gọi trực tiếp vào tầng `infrastructure` (qua file `di.py`) để lấy Dependencies. Điều này vi phạm nguyên tắc "High-level modules should not depend on low-level modules".
- **Rò rỉ Infrastructure vào Core:** Khởi tạo `chromadb.HttpClient` trực tiếp bên trong `app/core/database.py`, làm cho Core gắn chặt với một công nghệ cụ thể (ChromaDB), khó thay đổi sau này.

## 2. Đề xuất Cấu trúc mới (Sample Structure)

Dưới đây là cấu trúc sau khi đã Refactor. Sự thay đổi quan trọng nhất là việc di dời file `di.py` ra ngoài và làm sạch `core/database.py`.

```text
backend/app/
├── core/
│   ├── config.py
│   └── (Đã xóa file database.py chứa logic ChromaDB)
├── shared/
│   ├── infrastructure/
│   │   └── vector_db.py  <-- (Mới) Đưa logic ChromaDB vào đây, tách biệt hoàn toàn khỏi Core
│   ├── errors/
│   └── interfaces/
└── modules/
    ├── chat/
    │   ├── dependencies.py    <-- (Mới) Đổi tên từ infrastructure/di.py và đưa ra gốc module
    │   ├── application/
    │   │   └── service.py
    │   ├── domain/
    │   │   ├── entities.py
    │   │   └── interfaces.py
    │   ├── infrastructure/
    │   │   └── mock_provider.py
    │   └── presentation/
    │       ├── router.py      <-- Chỉ import từ `dependencies.py`, KHÔNG import từ `infrastructure/`
    │       └── schemas.py
    ├── handbook/
    │   ├── dependencies.py    <-- (Mới) Composition Root của Handbook
    │   ├── application/
    │   ├── domain/
    │   ├── infrastructure/
    │   │   └── mock_repository.py
    │   └── presentation/
    │       ├── router.py
    │       └── schemas.py
    └── diagnostics/
        ├── dependencies.py    <-- (Mới) Composition Root của Diagnostics
        ├── application/
        ├── domain/
        ├── infrastructure/
        └── presentation/
```

## 3. Các bước thực thi chi tiết

### Bước 1: Refactor Module Dependency Injection (Composition Root)
- Di chuyển `app/modules/chat/infrastructure/di.py` -> `app/modules/chat/dependencies.py`
- Di chuyển `app/modules/handbook/infrastructure/di.py` -> `app/modules/handbook/dependencies.py`
- Di chuyển `app/modules/diagnostics/infrastructure/di.py` -> `app/modules/diagnostics/dependencies.py`

### Bước 2: Cập nhật Import trong Presentation (Routers)
- Thay đổi toàn bộ các dòng `from ..infrastructure.di import get_...` trong các file `router.py` thành `from ..dependencies import get_...`
- Cập nhật lại các import relative bên trong chính file `dependencies.py` cho đúng đường dẫn mới.

### Bước 3: Đóng gói Infrastructure tầng Core (Tùy chọn nâng cao)
- Tạo file `app/shared/infrastructure/vector_db.py`.
- Di dời mã nguồn khởi tạo `chromadb` từ `app/core/database.py` sang `vector_db.py`.
- Sửa lại file `app/modules/handbook/infrastructure/mock_repository.py` (nếu sau này có ChromaRepository thật) để import từ `shared.infrastructure.vector_db`.
- Xóa file `app/core/database.py` nếu không còn sử dụng.

### Bước 4: Kiểm thử tĩnh (Validation)
- Chạy thử Server (`fastapi dev app/main.py`) để đảm bảo không bị lỗi vòng lặp import (Circular Import) và ứng dụng vẫn khởi động bình thường.
