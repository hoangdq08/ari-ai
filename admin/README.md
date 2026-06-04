# Nông Trí Admin

Admin là ứng dụng Vite + React riêng, dùng để vận hành dữ liệu và RAG cho Nông Trí AI.

## Chức năng

- **Dữ liệu**: tổng quan nguồn, chunk, chỉ mục vector fallback và độ phủ nội dung.
- **Thu thập**: research search, crawl URL/PDF/TXT, extract text và nạp vào RAG.
- **Nhật ký**: theo dõi luồng chat, crawl, chunking, feedback và image diagnose.
- **Báo cáo**: xem báo cáo chất lượng dữ liệu/RAG.

## API

Mặc định admin gọi:

```text
http://127.0.0.1:8081/api/v1/ml-agri
```

Có thể đổi bằng biến môi trường:

```bash
VITE_API_BASE=http://localhost:8081/api/v1/ml-agri
VITE_USER_APP_URL=http://localhost:8080
```

## Chạy local

```bash
cd admin
npm ci
npm run dev
```

Mặc định chạy ở `http://localhost:8082`.
