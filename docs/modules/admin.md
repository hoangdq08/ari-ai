# 🛠 Admin Portal — Giao diện Quản trị

## Tổng quan

Admin Portal là giao diện quản trị dành cho người vận hành hệ thống, xây dựng trên **Vite + React 18** với Tailwind CSS.

- **Port:** 8082 (mặc định)
- **URL:** `http://localhost:8082`
- **API Base:** `VITE_API_BASE` → Backend ML-Agri endpoints

## 🛠 Công nghệ

| Công nghệ | Phiên bản | Mục đích |
|-----------|-----------|----------|
| Vite | ^5.3.1 | Build tool |
| React | ^18.3.1 | UI Library |
| Tailwind CSS | ^3.4.4 | Utility-first CSS |
| Lucide React | ^0.468.0 | Icons |
| PostCSS + Autoprefixer | Latest | CSS processing |

## 📂 Cấu trúc

```
admin/
├── src/
│   ├── App.jsx                  # Root component + theme
│   ├── main.jsx                 # Entry point
│   ├── index.css                # Tailwind + global styles
│   └── components/
│       ├── AdminPortal.jsx      # Layout + navigation + routing
│       ├── DataDashboard.jsx    # Dashboard dữ liệu tổng quan
│       ├── TrustDashboard.jsx   # AI Trust & Governance
│       ├── ResearchPage.jsx     # Research, crawl & ingest
│       ├── ReportsDashboard.jsx # Báo cáo RAG & data quality
│       ├── OpsConsole.jsx       # Ops console & activity log
│       └── BrandMark.jsx        # Branding/Navigation mark
├── index.html
├── package.json
├── vite.config.js
├── tailwind.config.js
└── postcss.config.js
```

## 🧭 Navigation & Routing

Admin Portal dùng **client-side routing** dựa trên URL path (không cần thư viện router):

| Section | Path | Component | Chức năng |
|---------|------|-----------|-----------|
| Data Dashboard | `/admin/data` | `DataDashboard` | Tổng quan dữ liệu, thống kê |
| Trust & Governance | `/admin/trust` | `TrustDashboard` | AI Trust score, risk register, governance |
| Research | `/admin/crawl` | `ResearchPage` | Crawl URLs, ingest documents |
| Reports | `/admin/reports` | `ReportsDashboard` | Báo cáo RAG, data quality |
| Ops Console | `/admin/ops` | `OpsConsole` | Activity log, system events |

## 📊 Các Trang Chi tiết

### 1. DataDashboard

Dashboard tổng quan dữ liệu:
- Số lượng documents, chunks, embeddings
- Thống kê nguồn (official, internet, blocked)
- Trạng thái hệ thống
- Quick actions: crawl, ingest, reset

### 2. TrustDashboard

**Trang quan trọng nhất cho AI Governance:**

#### Trust Score
- Điểm trust tổng hợp (0-100) từ backend `trust-report`
- Status: Sẵn sàng / Cần review / Rủi ro cao

#### Khung Lý thuyết AI (6 concepts)
Mỗi concept được trình bày dưới dạng Theory Card với 3 phần:
1. **Lý thuyết**: Khái niệm AI ethics cốt lõi
2. **Trong dự án**: Áp dụng cụ thể vào nông nghiệp
3. **Minh chứng/Kiểm soát**: Cơ chế kiểm soát hiện có

Các concept:
- **Bias**: Sai lệch hệ thống từ dữ liệu nguồn
- **Fairness**: Công bằng theo điều kiện vùng miền
- **Robustness**: Chống học nhầm tương quan giả
- **Explainability**: Giải thích giúp người dùng hành động
- **Data Leakage**: Ngăn chặn rò rỉ dữ liệu đánh giá
- **Feedback Loop**: Kiểm soát vòng lặp phản hồi

#### Risk Register
- Danh sách rủi ro với trạng thái (đã kiểm soát / cần xử lý)
- Evidence & mitigation plan cho mỗi rủi ro

#### Governance Controls
- Các chốt kiểm soát đang áp dụng
- Trạng thái: active / policy / review

#### Độ phủ Chủ đề & Vùng miền
- Coverage theo nhóm kiến thức nông nghiệp
- Region coverage map
- Domain concentration analysis

#### System Card
- Mục đích sử dụng (intended use)
- Giới hạn (not intended use)
- Cách giải thích cho người dùng (counterfactual explanation)

### 3. ResearchPage

Công cụ research & crawl:
- Search URLs/discovery
- Batch crawl
- Upload documents (PDF, DOCX)
- Review crawl candidates
- Source policy configuration

### 4. ReportsDashboard

Báo cáo chất lượng:
- RAG evaluation metrics
- Data quality scores
- Embedding coverage
- Chunk statistics

### 5. OpsConsole

Vận hành hệ thống:
- Activity events timeline
- Crawl events log
- Error tracking
- Runtime status

## 🎨 Theme System

Admin Portal hỗ trợ **Light/Dark mode**:
- Lưu preference vào `localStorage` (`nongtri_admin_theme`)
- Toggle button trong header
- CSS class `dark` trên `<html>` cho Tailwind dark mode

## 🏗 Development Commands

```bash
cd admin

# Install dependencies
npm ci

# Development server
npm run dev          # → localhost:8082

# Production build
npm run build

# Preview production build
npm run preview
```

## 🌐 Environment Variables

| Variable | Mô tả | Default |
|----------|-------|---------|
| `VITE_API_BASE` | Backend API URL | `http://localhost:8081/api/v1/ml-agri` |
| `VITE_USER_APP_URL` | Frontend app URL | `http://localhost:8080` |

---

← [Frontend](./frontend.md) | [AI Trust & Governance](../trust-ai-governance.md) | [Về Trang chủ Tài liệu](../README.md) →
