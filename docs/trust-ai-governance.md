# 🛡 AI Trust & Governance

> Tài liệu này giải thích khung lý thuyết 6 trục AI được áp dụng trong Nông Trí AI, cách mỗi khái niệm được nối với rủi ro thật trong dữ liệu nông nghiệp và cơ chế kiểm soát đang có trong hệ thống.

## 🎯 Tổng quan

Nông Trí AI tích hợp AI Trust & Governance như một **lớp kiến trúc cốt lõi**, không phải là add-on. Mọi quyết định thiết kế — từ kiến trúc RAG, policy chọn nguồn, cách hiển thị kết quả — đều được dẫn dắt bởi 6 trục AI dưới đây.

Hệ thống Trust Dashboard (tại `/admin/trust`) cung cấp giao diện giám sát real-time cho toàn bộ khung lý thuyết này.

---

## 📊 Trust Score

Trust Score là chỉ số tổng hợp (0-100) phản ánh mức độ đáng tin cậy của toàn bộ pipeline AI. Điểm số được tính từ backend `/api/v1/ml-agri/trust-report` dựa trên:

- Tỷ lệ nguồn chính thống (≥ 60%)
- Tỷ lệ nguồn thương mại/internet (< 25%)
- Độ phủ chủ đề nông nghiệp (≥ 85%)
- Số lượng rủi ro đang mở
- Trạng thái governance controls

| Mức | Score | Hành động |
|-----|-------|-----------|
| 🟢 Sẵn sàng | 80-100 | Hệ thống đáng tin cậy, có thể dùng cho tư vấn |
| 🟡 Cần review | 50-79 | Cần kiểm tra thêm trước khi dùng |
| 🔴 Rủi ro cao | 0-49 | Không nên dùng cho tư vấn, cần xử lý ngay |

---

## 🧠 Khung Lý thuyết 6 Trục AI

### 1. 🧠 Bias — Không phải lỗi ngẫu nhiên

> "AI học từ dữ liệu lịch sử, nên sai lệch trong nguồn dữ liệu sẽ được mã hóa thành sai lệch có hệ thống trong khuyến nghị."

**Trong dự án:**
Bias xuất hiện khi nguồn internet/thương mại chiếm tỷ lệ cao hơn nguồn chính thống. Nếu AI học chủ yếu từ blog thương mại, nó sẽ thiên vị khuyến nghị sản phẩm cụ thể thay vì giải pháp khoa học.

**Cơ chế kiểm soát:**
- `source_policy.py`: whitelist domain chính thống, cảnh báo nguồn thương mại
- Trust Report đo tỷ lệ nguồn (`reviewed_source_share` vs `internet_source_share`)
- Gate review: nguồn không rõ ràng bị giữ lại để admin xét duyệt
- `needs_review_source_count`: số nguồn đang bị giữ review

### 2. ⚖️ Fairness — Công bằng theo điều kiện

> "Không có một định nghĩa fairness tối ưu cho mọi nhóm; hệ thống phải chọn mục tiêu công bằng phù hợp bối cảnh."

**Trong dự án:**
Với nông nghiệp, fairness là không áp một khuyến nghị chung cho mọi vùng, quy mô nông hộ, mùa vụ và điều kiện đất nước khác nhau. Một khuyến nghị đúng cho Tây Nguyên có thể sai cho Đồng bằng Sông Cửu Long.

**Cơ chế kiểm soát:**
- Dashboard đo coverage theo vùng (`region_coverage`) và chủ đề (`topic_coverage`)
- `taxonomy.py`: phân loại câu hỏi theo vùng miền, loại cây trồng
- Accent restoration (`accent_restoration.py`): hỗ trợ tiếng Việt không dấu
- UI mobile-first với nút lớn, icon trực quan — giảm rào cản công nghệ

### 3. 🛡 Robustness — Chống học nhầm tương quan

> "Mô hình dễ học các tín hiệu giả như nguồn thương mại, text nhiễu, ảnh mờ... thay vì bản chất nông học."

**Trong dự án:**
Chat/RAG phải hạ độ tin cậy khi:
- Thiếu thông tin vùng trồng, tuổi cây, mùa vụ
- Thiếu triệu chứng cụ thể
- Nguồn có nhiều cảnh báo chất lượng
- Ảnh đầu vào bị mờ, rung, sai góc

**Cơ chế kiểm soát:**
- `prompt_guard.py`: từ chối prompt injection, câu hỏi không liên quan
- `clean_img.py`: kiểm tra chất lượng ảnh (mờ, rung, nhiễu)
- `intent_classifier.py`: phân loại đúng intent, tránh xử lý nhầm
- Risk register: `high_risk_warning_total` theo dõi cảnh báo rủi ro

### 4. 📖 Explainability — Giúp người dùng hành động

