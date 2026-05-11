# Kế hoạch Loại bỏ Hoàn toàn Mock Data trên Frontend

Tài liệu này xác định các bước để "nhổ tận gốc" mọi dữ liệu Mock còn sót lại trên Frontend (đặc biệt là mảng `MOCK_ARTICLES` trong module Handbook) và chuyển toàn bộ trách nhiệm lưu trữ/xử lý dữ liệu về phía Backend.

## Mục tiêu
Frontend không được chứa bất kỳ chuỗi cứng (hardcode) nào liên quan đến dữ liệu nghiệp vụ. Mọi truy vấn (kể cả khi không có từ khóa) đều phải gọi xuống Backend API.

---

### Bước 1: Cập nhật Schema Backend (Handbook)
- **File**: `backend/app/modules/handbook/presentation/schemas.py`
- **Công việc**:
  - Bổ sung trường `id` (str) và `category` (str) vào model `SearchResultItem` để đồng bộ với cấu trúc `Article` mà Frontend cần.
  - Sửa `similarity_score` thành `Optional[float]` (vì khi fetch danh sách mặc định sẽ không có điểm tương đồng).

### Bước 2: Cập nhật Router Backend (Handbook)
- **File**: `backend/app/modules/handbook/presentation/router.py`
- **Công việc**:
  - Đưa mảng `MOCK_ARTICLES` từ Frontend sang file này.
  - Sửa đổi Endpoint `GET /search`:
    - Biến tham số `q` thành Optional (mặc định là chuỗi rỗng `""`).
    - Bổ sung tham số `category` (mặc định là `"Tất cả"`).
  - Logic xử lý:
    - Nếu `q` rỗng: Trả về toàn bộ `MOCK_ARTICLES` (có thể lọc theo `category`).
    - Nếu `q` có dữ liệu: Lọc `MOCK_ARTICLES` theo từ khóa và trả về kết quả (sau này sẽ thay bằng lệnh query thật xuống ChromaDB).

### Bước 3: Dọn dẹp Frontend (Handbook)
- **File**: `frontend/src/modules/handbook/infrastructure/api.ts`
- **Công việc**:
  - Xóa bỏ mảng hằng số `MOCK_ARTICLES`.
  - Sửa hàm `fetchArticles`: Bỏ hẳn đoạn lệnh `if (!search ...)` đang return mảng cứng.
  - Chuyển thành gọi API trực tiếp với 2 tham số `q` (có thể rỗng) và `category`.
  - Nhận mảng kết quả từ `response.data.results`, map trực tiếp các trường `id`, `title`, `content` (-> `description`), và `category` thành object `Article`.

### Bước 4: Khởi động lại và Kiểm thử
- Restart Backend container (`docker compose restart backend`) để ăn code mới.
- Vào trang Cẩm nang (Frontend) kiểm tra việc load danh sách bài viết khi chưa nhập gì, và khi gõ tìm kiếm. Đảm bảo Network tab báo có API Call thực tế.
