import chromadb
import os

# Lấy cấu hình từ biến môi trường
CHROMA_DB_URL = os.environ.get("CHROMA_DB_URL", "http://localhost:8000")

# Phân tách host và port từ URL để khởi tạo HttpClient
# Giả sử format luôn là http://host:port
try:
    url_without_http = CHROMA_DB_URL.replace("http://", "").replace("https://", "")
    chroma_host = url_without_http.split(":")[0]
    chroma_port = int(url_without_http.split(":")[1].split("/")[0])
except Exception:
    chroma_host = "chromadb"
    chroma_port = 8000

# Khởi tạo kết nối Vector DB qua mạng lưới
chroma_client = chromadb.HttpClient(host=chroma_host, port=chroma_port)

def get_chroma_client():
    """
    Trả về client ChromaDB.
    """
    return chroma_client

def get_handbook_collection():
    """
    Trả về (hoặc khởi tạo nếu chưa có) Collection chứa dữ liệu cẩm nang nông nghiệp.
    """
    return chroma_client.get_or_create_collection(
        name="agricultural_handbook",
        metadata={"hnsw:space": "cosine"} # Tối ưu cho tìm kiếm vector ngữ nghĩa
    )
