# ML-Agri-Chat Integrated Runtime

Thư mục này chứa phần backend được tích hợp từ `ML-Agri-Chat` để phục vụ admin và các tác vụ dữ liệu/RAG.

## Nhóm API

Khi dependency đầy đủ, router được mount dưới:

```text
/api/v1/ml-agri
```

Các nhóm endpoint chính:

- `GET /health`: trạng thái runtime và LLM.
- `POST /chat`: chat RAG cà phê có nguồn tham khảo.
- `POST /ingest-document`, `POST /ingest-url`, `POST /crawl-urls`: nạp dữ liệu vào RAG.
- `POST /research-search`, `POST /research-batch`: tìm nguồn crawl.
- `GET /sources`, `GET /data-quality`, `GET /crawl-dashboard`: dashboard dữ liệu.
- `GET /admin/ops-events`: nhật ký vận hành cho admin.
- `POST /rag-evaluate`, `POST /rag-rebuild-index`: kiểm thử và rebuild index.
- `POST /diagnose-image`: chẩn đoán ảnh placeholder/model nếu có artifact.

## Ghi chú tích hợp

- Code gốc được đặt trong namespace riêng để không phá các module DDD hiện tại.
- Nếu môi trường local thiếu dependency ML-Agri, `app.main` vẫn boot và trả fallback health cho `/api/v1/ml-agri/health`.
- Docker backend dùng Python 3.11, phù hợp hơn với các dependency native như `pydantic-core`, `pillow`, `opencv`.
