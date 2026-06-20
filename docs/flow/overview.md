# 🔄 Luồng Dữ liệu Hệ thống

## Sơ đồ Luồng End-to-End

```mermaid
graph TD
    subgraph Client["GIAO DIỆN ĐẦU VÀO"]
        UI["Web / App Mobile"]
        Voice["Ghi âm Giọng nói"]
        Cam["Chụp Mẫu bệnh"]
    end

    subgraph Robustness["LỚP KIỂM DUYỆT"]
        STT["Phân tích Giọng nói (Speech-to-Text)"]
        CleanImg["Kiểm tra Chất lượng Ảnh (Bộ lọc nhiễu)"]
        PromptGuard["Kiểm duyệt Nội dung (Chống Hack/Jailbreak)"]
        Reject("Báo lỗi / Từ chối")
    end

    subgraph Core["LÕI XỬ LÝ AI"]
        Orchestrator{"ĐIỀU PHỐI AI Router"}
        RAG["RAG Engine (Truy tìm ngữ cảnh)"]
        LLM["Logic Chẩn đoán (Vision and LLM)"]
    end

    subgraph DB["CƠ SỞ TRI THỨC"]
        Docs["Tài liệu Nông nghiệp (Khuyến nông VN)"]
        VectorDB[("Vector Database (ChromaDB)")]
    end

    subgraph Output["KẾT QUẢ ĐẦU RA"]
        UI_Out["Màn hình Hiển thị (Nông dân)"]
    end

    UI -->|"Nhập Text"| PromptGuard
    Voice -->|"File Audio"| STT
    Cam -->|"File Ảnh"| CleanImg

    STT -->|"Text"| PromptGuard
    CleanImg -->|"Ảnh đã lọc"| PromptGuard

    PromptGuard -->|"Hợp lệ"| Orchestrator
    PromptGuard -.->|"Vi phạm"| Reject

    Docs -.->|"Nhúng Embedding"| VectorDB
    Orchestrator -->|"Câu hỏi"| RAG

    RAG -->|"Truy vấn"| VectorDB
    VectorDB -.->|"Trả ngữ cảnh"| RAG

    RAG -->|"Gửi ngữ cảnh"| LLM
    Orchestrator -->|"Gửi ảnh mẫu bệnh"| LLM

    LLM ===>|"Kết quả và nguồn"| UI_Out
    Reject -.->|"Hiển thị lỗi"| UI_Out

    style UI fill:#eff6ff,stroke:#3b82f6
    style Voice fill:#eff6ff,stroke:#3b82f6
    style Cam fill:#eff6ff,stroke:#3b82f6
    style UI_Out fill:#eff6ff,stroke:#3b82f6
    style STT fill:#fef2f2,stroke:#ef4444
    style CleanImg fill:#fef2f2,stroke:#ef4444
    style PromptGuard fill:#fef2f2,stroke:#ef4444
    style Reject fill:#fef2f2,stroke:#ef4444
    style Orchestrator fill:#fff7ed,stroke:#f97316
    style RAG fill:#f0fdf4,stroke:#22c55e
    style LLM fill:#f0fdf4,stroke:#22c55e
    style Docs fill:#f5f3ff,stroke:#8b5cf6
    style VectorDB fill:#f5f3ff,stroke:#8b5cf6
```

## 🎯 Các Luồng Xử lý Chính

### Luồng 1: Hỏi đáp Văn bản (Chat)

```mermaid
graph TD
    Input["Người dùng nhập text"] --> PG["PromptGuard (Kiểm duyệt nội dung)"]
    PG --> IC["Intent Classifier (Phân loại câu hỏi)"]
    IC -->|"Nếu là câu hỏi nông nghiệp"| RAG["RAG Engine (Truy xuất ngữ cảnh từ Vector DB)"]
    RAG --> LLM["LLM Advisor (Sinh câu trả lời + trích dẫn nguồn)"]
    LLM --> Output["Hiển thị kết quả"]
    IC -->|"Nếu không phải"| Reject["Từ chối, gợi ý chủ đề nông nghiệp"]
    
    style Input fill:#eff6ff,stroke:#3b82f6
    style Output fill:#eff6ff,stroke:#3b82f6
    style PG fill:#fef2f2,stroke:#ef4444
    style IC fill:#fef2f2,stroke:#ef4444
    style Reject fill:#fef2f2,stroke:#ef4444
    style RAG fill:#f0fdf4,stroke:#22c55e
    style LLM fill:#fff7ed,stroke:#f97316
```

