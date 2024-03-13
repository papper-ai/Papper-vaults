import asyncio
import logging
from typing import List
from uuid import UUID

from fastapi import APIRouter, Body, Depends, File, UploadFile, status
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import HTTPException
from fastapi.responses import JSONResponse

from src.documents.dependencies import vault_exists
from src.documents.schemas import CreateVaultRequest, Document, RequestToGraphKBService
from src.documents.utils import add_document, add_vault
from src.repositories.postgres_repository import DocumentRepository, VaultRepository
from src.utils.exceptions import UnsupportedFileType
from src.utils.requests import send_delete_request, send_upload_request

documents_router = APIRouter(tags=["Documents"])


@documents_router.post("/create_vault", status_code=status.HTTP_201_CREATED)
async def create_vault(
    create_vault_request: CreateVaultRequest = Body(...),
    files: List[UploadFile] = File(...),
) -> JSONResponse:
    logging.info(f"Files received: {[f.filename for f in files]}")

    vault = await add_vault(create_vault_request, VaultRepository())

    try:
        documents = await asyncio.gather(
            *[add_document(file, vault.id, DocumentRepository()) for file in files]
        )
    except UnsupportedFileType as e:
        await VaultRepository().delete(vault.id)
        raise HTTPException(status_code=406, detail=e.message)

    request_body = jsonable_encoder(
        RequestToGraphKBService(
            vault_id=vault.id,
            documents=[
                Document(document_id=doc.id, text=doc.text) for doc in documents
            ],
        )
    )
    await send_upload_request(request_body)

    # Return the created vault representation
    return jsonable_encoder(vault)


@documents_router.delete("/delete_vault", status_code=status.HTTP_204_NO_CONTENT)
async def delete_vault(
    vault_id: UUID = Body(...),
    vault_repository: VaultRepository = Depends(vault_exists),
) -> None:
    await vault_repository.delete(vault_id)
    await send_delete_request(body=jsonable_encoder(vault_id))


@documents_router.post("/get_vault_documents", status_code=status.HTTP_200_OK)
async def get_vault_documents(
    vault_id: UUID = Body(...),
    vault_repository: VaultRepository = Depends(vault_exists),
) -> JSONResponse:
    documents = await vault_repository.get_vault_documents(vault_id)
    return jsonable_encoder(documents)


@documents_router.post("/get_users_vaults", status_code=status.HTTP_200_OK)
async def get_users_vaults(user_id: UUID = Body(...)) -> JSONResponse:
    vault_repository = VaultRepository()

    vaults = await vault_repository.get_users_vaults(user_id)

    return jsonable_encoder(vaults)
