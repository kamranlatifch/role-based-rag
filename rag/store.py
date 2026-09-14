import shutil

import chromadb

from config import COLLECTION_PREFIX, INDEX_DIR


def collection_name(role: str) -> str:
    return f"{COLLECTION_PREFIX}{role}"


def get_client(role: str):
    INDEX_DIR.mkdir(parents=True, exist_ok=True)
    return chromadb.PersistentClient(path=str(INDEX_DIR / role))


def _collection_metadata() -> dict:
    return {"hnsw:space": "cosine", "hnsw:sync_threshold": 100000}


def get_collection(role: str):
    client = get_client(role)
    return client.get_or_create_collection(collection_name(role), metadata=_collection_metadata())


def reset_and_get_collection(role: str):
    """Drop the role's on-disk index and return a fresh empty collection."""
    role_path = INDEX_DIR / role
    if role_path.exists():
        shutil.rmtree(role_path)
    client = get_client(role)
    return client.get_or_create_collection(collection_name(role), metadata=_collection_metadata())


def upsert(role: str, ids: list[str], documents: list[str], embeddings: list[list[float]], metadatas: list[dict]):
    col = reset_and_get_collection(role)
    col.add(ids=ids, documents=documents, embeddings=embeddings, metadatas=metadatas)


def search(role: str, query_embedding: list[float], top_k: int):
    col = get_collection(role)
    if col.count() == 0:
        return {"documents": [[]], "metadatas": [[]], "distances": [[]]}
    return col.query(query_embeddings=[query_embedding], n_results=min(top_k, col.count()))
