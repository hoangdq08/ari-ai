# 📝 Nông Trí AI - To-Do List

Tài liệu này liệt kê các hạng mục công việc (TODO) còn lại sau khi dự án đã hoàn tất pha Khởi tạo Kiến trúc (Clean Architecture + DDD) và Cấu hình Môi trường (Docker). Các thành viên trong team sử dụng file này để bám sát mục tiêu, **đặc biệt tuân thủ chặt chẽ 5 Trục AI cốt lõi**.

## 👥 Phân công nhiệm vụ

- **Cả 3 thành viên**: Thảo luận giải pháp và kiến trúc hệ thống.
- **Toàn**: Làm tài liệu, kiểm thử, scraping (một phần), devops (một phần).
- **Thái**: Scraping và một phần frontend.
- **Hoàng**: Fullstack (backend + frontend).

---

## 📚 Giai đoạn 0: Tiền xử lý & Xây dựng Cơ sở Tri thức (Data Pipeline)
*Mục tiêu: Xây dựng "não bộ" tri thức nông nghiệp chuẩn xác cho AI học và truy xuất.*

- [x] **Thu thập & Làm sạch dữ liệu (Data Ingestion):**
  - [x] Thu thập các tài liệu chính thống (PDF/Word/Web) từ Sổ tay Khuyến nông (Bộ NN&PTNT).
  - [x] Viết script Python để trích xuất chữ từ PDF, loại bỏ nhiễu (header/footer thừa, ký tự lạ).
- [x] **Băm nhỏ & Nhúng dữ liệu (Chunking & Embedding):**
  - [x] Phân rã tài liệu thành các đoạn nhỏ (Text Splitter) đảm bảo không làm đứt gãy ngữ cảnh.
  - [x] Sử dụng mô hình Embedding (Text-to-Vector) để mã hóa các đoạn văn bản thành Vector toán học.
- [x] **Lưu trữ vào Vector Database:**
  - [x] Lưu toàn bộ Vector vào `ChromaDB` kèm theo **Metadata** (Tên sách, Số trang, Tác giả). Việc lưu Metadata này là bắt buộc để AI có thể trích dẫn nguồn (phục vụ Trục Explainability).

---

## 🧠 Giai đoạn 1: Lõi Trí tuệ Nhân tạo & 5 Trục AI (Backend)
*Mục tiêu: Hoàn thiện kiến trúc AI an toàn, minh bạch và đáng tin cậy.*

- [x] **🤖 Lõi Điều Phối (AI Orchestrator & Memory):**
  - [x] **AI Router (LangChain/LangGraph):** Xây dựng bộ não điều phối trung tâm. Tự động phân loại luồng yêu cầu: Nếu người dùng gửi ảnh -> Gọi luồng *Chẩn đoán (Vision)*; Nếu người dùng hỏi chữ/giọng nói -> Gọi luồng *Hỏi đáp (RAG)*.
  - [x] **Conversation Memory:** Thiết lập bộ nhớ lưu trữ ngữ cảnh hội thoại (Redis hoặc SQLite) để AI nhớ được câu hỏi trước đó của nông dân, tạo cảm giác giao tiếp tự nhiên.
  - [ ] **Tối ưu Conversation Memory:** Chuyển hoàn toàn việc lưu trữ lịch sử hội thoại xuống Backend DB (Redis/SQLite) thay vì truyền đi truyền lại qua request từ Frontend, giúp tiết kiệm băng thông 3G/4G cho nông dân.

- [x] **🛡️ Trục 1: Robustness (Bền bỉ / Chống lỗi)**
  - [x] **CleanImg:** Xây dựng module đánh giá ảnh đầu vào. Tự động từ chối ảnh mờ, rung tay, sai góc độ và yêu cầu nông dân chụp lại.
  - [x] **PromptGuard:** Phát triển màng lọc chặn Prompt Injection (Hỏi những câu không liên quan đến nông nghiệp).
  - [x] **Hỗ trợ Tiếng Việt không dấu:** Nâng cấp PromptGuard và Intent Classifier để xử lý tốt câu hỏi tiếng Việt không dấu (vd: "cay ca phe bi vang la"), tránh từ chối nhầm câu hỏi hợp lệ của bà con.

