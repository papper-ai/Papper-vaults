import asyncio
import logging
import uuid
from typing import List
from uuid import UUID

from fastapi import BackgroundTasks, UploadFile
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import HTTPException

from src.database.models import Document, Vault
from src.database.repositories import DocumentRepository, VaultRepository
from src.utils.exceptions import UnsupportedFileType
from src.utils.readers import read_document
from src.utils.requests import (
    send_delete_request_to_graph_kb_service,
    send_delete_request_to_vector_kb_service,
    send_upload_request_to_graph_kb_service,
    send_upload_request_to_vector_kb_service,
)
from src.vaults.schemas import (
    CreateRequestToKBService,
    CreateVaultRequest,
    DeleteRequestToKBService,
    DocumentResponse,
    DocumentText,
    VaultPreviewResponse,
    VaultResponse,
    VaultType,
)


async def add_vault(
    create_vault_request: CreateVaultRequest, vault_repository: VaultRepository
) -> Vault:
    id = uuid.uuid4()  # Generate random unique identifier

    vault = Vault(
        id=id,
        name=create_vault_request.vault_name,
        type=create_vault_request.vault_type,
        user_id=create_vault_request.user_id,
    )

    await vault_repository.add(vault)

    return vault


async def add_document(
    file: UploadFile, vault_id: uuid.UUID, document_repository: DocumentRepository
) -> Document:
    id = uuid.uuid4()  # Generate random unique identifier

    text = await read_document(file)

    document = Document(
        id=id,
        name=file.filename,
        text=text,
        vault_id=vault_id,
    )

    await document_repository.add(document)

    return document


async def delete_documents_background(
    vault_id: uuid.UUID, vault_type: VaultType
) -> None:
    delete_request_body = jsonable_encoder(DeleteRequestToKBService(vault_id=vault_id))

    if vault_type == VaultType.GRAPH:
        await send_delete_request_to_graph_kb_service(body=delete_request_body)
    else:
        await send_delete_request_to_vector_kb_service(body=delete_request_body)


async def upload_documents_to_kb(
    vault_id: uuid.UUID, documents: List[Document], vault_type: VaultType
) -> None:
    # Make an upload request to graph KB service
    upload_request_body = jsonable_encoder(
        CreateRequestToKBService(
            vault_id=vault_id,
            documents=[
                DocumentText(document_id=doc.id, text=doc.text) for doc in documents
            ],
        )
    )

    if vault_type == VaultType.GRAPH:
        await send_upload_request_to_graph_kb_service(upload_request_body)
    else:
        await send_upload_request_to_vector_kb_service(upload_request_body)


async def create_vault(
    create_vault_request: CreateVaultRequest, files: List[UploadFile]
) -> VaultResponse:
    if not files:
        raise HTTPException(status_code=400, detail="No files provided")

    logging.info(f"Files received: {[f.filename for f in files]}")

    vault_repository = VaultRepository()
    vault = await add_vault(create_vault_request, vault_repository)

    documents = await asyncio.gather(
        *[add_document(file, vault.id, DocumentRepository()) for file in files],
        return_exceptions=True,
    )
    # On any UnsupportedFileType, delete the entire vault and raise an HTTPException
    for result in documents:
        if isinstance(result, UnsupportedFileType):
            await vault_repository.delete(vault.id)
            raise HTTPException(status_code=406, detail=result.message)

    try:
        await upload_documents_to_kb(
            vault_id=vault.id, documents=documents, vault_type=vault.type
        )
    except Exception as e:
        logging.error(e)
        await vault_repository.delete(vault.id)
        raise HTTPException(
            status_code=500,
            detail=f"Error uploading documents to {vault.type} knowledge base",
        )

    vault_response = VaultResponse(
        id=vault.id,
        name=vault.name,
        type=vault.type,
        created_at=vault.created_at,
        user_id=vault.user_id,
        documents=[
            DocumentResponse.model_validate(document)
            for document in await vault_repository.get_vault_documents(vault.id)
        ],
    )

    return vault_response


async def delete_vault(
    vault_id: UUID,
    vault_repository: VaultRepository,
    background_tasks: BackgroundTasks,
) -> None:
    vault = await vault_repository.get(vault_id)
    await vault_repository.delete(vault_id)

    background_tasks.add_task(delete_documents_background, vault_id, vault.type)


async def get_vault_documents(
    vault_id: UUID,
    vault_repository: VaultRepository,
) -> List[DocumentResponse]:
    documents = await vault_repository.get_vault_documents(vault_id)

    return [DocumentResponse.model_validate(document) for document in documents]


async def get_users_vaults(user_id: UUID) -> List[VaultPreviewResponse]:
    vault_repository = VaultRepository()

    vaults = await vault_repository.get_users_vaults(user_id)

    return [VaultPreviewResponse.model_validate(vault) for vault in vaults]


async def get_vault_by_id(
    vault_id: UUID, vault_repository: VaultRepository
) -> VaultResponse:
    vault = await vault_repository.get(vault_id)

    vault_response = VaultResponse(
        id=vault.id,
        name=vault.name,
        type=vault.type,
        created_at=vault.created_at,
        user_id=vault.user_id,
        documents=[
            DocumentResponse.model_validate(document)
            for document in await vault_repository.get_vault_documents(vault.id)
        ],
    )

    return vault_response


async def get_document_by_id(
    document_id: UUID,
    document_repository: DocumentRepository,
) -> DocumentResponse:
    document = await document_repository.get(document_id)
    return DocumentResponse.model_validate(document)
