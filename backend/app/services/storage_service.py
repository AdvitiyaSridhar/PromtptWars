import os
import json
import uuid
from abc import ABC, abstractmethod
from typing import Optional
from app.config import settings

class BaseStorageService(ABC):
    @abstractmethod
    def save_file(self, file_name: str, content: bytes, mime_type: str) -> str:
        """Saves file bytes and returns persistent storage path/URI."""
        pass

    @abstractmethod
    def get_url(self, storage_path: str) -> str:
        """Returns accessible or signed URL for the stored file."""
        pass

class LocalFileStorage(BaseStorageService):
    def __init__(self, upload_dir: str = settings.LOCAL_UPLOAD_DIR):
        self.upload_dir = upload_dir
        os.makedirs(self.upload_dir, exist_ok=True)

    def save_file(self, file_name: str, content: bytes, mime_type: str) -> str:
        ext = os.path.splitext(file_name)[1]
        unique_name = f"{uuid.uuid4().hex}{ext}"
        target_path = os.path.join(self.upload_dir, unique_name)
        with open(target_path, "wb") as f:
            f.write(content)
        return unique_name

    def get_url(self, storage_path: str) -> str:
        return storage_path

class GCSStorage(BaseStorageService):
    def __init__(self, bucket_name: Optional[str] = settings.GCS_BUCKET_NAME):
        if not bucket_name:
            raise ValueError("GCS_BUCKET_NAME is required when GCS storage is enabled.")
        self.bucket_name = bucket_name

    @staticmethod
    def _client():
        from google.cloud import storage
        from app.config import settings

        if settings.GCS_SERVICE_ACCOUNT_JSON:
            from google.oauth2 import service_account

            info = json.loads(settings.GCS_SERVICE_ACCOUNT_JSON)
            credentials = service_account.Credentials.from_service_account_info(info)
            return storage.Client(project=credentials.project_id, credentials=credentials)
        return storage.Client()

    def save_file(self, file_name: str, content: bytes, mime_type: str) -> str:
        client = self._client()
        bucket = client.bucket(self.bucket_name)
        ext = os.path.splitext(file_name)[1]
        blob_name = f"evidence/{uuid.uuid4().hex}{ext}"
        blob = bucket.blob(blob_name)
        blob.upload_from_string(content, content_type=mime_type)
        return f"gs://{self.bucket_name}/{blob_name}"

    def get_url(self, storage_path: str) -> str:
        if storage_path.startswith("gs://"):
            from datetime import timedelta
            client = self._client()
            parts = storage_path.replace("gs://", "").split("/", 1)
            bucket = client.bucket(parts[0])
            blob = bucket.blob(parts[1])
            return blob.generate_signed_url(expiration=timedelta(minutes=15))
        raise ValueError("Unsupported storage URI.")

def get_storage_service() -> BaseStorageService:
    if settings.STORAGE_BACKEND == "gcs":
        return GCSStorage()
    if settings.STORAGE_BACKEND != "local":
        raise ValueError(f"Unsupported storage backend: {settings.STORAGE_BACKEND}")
    return LocalFileStorage()
