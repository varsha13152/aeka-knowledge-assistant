"""Object storage service for Cloudflare R2 (S3-compatible).

Provides a centralized interface for all object storage operations:
- Upload/delete objects
- Generate presigned URLs for browser-direct downloads
- Bucket lifecycle management

All methods are async-safe — synchronous boto3 calls are wrapped
in asyncio.to_thread() to avoid blocking the event loop.
"""

import asyncio

import structlog

import boto3
from botocore.config import Config as BotoConfig

from app.core.config import get_settings

settings = get_settings()
logger = structlog.get_logger()


class StorageService:
    """Cloudflare R2 object storage via S3-compatible API.

    Uses boto3 under the hood — R2 is fully S3-compatible for the
    operations we need (PutObject, DeleteObject, GetObject, presigned URLs).

    All public methods are async to prevent blocking the event loop.
    """

    def __init__(self):
        self.bucket = settings.r2_bucket_name
        self._client = boto3.client(
            "s3",
            endpoint_url=settings.r2_endpoint_url,
            aws_access_key_id=settings.r2_access_key_id,
            aws_secret_access_key=settings.r2_secret_access_key,
            region_name="auto",
            config=BotoConfig(
                signature_version="s3v4",
                retries={"max_attempts": 3, "mode": "standard"},
            ),
        )

    async def upload_object(self, key: str, body: bytes, content_type: str) -> None:
        """Upload an object to the bucket (non-blocking)."""
        await asyncio.to_thread(
            self._client.put_object,
            Bucket=self.bucket,
            Key=key,
            Body=body,
            ContentType=content_type,
        )

    async def delete_object(self, key: str) -> None:
        """Delete an object from the bucket (non-blocking)."""
        await asyncio.to_thread(
            self._client.delete_object,
            Bucket=self.bucket,
            Key=key,
        )

    def generate_presigned_url(self, key: str, expires_in: int = 3600) -> str:
        """Generate a presigned GET URL for browser-direct download.

        This is fast (no network call) so it remains synchronous.
        """
        return self._client.generate_presigned_url(
            "get_object",
            Params={"Bucket": self.bucket, "Key": key},
            ExpiresIn=expires_in,
        )

    def ensure_bucket_exists(self) -> None:
        """Create the bucket if it doesn't already exist.

        Called once at startup — safe to be synchronous.
        """
        try:
            self._client.head_bucket(Bucket=self.bucket)
        except Exception:
            try:
                self._client.create_bucket(Bucket=self.bucket)
                logger.info("Created storage bucket", bucket=self.bucket)
            except Exception as e:
                logger.warning("Could not create storage bucket", error=str(e))


# Module-level singleton
storage_service = StorageService()
