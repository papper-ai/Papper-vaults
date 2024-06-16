from abc import ABC, abstractmethod
from contextlib import asynccontextmanager
from uuid import UUID

from aiobotocore.client import AioBaseClient
from aiobotocore.session import get_session

from src.config import settings


class AbstractRepository(ABC):
    @abstractmethod
    async def get(self, *args, **kwargs):
        pass

    @abstractmethod
    async def put(self, *args, **kwargs):
        pass

    @abstractmethod
    async def delete(self, *args, **kwargs):
        pass


class S3Repository(AbstractRepository):
    def __init__(self):
        self.access_key = settings.s3_access_key
        self.secret_key = settings.s3_secret_key
        self.endpoint_url = settings.s3_endpoint_url
        self.bucket_name = settings.s3_bucket_name
        self.session = get_session()

    @asynccontextmanager
    async def get_client(self) -> AioBaseClient:
        config = {
            "aws_access_key_id": self.access_key,
            "aws_secret_access_key": self.secret_key,
            "endpoint_url": self.endpoint_url,
            "verify": settings.verify,
        }
        async with self.session.create_client("s3", **config) as client:
            yield client

    async def get(self, id: str) -> str:
        async with self.get_client() as client:
            return await client.get_object(Bucket=self.bucket_name, Key=id)

    async def put(self, file: bytes, file_id: UUID) -> None:
        async with self.get_client() as client:
            object_name = str(file_id)
            await client.put_object(
                Bucket=self.bucket_name,
                Key=object_name,
                Body=file,
            )
        
    async def delete(self, name: str):
        async with self.get_client() as client:
            await client.delete_object(Bucket=self.bucket_name, Key=name)
