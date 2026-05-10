# Kế hoạch Triển khai: Refactor Frontend sang DDD + Clean Architecture

## 1. Mục tiêu
Chuyển đổi cấu trúc dự án Next.js hiện tại sang kiến trúc Domain-Driven Design (DDD) kết hợp Frontend Clean Architecture nhằm đảm bảo tính mở rộng, dễ bảo trì và tách biệt rõ ràng UI khỏi Logic nghiệp vụ.

## 2. Quyết định Công nghệ
- **Framework**: Next.js 15+ (App Router)
- **State Management**: Zustand
- **Data Fetching / Caching**: React Query (TanStack Query)
- **Styling**: Tailwind CSS

## 3. Cấu trúc Thư mục Mới (Domain-Centric)
```text
frontend/src/
├── app/                    # 🟢 Tầng Framework (Chỉ chứa Routing & Provider)
│   ├── layout.tsx          # Setup React Query Provider
│   └── chat/page.tsx       # Wrapper gọi Screen component
│
├── core/                   # ⚙️ Core System
│   ├── config/             # Biến môi trường, hằng số
│   ├── errors/             # Base Error classes
│   └── http/               # Base Fetch/Axios client
│
├── shared/                 # 🧩 Shared UI & Utils
│   ├── components/         # Design System (BottomNav, Button,...)
│   ├── hooks/              # Custom hooks chung
│   └── utils/              # Helper format functions
│
└── modules/                # 🧱 CÁC DOMAINS (DDD)
    │
    ├── chat/               # 💬 Domain: Trò chuyện AI
    │   ├── domain/         # Entities (Message, Session)
    │   ├── application/    # Zustand Store, Use Cases
    │   ├── infrastructure/ # API client cho Chat
    │   └── presentation/   # ChatBubble, ChatInput, ChatScreen
    │
    ├── diagnostics/        # 🔍 Domain: Chẩn đoán sâu bệnh (Vision)
    │   ├── domain/         # Entities (DiseaseResult, ImagePayload)
    │   ├── application/    # React Query hooks (useDiagnose)
    │   ├── infrastructure/ # Upload API, Vision API
    │   └── presentation/   # Camera Modal, Result UI
    │
    └── handbook/           # 📚 Domain: Cẩm nang nông nghiệp
        ├── domain/
        ├── application/
        ├── infrastructure/
        └── presentation/
```

## 4. Các Giai đoạn Thực thi (Phases)

### Phase 1: Nền móng & Cấu hình (Core & Config)
- Cài đặt thư viện: `zustand` và `@tanstack/react-query`.
- Khởi tạo thư mục `core/`, `shared/`, `modules/`.
- Cấu hình alias path trong `tsconfig.json` (ví dụ: `@/core/*`, `@/shared/*`, `@/modules/*`).
- Tạo và thiết lập `QueryClientProvider` trong `app/layout.tsx`.

### Phase 2: Refactor Shared UI
- Di chuyển `BottomNav.tsx` từ `components/layout/` sang `shared/components/layout/`.
- Sửa lại các đường dẫn import bị lỗi trong project.

### Phase 3: Xây dựng Domain `chat` (Trò chuyện)
- Di chuyển `ChatBubble` và `ChatInput` vào `modules/chat/presentation/components/`.
- Khởi tạo Zustand store `useChatStore` trong `modules/chat/application/` để quản lý danh sách tin nhắn.
- Refactor `app/chat/page.tsx` thành một server component siêu mỏng, chỉ import `ChatScreen` từ tầng presentation của module `chat`.

### Phase 4: Thiết lập Domain `diagnostics` (Chẩn đoán)
- Khởi tạo cấu trúc cho `modules/diagnostics/`.
- Xây dựng React Query hook để mô phỏng (mock) việc gửi hình ảnh và nhận về kết quả bệnh học.
- Nối sự kiện nút "Chụp ảnh" ở `ChatInput` với domain `diagnostics`.

### Phase 5: Clean up (Dọn dẹp)
- Xóa thư mục `src/components/` cũ khi đã chuyển đổi xong toàn bộ.

## 5. Quy tắc Kiến trúc (Architecture Rules)
- **Dependency Rule**: Tương tác chỉ đi từ ngoài vào trong: `Presentation` -> `Application` -> `Domain` <- `Infrastructure`.
- Tầng `Domain` là trung tâm, tuyệt đối **không** phụ thuộc vào React, Next.js hay thư viện ngoài.
- Tầng `Presentation` (UI) chỉ hiển thị dữ liệu và gọi các action, **không** gọi trực tiếp `fetch` hay `axios`.
- Tầng `Application` (Zustand/React Query hooks) làm cầu nối giữa UI và Data.
