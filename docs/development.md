# 💻 Hướng dẫn Phát triển (Development)

## Tổng quan

Hướng dẫn này dành cho developer muốn thiết lập môi trường phát triển local cho Nông Trí AI.

## 📋 Yêu cầu

- **Python 3.11** (bắt buộc — không dùng 3.14)
- **Node.js 20+** + npm
- **Docker Desktop** (cho ChromaDB và chạy production)
- **Make** (tùy chọn, dùng Makefile)

## 🚀 Quick Start (Local)

### Cách 1: Dùng start.sh (khuyến nghị)

```bash
# Cài đặt dependencies và chạy tất cả services local
./start.sh

# Truy cập:
# Frontend: http://localhost:8080
# Admin:    http://localhost:8082
# API Docs: http://localhost:8081/api/v1/docs
```

Script tự động:
1. Tạo `.env` từ `.env.example` nếu chưa có
2. Tạo virtualenv Python 3.11
3. Cài đặt dependencies cho backend + frontend + admin
4. Khởi chạy cả 3 services song song

### Cách 2: Dùng Makefile

```bash
# Cài đặt tất cả dependencies
make install

# Chạy tất cả services (song song)
make start

# Hoặc chạy từng service riêng
make start-backend
make start-frontend
make start-admin
```

### Cách 3: Thủ công

```bash
# 1. Backend
cd backend
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --host 127.0.0.1 --port 8081

# 2. Frontend (terminal khác)
cd frontend
npm ci
npm run dev
# → http://localhost:8080

# 3. Admin (terminal khác)
cd admin
npm ci
npm run dev
# → http://localhost:8082
```

## 📂 Cấu trúc Code

### Backend (`backend/`)

```
backend/app/
├── main.py              # FastAPI app factory
├── core/config.py       # Settings (env vars)
├── ml_agri_chat/        # Module chính — ML-Agri-Chat
│   ├── router.py        # API endpoints
│   ├── _routes/         # Sub-routers theo domain
│   ├── modules/         # Business logic
│   └── data/            # Dữ liệu mẫu
├── shared/              # Utilities dùng chung
│   ├── latency.py       # Latency tracking
│   ├── rate_limit.py    # Rate limiting
│   ├── upload.py        # File upload
│   └── text_utils.py    # Text processing
└── tests/               # Test suite
```

### Frontend (`frontend/`)

```
frontend/src/
├── app/                 # Next.js App Router
├── core/                # DI, domain, infrastructure
├── modules/             # Domain modules
│   ├── chat/
│   ├── diagnostics/
│   ├── handbook/
│   └── home/
└── shared/              # Components, hooks, providers
```

### Admin (`admin/`)

```
admin/src/
├── App.jsx              # Root + theme
├── main.jsx             # Entry point
└── components/          # 6 page components
```

## 🧪 Testing

### Backend Tests

```bash
cd backend
source .venv/bin/activate
pip install pytest pytest-asyncio

# Chạy tất cả tests
pytest

# Chạy test cụ thể
pytest tests/test_prompt_guard.py -v
pytest tests/test_rag.py -v

# Với coverage
pytest --cov=app --cov-report=html
```

### Test Categories

| File | Mô tả |
|------|-------|
| `test_prompt_guard.py` | Kiểm tra bộ lọc bảo mật |
| `test_intent_classifier.py` | Phân loại intent |
| `test_internet_crawler.py` | Crawl dữ liệu web |
| `test_llm_client.py` | LLM client integration |
| `test_embedding_store.py` | ChromaDB operations |
| `test_kpi_reporting.py` | KPI & trust metrics |
| `test_latency.py` | Latency tracking |
| `test_security_and_privacy.py` | Security & privacy tests |
| `test_e2e_flows.py` | End-to-end flows |
| `test_e2e_full_coverage.py` | Full coverage E2E |

## 🎨 Coding Standards

### Python (Backend)
- **Python 3.11** — type hints bắt buộc
- **Format:** `ruff` hoặc `black` (line length 100)
- **Lint:** `ruff check .`
- **Import order:** stdlib → third-party → app
- **Docstrings:** Google style
- **Async:** Ưu tiên `async def` cho I/O operations

### TypeScript (Frontend)
- **Strict mode** bật
- **ESLint:** `eslint.config.mjs` với `eslint-config-next`
- **Import alias:** `@/` → `src/`
- **Components:** Functional components + hooks

### JavaScript/JSX (Admin)
- **Functional components**
- **Tailwind CSS** class ordering
- **Lucide React** cho icons
- **No external routing library** (URL-based navigation)

## 🔧 Development Tips

### Hot Reload
- **Backend:** Uvicorn với `--reload` (mặc định khi dùng `fastapi dev`)
- **Frontend:** Next.js Fast Refresh (mặc định)
- **Admin:** Vite HMR (mặc định)

### Debugging Backend

```bash
# Chạy với debug logs
uvicorn app.main:app --log-level debug

# Xem latency report
curl http://localhost:8081/api/v1/ml-agri/latency-report

# Gọi API trực tiếp
curl -X POST http://localhost:8081/api/v1/ml-agri/chat \
  -H "Content-Type: application/json" \
  -d '{"question": "cây cà phê bị vàng lá"}'
```

### Debugging Frontend
- React DevTools browser extension
- Network tab → kiểm tra API calls
- `console.log` state trong React Query devtools

## 📦 Dependency Management

### Backend
```bash
# Thêm package mới
cd backend
source .venv/bin/activate
pip install <package>
pip freeze > requirements.txt  # Cập nhật lock file
```

### Frontend / Admin
```bash
cd frontend  # hoặc admin
npm install <package>
# Peer dependencies auto-checked
```

## 🌿 Git Workflow

```bash
# Tạo branch mới
git checkout -b feature/ten-feature

# Commit message format
<type>(<scope>): <mô tả ngắn>

# Types: feat, fix, docs, refactor, test, chore
# Scopes: backend, frontend, admin, docs, docker

# Ví dụ:
git commit -m "feat(backend): thêm rate limiting cho chat endpoint"
git commit -m "fix(frontend): sửa lỗi CORS khi gọi API"
git commit -m "docs: cập nhật README với hướng dẫn mới"
```

---

← [Triển khai](./deployment.md) | [Về Trang chủ Tài liệu](./README.md) →
