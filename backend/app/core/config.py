from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    PROJECT_NAME: str = "Nông Trí AI Backend"
    API_V1_STR: str = "/api/v1"

    # CORS
    BACKEND_CORS_ORIGINS: list[str] = [
        "http://localhost:8080",
        "http://127.0.0.1:8080",
        "http://localhost:8082",
        "http://127.0.0.1:8082",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ]

    class Config:
        extra = "ignore"
        # Hỗ trợ đọc .env ở cả thư mục hiện tại và thư mục gốc
        env_file = (".env", "../.env")

settings = Settings()
