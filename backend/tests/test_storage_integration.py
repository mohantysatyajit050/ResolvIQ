import urllib.error
import urllib.request
import uuid

import pytest
from botocore.exceptions import BotoCoreError

from app.services import storage_service


def test_real_storage_round_trip_and_signed_link():
    """Talks to the real storage container. Skipped when it is not running."""
    try:
        storage_service.ensure_bucket()
    except BotoCoreError:
        pytest.skip("storage is not running")

    key = f"test/{uuid.uuid4()}.txt"
    storage_service.put_object(key, b"hello", "text/plain")
    try:
        url = storage_service.presigned_download_url(key, "text/plain", expires_in=60)
        with urllib.request.urlopen(url) as response:
            assert response.read() == b"hello"

        with pytest.raises(urllib.error.HTTPError) as error:
            urllib.request.urlopen(url.split("?")[0])  # the same file, no signature
        assert error.value.code == 403
    finally:
        storage_service.delete_object(key)
