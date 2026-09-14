"""Build Chroma index for one role from data/<role>/*.pdf, *.txt, and *.md"""

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from config import DATA_DIR, ROLES
from rag.chunking import chunk_document
from rag.client import embed_texts
from rag.extract import SUPPORTED_SUFFIXES, load_document
from rag.store import upsert


def _load_docs(role_dir: Path) -> list:
    docs = []
    for path in sorted(role_dir.glob("*")):
        if path.suffix.lower() not in SUPPORTED_SUFFIXES:
            continue
        doc = load_document(path)
        if doc.blocks:
            docs.append(doc)
    return docs


def ingest_role(role: str) -> int:
    role_dir = DATA_DIR / role
    if not role_dir.is_dir():
        raise SystemExit(f"Missing folder: {role_dir}")

    docs = _load_docs(role_dir)
    if not docs:
        raise SystemExit(f"No supported files in {role_dir} ({', '.join(sorted(SUPPORTED_SUFFIXES))})")

    ids, documents, metadatas = [], [], []
    for doc in docs:
        for i, chunk in enumerate(chunk_document(doc)):
            doc_id = f"{role}_{doc.filename}_{i}"
            ids.append(doc_id)
            documents.append(chunk["text"])
            metadatas.append(
                {
                    "role": role,
                    "source": doc.filename,
                    "section": chunk["section"],
                    "page": int(chunk["page"]),
                    "chunk": i,
                }
            )

    embeddings = embed_texts(documents)
    upsert(role, ids, documents, embeddings, metadatas)
    return len(documents)


def main():
    parser = argparse.ArgumentParser(description="Ingest role documents into Chroma")
    parser.add_argument("--role", choices=ROLES, help="Ingest one role only")
    args = parser.parse_args()

    roles = [args.role] if args.role else list(ROLES)
    for role in roles:
        n = ingest_role(role)
        print(f"{role}: indexed {n} chunks")


if __name__ == "__main__":
    main()
