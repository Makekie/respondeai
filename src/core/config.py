from pydantic_settings import BaseSettings
from pydantic import Field
from typing import List, Dict, Any
import json
import yaml
import os
from pathlib import Path


def load_yaml_config() -> Dict[str, Any]:
    """Carrega configurações do arquivo YAML"""
    config_path = Path("config.yaml")
    if config_path.exists():
        with open(config_path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)
    return {}


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
    
    def __init__(self, **kwargs):
        # Carrega configurações do YAML primeiro
        yaml_config = load_yaml_config()
        
        # Mapeia configurações do YAML para variáveis de ambiente
        if yaml_config:
            self._map_yaml_to_env(yaml_config)
        
        super().__init__(**kwargs)
    
    def _map_yaml_to_env(self, config: Dict[str, Any]):
        """Mapeia configurações do YAML para o formato esperado"""
        mapping = {
            "app.name": "APP_NAME",
            "app.version": "APP_VERSION", 
            "app.env": "APP_ENV",
            "app.debug": "DEBUG",
            "app.host": "HOST",
            "app.port": "PORT",
            "ollama.base_url": "OLLAMA_BASE_URL",
            "ollama.model": "OLLAMA_MODEL",
            "ollama.embedding_model": "OLLAMA_EMBEDDING_MODEL",
            "opensearch.host": "OPENSEARCH_HOST",
            "opensearch.port": "OPENSEARCH_PORT",
            "opensearch.user": "OPENSEARCH_USER",
            "opensearch.password": "OPENSEARCH_PASSWORD",
            "opensearch.index": "OPENSEARCH_INDEX",
            "opensearch.use_ssl": "OPENSEARCH_USE_SSL",
            "rag.top_k": "RAG_TOP_K",
            "rag.score_threshold": "RAG_SCORE_THRESHOLD",
            "cors.origins": "CORS_ORIGINS"
        }
        
        for yaml_path, env_var in mapping.items():
            value = self._get_nested_value(config, yaml_path)
            if value is not None:
                if env_var == "CORS_ORIGINS" and isinstance(value, list):
                    os.environ[env_var] = json.dumps(value)
                else:
                    os.environ[env_var] = str(value)
    
    def _get_nested_value(self, data: Dict[str, Any], path: str) -> Any:
        """Obtém valor aninhado usando notação de ponto"""
        keys = path.split(".")
        current = data
        for key in keys:
            if isinstance(current, dict) and key in current:
                current = current[key]
            else:
                return None
        return current
    
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