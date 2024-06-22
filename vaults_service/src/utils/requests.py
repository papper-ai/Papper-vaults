import aiohttp

from src.vaults.schemas import (
    AddDocumentRequestToKBService,
    CreateRequestToKBService,
    DeleteDocumentRequestToKBService,
    DropRequestToKBService,
)

from src.config import settings

async def send_create_request_to_graph_kb_service(
    body: CreateRequestToKBService,
) -> dict:
    async with aiohttp.ClientSession() as session:
        async with session.post(
            f"{settings.graph_service_url}/create", json=body
        ) as response:
            return await response.json()


async def send_add_document_request_to_graph_kb_service(
    body: AddDocumentRequestToKBService,
) -> dict:
    async with aiohttp.ClientSession() as session:
        async with session.post(
            f"{settings.graph_service_url}/add_document", json=body
        ) as response:
            return await response.json()


async def send_drop_request_to_graph_kb_service(
    body: DropRequestToKBService,
) -> dict:
    async with aiohttp.ClientSession() as session:
        async with session.delete(
            f"{settings.graph_service_url}/drop", json=body
        ) as response:
            return await response.json()


async def send_delete_document_request_to_graph_kb_service(
    body: DeleteDocumentRequestToKBService,
) -> dict:
    async with aiohttp.ClientSession() as session:
        async with session.delete(
            f"{settings.graph_service_url}/delete_document", json=body
        ) as response:
            return await response.json()


async def send_create_request_to_vector_kb_service(
    body: CreateRequestToKBService,
) -> dict:
    async with aiohttp.ClientSession() as session:
        async with session.post(
                f"{settings.vector_service_url}/create", json=body
        ) as response:
            return await response.json()


async def send_add_document_request_to_vector_kb_service(
    body: AddDocumentRequestToKBService,
) -> dict:
    async with aiohttp.ClientSession() as session:
        async with session.post(
                f"{settings.vector_service_url}/add_document", json=body
        ) as response:
            return await response.json()


async def send_drop_request_to_vector_kb_service(
    body: DropRequestToKBService,
) -> dict:
    async with aiohttp.ClientSession() as session:
        async with session.delete(
                f"{settings.vector_service_url}/drop", json=body
        ) as response:
            return await response.json()


async def send_delete_document_request_to_vector_kb_service(
    body: DeleteDocumentRequestToKBService,
) -> dict:
    async with aiohttp.ClientSession() as session:
        async with session.delete(
                f"{settings.vector_service_url}/delete_document", json=body
        ) as response:
            return await response.json()
