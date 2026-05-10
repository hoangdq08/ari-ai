# Kế Hoạch Triển Khai Backend & AI - Nông Trí AI (Cập nhật)

Dựa trên tài liệu thiết kế và yêu cầu mới nhất: **Sử dụng kiến trúc DDD + Clean Architecture + Dependency Injection (DI)** và tối ưu chi phí bằng các giải pháp **Mã nguồn mở (Open Source)** cho Vector DB và Voice-to-Text.

## 1. Đề Xuất Công Nghệ (Tech Stack Recommendations)

| Thành phần | Công nghệ Đề xuất | Lý do & Phân tích |
| :--- | :--- | :--- |
| **Framework Backend** | **FastAPI (Python)** | Tốc độ cực nhanh, hỗ trợ tuyệt vời cho AI. Tích hợp sẵn cơ chế **Dependency Injection (DI)** thông qua `Depends()`, rất phù hợp để làm Clean Architecture. |
| **AI Orchestrator** | **LangChain / LangGraph** | Dùng để thiết kế luồng kiểm duyệt dữ liệu rẽ nhánh và RAG. |
| **Lõi AI (LLM & Vision)** | **Gemini 1.5 Flash** | Sử dụng gói Free Tier của Google AI Studio (Miễn phí 15 request/phút). Hỗ trợ đọc ảnh (Vision) xuất sắc và ngữ cảnh lớn. |
| **Vector Database** | **ChromaDB** hoặc **Qdrant** | **100% Mã nguồn mở & Miễn phí**. Lưu trữ file vector cục bộ (Local) hoặc chạy qua Docker. Không tốn bất kỳ chi phí cloud nào. |
| **Speech-to-Text (Voice)** | **Faster-Whisper** | Phiên bản mã nguồn mở, tối ưu hiệu năng của mô hình Whisper (OpenAI). **Chạy hoàn toàn Offline trên server của bạn**, không tốn phí API. Model `small` hoặc `base` chạy rất nhanh trên CPU thông thường và nhận diện tiếng Việt khá ổn định. |

## 2. Kiến Trúc Hệ Thống (DDD & Clean Architecture)

Hệ thống Backend sẽ được tuân thủ nghiêm ngặt theo **Clean Architecture** (Tách biệt logic nghiệp vụ khỏi Framework và Database) và **Domain-Driven Design (DDD)** (Chia theo các miền nghiệp vụ).

- **Domain Layer**: Chứa Entities (Ví dụ: `Message`, `Disease`, `Article`) và Interface/Abstract Base Classes (Ví dụ: `IVoiceToTextService`, `IVectorRepository`). Lớp này KHÔNG phụ thuộc vào bất kỳ thư viện bên ngoài nào.
- **Application Layer (Use Cases)**: Chứa logic luồng công việc. Ví dụ: `DiagnoseDiseaseUseCase` (Nhận ảnh -> Gọi AI -> Lưu lịch sử).
- **Infrastructure Layer**: Chứa code thực thi (Implementation) cho các giao diện ở tầng Domain. Chứa code gọi `Faster-Whisper`, kết nối `ChromaDB`, gọi API `Gemini`.
- **Presentation Layer**: Tầng giao tiếp (FastAPI Routers), nhận HTTP Request, gọi Use Case và trả về JSON.

## 3. Cấu trúc Thư mục Backend (Theo chuẩn DDD)

```text
backend/
├── app/
│   ├── main.py                    # Khởi chạy FastAPI, cấu hình CORS
│   ├── core/                      # Config (Env), Dependency Injection Container
│   ├── shared/                    # Các module dùng chung (Errors, HTTP Clients)
│   └── modules/                   # 🧱 CÁC DOMAIN NGHIỆP VỤ (DDD)
│       │
│       ├── chat/                  # 💬 Domain: Chat & Xử lý Giọng nói
│       │   ├── domain/            # Entities, Interfaces (ISTTService)
│       │   ├── application/       # ProcessVoiceChatUseCase
│       │   ├── infrastructure/    # FasterWhisperSTTService, GeminiService
│       │   └── presentation/      # chat_router.py (FastAPI Routes)
│       │
│       ├── diagnostics/           # 🔍 Domain: Chẩn đoán sâu bệnh (Vision)
│       │   ├── domain/
│       │   ├── application/
│       │   ├── infrastructure/
│       │   └── presentation/
│       │
│       └── handbook/              # 📚 Domain: Cẩm nang & RAG
│           ├── domain/            # Interfaces (IVectorDB)
│           ├── application/       # SearchHandbookUseCase
│           ├── infrastructure/    # ChromaDBRepository
│           └── presentation/
│
├── requirements.txt               # Thư viện Python
└── Dockerfile                     # Đóng gói Backend
```

## 4. Kế Hoạch Triển Khai (3 Giai đoạn)

### Giai Đoạn 1: Thiết lập Core Backend & Phân hệ Chat (Tuần 1)
- **Mục tiêu**: Xây dựng móng vững chắc với DI và Clean Architecture.
- **Công việc**:
  - Dựng khung FastAPI, cấu hình `dependency_injector` hoặc `Depends`.
  - Khởi tạo module `chat`. Triển khai **Faster-Whisper** (Tải model offline) ở tầng Infrastructure để test chuyển đổi Giọng nói -> Text miễn phí.
  - Tích hợp Gemini 1.5 Flash (Free API) vào tầng Infrastructure.

### Giai Đoạn 2: Chẩn Đoán Hình Ảnh (Vision) (Tuần 2)
- **Mục tiêu**: Giải quyết bài toán cốt lõi: Nhận ảnh bệnh -> Trả về kết quả.
- **Công việc**:
  - Viết `DiagnoseDiseaseUseCase` trong module `diagnostics`.
  - Kết nối Gemini Vision API, ép định dạng đầu ra thành chuẩn JSON có cấu trúc (Bệnh gì, Lý do, Cách trị).

### Giai Đoạn 3: Cẩm Nang Khuyến Nông & RAG (Tuần 3)
- **Mục tiêu**: Tích hợp ChromaDB để AI trả lời có cơ sở.
- **Công việc**:
  - Cài đặt **ChromaDB** cục bộ.
  - Chuẩn bị dữ liệu mẫu (các đoạn text về bệnh lúa, bệnh sầu riêng...).
  - Dùng mô hình mã nguồn mở (như `all-MiniLM-L6-v2` của SentenceTransformers - Hoàn toàn miễn phí) để tạo Vector Embedding.
  - Hoàn thiện `SearchHandbookUseCase` (Tìm Vector -> Trộn Context -> Gửi Gemini).
