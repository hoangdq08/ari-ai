# 🌿 Nông Trí AI — Trợ lý Nông nghiệp Thông minh

<p align="center">
  <strong>AI-powered agricultural assistant for Vietnamese farmers</strong><br>
  Chat · Diagnostics · Handbook · AI Trust & Governance<br>
  <sub>Đồ án môn AI002.F21.CN1.TTNT, Tư duy Trí tuệ nhân tạo · Giảng viên: TS. Phan Thế Duy · Trường ĐH Công nghệ Thông tin (UIT), ĐHQG-HCM</sub>
</p>

---

## 📖 Tài liệu

> Toàn bộ tài liệu dự án được tổ chức trong thư mục [`docs/`](./docs/README.md).

| Tài liệu | Mô tả |
|----------|-------|
| [🏗 Kiến trúc Hệ thống](./docs/architecture.md) | Clean Architecture + DDD, sơ đồ thành phần, dependency rule |
| [🔄 Luồng Dữ liệu](./docs/flow/overview.md) | Sơ đồ end-to-end từ người dùng đến AI Engine |
| [🔍 Pipeline RAG](./docs/flow/rag-pipeline.md) | Retrieval-Augmented Generation cho tri thức nông nghiệp |
| [⚙️ Backend](./docs/modules/backend.md) | FastAPI, module ML-Agri-Chat, API endpoints |
| [📱 Frontend](./docs/modules/frontend.md) | Next.js 15+, DDD, state management |
| [🛠 Admin Portal](./docs/modules/admin.md) | Giao diện quản trị, Trust Dashboard |
| [🛡 AI Trust & Governance](./docs/trust-ai-governance.md) | Khung lý thuyết 6 trục AI, Risk Register |
| [🚀 Triển khai](./docs/deployment.md) | Docker Compose, cấu hình, monitoring |
| [💻 Phát triển](./docs/development.md) | Local dev setup, testing, coding standards |

---

## 🎯 Tổng quan

**Nông Trí AI** là nền tảng ứng dụng Trí tuệ Nhân tạo giúp bà con nông dân chẩn đoán sâu bệnh, tra cứu cẩm nang canh tác và nhận tư vấn trực tiếp từ chuyên gia AI.

### Tính năng chính
- 💬 **Chat với AI**: Hỏi đáp kiến thức nông nghiệp bằng text
- 📸 **Chẩn đoán ảnh**: Chụp lá/bệnh cây trồng để AI phân tích
- 📚 **Cẩm nang**: Tra cứu tài liệu khuyến nông từ nguồn chính thống
- 🛡 **AI Trust Dashboard**: Giám sát 6 trục AI (Robustness, Reliability, Explainability, Fairness, Privacy, Social Impact)

---

## 🛠 Công nghệ

| Layer | Công nghệ |
|-------|-----------|
| **Frontend** | Next.js 15+ · React 19 · Tailwind CSS 4 · Zustand · React Query |
| **Backend** | FastAPI · Python 3.11 · Clean Architecture · DDD |
| **AI/ML** | Ollama `qwen2.5:3b` (LLM) · Keras (Vision) · ChromaDB (Vector DB) |
| **Infrastructure** | Docker Compose · Nginx |

---

## 🏗 Kiến trúc

Dự án được cấu trúc theo mô hình **Microservices** với **Domain-Driven Design (DDD)** và **Clean Architecture**:

```
┌──────────┐     ┌──────────┐     ┌──────────────┐     ┌────────────┐
│ Frontend │────▶│ Backend  │────▶│  ChromaDB    │     │   Admin    │
│ :8080    │     │ :8081    │     │  :8000       │◀────│   :8082    │
└──────────┘     └──────────┘     └──────────────┘     └────────────┘
   Next.js          FastAPI          Vector DB            Vite+React
```

> Xem chi tiết: [Kiến trúc Hệ thống](./docs/architecture.md)

---

## 🚀 Khởi chạy nhanh (Quick Start)

### Yêu cầu hệ thống
**[Docker Desktop](https://www.docker.com/products/docker-desktop/)** (hoặc Docker Engine)

### Khởi chạy bằng Docker (Khuyến nghị)

Chỉ với một lệnh duy nhất:

```bash
make docker
```

Hoặc thủ công:

```bash
cp .env.example .env
docker compose up -d --build
```

### Truy cập

| Dịch vụ | URL |
|---------|-----|
| 🌾 Ứng dụng Nông dân | [http://localhost:8080](http://localhost:8080) |
| 🛠 Admin Portal | [http://localhost:8082](http://localhost:8082) |
| 📘 API Docs (Swagger) | [http://localhost:8081/api/v1/docs](http://localhost:8081/api/v1/docs) |

> **Lưu ý:** Backend yêu cầu **Python 3.11**. Xem [Hướng dẫn Triển khai](./docs/deployment.md) để biết thêm chi tiết.

---

## 📂 Cấu trúc Thư mục

```text
ari_ai/
├── frontend/          # 📱 Ứng dụng Next.js cho nông dân
├── admin/             # 🛠 Giao diện quản trị (Vite + React)
├── backend/           # ⚙️ API Server (FastAPI)
│   └── app/ml_agri_chat/  # Module chính — ML-Agri-Chat Runtime
├── data/chromadb/     # 🗄️ ChromaDB persistent storage
├── docs/              # 📚 Tài liệu dự án (mới!)
├── plan/              # 🗓️ Kế hoạch chi tiết
├── docker-compose.yml # 🐳 Docker Compose config
├── Makefile           # 🚀 Các lệnh tiện ích tự động (start, docker, install)
└── TODO.md            # 📝 Lộ trình phát triển
```

---

## 🛡 AI Trust & Governance

Nông Trí AI được xây dựng với **6 trục AI** làm nền tảng kiến trúc:

| Trục | Mô tả | Module |
|------|-------|--------|
| 🧠 **Bias** | Chống thiên lệch nguồn dữ liệu | Source Policy, Gate Review |
| ⚖️ **Fairness** | Công bằng vùng miền, quy mô | Coverage Monitoring |
| 🛡 **Robustness** | Chống prompt injection, ảnh nhiễu | PromptGuard, CleanImg |
| 📖 **Explainability** | Trích dẫn nguồn, giải thích | System Card, Citation |
| 🔒 **Privacy** | Dữ liệu cục bộ, data minimization | Local-first architecture |
| 🤝 **Social Impact** | Miễn phí, mobile-first | Cost-optimized models |

> Xem chi tiết: [AI Trust & Governance](./docs/trust-ai-governance.md)

---

## 🤝 Đóng góp

Xem [Hướng dẫn Phát triển](./docs/development.md) để biết:
- Cách thiết lập môi trường local
- Coding standards (Python, TypeScript, JSX)
- Git workflow
- Testing guide

---

*Dự án Nông Trí AI — Đồng hành cùng nền nông nghiệp Việt Nam.* 🌾