### Luồng 2: Chẩn đoán Ảnh (Diagnostics)

```mermaid
graph TD
    Input["Người dùng chụp/gửi ảnh"] --> CleanImg["CleanImg (Kiểm tra chất lượng: mờ, rung, sai góc)"]
    CleanImg -->|"Nếu ảnh không đạt"| Reject["Yêu cầu chụp lại"]
    CleanImg -->|"Nếu ảnh đạt"| Vision["Vision Model (CoffeeVisionClassifier - Keras)"]
    Vision -->|"Phân loại bệnh + độ tin cậy"| LLM["LLM Advisor (Giải thích kết quả + khuyến nghị)"]
    LLM --> Output["Hiển thị chẩn đoán + nguồn tham khảo"]

    style Input fill:#eff6ff,stroke:#3b82f6
    style Output fill:#eff6ff,stroke:#3b82f6
    style Reject fill:#fef2f2,stroke:#ef4444
    style CleanImg fill:#fef2f2,stroke:#ef4444
    style Vision fill:#f0fdf4,stroke:#22c55e
    style LLM fill:#fff7ed,stroke:#f97316
```

### Luồng 3: Giọng nói (Voice - kế hoạch)

```mermaid
graph TD
    Input["Người dùng ghi âm"] --> STT["Faster-Whisper (Speech-to-Text offline)"]
    STT --> Accent["Accent Restoration (Khôi phục dấu tiếng Việt)"]
    Accent --> PG["PromptGuard"]
    PG -->|"Tiếp tục như Luồng 1"| L1["Luồng 1 (Chat)"]

    style Input fill:#eff6ff,stroke:#3b82f6
    style L1 fill:#eff6ff,stroke:#3b82f6
    style STT fill:#fef2f2,stroke:#ef4444
    style Accent fill:#f0fdf4,stroke:#22c55e
    style PG fill:#fef2f2,stroke:#ef4444
```

### Luồng 4: Admin - Crawl & Ingest

```mermaid
graph TD
    Input["Admin chọn URL / Upload document"] --> API["FastAPI Backend (Tiếp nhận request)"]
    API --> Crawl["Internet Crawler (Tải nội dung)"]
    Crawl --> Clean["Text Cleaning (Làm sạch)"]
    Clean --> Policy["Source Policy Check (Đánh giá độ tin cậy nguồn)"]
    Policy --> Chunk["Document Chunking (Chia nhỏ)"]
    Chunk --> Embed["Embedding Generation"]
    Embed --> DB[("Lưu vào Vector DB (ChromaDB)")]

    style Input fill:#fef3c7,stroke:#f59e0b
    style API fill:#eff6ff,stroke:#3b82f6
    style Crawl fill:#f0fdf4,stroke:#22c55e
    style Clean fill:#f0fdf4,stroke:#22c55e
    style Policy fill:#fef2f2,stroke:#ef4444
    style Chunk fill:#f0fdf4,stroke:#22c55e
    style Embed fill:#f0fdf4,stroke:#22c55e
    style DB fill:#f5f3ff,stroke:#8b5cf6
```

## 🔍 Chi tiết các Module trong Luồng

| Module | Vị trí | Chức năng |
|--------|--------|-----------|
| PromptGuard | `ml_agri_chat/modules/prompt_guard.py` | Lọc prompt injection, từ chối câu hỏi không liên quan |
| CleanImg | `ml_agri_chat/modules/clean_img.py` | Đánh giá chất lượng ảnh đầu vào |
| IntentClassifier | `ml_agri_chat/modules/intent_classifier.py` | Phân loại intent câu hỏi |
| RAG Engine | `ml_agri_chat/modules/rag.py` | Retrieval-Augmented Generation |
| LLM Advisor | `ml_agri_chat/modules/llm_advisor.py` | Sinh câu trả lời có kiểm soát |
| Vision Model | `ml_agri_chat/modules/vision_model.py` | Phân loại bệnh cây trồng từ ảnh |
| Source Policy | `ml_agri_chat/modules/source_policy.py` | Chính sách đánh giá độ tin cậy nguồn |
| Data Governance | `ml_agri_chat/modules/data_governance.py` | Sinh báo cáo Trust & Governance |

---

← [Về Trang chủ Tài liệu](./README.md) | [Tiếp: Pipeline RAG](./rag-pipeline.md) →
