from typing import Annotated
from uuid import UUID

from fastapi import Body
from fastapi.exceptions import HTTPException

from src.database.postgres_repositories import DocumentRepository, VaultRepository


async def vault_exists(vault_id: Annotated[UUID, Body()]) -> VaultRepository:
    vault_repository = VaultRepository()

    vault = await vault_repository.get(vault_id)
    if not vault:
        raise HTTPException(status_code=404, detail="Vault not found")

    return vault_repository


async def document_exists(document_id: Annotated[UUID, Body()]) -> DocumentRepository:
    document_repository = DocumentRepository()

    document = await document_repository.get(document_id)
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    return document_repository
