# 📚 Tài liệu Dự án Nông Trí AI

Chào mừng đến với trung tâm tài liệu của **Nông Trí AI** (ArgiAI) — Trợ lý Nông nghiệp Thông minh cho nông dân Việt Nam.

## 📖 Mục lục

### 🏗 Kiến trúc & Thiết kế
| Tài liệu | Mô tả |
|----------|-------|
| [Kiến trúc Hệ thống](./architecture.md) | Tổng quan kiến trúc Clean Architecture + DDD, sơ đồ thành phần và dependency rule |
| [Luồng Dữ liệu](./flow/overview.md) | Sơ đồ luồng dữ liệu end-to-end từ người dùng đến AI Engine |
| [Pipeline RAG](./flow/rag-pipeline.md) | Chi tiết pipeline Retrieval-Augmented Generation cho truy xuất tri thức nông nghiệp |

### 🧩 Module Chi tiết
| Tài liệu | Mô tả |
|----------|-------|
| [Backend](./modules/backend.md) | Kiến trúc FastAPI, cấu trúc thư mục, các module ML-Agri-Chat |
| [Frontend](./modules/frontend.md) | Ứng dụng Next.js cho nông dân, cấu trúc DDD, state management |
| [Admin Portal](./modules/admin.md) | Giao diện quản trị dữ liệu, crawl, ops và báo cáo |

### 🛡 AI Trust & Governance
| Tài liệu | Mô tả |
|----------|-------|
| [AI Trust & Governance](./trust-ai-governance.md) | Khung lý thuyết 6 trục AI, Risk Register, Governance Controls |

### 🚀 Vận hành
| Tài liệu | Mô tả |
|----------|-------|
| [Hướng dẫn Triển khai](./deployment.md) | Docker Compose, cấu hình môi trường, CI/CD |
| [Hướng dẫn Phát triển](./development.md) | Local development setup, coding standards, testing |

### 📋 Kế hoạch
| Tài liệu | Mô tả |
|----------|-------|
| [Kế hoạch Triển khai](./planning/KeHoachTrienKhai_NongTri.html) | Kế hoạch triển khai chi tiết (HTML) |
| [Kế hoạch Refactor Backend](./planning/backend-clean-arch-refactor.md) | Lộ trình tái cấu trúc Clean Architecture |

---

## 🎯 Tổng quan Dự án

**Nông Trí AI** là nền tảng ứng dụng Trí tuệ Nhân tạo phục vụ nông dân Việt Nam:
- 📱 **Chat & Hỏi đáp**: Giao tiếp bằng text/giọng nói với AI chuyên gia nông nghiệp
- 📸 **Chẩn đoán ảnh**: Chụp lá/bệnh cây trồng để AI phân tích
- 📚 **Cẩm nang**: Tra cứu kiến thức nông nghiệp từ nguồn chính thống
- 🛡 **Trust & Governance**: Hệ thống giám sát 6 trục AI (Robustness, Reliability, Explainability, Fairness, Privacy, Social Impact)

### 🛠 Công nghệ chính
- **Frontend:** Next.js 15+ · React 19 · Tailwind CSS 4 · Zustand · React Query
- **Backend:** FastAPI · Python 3.11 · Clean Architecture · DDD
- **AI/ML:** Ollama (LLM nội bộ) · ChromaDB (Vector DB) · RAG Pipeline
- **Infrastructure:** Docker Compose · Nginx · GitHub Actions

### 🏗 Nguyên tắc Kiến trúc
- **Domain-Driven Design (DDD)**: Phân tách nghiệp vụ thành các domain độc lập
- **Clean Architecture**: Dependency Inversion, tách biệt Presentation - Application - Domain - Infrastructure
- **Microservices**: 3 service độc lập (Frontend, Admin, Backend) + 1 database service (ChromaDB)
- **AI Safety by Design**: 6 trục AI được tích hợp từ đầu vào kiến trúc hệ thống

---

*Dự án Nông Trí AI — Đồng hành cùng nền nông nghiệp Việt Nam.* 🌾
