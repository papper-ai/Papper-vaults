import logging
from pathlib import Path

from pydantic_settings import BaseSettings

logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)

BASE_DIR = Path(__file__).parent


class Settings(BaseSettings):
    db_dialect: str
    db_async_driver: str
    db_host: str
    db_name: str
    db_user: str
    db_password: str

    graph_service_url: str = "http://papper-graph-kb-service:8000"
    vector_service_url: str = "http://papper-vector-kb-service:8000"
    
    s3_access_key: str
    s3_secret_key: str
    s3_endpoint_url: str
    s3_bucket_name: str
    verify: bool = False
    
    @property
    def database_url(self) -> str:
        return f"{self.db_dialect}+{self.db_async_driver}://{self.db_user}:{self.db_password}@{self.db_host}:5432/{self.db_name}"

    class Config:
        extra = "ignore"


settings = Settings()
