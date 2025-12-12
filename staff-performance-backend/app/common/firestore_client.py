# app/common/firestore_client.py
from typing import Generator
import os

from google.cloud import firestore  # type: ignore


_db: firestore.Client | None = None


def get_db() -> firestore.Client:
    """
    Returns a singleton Firestore client.
    Cloud Run will use Application Default Credentials.
    """
    global _db
    if _db is None:
        project_id = os.getenv("GOOGLE_CLOUD_PROJECT")
        _db = firestore.Client(project=project_id)
    return _db


def get_db_dep() -> Generator[firestore.Client, None, None]:
    """
    Dependency function for FastAPI (so we can use Depends(get_db_dep)).
    """
    db = get_db()
    try:
        yield db
    finally:
        # Nothing special to close for Firestore
        pass

