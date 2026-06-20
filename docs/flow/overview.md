# 🔄 Luồng Dữ liệu Hệ thống

## Sơ đồ Luồng End-to-End

```mermaid
flowchart TD
    classDef userLayer fill:#eff6ff,stroke:#3b82f6,stroke-width:2px,color:#1e3a8a,rx:10,ry:10
    classDef securityLayer fill:#fef2f2,stroke:#ef4444,stroke-width:2px,color:#991b1b,rx:10,ry:10
    classDef coreLayer fill:#f0fdf4,stroke:#22c55e,stroke-width:2px,color:#166534,rx:10,ry:10
    classDef dbLayer fill:#f5f3ff,stroke:#8b5cf6,stroke-width:2px,color:#5b21b6,rx:10,ry:10
    classDef orchestrator fill:#fff7ed,stroke:#f97316,stroke-width:2px,color:#9a3412,rx:10,ry:10

    subgraph Client["🧑‍🌾 GIAO DIỆN ĐẦU VÀO"]
        direction LR
        UI["📱 Web / App Mobile"]:::userLayer
        Voice["🎙️ Ghi âm Giọng Nói"]:::userLayer
        Cam["📸 Chụp Mẫu Bệnh"]:::userLayer
    end

    subgraph Robustness["🛡️ LỚP KIỂM DUYỆT"]
        STT["Phân Tích & Dịch Giọng<br>(Speech-to-Text)"]:::securityLayer
        CleanImg["Kiểm Tra Chất Lượng Ảnh<br>(Bộ Lọc Nhiễu)"]:::securityLayer
        PromptGuard["Kiểm Duyệt Nội Dung<br>(Chống Hack/Jailbreak)"]:::securityLayer
        Reject("🛑 Báo Lỗi / Từ Chối"):::securityLayer
    end

    subgraph Core["🧠 LÕI XỬ LÝ TRÍ TUỆ NHÂN TẠO"]
        Orchestrator{"ĐIỀU PHỐI AI Router"}:::orchestrator
        RAG["🔍 RAG Engine<br>(Truy tìm ngữ cảnh)"]:::coreLayer
        LLM["🤖 Logic Chẩn Đoán<br>(Vision & LLM)"]:::coreLayer
    end

    subgraph DB["📚 CƠ SỞ TRI THỨC"]
        Docs["Tài Liệu Nông Nghiệp<br>Khuyến Nông VN"]:::dbLayer
        VectorDB[("Vector Database<br>ChromaDB")]:::dbLayer
    end

    subgraph Output["✨ KẾT QUẢ ĐẦU RA"]
        UI_Out["📱 Màn Hình Hiển Thị<br>Của Nông Dân"]:::userLayer
    end

    UI -->|"Nhập Text"| PromptGuard
    Voice -->|"File Audio"| STT
    Cam -->|"File Ảnh"| CleanImg

    STT -->|"Text"| PromptGuard
    CleanImg -->|"Ảnh Đã Lọc"| PromptGuard

    PromptGuard -->|"Hợp Lệ"| Orchestrator
    PromptGuard -.->|"Vi Phạm"| Reject

    Docs -.->|"Nhúng Data (Embedding)"| VectorDB
    Orchestrator -->|"Câu Hỏi"| RAG
    
    RAG -->|"Truy vấn"| VectorDB
    VectorDB -.->|"Trả Ngữ cảnh"| RAG

    RAG -->|"Gửi Ngữ Cảnh"| LLM
    Orchestrator -->|"Gửi Ảnh Mẫu Bệnh"| LLM

    LLM ===>|"Trả Lời Khuyên & Nguồn Bệnh"| UI_Out
    Reject -.->|"Hiển thị lỗi"| UI_Out
```

## 🎯 Các Luồng Xử lý Chính

### Luồng 1: Hỏi đáp Văn bản (Chat)

```
Người dùng nhập text
    → PromptGuard (kiểm duyệt nội dung) 
        → Intent Classifier (phân loại câu hỏi)
            → [Nếu là câu hỏi nông nghiệp]
                → RAG Engine (truy xuất ngữ cảnh từ Vector DB)
                → LLM Advisor (sinh câu trả lời + trích dẫn nguồn)
                → Hiển thị kết quả
            → [Nếu không phải]
                → Từ chối, gợi ý chủ đề nông nghiệp
```

### Luồng 2: Chẩn đoán Ảnh (Diagnostics)

```
Người dùng chụp/gửi ảnh
    → CleanImg (kiểm tra chất lượng: mờ, rung, sai góc)
        → [Nếu ảnh không đạt] → Yêu cầu chụp lại
        → [Nếu ảnh đạt]
            → Vision Model (CoffeeVisionClassifier - Keras)
                → Phân loại bệnh + độ tin cậy
                → LLM Advisor (giải thích kết quả + khuyến nghị)
                → Hiển thị chẩn đoán + nguồn tham khảo
```

### Luồng 3: Giọng nói (Voice - kế hoạch)

```
Người dùng ghi âm
    → Faster-Whisper (Speech-to-Text offline)
        → Accent Restoration (khôi phục dấu tiếng Việt)
            → PromptGuard
                → [Tiếp tục như Luồng 1]
```

### Luồng 4: Admin - Crawl & Ingest

```
Admin chọn URL / Upload document
    → Internet Crawler (tải nội dung)
        → Text Cleaning (làm sạch)
            → Source Policy Check (đánh giá độ tin cậy nguồn)
                → Document Chunking (chia nhỏ)
                    → Embedding Generation
                        → Lưu vào Vector DB (ChromaDB)
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
