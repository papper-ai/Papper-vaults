import asyncio
import logging
import uuid
from typing import List
from uuid import UUID

from Crypto.Cipher import AES
from Crypto.Hash import HMAC, SHA256
from Crypto.Protocol.KDF import PBKDF2
from Crypto.Random import get_random_bytes
from Crypto.Util.Padding import pad
from fastapi import BackgroundTasks, UploadFile
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import HTTPException

from src.config import settings
from src.database.models import Document, Vault
from src.database.postgres_repositories import DocumentRepository, VaultRepository
from src.database.s3_repositories import S3Repository
from src.utils.exceptions import EmptyFile, UnsupportedFileType
from src.utils.readers import read_document
from src.utils.requests import (
    send_add_document_request_to_graph_kb_service,
    send_add_document_request_to_vector_kb_service,
    send_create_request_to_graph_kb_service,
    send_create_request_to_vector_kb_service,
    send_delete_document_request_to_graph_kb_service,
    send_delete_document_request_to_vector_kb_service,
    send_drop_request_to_graph_kb_service,
    send_drop_request_to_vector_kb_service,
)
from src.vaults.schemas import (
    AddDocumentRequestToKBService,
    CreateRequestToKBService,
    CreateVaultRequest,
    DeleteDocumentRequestToKBService,
    DocumentResponse,
    DocumentText,
    DropRequestToKBService,
    VaultPreviewResponse,
    VaultResponse,
    VaultType,
)


async def encrypt_data(data, password):
    # Generate a random salt and initialization vector (IV)
    salt = get_random_bytes(16)
    iv = get_random_bytes(16)

    # Derive a key from the password
    key = PBKDF2(
        password,
        salt,
        dkLen=32,
        count=1000,
        prf=lambda p, s: HMAC.new(p, s, SHA256).digest(),
    )

    # Create cipher object and encrypt the data
    cipher = AES.new(key, AES.MODE_CBC, iv)
    ct_bytes = cipher.encrypt(pad(data, AES.block_size))

    # Combine salt, iv, and ciphertext into a single bytes object
    encrypted_data = salt + iv + ct_bytes

    return encrypted_data


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


async def handle_document(
    file: UploadFile,
    vault_id: UUID,
    document_repository: DocumentRepository,
    s3_repository: S3Repository,
) -> Document:
    id = uuid.uuid4()

    content = await file.read()
    file.file.seek(0)

    text = await read_document(file)

    if text == "":
        raise EmptyFile()

    document = Document(
        id=id,
        name=file.filename,
        text=text,
        vault_id=vault_id,
    )

    await document_repository.add(document)

    encrypted_content = await encrypt_data(
        content, password=settings.encryption_password
    )
    await s3_repository.put(encrypted_content, id)

    return document


async def drop_knowledge_base_background(vault_id: UUID, vault_type: VaultType) -> None:
    delete_request_body = jsonable_encoder(DropRequestToKBService(vault_id=vault_id))

    if vault_type == VaultType.GRAPH:
        await send_drop_request_to_graph_kb_service(body=delete_request_body)
    else:
        await send_drop_request_to_vector_kb_service(body=delete_request_body)


async def delete_document_background(
    vault_id: UUID, vault_type: VaultType, document_id: UUID
) -> None:
    delete_request_body = jsonable_encoder(
        DeleteDocumentRequestToKBService(vault_id=vault_id, document_id=document_id)
    )

    if vault_type == VaultType.GRAPH:
        await send_delete_document_request_to_graph_kb_service(body=delete_request_body)
    else:
        await send_delete_document_request_to_vector_kb_service(
            body=delete_request_body
        )


async def create_knowledge_base(
    vault_id: UUID, documents: List[Document], vault_type: VaultType
) -> None:
    # Make a create request to KB service
    upload_request_body = jsonable_encoder(
        CreateRequestToKBService(
            vault_id=vault_id,
            documents=[
                DocumentText(document_id=doc.id, document_name=doc.name, text=doc.text)
                for doc in documents
            ],
        )
    )

    if vault_type == VaultType.GRAPH:
        await send_create_request_to_graph_kb_service(upload_request_body)
    else:
        await send_create_request_to_vector_kb_service(upload_request_body)


async def add_document_to_knowledge_base(vault_id: UUID, document: Document) -> None:
    # Make an add request to KB service
    upload_request_body = jsonable_encoder(
        AddDocumentRequestToKBService(
            vault_id=vault_id,
            document=DocumentText(
                document_id=document.id, document_name=document.name, text=document.text
            ),
        )
    )

    vault_type = (await VaultRepository().get(vault_id)).type

    if vault_type == VaultType.GRAPH:
        await send_add_document_request_to_graph_kb_service(upload_request_body)
    else:
        await send_add_document_request_to_vector_kb_service(upload_request_body)


async def create_vault(
    create_vault_request: CreateVaultRequest, files: List[UploadFile]
) -> VaultResponse:
    if not files:
        raise HTTPException(status_code=400, detail="No files provided")

    logging.info(f"Files received: {[f.filename for f in files]}")

    vault_repository = VaultRepository()
    vault = await add_vault(create_vault_request, vault_repository)

    documents = await asyncio.gather(
        *[
            handle_document(file, vault.id, DocumentRepository(), S3Repository())
            for file in files
        ],
        return_exceptions=True,
    )

    for result in documents:
        if isinstance(result, BaseException):
            logging.exception("Task exception", exc_info=result)

    # On any UnsupportedFileType, delete the entire vault and raise an HTTPException
    for result in documents:
        if isinstance(result, UnsupportedFileType):
            await vault_repository.delete(vault.id)
            raise HTTPException(status_code=406, detail=result.message)

    if all(isinstance(result, EmptyFile) for result in documents):
        await vault_repository.delete(vault.id)
        raise HTTPException(status_code=406, detail=result.message)

    try:
        await create_knowledge_base(
            vault_id=vault.id,
            documents=[
                document
                for document in documents
                if not (isinstance(document, EmptyFile))
            ],
            vault_type=vault.type,
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


async def add_document(
    vault_id: UUID, file: UploadFile, vault_repository: VaultRepository
) -> None:
    if not file:
        raise HTTPException(status_code=400, detail="File not provided")

    logging.info(f"File received: {file.filename}")

    try:
        document = await handle_document(file, vault_id, DocumentRepository(), S3Repository())
    except UnsupportedFileType as e:
        raise HTTPException(status_code=406, detail=e.message)
    except EmptyFile as e:
        raise HTTPException(status_code=406, detail=e.message)

    try:
        await add_document_to_knowledge_base(vault_id=vault_id, document=document)
    except Exception as e:
        logging.error(e)
        raise HTTPException(
            status_code=500,
            detail=f"Error adding documents to knowledge base {vault_id}",
        )

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


async def delete_vault(
    vault_id: UUID,
    vault_repository: VaultRepository,
    background_tasks: BackgroundTasks,
) -> None:
    vault = await vault_repository.get(vault_id)
    await vault_repository.delete(vault_id)

    background_tasks.add_task(drop_knowledge_base_background, vault_id, vault.type)


async def delete_document(
    vault_id: UUID,
    document_id: UUID,
    vault_repository: VaultRepository,
    background_tasks: BackgroundTasks,
) -> None:
    vault_type = (await vault_repository.get(vault_id)).type

    document_repository = DocumentRepository()
    await document_repository.delete(document_id)

    background_tasks.add_task(
        delete_document_background, vault_id, vault_type, document_id
    )


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
