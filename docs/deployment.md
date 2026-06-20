# 🚀 Hướng dẫn Triển khai (Deployment)

## Tổng quan

Nông Trí AI được thiết kế để triển khai qua **Docker Compose**, đảm bảo hoạt động ổn định trên mọi hệ điều hành (Windows, macOS, Linux) mà không cần cài đặt thủ công các dependency phức tạp.

## 📋 Yêu cầu Hệ thống

### Tối thiểu
- **Docker Engine** 24+ hoặc **Docker Desktop**
- **RAM:** 8GB (khuyến nghị 16GB cho Ollama)
- **Disk:** 10GB trống
- **Python 3.11** (chỉ khi chạy local development)

### Khuyến nghị cho Production
- **RAM:** 16GB+ (cho Ollama LLM + ChromaDB)
- **CPU:** 4 cores+
- **Disk:** 20GB+ SSD
- **GPU:** Optional (tăng tốc Ollama inference)

## 🐳 Triển khai với Docker

### Khởi chạy nhanh (1 lệnh)

```bash
# Từ thư mục gốc dự án
make docker
```

Hoặc thủ công:

```bash
# 1. Tạo file .env từ mẫu
cp .env.example .env

# 2. (Tùy chọn) Chỉnh sửa .env — thêm API keys nếu cần
nano .env

# 3. Build và khởi chạy toàn bộ hệ thống
docker compose up -d --build
```

### Kiểm tra trạng thái

```bash
# Kiểm tra tất cả services
docker compose ps

# Xem logs
docker compose logs -f backend
docker compose logs -f frontend
docker compose logs -f admin
```

### Dừng hệ thống

```bash
# Dừng và giữ dữ liệu
docker compose down

# Dừng và xóa toàn bộ dữ liệu
docker compose down -v
```

## 🌐 Truy cập Hệ thống

Sau khi Docker khởi động thành công:

| Dịch vụ | URL | Mô tả |
|---------|-----|-------|
| Frontend | `http://localhost:8080` | Ứng dụng cho nông dân |
| Admin | `http://localhost:8082` | Giao diện quản trị |
| API Docs | `http://localhost:8081/api/v1/docs` | Swagger UI |
| API Base | `http://localhost:8081/api/v1/ml-agri` | API endpoints |

## 📦 Kiến trúc Docker

```yaml
services:
  frontend:        # Next.js production build → port 8080
  admin:           # Vite static build + Nginx → port 8082
  backend:         # FastAPI + Uvicorn → port 8081 (internal :8000)
  chromadb:        # ChromaDB official image → internal :8000
```

### Network
Tất cả services giao tiếp qua Docker bridge network `argiai_net`.

### Volumes
- `./data/chromadb` → `/chroma/chroma` (ChromaDB persistent storage)

## ⚙️ Cấu hình Môi trường (.env)

File `.env` được tạo từ `.env.example`:

```bash
# API Keys (tùy chọn — hệ thống chạy local-first)
GEMINI_API_KEY=           # Gemini API key (nếu dùng fallback cloud)
NEXT_PUBLIC_API_URL=      # http://localhost:8081
FRONTEND_PORT=8080
ADMIN_PORT=8082
BACKEND_PORT=8081

# Docker build-time
ADMIN_API_URL=http://localhost:8081/api/v1/ml-agri
FRONTEND_URL=http://localhost:8080
```

## 🔒 Bảo mật Production

### Trước khi deploy production:
1. **Đổi CORS Origins**: Cập nhật `BACKEND_CORS_ORIGINS` trong `config.py` thành domain thật
2. **Admin Token**: Bảo vệ endpoint admin với `X-Admin-Token` header
3. **Rate Limiting**: Điều chỉnh rate limit trong `rate_limit.py`
4. **HTTPS**: Sử dụng reverse proxy (Nginx/Caddy) với SSL
5. **Firewall**: Chỉ mở ports 80/443, không expose trực tiếp backend

### Security Checklist
- [ ] File `.env` đã được cấu hình đúng
- [ ] CORS origins giới hạn domain production
- [ ] Rate limiting phù hợp với traffic dự kiến
- [ ] Admin token đã được đổi khỏi mặc định
- [ ] HTTPS đã được bật
- [ ] Docker images được build từ source tin cậy

## 📊 Monitoring

### Health Check
```bash
# Kiểm tra backend
curl http://localhost:8081/api/v1/ml-agri/health
# → {"status": "ok", "message": "Nông Trí AI Backend is running!"}

# Kiểm tra runtime status
curl http://localhost:8081/api/v1/ml-agri/runtime-status

# Latency report
curl http://localhost:8081/api/v1/ml-agri/latency-report
```

### Docker Resource Usage
```bash
docker stats argiai_backend argiai_frontend argiai_admin argiai_chromadb
```

## 🔄 CI/CD (Kế hoạch)

```yaml
# .github/workflows/deploy.yml (kế hoạch)
- Lint & Format check
- Unit tests (pytest)
- Build Docker images
- Push to container registry
- Deploy to VPS/Cloud
```

## 🆘 Troubleshooting

| Vấn đề | Giải pháp |
|--------|-----------|
| Backend không start | Kiểm tra Python 3.11, `docker compose logs backend` |
| ChromaDB connection refused | Đảm bảo `depends_on: chromadb` trong compose |
| Frontend fetch error | Kiểm tra `NEXT_PUBLIC_API_URL` và CORS |
| Admin không load được data | Kiểm tra `VITE_API_BASE` đúng backend URL |
| Container exit ngay | Kiểm tra logs: `docker compose logs` |

---

← [AI Trust & Governance](./trust-ai-governance.md) | [Phát triển](./development.md) | [Về Trang chủ Tài liệu](./README.md) →
