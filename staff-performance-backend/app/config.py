# app/config.py
import os
from functools import lru_cache

class Settings:
    def __init__(self) -> None:
        # GCP project id
        self.project_id: str | None = os.getenv("GOOGLE_CLOUD_PROJECT")

        # Later you can add more configs here (JWT secrets, etc.)

@lru_cache()
def get_settings() -> Settings:
    return Settings()