- [x] **📈 Trục 2: Reliability (Độ tin cậy / Chống ảo giác)**
  - [x] Liên kết hệ thống Chatbot với bộ dữ liệu đã được nạp ở **Giai đoạn 0**.
  - [x] Code luồng **RAG (Retrieval-Augmented Generation)** để LLM chỉ được phép trả lời dựa trên tài liệu khoa học, tuyệt đối không "bịa" kiến thức.

- [x] **🔍 Trục 3: Explainability (Tính Minh bạch)**
  - [x] Thiết kế **System Prompt** ép buộc `Gemini 1.5 Flash` phải luôn đính kèm **nguồn trích dẫn** và **lý luận chẩn đoán**. *(VD: Kết luận đạo ôn dựa trên đốm xám mắt én - Trích Sổ tay trang 15)*.

- [ ] **⚖️ Trục 4: Bias & Fairness (Tính Công bằng)**
  - [ ] Tích hợp `faster-whisper` xử lý **Voice-to-Text** đa vùng miền (Bắc - Trung - Nam).
  - [ ] Tích hợp API chuyển Text thành Giọng nói (Text-to-Speech) để máy tự đọc kết quả cho nông dân bị hạn chế khả năng đọc chữ.

- [ ] **🤝 Trục 5: Social Impact (Tác động xã hội)**
  - [ ] Chuyển đổi toàn bộ LLM sang phiên bản tối ưu chi phí (Gemini Flash + Local Whisper) để duy trì app ở mức **miễn phí 0đ**

---

## 📱 Giai đoạn 2: Kết nối Giao diện & Trải nghiệm (Frontend)
*Mục tiêu: Đảm bảo giao diện thân thiện tối đa với người nông dân.*

- [x] **Kết nối API Thực (Real Data):**
  - [x] Xóa bỏ Mock Data, nối các hooks React Query (`useChatStore`, `useDiagnoseImage`) với các endpoint FastAPI thực tế.
  - [x] Hoàn thiện cơ chế gửi FormData (gồm file Hình ảnh / Âm thanh) từ máy người dùng lên server.

- [ ] **Tối ưu hóa UI/UX cho Nông dân:**
  - [ ] Phóng to các nút bấm "Ghi âm" và "Chụp nấm bệnh", sử dụng màu sắc có độ tương phản cao để người lớn tuổi dễ thao tác ngoài nắng gắt ngoài đồng.
  - [ ] Thêm trạng thái "AI đang suy nghĩ..." (Typing indicator) trong màn hình Chatbox và hiệu ứng Skeleton Loading cho Cẩm nang.
  - [ ] **Streaming Trả lời (SSE):** Cập nhật API Chat để stream kết quả từng chữ về Frontend, giúp người dùng thấy chữ hiện ra ngay lập tức, tránh cảm giác ứng dụng bị treo.

---

## 🛡 Giai đoạn 3: Kiểm thử, Tối ưu & Triển khai (DevOps)
*Mục tiêu: Dự án sẵn sàng đưa lên môi trường Production.*

- [ ] **Kiểm thử (Testing):**
  - [ ] Viết Unit Test cho các business rules ở tầng `Application` và `Domain`.
  - [ ] Chạy bộ Test Dataset gồm 100 ảnh bệnh thực tế để đánh giá % độ chính xác của Gemini Vision.

- [ ] **📊 Giám sát Hệ thống AI (LLMOps):**
  - [ ] Tích hợp `LangSmith` (hoặc tương đương) để theo dõi chi phí (Token usage) và giám sát thời gian phản hồi (Latency) của mô hình.
  - [ ] Lưu log các câu hỏi bị `PromptGuard` từ chối để liên tục cải thiện bộ lọc bảo mật.

- [ ] **Bảo mật & Hiệu suất:**
  - [ ] Tối ưu hóa kích thước Docker Image (đặc biệt là Backend do chứa các thư viện AI nặng).
  - [ ] Thiết lập Rate Limit cho các API công khai để tránh bị spam làm cạn kiệt API Key.

- [ ] **CI/CD & Deployment:**
  - [ ] Cấu hình Github Actions tự động kiểm tra code (Lint/Format) khi có Pull Request.
  - [ ] Triển khai hệ thống lên server (VPS / Cloud) qua file `docker-compose.yml` (Docker-Only).
