import os
from datetime import timedelta


class WebConfig:
    SECRET_KEY = os.getenv("SECRET_KEY", "cert-management-secret-key-2024")
    ALGORITHM = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 60 * 24))
    
    API_V1_PREFIX = "/api/v1"
    
    BACKEND_HOST = os.getenv("BACKEND_HOST", "0.0.0.0")
    BACKEND_PORT = int(os.getenv("BACKEND_PORT", 8000))
    
    FRONTEND_ORIGINS = [
        "http://localhost:5173",
        "http://localhost:3000",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:3000",
    ]
    
    MAX_UPLOAD_SIZE = 10 * 1024 * 1024
    ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "bmp", "pdf"}
    
    ADMIN_DEFAULT_USERNAME = os.getenv("ADMIN_DEFAULT_USERNAME", "admin")
    ADMIN_DEFAULT_PASSWORD = os.getenv("ADMIN_DEFAULT_PASSWORD", "admin123")
    ADMIN_DEFAULT_EMAIL = os.getenv("ADMIN_DEFAULT_EMAIL", "admin@company.com")
