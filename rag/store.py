from __future__ import annotations

import os
import shutil

import chromadb

from config import COLLECTION_PREFIX, INDEX_DIR, ROOT

BUNDLED_INDEX_DIR = ROOT / "index"
_ephemeral_client_instance = None


def _on_cloud() -> bool:
    return os.getenv("STREAMLIT_RUNTIME_ENVIRONMENT") == "cloud" or (ROOT / "app.py").as_posix().startswith("/mount/src/")


def bundled_index_available(role: str) -> bool:
    return (BUNDLED_INDEX_DIR / role / "chroma.sqlite3").is_file()


def _collection_metadata() -> dict:
    return {"hnsw:space": "cosine", "hnsw:sync_threshold": 100000}


def collection_name(role: str) -> str:
    return f"{COLLECTION_PREFIX}{role}"


def _get_ephemeral_client() -> chromadb.EphemeralClient:
    global _ephemeral_client_instance
    if _ephemeral_client_instance is None:
        _ephemeral_client_instance = chromadb.EphemeralClient()
    return _ephemeral_client_instance


def _materialize_bundled_index(role: str) -> bool:
    """Copy committed Chroma files from the repo into writable storage on Cloud."""
    src = BUNDLED_INDEX_DIR / role
    dst = INDEX_DIR / role
    if not src.is_dir():
        return False
    INDEX_DIR.mkdir(parents=True, exist_ok=True)
    if dst.exists():
        shutil.rmtree(dst)
    shutil.copytree(src, dst)
    return True


def _persistent_client(role: str):
    INDEX_DIR.mkdir(parents=True, exist_ok=True)
    return chromadb.PersistentClient(path=str(INDEX_DIR / role))


def get_client(role: str):
    if _on_cloud():
        if bundled_index_available(role):
            _materialize_bundled_index(role)
            return _persistent_client(role)
        return _get_ephemeral_client()
    return _persistent_client(role)


def get_collection(role: str):
    client = get_client(role)
    return client.get_or_create_collection(collection_name(role), metadata=_collection_metadata())


def reset_and_get_collection(role: str):
    """Drop the role index and return a fresh empty collection."""
    if _on_cloud() and not bundled_index_available(role):
        client = _get_ephemeral_client()
        name = collection_name(role)
        try:
            client.delete_collection(name)
        except Exception:
            pass
        return client.create_collection(name, metadata=_collection_metadata())

    role_path = INDEX_DIR / role
    if role_path.exists():
        shutil.rmtree(role_path)
    client = _persistent_client(role)
    return client.create_collection(collection_name(role), metadata=_collection_metadata())


def upsert(role: str, ids: list[str], documents: list[str], embeddings: list[list[float]], metadatas: list[dict]):
    col = reset_and_get_collection(role)
    col.add(ids=ids, documents=documents, embeddings=embeddings, metadatas=metadatas)


def search(role: str, query_embedding: list[float], top_k: int):
    col = get_collection(role)
    if col.count() == 0:
        return {"documents": [[]], "metadatas": [[]], "distances": [[]]}
    return col.query(query_embeddings=[query_embedding], n_results=min(top_k, col.count()))
