"""Smoke test for object storage.

Run from the backend folder:
    uv run python -m scripts.storage_smoke_test
"""

import urllib.error
import urllib.request

from app.services import storage_service

KEY = "smoke-test/hello.txt"

storage_service.ensure_bucket()
storage_service.put_object(KEY, b"Hello from ResolvIQ storage!", "text/plain")
url = storage_service.presigned_download_url(KEY, "text/plain", expires_in=60)

print("Presigned URL (valid for 60 seconds):")
print(url)
print()

# 1. the signed link works without any password
with urllib.request.urlopen(url) as response:
    print("1. With the signed URL:", response.status, response.read().decode())

# 2. the same file without the signature is refused
bare_url = url.split("?")[0]
try:
    urllib.request.urlopen(bare_url)
    print("2. Without the signature: STILL OPEN (the bucket is public, which is wrong)")
except urllib.error.HTTPError as error:
    print("2. Without the signature:", error.code, "(refused, as it should be)")
