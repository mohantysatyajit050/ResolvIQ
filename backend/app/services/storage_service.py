from functools import lru_cache

import boto3
from botocore.client import Config
from botocore.exceptions import ClientError

from app.core.config import settings

REGION = "us-east-1"  # S3-compatible servers ignore the region, but the signer needs a value


@lru_cache
def _client():
    """One S3 client for the whole app. 'path' style means http://host:9000/bucket/key."""
    return boto3.client(
        "s3",
        endpoint_url=settings.s3_endpoint_url,
        aws_access_key_id=settings.s3_access_key,
        aws_secret_access_key=settings.s3_secret_key,
        region_name=REGION,
        config=Config(
            signature_version="s3v4",
            s3={"addressing_style": "path"},
            connect_timeout=5,  # fail fast if storage is not running
            read_timeout=30,
            retries={"max_attempts": 2},
            # newer boto3 adds checksum trailers that some S3-compatible servers reject
            request_checksum_calculation="when_required",
            response_checksum_validation="when_required",
        ),
    )


def ensure_bucket() -> None:
    """Create the evidence bucket if it does not exist yet."""
    client = _client()
    try:
        client.head_bucket(Bucket=settings.s3_bucket)
    except ClientError as exc:
        code = str(exc.response.get("Error", {}).get("Code"))
        if code in ("404", "NoSuchBucket", "NotFound"):
            client.create_bucket(Bucket=settings.s3_bucket)
        else:
            raise


def put_object(key: str, data: bytes, content_type: str) -> None:
    _client().put_object(
        Bucket=settings.s3_bucket, Key=key, Body=data, ContentType=content_type
    )


def delete_object(key: str) -> None:
    _client().delete_object(Bucket=settings.s3_bucket, Key=key)


def presigned_download_url(key: str, content_type: str, expires_in: int = 300) -> str:
    """A temporary link that lets whoever holds it download this one file."""
    return _client().generate_presigned_url(
        "get_object",
        Params={
            "Bucket": settings.s3_bucket,
            "Key": key,
            "ResponseContentType": content_type,
        },
        ExpiresIn=expires_in,
    )
