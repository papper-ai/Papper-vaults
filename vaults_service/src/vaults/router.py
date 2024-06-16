from typing import Annotated, List
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Body, Depends, File, UploadFile, status

from src.database.postgres_repositories import DocumentRepository, VaultRepository
from src.vaults.dependencies import document_exists, vault_exists
from src.vaults.schemas import (
    CreateVaultRequest,
    DocumentResponse,
    VaultPreviewResponse,
    VaultResponse,
)
from src.vaults.utils import (
    add_document,
    create_vault,
    delete_document,
    delete_vault,
    get_document_by_id,
    get_users_vaults,
    get_vault_by_id,
    get_vault_documents,
)

vaults_router = APIRouter(tags=["Vaults & Documents"])


@vaults_router.post(
    "/create_vault", status_code=status.HTTP_201_CREATED, response_model=VaultResponse
)
async def create_vault_route(
    create_vault_request: Annotated[CreateVaultRequest, Body()],
    files: Annotated[List[UploadFile], File(...)],
):
    return await create_vault(create_vault_request, files)


@vaults_router.post(
    "/add_document", status_code=status.HTTP_201_CREATED, response_model=VaultResponse
)
async def add_document_route(
    vault_id: Annotated[UUID, Body(embed=True)],
    vault_repository: Annotated[VaultRepository, Depends(vault_exists)],
    file: UploadFile,
):
    return await add_document(vault_id, file, vault_repository)


@vaults_router.delete("/delete_vault", status_code=status.HTTP_204_NO_CONTENT)
async def delete_vault_route(
    vault_id: Annotated[UUID, Body(embed=True)],
    vault_repository: Annotated[VaultRepository, Depends(vault_exists)],
    background_tasks: BackgroundTasks,
) -> None:
    await delete_vault(vault_id, vault_repository, background_tasks)


@vaults_router.delete("/delete_document", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document_route(
    vault_id: Annotated[UUID, Body()],
    document_id: Annotated[UUID, Body()],
    vault_repository: Annotated[VaultRepository, Depends(vault_exists)],
    background_tasks: BackgroundTasks,
) -> None:
    await delete_document(vault_id, document_id, vault_repository, background_tasks)


@vaults_router.patch("/rename_vault", status_code=status.HTTP_200_OK)
async def rename_vault(
    vault_id: Annotated[UUID, Body()],
    name: Annotated[str, Body()],
    vault_repository: Annotated[VaultRepository, Depends(vault_exists)],
) -> None:
    await vault_repository.rename(id=vault_id, name=name)


@vaults_router.post(
    "/get_vault_documents",
    status_code=status.HTTP_200_OK,
    response_model=List[DocumentResponse],
)
async def get_vault_documents_route(
    vault_id: Annotated[UUID, Body(embed=True)],
    vault_repository: Annotated[VaultRepository, Depends(vault_exists)],
):
    return await get_vault_documents(vault_id, vault_repository)


@vaults_router.post(
    "/get_users_vaults",
    status_code=status.HTTP_200_OK,
    response_model=List[VaultPreviewResponse],
)
async def get_users_vaults_route(user_id: Annotated[UUID, Body(embed=True)]):
    return await get_users_vaults(user_id)


@vaults_router.post(
    "/get_vault_by_id",
    status_code=status.HTTP_200_OK,
    response_model=VaultResponse,
)
async def get_vault_by_id_route(
    vault_id: Annotated[UUID, Body(embed=True)],
    vault_repository: Annotated[VaultRepository, Depends(vault_exists)],
):
    return await get_vault_by_id(vault_id, vault_repository)


@vaults_router.post(
    "/get_document_by_id",
    status_code=status.HTTP_200_OK,
    response_model=DocumentResponse,
)
async def get_document_by_id_route(
    document_id: Annotated[UUID, Body(embed=True)],
    document_repository: Annotated[DocumentRepository, Depends(document_exists)],
):
    return await get_document_by_id(document_id, document_repository)
