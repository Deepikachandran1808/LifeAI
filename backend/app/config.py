import os
from pydantic_settings import BaseSettings
from typing import List

class Settings(BaseSettings):
    PROJECT_NAME: str = "LifeAI – Intelligent Daily Life Ecosystem"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"
    
    # Security
    SECRET_KEY: str = "lifeai-super-secret-key-change-in-production-2026-secure-token"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days
    
    # Database
    # Defaults to async SQLite for local execution, seamlessly supports PostgreSQL / pgvector
    DATABASE_URL: str = "sqlite+aiosqlite:///./lifeai.db"
    
    # CORS
    CORS_ORIGINS: List[str] = [
        "http://localhost:5173",
        "http://localhost:3000",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:3000",
        "*"
    ]
    
    # Paths
    BASE_DIR: str = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    ML_MODELS_DIR: str = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "ml", "models")
    ML_DATASETS_DIR: str = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "ml", "datasets")
    
    class Config:
        case_sensitive = True
        env_file = ".env"

settings = Settings()
