# 🌿 Nông Trí AI - Trợ lý Nông nghiệp Thông minh

Chào mừng bạn đến với dự án **Nông Trí AI** (ArgiAI). Đây là nền tảng ứng dụng công nghệ Trí tuệ Nhân tạo (AI) giúp bà con nông dân chẩn đoán sâu bệnh, tra cứu cẩm nang canh tác và nhận tư vấn trực tiếp từ Chuyên gia AI theo thời gian thực.

Dự án được cấu trúc theo mô hình **Microservices**, phân tách rõ ràng giữa giao diện người dùng (Frontend) và máy chủ xử lý dữ liệu (Backend).

---

## 🏗 Cấu trúc Hệ thống (Architecture)

### 1. Luồng hoạt động (Data Flow)
Sơ đồ dưới đây thể hiện luồng luân chuyển dữ liệu từ phía Nông dân (Mobile/Web) tới các phân hệ AI cốt lõi của Backend.

```mermaid
flowchart TD
    classDef userLayer fill:#eff6ff,stroke:#3b82f6,stroke-width:2px,color:#1e3a8a,rx:10,ry:10;
    classDef securityLayer fill:#fef2f2,stroke:#ef4444,stroke-width:2px,color:#991b1b,rx:10,ry:10;
    classDef coreLayer fill:#f0fdf4,stroke:#22c55e,stroke-width:2px,color:#166534,rx:10,ry:10;
    classDef dbLayer fill:#f5f3ff,stroke:#8b5cf6,stroke-width:2px,color:#5b21b6,rx:10,ry:10;
    classDef orchestrator fill:#fff7ed,stroke:#f97316,stroke-width:2px,color:#9a3412,rx:10,ry:10;

    subgraph Client [🧑‍🌾 GIAO DIỆN ĐẦU VÀO]
        direction LR
        UI["📱 Web / App Mobile"]:::userLayer
        Voice["🎙️ Ghi âm Giọng Nói"]:::userLayer
        Cam["📸 Chụp Mẫu Bệnh"]:::userLayer
    end

    subgraph Robustness [🛡️ LỚP KIỂM DUYỆT Đoạn 1]
        STT["Phân Tích & Dịch Giọng<br>(Speech-to-Text)"]:::securityLayer
        CleanImg["Kiểm Tra Chất Lượng Ảnh<br>(Bộ Lọc Nhiễu)"]:::securityLayer
        PromptGuard["Kiểm Duyệt Nội Dung<br>(Chống Hack/Jailbreak)"]:::securityLayer
        Reject("🛑 Báo Lỗi / Từ Chối"):::securityLayer
    end

    subgraph Core [🧠 LÕI XỬ LÝ TRÍ TUỆ NHÂN TẠO]
        Orchestrator{"ĐIỀU PHỐI AI Router"}:::orchestrator
        RAG["🔍 RAG Engine<br>(Truy tìm ngữ cảnh)"]:::coreLayer
        LLM["🤖 Logic Chẩn Đoán<br>(Vision & LLM)"]:::coreLayer
    end

    subgraph DB [📚 CƠ SỞ TRI THỨC]
        Docs["Tài Liệu Nông Nghiệp<br>Khuyến Nông VN"]:::dbLayer
        VectorDB[("Vector Database<br>(Pinecone/Chroma)")]:::dbLayer
    end

    subgraph Output [✨ KẾT QUẢ ĐẦU RA]
        UI_Out["📱 Màn Hình Hiển Thị Của Nông Dân"]:::userLayer
    end

    %% Ép Layout xếp dọc để tránh vỡ khung hình
    Client ~~~ Robustness
    Robustness ~~~ Core
    Core ~~~ Output

    %% Các liên kết luồng đi xuống
    UI -->|"Nhập Text"| PromptGuard
    Voice -->|"File Audio"| STT
    Cam -->|"File Ảnh"| CleanImg

    STT -->|"Text"| PromptGuard
    CleanImg -->|"Ảnh Đã Lọc"| PromptGuard

    PromptGuard -->|"Hợp Lệ"| Orchestrator
    PromptGuard -.->|"Vi Phạm"| Reject

    Docs -.->|"Nhúng Data<br>(Embedding)"| VectorDB
    Orchestrator -->|"Câu Hỏi"| RAG
    
    RAG -->|"Truy vấn"| VectorDB
    VectorDB -.->|"Trả Ngữ cảnh"| RAG

    RAG -->|"Gửi Ngữ Cảnh Chính Xác"| LLM
    Orchestrator -->|"Gửi Ảnh Mẫu Bệnh"| LLM

    %% Trả kết quả về giao diện cuối cùng
    LLM ===>|"Trả Lời Khuyên & Nguồn Bệnh"| UI_Out
    Reject -.->|"Hiển thị lỗi"| UI_Out
```

### 2. Cây thư mục (Directory Tree)
Toàn bộ mã nguồn dự án được đặt trong thư mục gốc `ArgiAI/` với 2 phân hệ chính:

