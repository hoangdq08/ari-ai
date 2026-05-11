from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings

def get_application() -> FastAPI:
    application = FastAPI(
        title=settings.PROJECT_NAME,
        openapi_url=f"{settings.API_V1_STR}/openapi.json",
        docs_url=f"{settings.API_V1_STR}/docs",
        redoc_url=f"{settings.API_V1_STR}/redoc",
    )

    # Set all CORS enabled origins
    if settings.BACKEND_CORS_ORIGINS:
        application.add_middleware(
            CORSMiddleware,
            allow_origins=[str(origin) for origin in settings.BACKEND_CORS_ORIGINS],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

    # Khai báo các Routers từ Presentation Layers
    from app.modules.chat.presentation.router import router as chat_router
    from app.modules.diagnostics.presentation.router import router as diagnostics_router
    from app.modules.handbook.presentation.router import router as handbook_router

    application.include_router(chat_router, prefix=f"{settings.API_V1_STR}/chat", tags=["Chat"])
    application.include_router(diagnostics_router, prefix=f"{settings.API_V1_STR}/diagnostics", tags=["Diagnostics"])
    application.include_router(handbook_router, prefix=f"{settings.API_V1_STR}/handbook", tags=["Handbook"])
    return application

app = get_application()

@app.get("/health")
def health_check():
    return {"status": "ok", "message": "ArgiAI Backend is running!"}
