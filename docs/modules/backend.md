# ⚙️ Backend — FastAPI Server

## Tổng quan

Backend là API server trung tâm của Nông Trí AI, xây dựng trên **FastAPI** (Python 3.11), cung cấp toàn bộ năng lực AI thông qua REST API.

- **Port:** 8081 (mặc định)
- **Swagger Docs:** `http://localhost:8081/api/v1/docs`
- **Health Check:** `GET /api/v1/ml-agri/health`

## 🧱 Kiến trúc Clean Architecture

```
┌──────────────────────────────────────┐
│          PRESENTATION                │
│  router.py, _routes/*.py             │
│  → FastAPI endpoints                 │
├──────────────────────────────────────┤
│          APPLICATION                 │
│  _helpers.py (business logic)        │
│  → Use cases, orchestration          │
├──────────────────────────────────────┤
│            DOMAIN                    │
│  Pydantic models, type definitions   │
│  → Entities, value objects           │
├──────────────────────────────────────┤
│        INFRASTRUCTURE                │
│  ChromaDB, Vision Model, Crawler     │
│  → External dependencies             │
└──────────────────────────────────────┘
```

## 📂 Cấu trúc Module ML-Agri-Chat

```
backend/app/ml_agri_chat/
├── router.py                    # API endpoints chính
├── _routes/
│   ├── _shared.py               # Shared state, singletons, models
│   ├── _helpers.py              # Business logic functions
│   └── __init__.py
├── modules/
│   ├── rag.py                   # RAG Engine
│   ├── llm_advisor.py           # LLM Advisor (Ollama wrapper)
│   ├── intent_classifier.py     # Intent classification
│   ├── prompt_guard.py          # Security filter
│   ├── clean_img.py             # Image quality validation
│   ├── vision_model.py          # CoffeeVisionClassifier (Keras)
│   ├── data_governance.py       # Trust report generation
│   ├── data_quality.py          # Data quality & evaluation
│   ├── data_ingestion.py        # Document ingestion
│   ├── document_chunking.py     # Text chunking
│   ├── internet_crawler.py      # Web crawler
│   ├── source_policy.py         # Source reliability policy
│   ├── taxonomy.py              # Agricultural taxonomy
│   ├── text_cleaning.py         # Text preprocessing
│   ├── accent_restoration.py    # Vietnamese accent restoration
│   ├── search_discovery.py      # Search & discovery
│   └── logger.py                # Request logging
├── data/                        # Dữ liệu mẫu & knowledge base
└── ml_pipeline/                 # Pipeline ML artifacts
```

## 🔌 API Endpoints

### Health & Status

| Method | Path | Mô tả |
|--------|------|-------|
| GET | `/api/v1/ml-agri/health` | Health check |
| GET | `/api/v1/ml-agri/runtime-status` | Trạng thái runtime chi tiết |
| GET | `/api/v1/ml-agri/latency-report` | Báo cáo latency |
| DELETE | `/api/v1/ml-agri/reset-data` | Reset toàn bộ dữ liệu (admin) |

### Chat

| Method | Path | Mô tả |
|--------|------|-------|
| POST | `/api/v1/ml-agri/chat` | Chat với AI |
| POST | `/api/v1/ml-agri/chat/feedback` | Gửi feedback cho câu trả lời |
| DELETE | `/api/v1/ml-agri/chat/history` | Xóa lịch sử chat |

### Data Ingest & Crawl

| Method | Path | Mô tả |
|--------|------|-------|
| POST | `/api/v1/ml-agri/ingest/upload` | Upload tài liệu |
| POST | `/api/v1/ml-agri/ingest/url` | Ingest từ URL |
| POST | `/api/v1/ml-agri/crawl/urls` | Crawl nhiều URLs |
| GET | `/api/v1/ml-agri/crawl/status` | Trạng thái crawl |
| GET | `/api/v1/ml-agri/crawl/events` | Sự kiện crawl gần đây |

### RAG & Data Quality

