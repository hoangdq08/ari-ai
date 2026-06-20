# 📱 Phân hệ Frontend - Nông Trí AI

Đây là phân hệ Giao diện người dùng của dự án **Nông Trí AI**, được phát triển dựa trên Next.js (App Router) và áp dụng triệt để kiến trúc **Domain-Driven Design (DDD)** kết hợp **Clean Architecture**.

---

## 🛠 Công nghệ sử dụng (Tech Stack)

- **Framework:** Next.js 15+ (App Router), React 19.
- **Kiến trúc:** Domain-Driven Design (DDD) + Clean Architecture + Dependency Injection (thông qua Custom Hooks/Context API).
- **State Management:** Zustand (Global) & React Query (Server).
- **UI/UX & Animation:** Tailwind CSS, Framer Motion, Lucide React, Font Be Vietnam Pro.

---

## 🏗 Kiến trúc & Cấu trúc Thư mục (Architecture & Directory Tree)

### 1. Sơ đồ Luồng dữ liệu (Data Flow & Dependency Rule)

Quy tắc cốt lõi: Các tầng bên ngoài phụ thuộc vào tầng bên trong (Domain). UI không bao giờ được gọi trực tiếp API.

```mermaid
flowchart TD
    classDef domain fill:#fef3c7,stroke:#d97706,stroke-width:2px,color:#92400e,rx:8,ry:8
    classDef infra fill:#fce7f3,stroke:#db2777,stroke-width:2px,color:#9d174d,rx:8,ry:8
    classDef presentation fill:#dcfce3,stroke:#16a34a,stroke-width:2px,color:#166534,rx:8,ry:8
    classDef core fill:#e0e7ff,stroke:#4f46e5,stroke-width:2px,color:#3730a3,rx:8,ry:8
    
    P["🖥️ Presentation Layer (UI Components, Hooks, Stores)"]:::presentation
    C["⚙️ Core / DI (Composition Root / Registry)"]:::core
    D["🧱 Domain Layer (Models, Repository Interfaces)"]:::domain
    I["🌐 Infrastructure Layer (API Implementations)"]:::infra
    
    C -. "1. Khởi tạo & Tiêm (Inject) Dependencies" .-> P
    C -. "1. Quản lý vòng đời" .-> I
    
    P -- "2. Gọi hàm (Chỉ biết Interface)" --> D
    I -. "3. Thực thi (Implements Interface)" .-> D
    
    I == "4. Giao tiếp mạng" ==> Server[("☁️ Backend Server")]
    
    %% Chú thích Dependency Rule
    P -. "Phụ thuộc chiều xuôi" .-> D
    I -. "Phụ thuộc đảo ngược (DIP)" .-> D
```

### 2. Cây thư mục (Directory Tree)

Dự án áp dụng chia tách theo các miền nghiệp vụ (Domains), giúp mã nguồn dễ mở rộng, dễ bảo trì và test.

```text
frontend/
├── public/               # Tài nguyên hình ảnh, biểu tượng
└── src/
    ├── app/              # Lớp Framework (Routing & Providers, Server Components)
    ├── core/             # Thiết lập lõi toàn cục (HTTP Client, Dependency Registry)
    ├── shared/           # Components, Hooks, Providers dùng chung (DIProvider, QueryProvider)
    └── modules/          # Các phân hệ nghiệp vụ chính (chat, diagnostics, handbook)
        ├── domain/       # Tầng trung tâm (Core)
        │   ├── models/     # Các object, type định nghĩa hình dáng dữ liệu
        │   └── repositories/ # Các hợp đồng (contracts) cho Interface
        ├── infrastructure/ # Giao tiếp API, implement các interfaces từ domain
        └── presentation/ # Tầng Hiển thị (Components, Hooks, Zustand Stores)
```

---

## 🚀 Hướng dẫn Cài đặt & Khởi chạy (Docker-Only)

Để đảm bảo tính đồng bộ trên mọi môi trường và tránh các lỗi cấu hình phiên bản Node.js phức tạp, phân hệ Frontend được tự động hoá khởi chạy thông qua **Docker Compose** ở cấp độ dự án.

Vui lòng tham khảo [👉 Hướng dẫn Khởi chạy tại Tài liệu Gốc](../README.md#🚀-hướng-dẫn-cài-đặt--khởi-chạy-docker-only) để bật toàn bộ hệ thống bằng một dòng lệnh duy nhất.

---
*Dự án Nông Trí AI - Đồng hành cùng nền nông nghiệp Việt Nam.* 🌾
