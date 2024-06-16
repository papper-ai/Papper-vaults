import typing
from abc import ABC, abstractmethod
from uuid import UUID

from sqlalchemy import pool, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.config import settings
from src.database import models

engine = create_async_engine(
    settings.database_url,
    poolclass=pool.AsyncAdaptedQueuePool,
    pool_size=12,
    max_overflow=4,
    pool_pre_ping=True,
)

Session = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)


class AbstractRepository(ABC):
    @abstractmethod
    async def add(self, entity):
        raise NotImplementedError

    @abstractmethod
    async def get(self, entity_id):
        raise NotImplementedError


class DocumentRepository(AbstractRepository):
    def __init__(self):
        self.session = Session()

    async def add(self, entity) -> None:
        async with self.session as session:
            async with session.begin():
                session.add(entity)

    async def get(self, id: UUID) -> models.Document | None:
        async with self.session as session:
            document = await session.get(models.Document, id)
            return document

    async def delete(self, id: UUID) -> None:
        async with self.session as session:
            async with session.begin():
                document = await session.get(models.Document, id)
                if document:
                    await session.delete(document)


class VaultRepository(AbstractRepository):
    def __init__(self):
        self.session = Session()

    async def add(self, entity) -> None:
        async with self.session as session:
            async with session.begin():
                session.add(entity)

    async def get(self, id: UUID) -> models.Vault | None:
        async with self.session as session:
            vault = await session.get(models.Vault, id)
            return vault

    async def delete(self, id: UUID) -> None:
        async with self.session as session:
            async with session.begin():
                vault = await session.get(models.Vault, id)

                if vault:
                    # Query and delete all documents associated with the vault
                    documents = await session.execute(
                        select(models.Document).where(models.Document.vault_id == id)
                    )
                    for document in documents.scalars().all():
                        await session.delete(document)

                    await session.delete(vault)

    async def rename(self, id: UUID, name: str) -> None:
        async with self.session as session:
            async with session.begin():
                vault = await session.get(models.Vault, id)
                if vault:
                    vault.name = name

    async def get_vault_documents(
        self, id: UUID
    ) -> typing.Optional[typing.List[models.Document]]:
        async with self.session as session:
            # Query and delete all documents associated with the vault
            documents = await session.execute(
                select(models.Document).where(models.Document.vault_id == id)
            )
            return documents.scalars().all()

    async def get_users_vaults(
        self, user_id: UUID
    ) -> typing.Optional[typing.List[models.Vault]]:
        async with self.session as session:
            vaults = await session.execute(
                select(models.Vault).where(models.Vault.user_id == user_id)
            )
            return vaults.scalars().all()
