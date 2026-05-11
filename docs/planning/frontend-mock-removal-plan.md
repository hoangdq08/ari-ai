# Kế hoạch Thay thế Mock Data Frontend bằng Real API

Tài liệu này vạch ra các bước chi tiết để loại bỏ toàn bộ dữ liệu giả lập (Mock Data) còn sót lại trên Frontend và kết nối trực tiếp với Backend API thông qua `apiClient.ts`.

## Phạm vi thực hiện
1. **Module Diagnostics (Chẩn đoán hình ảnh)**
2. **Module Handbook (Cẩm nang nông nghiệp)**

*(Lưu ý: Module Chat đã được hoàn tất tích hợp ở giai đoạn trước).*

---

### Bước 1: Cập nhật Module Diagnostics (Chẩn đoán bệnh)
- **File ảnh hưởng**: 
  - `frontend/src/modules/diagnostics/infrastructure/api.ts`
  - `frontend/src/modules/diagnostics/application/useDiagnoseImage.ts`
- **Chi tiết công việc**:
  - Xóa hàm `mockDiagnoseImage`.
  - Viết hàm `diagnoseImage(file: File)`:
    - Tạo `FormData` và đính kèm `image`.
    - Gọi API POST `apiClient.post('/diagnostics/analyze', formData, { headers: { 'Content-Type': 'multipart/form-data' }})`.
  - **Mapping Dữ liệu**:
    - Backend trả về: `disease_name`, `confidence`, `treatment`, `preventive_measures`.
    - Frontend cần (`DiseaseResult`): `diseaseName`, `confidence`, `advice`, `citation`.
    - -> Gộp `treatment` và `preventive_measures` vào trường `advice`.
  - Cập nhật custom hook `useDiagnoseImage` để trỏ vào hàm `diagnoseImage` thật.

### Bước 2: Cập nhật Module Handbook (Tra cứu Cẩm nang)
- **File ảnh hưởng**: 
  - `frontend/src/modules/handbook/infrastructure/api.ts`
  - `frontend/src/modules/handbook/application/useArticles.ts`
- **Chi tiết công việc**:
  - Xóa/thay thế hàm `mockFetchArticles`.
  - Viết hàm `searchArticles(query: string)` gọi API GET `/handbook/search?q={query}`.
  - **Xử lý Edge Case**: 
    - API Backend yêu cầu `q` (min_length=2). Do đó, nếu User không nhập từ khóa (`search` rỗng) hoặc từ khóa quá ngắn, Frontend sẽ không gọi API mà sẽ trả về danh sách mặc định (giữ lại 1 phần nhỏ dữ liệu tĩnh hoặc gọi 1 API get-all trong tương lai).
  - **Mapping Dữ liệu**:
    - Backend trả về `SearchResultItem` (`title`, `content`, `similarity_score`).
    - Frontend cần `Article` (`id`, `title`, `description`, `category`).
    - -> Ánh xạ `content` sang `description`, `title` sang `title`, đặt `category` là `"Tìm kiếm"`.
  - Cập nhật `useArticles` để bắt điều kiện gọi API thật khi có từ khóa.

### Bước 3: Kiểm thử
- **Diagnostics**: Upload 1 bức ảnh từ giao diện Chat để kiểm tra xem request multipart/form-data có đi xuống cổng 8081 và nhận về kết quả Mock của Backend không.
- **Handbook**: Gõ từ khóa tìm kiếm (>= 2 ký tự) vào ô tìm kiếm Cẩm nang để kiểm tra chức năng lấy kết quả từ Vector DB Mock trên Backend.

---
*Tiến hành thực hiện Bước 1 và 2 song song.*
