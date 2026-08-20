"""Storage backend tests: LocalStorage (filesystem) and S3Storage (moto mock)."""

import asyncio

import boto3
from moto import mock_aws

from app.storage import LocalStorage, S3Storage


async def test_local_storage_roundtrip(tmp_path):
    store = LocalStorage(tmp_path / "uploads")

    location = await store.save("abc.png", b"hello-bytes", "image/png")
    loaded = await store.load(location)
    assert loaded is not None
    data, content_type = loaded
    assert data == b"hello-bytes"
    assert content_type == "image/png"

    await store.delete(location)
    assert await store.load(location) is None


async def test_local_storage_missing_returns_none(tmp_path):
    store = LocalStorage(tmp_path / "uploads")
    assert await store.load(str(tmp_path / "nope.png")) is None


@mock_aws
def test_s3_storage_roundtrip():
    boto3.client("s3", region_name="us-east-1").create_bucket(Bucket="test-bucket")
    store = S3Storage(
        bucket="test-bucket",
        region="us-east-1",
        access_key_id="x",
        secret_access_key="y",
    )

    async def run():
        location = await store.save("k.png", b"img-bytes", "image/png")
        assert location == "k.png"

        loaded = await store.load("k.png")
        assert loaded == (b"img-bytes", "image/png")

        await store.delete("k.png")
        assert await store.load("k.png") is None  # NoSuchKey -> None

    asyncio.run(run())