> "Giải thích tốt không chỉ nói mô hình dự đoán gì, mà nói vì sao, dựa vào nguồn nào, và cần thay đổi thông tin gì để kết quả tốt hơn."

**Trong dự án:**
Mỗi câu trả lời phải:
- Nêu nguồn trích dẫn (tên tài liệu, URL, độ tin cậy)
- Giải thích lý do chẩn đoán
- Nêu giả định về vùng/mùa vụ
- Chỉ ra thông tin còn thiếu → gợi ý người dùng cung cấp thêm

**Cơ chế kiểm soát:**
- System Card (`model_card`) định nghĩa intended use, limitations
- User explanation pattern: "Nếu bổ sung X, kết quả có thể chính xác hơn"
- Counterfactual: nếu vùng trồng, tuổi cây, triệu chứng rõ hơn → kết quả cụ thể hơn
- RAG response format bắt buộc kèm `sources[]`

### 5. 🔀 Data Leakage — Điểm đánh giá ảo

> "Nếu dữ liệu tương lai, cùng URL, cùng chunk lọt vào cả train và test, mô hình trông có vẻ giỏi nhưng thất bại ngoài thực tế."

**Trong dự án:**
- Dữ liệu RAG cần dedupe theo nội dung — không dùng content_hash trùng
- Khi đánh giá: split theo nguồn/thời gian thay vì split ngẫu nhiên theo chunk
- Train/eval/test phải từ các nguồn KHÁC NHAU

**Cơ chế kiểm soát:**
- Backend chặn nạp trùng bằng `content_hash`
- Risk register có control chống leakage
- Đánh giá RAG với test cases từ nguồn riêng biệt

### 6. 🔄 Feedback Loop — Khuếch đại bias

> "Khi dự đoán của hệ thống tạo ra dữ liệu huấn luyện tương lai, hệ thống có thể tự củng cố lựa chọn sai."

**Trong dự án:**
Click/feedback của người dùng KHÔNG được đi thẳng vào training data. Phải qua review trước khi thành nhãn huấn luyện.

**Cơ chế kiểm soát:**
- `/api/v1/ml-agri/chat/feedback` lưu feedback riêng, không tự động huấn luyện
- Policy review trước khi dùng feedback cho training
- Risk register đánh dấu feedback loop đang được kiểm soát

---

## 📋 Risk Register

Hệ thống duy trì risk register với các rủi ro chính:

| Rủi ro | Trục AI | Trạng thái |
|--------|---------|------------|
| Thiên lệch nguồn thương mại | Bias | Giám sát liên tục |
| Under-representation vùng miền | Fairness | Đo coverage định kỳ |
| Prompt injection | Robustness | PromptGuard active |
| Model hallucination | Reliability | RAG + source citation |
| Data leakage train/test | Leakage | Content hash dedupe |
| Feedback loop amplification | Feedback | Policy review gate |

---

## 🏛 Governance Controls

Các cơ chế kiểm soát đang áp dụng:

1. **Source Policy Whitelist**: Chỉ nguồn chính thống được ưu tiên
2. **Content Hash Dedup**: Ngăn trùng lặp dữ liệu
3. **Gate Review**: Nguồn không rõ ràng → admin xét duyệt
4. **Prompt Filter**: Từ chối nội dung không liên quan
5. **Image Quality Gate**: Từ chối ảnh kém chất lượng
6. **Citation Requirement**: Mọi câu trả lời phải kèm nguồn
7. **Feedback Isolation**: Feedback không tự động vào training
8. **Coverage Monitoring**: Theo dõi độ phủ vùng miền, chủ đề

---

## 🔒 Privacy by Design

Nông Trí AI áp dụng nguyên tắc **Privacy by Design**:

- **Data Minimization**: Chỉ thu thập dữ liệu tối thiểu cần thiết
- **Local-First**: Toàn bộ pipeline chạy cục bộ (Ollama, ChromaDB, Keras)
- **No Third-Party**: Dữ liệu hội thoại & ảnh không gửi ra dịch vụ bên ngoài
- **PII Anonymization**: Ẩn danh thông tin cá nhân trước khi log
- **User Data Rights**: Người dùng có quyền xóa lịch sử bất cứ lúc nào

---

## 📈 Social Impact

Dự án ưu tiên **hỗ trợ sinh kế cho nông dân nhỏ lẻ**:

- **Miễn phí 0đ**: Chiến lược chọn model tối ưu chi phí (Ollama local, Gemini Flash)
- **Mobile-First**: Tối ưu cho điện thoại giá rẻ, kết nối 3G/4G
- **Voice-First Roadmap**: Hỗ trợ giọng nói → xóa bỏ rào cản chữ viết
- **Vùng sâu vùng xa**: Kênh tư vấn ban đầu khi chưa tiếp cận được chuyên gia

---

← [Admin Portal](./modules/admin.md) | [Triển khai](./deployment.md) | [Về Trang chủ Tài liệu](./README.md) →
