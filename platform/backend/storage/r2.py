"""Cloudflare R2 storage layer for media files.

Uses boto3 S3-compatible API to upload/download from Cloudflare R2.
Zero egress fees make this ideal for serving media publicly.
"""

import logging
import os

import boto3
from botocore.config import Config

logger = logging.getLogger(__name__)

R2_ACCOUNT_ID = os.getenv("R2_ACCOUNT_ID", "")
R2_ACCESS_KEY_ID = os.getenv("R2_ACCESS_KEY_ID", "")
R2_SECRET_ACCESS_KEY = os.getenv("R2_SECRET_ACCESS_KEY", "")
R2_BUCKET_NAME = os.getenv("R2_BUCKET_NAME", "deep-sci-fi-media")
R2_PUBLIC_URL = os.getenv("R2_PUBLIC_URL", "https://media.deep-sci-fi.world")


def _get_client():
    """Create a boto3 S3 client configured for Cloudflare R2."""
    return boto3.client(
        "s3",
        endpoint_url=f"https://{R2_ACCOUNT_ID}.r2.cloudflarestorage.com",
        aws_access_key_id=R2_ACCESS_KEY_ID,
        aws_secret_access_key=R2_SECRET_ACCESS_KEY,
        config=Config(
            retries={"max_attempts": 3, "mode": "adaptive"},
            signature_version="s3v4",
        ),
        region_name="auto",
    )


def upload_media(data: bytes, key: str, content_type: str) -> str:
    """Upload media bytes to R2 and return the public URL.

    Args:
        data: Raw file bytes
        key: Storage key (e.g., media/world/{id}/cover_image/{uuid}.png)
        content_type: MIME type (e.g., image/png, video/mp4)

    Returns:
        Public URL for the uploaded file
    """
    client = _get_client()
    client.put_object(
        Bucket=R2_BUCKET_NAME,
        Key=key,
        Body=data,
        ContentType=content_type,
    )
    logger.info(f"Uploaded {len(data)} bytes to R2: {key}")
    return get_public_url(key)


def get_public_url(key: str) -> str:
    """Construct the public CDN URL for a storage key."""
    return f"{R2_PUBLIC_URL.rstrip('/')}/{key}"


def delete_media(key: str) -> None:
    """Delete a media file from R2."""
    client = _get_client()
    client.delete_object(Bucket=R2_BUCKET_NAME, Key=key)
    logger.info(f"Deleted from R2: {key}")
