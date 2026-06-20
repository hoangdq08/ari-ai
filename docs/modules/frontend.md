# 📱 Frontend — Ứng dụng Web cho Nông dân

## Tổng quan

Frontend là ứng dụng web cho nông dân, xây dựng trên **Next.js 15+** với App Router, React 19 và kiến trúc DDD + Clean Architecture.

- **Port:** 8080 (mặc định)
- **URL:** `http://localhost:8080`
- **API Base:** `NEXT_PUBLIC_API_URL` → Backend (:8081)

## 🛠 Công nghệ

| Công nghệ | Phiên bản | Mục đích |
|-----------|-----------|----------|
| Next.js | 16.2.4 | Framework (App Router) |
| React | 19.2.4 | UI Library |
| TypeScript | ^5 | Type safety |
| Tailwind CSS | ^4 | Utility-first CSS |
| Zustand | ^5.0.13 | Global state management |
| React Query | ^5.100.9 | Server state & caching |
| Framer Motion | ^12.38.0 | Animations |
| Lucide React | ^1.8.0 | Icons |
| shadcn/ui | ^4.4.0 | UI components |
| Axios | ^1.16.0 | HTTP client |

## 🧱 Kiến trúc DDD + Clean Architecture

```
src/
├── app/                    # Next.js App Router
│   ├── layout.tsx          # Root layout
│   ├── page.tsx            # Home page
│   ├── not-found.tsx       # 404 page
│   ├── globals.css         # Global styles
│   ├── chat/               # Chat page
│   └── handbook/           # Handbook page
├── core/                   # Lõi hệ thống
│   ├── di/                 # Dependency Injection
│   ├── domain/             # Domain entities & interfaces
│   └── infrastructure/     # HTTP clients, repositories
├── lib/                    # Shared utilities
│   └── utils.ts
├── modules/                # Domain nghiệp vụ
│   ├── chat/               # Module chat
│   ├── diagnostics/        # Module chẩn đoán ảnh
│   ├── handbook/           # Module cẩm nang
│   └── home/               # Module trang chủ
└── shared/                 # Shared UI
    ├── components/         # Components dùng chung
    ├── hooks/              # Custom hooks
    └── providers/          # Context providers
```

## 📄 Các Trang

| Trang | Route | Module |
|-------|-------|--------|
| Trang chủ | `/` | `modules/home` |
| Chat với AI | `/chat` | `modules/chat` |
| Chẩn đoán ảnh | Trong `/chat` | `modules/diagnostics` |
| Cẩm nang | `/handbook` | `modules/handbook` |
| 404 | `*` | `not-found.tsx` |

## 🎨 UI/UX Design Principles

### Mobile-First & Nông dân Friendly
- Nút bấm cỡ lớn, dễ thao tác ngoài đồng
- Màu sắc tương phản cao cho người lớn tuổi
- Icon trực quan, giảm text khi có thể
- Font: Be Vietnam Pro (hỗ trợ tiếng Việt tốt)

### Component Architecture
- **Shared Components**: Button, Card, Input, Modal... từ `shared/components/`
- **Module Components**: Domain-specific trong `modules/[domain]/presentation/`
- **shadcn/ui**: Base UI components với Tailwind CSS

## 🔄 Data Flow

```
User Action
  → React Query Hook (useQuery/useMutation)
    → Infrastructure HTTP Client (Axios)
      → Backend API (:8081)
        → Response
      ← Cache & State Update
    ← Optimistic Update
  ← Re-render
```

### State Management

| Layer | Công cụ | Phạm vi |
|-------|---------|---------|
| Server State | React Query (`@tanstack/react-query`) | Cache, sync với Backend |
| Global State | Zustand | Chat history, user preferences |
| Local State | React `useState` | UI state (modals, forms) |
| Context | React Context | Theme, DI container |

## 📦 Module Chi tiết

### Chat Module (`modules/chat/`)
- **ChatScreen**: Giao diện chat chính
- **MessageList**: Danh sách tin nhắn
- **MessageInput**: Input text + voice + image
- **ChatStore** (Zustand): Lưu lịch sử chat local
- **useChatMutation** (React Query): Gửi/nhận tin nhắn

### Diagnostics Module (`modules/diagnostics/`)
- **DiagnoseImage**: Upload & hiển thị kết quả chẩn đoán
- **ImagePreview**: Zoom & pan ảnh bệnh
- **DiagnosisResult**: Kết quả + nguồn tham khảo
- **useDiagnoseImage** (React Query): Gọi Vision API

### Handbook Module (`modules/handbook/`)
- **HandbookScreen**: Danh sách cẩm nang
- **HandbookDetail**: Chi tiết cẩm nang
- **SearchBar**: Tìm kiếm cẩm nang
- **useHandbook** (React Query): Fetch dữ liệu cẩm nang

### Home Module (`modules/home/`)
- **HomeScreen**: Trang chủ với navigation chính
- **FeatureCards**: Các tính năng nổi bật
- **QuickActions**: Chat nhanh, chẩn đoán nhanh

## 🏗 Development Commands

```bash
cd frontend

# Install dependencies
npm ci

# Development server
npm run dev          # → localhost:8080

# Production build
npm run build

# Start production server
npm run start
```

## 🌐 Environment Variables

| Variable | Mô tả | Default |
|----------|-------|---------|
| `NEXT_PUBLIC_API_URL` | Backend API URL | `http://localhost:8081` |
| `FRONTEND_PORT` | Frontend port | `8080` |

---

← [Backend](./backend.md) | [Admin Portal](./admin.md) | [Về Trang chủ Tài liệu](./README.md) →
