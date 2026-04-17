from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List

class Settings(BaseSettings):
    """
    Global application settings and environment variables.
    
    Attributes:
        PROJECT_TITLE: The name of the API.
        PROJECT_VERSION: Current semantic version of the API.
        GCP_PROJECT_ID: The target Google Cloud project ID.
        GCP_REGION: The primary region for GCP services (e.g. Vertex AI).
        USE_REAL_GCP: Master toggle for live vs. mock Google Cloud services.
        CORS_ORIGINS: List of allowed origins for cross-domain requests.
        RATE_LIMIT_PER_MINUTE: API rate limiting threshold.
        FIRESTORE_THROTTLE_SECONDS: Minimum interval between Firestore telemetry writes.
        BIGQUERY_DATASET: The BigQuery dataset for analytical logs.
        BIGQUERY_TABLE: The BigQuery table for historical telemetry.
    """
    PROJECT_TITLE: str = "Smart Venue Experience — Decision Engine API"
    PROJECT_VERSION: str = "5.0.0"
    
    GCP_PROJECT_ID: str = "promptwars-1-493418"
    GCP_REGION: str = "us-central1"
    USE_REAL_GCP: bool = False  # Default to False for local safety
    
    CORS_ORIGINS: List[str] = ["*"]
    RATE_LIMIT_PER_MINUTE: int = 60
    
    FIRESTORE_THROTTLE_SECONDS: float = 5.0
    BIGQUERY_DATASET: str = "venue_analytics"
    BIGQUERY_TABLE: str = "telemetry_history"
    PUB_SUB_TOPIC: str = "venue-telemetry-topic"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True
    )

# Global settings instance
settings = Settings()
