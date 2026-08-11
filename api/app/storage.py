import time

import boto3
from botocore.config import Config as BotoConfig

from .config import settings

_client = None


def s3():
    global _client
    if _client is None:
        _client = boto3.client(
            "s3",
            endpoint_url=settings.s3_endpoint,
            aws_access_key_id=settings.s3_access_key,
            aws_secret_access_key=settings.s3_secret_key,
            config=BotoConfig(signature_version="s3v4"),
        )
    return _client


def ensure_bucket(retries: int = 15, delay: float = 2.0) -> None:
    for attempt in range(retries):
        try:
            names = [b["Name"] for b in s3().list_buckets().get("Buckets", [])]
            if settings.s3_bucket not in names:
                s3().create_bucket(Bucket=settings.s3_bucket)
            return
        except Exception:
            if attempt == retries - 1:
                raise
            time.sleep(delay)


def put_bytes(key: str, data: bytes, content_type: str) -> None:
    s3().put_object(Bucket=settings.s3_bucket, Key=key, Body=data, ContentType=content_type)


def get_bytes(key: str) -> bytes:
    return s3().get_object(Bucket=settings.s3_bucket, Key=key)["Body"].read()


def presigned_get(key: str, expires: int = 3600) -> str:
    return s3().generate_presigned_url(
        "get_object",
        Params={"Bucket": settings.s3_bucket, "Key": key},
        ExpiresIn=expires,
    )
