from langchain_core.documents import Document
import weaviate
import weaviate.classes as wvc
from weaviate.config import AdditionalConfig, Timeout
from weaviate.util import generate_uuid5

from backend.config import get_settings


def connect():
    settings = get_settings()
    return weaviate.connect_to_custom(
        http_host=settings.weaviate_http_host,
        http_port=settings.weaviate_http_port,
        http_secure=settings.weaviate_http_secure,
        grpc_host=settings.weaviate_grpc_host,
        grpc_port=settings.weaviate_grpc_port,
        grpc_secure=settings.weaviate_grpc_secure,
        additional_config=AdditionalConfig(
            timeout=Timeout(init=30, query=60, insert=120)
        ),
    )


def ensure_collection(client) -> None:
    settings = get_settings()
    if client.collections.exists(settings.weaviate_collection):
        return
    client.collections.create(
        name=settings.weaviate_collection,
        vector_config=wvc.config.Configure.Vectors.self_provided(),
        properties=[
            wvc.config.Property(name="text", data_type=wvc.config.DataType.TEXT),
            wvc.config.Property(
                name="collection_id", data_type=wvc.config.DataType.TEXT
            ),
            wvc.config.Property(name="document_id", data_type=wvc.config.DataType.TEXT),
            wvc.config.Property(name="filename", data_type=wvc.config.DataType.TEXT),
            wvc.config.Property(name="page", data_type=wvc.config.DataType.INT),
            wvc.config.Property(name="chunk_index", data_type=wvc.config.DataType.INT),
            wvc.config.Property(name="start_index", data_type=wvc.config.DataType.INT),
        ],
    )


def store_chunks(
    *,
    chunks: list[Document],
    vectors: list[list[float]],
    document_id: str,
    collection_id: str,
    filename: str,
) -> int:
    if len(chunks) != len(vectors):
        raise ValueError("Every chunk must have one embedding vector")

    settings = get_settings()
    with connect() as client:
        ensure_collection(client)
        collection = client.collections.use(settings.weaviate_collection)
        with collection.batch.dynamic() as batch:
            for index, (chunk, vector) in enumerate(zip(chunks, vectors)):
                batch.add_object(
                    uuid=generate_uuid5(f"{document_id}:{index}"),
                    properties={
                        "text": chunk.page_content,
                        "collection_id": collection_id,
                        "document_id": document_id,
                        "filename": filename,
                        "page": int(chunk.metadata.get("page", 0)),
                        "chunk_index": index,
                        "start_index": int(chunk.metadata.get("start_index", 0)),
                    },
                    vector=vector,
                )
        failures = collection.batch.failed_objects
        if failures:
            raise RuntimeError(f"Weaviate rejected {len(failures)} chunk(s)")
    return len(chunks)


def search_chunks(
    *,
    vector: list[float],
    collection_id: str,
    ready_document_ids: set[str],
    limit: int,
) -> list[Document]:
    """Search a collection and return citation-ready LangChain documents."""
    if not ready_document_ids:
        return []

    settings = get_settings()
    with connect() as client:
        if not client.collections.exists(settings.weaviate_collection):
            return []
        collection = client.collections.use(settings.weaviate_collection)
        response = collection.query.near_vector(
            near_vector=vector,
            filters=wvc.query.Filter.by_property("collection_id").equal(collection_id),
            limit=max(limit * 3, limit),
            return_metadata=wvc.query.MetadataQuery(distance=True),
        )

    documents: list[Document] = []
    for item in response.objects:
        properties = item.properties
        document_id = str(properties.get("document_id", ""))
        if document_id not in ready_document_ids:
            continue
        distance = item.metadata.distance
        if distance is not None and distance > settings.retrieval_max_distance:
            continue
        documents.append(
            Document(
                page_content=str(properties.get("text", "")),
                metadata={
                    "source_type": "pdf",
                    "document_id": document_id,
                    "filename": str(properties.get("filename", "document.pdf")),
                    "page": int(properties.get("page", 0)),
                    "chunk_index": int(properties.get("chunk_index", 0)),
                    "distance": distance,
                },
            )
        )
        if len(documents) == limit:
            break
    return documents
