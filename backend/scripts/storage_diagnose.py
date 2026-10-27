"""Find out why the storage refuses us.

Run from the backend folder:
    uv run python -m scripts.storage_diagnose
"""

from datetime import datetime, timezone
from email.utils import parsedate_to_datetime

import boto3
from botocore.client import Config
from botocore.exceptions import ClientError, EndpointConnectionError

from app.core.config import settings

HINTS = {
    "InvalidAccessKeyId": "The access key is wrong. S3_ACCESS_KEY in backend/.env must match MINIO_ROOT_USER in docker-compose.yml.",
    "SignatureDoesNotMatch": "The secret key is wrong. S3_SECRET_KEY in backend/.env must match MINIO_ROOT_PASSWORD in docker-compose.yml.",
    "RequestTimeTooSkewed": "The clock inside Docker is out of sync with Windows.",
    "AccessDenied": "The server knows the keys but does not allow this action.",
}

print("Endpoint:   ", settings.s3_endpoint_url)
print("Access key: ", settings.s3_access_key)
print("Bucket:     ", settings.s3_bucket)

client = boto3.client(
    "s3",
    endpoint_url=settings.s3_endpoint_url,
    aws_access_key_id=settings.s3_access_key,
    aws_secret_access_key=settings.s3_secret_key,
    region_name="us-east-1",
    config=Config(
        signature_version="s3v4",
        s3={"addressing_style": "path"},
        connect_timeout=5,
        retries={"max_attempts": 1},
        request_checksum_calculation="when_required",
        response_checksum_validation="when_required",
    ),
)


def show_server_info(headers: dict) -> None:
    print("Server software:", headers.get("server"))
    server_date = headers.get("date")
    if server_date:
        skew = (parsedate_to_datetime(server_date) - datetime.now(timezone.utc)).total_seconds()
        print(f"Server clock minus your clock: {skew:.0f} seconds")


try:
    result = client.list_buckets()
    print("OK: the keys are accepted. Buckets:", [b["Name"] for b in result["Buckets"]])
    show_server_info(result["ResponseMetadata"]["HTTPHeaders"])
except EndpointConnectionError:
    print("FAIL: cannot reach the storage endpoint. Is the container running?")
except ClientError as exc:
    error = exc.response.get("Error", {})
    code = error.get("Code")
    print("FAIL:", code, "-", error.get("Message"))
    print("Hint:", HINTS.get(code, "Unknown error. Send this whole output to your mentor."))
    show_server_info(exc.response.get("ResponseMetadata", {}).get("HTTPHeaders", {}))
