from pydantic_settings import BaseSettings
from pydantic import Field
from typing import List
import json


class Settings(BaseSettings):
    # App
    APP_NAME: str = "Gerador de Questões"
    APP_VERSION: str = "1.0.0"
    APP_ENV: str = "development"
    DEBUG: bool = True
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    
    # Ollama
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "llama3.2:3b"
    OLLAMA_EMBEDDING_MODEL: str = "bge-m3:latest"
    
    # OpenSearch
    OPENSEARCH_HOST: str = "localhost"
    OPENSEARCH_PORT: int = 9200
    OPENSEARCH_USER: str = "admin"
    OPENSEARCH_PASSWORD: str = "Luluadmin"
    OPENSEARCH_INDEX: str = "documentos_juridicos"
    OPENSEARCH_USE_SSL: bool = False
    
    # RAG
    RAG_TOP_K: int = 5
    RAG_SCORE_THRESHOLD: float = 0.5
    
    # CORS
    CORS_ORIGINS: List[str] = ["http://localhost:3000"]
    
    @property
    def opensearch_url(self) -> str:
        protocol = "https" if self.OPENSEARCH_USE_SSL else "http"
        return f"{protocol}://{self.OPENSEARCH_HOST}:{self.OPENSEARCH_PORT}"
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        
        @classmethod
        def parse_env_var(cls, field_name: str, raw_val: str):
            if field_name == "CORS_ORIGINS":
                return json.loads(raw_val)
            return raw_val


settings = Settings()