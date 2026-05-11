from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    PROJECT_NAME: str = "ArgiAI Backend"
    API_V1_STR: str = "/api/v1"
    
    # AI Config
    GEMINI_API_KEY: str = ""
    
    # CORS
    BACKEND_CORS_ORIGINS: list[str] = ["http://localhost:8080", "http://127.0.0.1:8080"]

    class Config:
        # Hỗ trợ đọc .env ở cả thư mục hiện tại và thư mục gốc
        env_file = (".env", "../.env")

settings = Settings()