| Method | Path | Mô tả |
|--------|------|-------|
| POST | `/api/v1/ml-agri/rag/evaluate` | Đánh giá RAG |
| GET | `/api/v1/ml-agri/rag/quality-report` | Báo cáo chất lượng dữ liệu |
| GET | `/api/v1/ml-agri/rag/evaluation-cases` | Test cases đánh giá |

### Trust & Governance

| Method | Path | Mô tả |
|--------|------|-------|
| GET | `/api/v1/ml-agri/trust-report` | AI Trust Dashboard report |
| GET | `/api/v1/ml-agri/taxonomy` | Danh mục phân loại nông nghiệp |

### Admin/Ops

| Method | Path | Mô tả |
|--------|------|-------|
| GET | `/api/v1/ml-agri/ops/activity` | Activity log gần đây |
| POST | `/api/v1/ml-agri/research/search` | Research search |
| POST | `/api/v1/ml-agri/research/batch-search` | Batch search URLs |

## 🛡 Module Chi tiết

### PromptGuard (`prompt_guard.py`)

- Lọc prompt injection / jailbreak attacks
- Từ chối câu hỏi không liên quan đến nông nghiệp
- Hỗ trợ tiếng Việt không dấu
- Disclaimer: "Đây là tư vấn ban đầu, không thay thế chuyên gia"

### RAG Engine (`rag.py`)

- `AgriculturalRAG`: class chính cho retrieval
- Embedding: hashing-based (kế hoạch: sentence-transformers)
- ChromaDB collection: `agriculture_kb`
- Top-K retrieval + re-ranking

### LLM Advisor (`llm_advisor.py`)

- `ControlledAdvisor`: wrapper quanh Ollama
- Default model: `qwen2.5:3b`
- Temperature: cấu hình qua biến `NONGTRI_LLM_TEMPERATURE` (mặc định 0.1 - low creativity)
- System prompt ép buộc trích dẫn nguồn
- Fallback: trả về disclaimer nếu không có context

### Vision Model (`vision_model.py`)

- `CoffeeVisionClassifier`: phân loại bệnh cây cà phê
- Framework: Keras/TensorFlow
- Input: ảnh lá cây
- Output: tên bệnh + confidence score

### Source Policy (`source_policy.py`)

- Whitelist các domain chính thống
- Chấm điểm reliability theo nguồn
- Cảnh báo nguồn thương mại, mạng xã hội
- Gate review cho nguồn không rõ ràng

### Data Governance (`data_governance.py`)

- Sinh `trust-report` cho Trust Dashboard
- Tính toán trust_score, source distribution
- Risk register: bias, fairness, robustness, leakage...
- Governance controls status

## 🔧 Shared Utilities

| File | Chức năng |
|------|-----------|
| `shared/latency.py` | `LatencyMiddleware` đo thời gian xử lý, `StageTimer` đo từng stage |
| `shared/rate_limit.py` | Rate limiting với SlowAPI, configurable limits |
| `shared/text_utils.py` | Xử lý tiếng Việt, accent detection |
| `shared/upload.py` | File upload với size limit, format validation |

## 📊 Middleware

```
Request → LatencyMiddleware → SlowAPI (RateLimit) → CORS → Router
```

- **LatencyMiddleware**: Đo `X-Process-Time` cho mọi request
- **SlowAPI**: Rate limit mặc định: chat 30/min, image 10/min, admin 60/min
- **CORS**: Allow origins từ `BACKEND_CORS_ORIGINS` config

## 📦 Dependencies Chính

```
fastapi==0.109.2          # Web framework
uvicorn[standard]==0.27.1  # ASGI server
pydantic==2.6.1            # Data validation
chromadb==0.4.24           # Vector database
httpx==0.27.2              # HTTP client
beautifulsoup4==4.12.3     # HTML parsing
pypdf==4.2.0               # PDF processing
pillow==10.4.0             # Image processing
opencv-python-headless     # Image analysis
slowapi==0.1.9             # Rate limiting
```

> Python **3.11** là bắt buộc. Không dùng Python 3.14 do vấn đề tương thích package native.

---

← [Về Trang chủ Tài liệu](./README.md) | [Tiếp: Frontend](./frontend.md) →