```text
ArgiAI/
├── docs/                 # 📚 Tài liệu, thiết kế và kế hoạch dự án
├── frontend/             # 📱 Giao diện Web App (Kiến trúc DDD + Clean Architecture)
│   ├── public/           # Tài nguyên hình ảnh, biểu tượng
│   └── src/
│       ├── app/          # Tầng Routing (Next.js App Router)
│       ├── core/         # Lõi hệ thống (Cấu hình, HTTP client)
│       ├── shared/       # UI Components & Hooks dùng chung
│       └── modules/      # Các Domain nghiệp vụ (chat, diagnostics, handbook)
│
├── backend/              # ⚙️ Hệ thống API Server (FastAPI + Clean Architecture)
│   ├── app/
│   │   ├── core/         # Lõi hệ thống (Cấu hình env, Dependency Injection)
│   │   ├── shared/       # Error Handlers, Interfaces & Utils dùng chung
│   │   └── modules/      # Các Domain nghiệp vụ (chat, diagnostics, handbook)
│   ├── Dockerfile        # Cấu hình Docker
│   ├── requirements.txt  # Thư viện Python
│   └── README.md         # Tài liệu cấu trúc chi tiết Backend
│
├── docker-compose.yml    # File cấu hình chạy toàn bộ hệ thống
└── README.md             # 📍 Tài liệu tổng quan dự án
```

---

## 📱 Phân hệ Frontend 

Giao diện người dùng được thiết kế chuẩn mực theo phong cách **Premium Glassmorphism**, tối ưu hóa tuyệt đối cho trải nghiệm trên màn hình di động (Mobile Simulator) nhằm mang lại sự mượt mà và trực quan nhất.

### 🛠 Công nghệ sử dụng (Tech Stack)

- **Framework:** Next.js 15+ (App Router), React 19.
- **Kiến trúc:** Domain-Driven Design (DDD) kết hợp Frontend Clean Architecture.
- **State Management:** Zustand (Global State).
- **Data Fetching/Caching:** React Query (TanStack Query) cho Server State.
- **Styling:** Tailwind CSS.
- **Typography:** Be Vietnam Pro (tối ưu hiển thị tiếng Việt).
- **Animations:** Framer Motion (hiệu ứng chuyển động mượt mà).
- **Icons:** Lucide React.

---

## ⚙️ Phân hệ Backend (API Server)

Thư mục `backend/` được quy hoạch chuẩn mực theo kiến trúc **Domain-Driven Design (DDD)** kết hợp **Clean Architecture** và cơ chế **Dependency Injection**, đảm bảo khả năng mở rộng tối đa. Hệ thống tập trung tối ưu chi phí bằng các giải pháp AI mã nguồn mở.

### 🛠 Công nghệ sử dụng (Tech Stack)

- **Framework:** FastAPI (Python) siêu tốc độ, hỗ trợ Async. Tích hợp sẵn cơ chế **Dependency Injection** qua `Depends()`.
- **Kiến trúc:** Domain-Driven Design (DDD) kết hợp Backend Clean Architecture.
- **Trí tuệ nhân tạo (Lõi LLM & Vision):** Gemini 1.5 Flash (Xử lý ảnh và phân tích ngữ cảnh RAG cực tốt, tiết kiệm chi phí).
- **Voice-to-Text (Offline):** Faster-Whisper (Giải pháp mã nguồn mở chạy trực tiếp trên CPU, nhận diện tiếng Việt cực chuẩn mà không tốn phí API).
- **Vector Database (Mã nguồn mở):** ChromaDB lưu trữ cục bộ, phục vụ kiến trúc RAG không giới hạn.
- **AI Orchestrator:** LangChain/LangGraph điều phối luồng kiểm duyệt và tạo chuỗi suy luận.

---

## 🚀 Hướng dẫn Khởi chạy (Local Development)

### Khởi chạy toàn bộ hệ thống bằng Docker Compose (Khuyên dùng)
Cách nhanh nhất để chạy toàn bộ dự án (cả Frontend và Backend) ở môi trường Production mà không cần cấu hình phức tạp:

```bash
# Đứng tại thư mục gốc của dự án (ArgiAI)
docker compose up -d --build
```
Hệ thống sẽ tự động đóng gói và bật song song 2 máy chủ:
- 📱 **Giao diện Nông dân (Frontend)**: [http://localhost:3000](http://localhost:3000)
- ⚙️ **Hệ thống API (Backend Swagger)**: [http://localhost:8000/docs](http://localhost:8000/docs)

Để dừng toàn bộ hệ thống, chạy lệnh `docker compose down`.

---
### Khởi chạy thủ công từng phân hệ (Môi trường Dev)

#### 1. Chạy giao diện Frontend (Next.js)
Nếu bạn muốn code và xem thay đổi ngay lập tức (Hot-Reload):

```bash
# 1. Di chuyển vào thư mục frontend
cd frontend

# 2. Cài đặt các gói phụ thuộc
npm install

# 3. Khởi động máy chủ giao diện
npm run dev
```
Sau đó, mở trình duyệt tại: [http://localhost:3000](http://localhost:3000) để trải nghiệm.

#### 2. Chạy máy chủ Backend (FastAPI)
Mở một tab Terminal mới:

```bash
# 1. Di chuyển vào thư mục backend
cd backend

# 2. Tạo môi trường ảo và cài đặt thư viện
python3 -m venv venv
source venv/bin/activate  # (Windows: venv\Scripts\activate)
pip install -r requirements.txt

# 3. Tạo file biến môi trường (Cấu hình API Key nếu cần)
cp .env.example .env

# 4. Chạy server FastAPI
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```
Truy cập tài liệu API tự động tại: [http://localhost:8000/docs](http://localhost:8000/docs).

---
*Dự án Nông Trí AI - Đồng hành cùng nền nông nghiệp Việt Nam.* 🌾
