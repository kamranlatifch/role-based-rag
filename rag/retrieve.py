from config import TOP_K
from rag.client import embed_query
from rag.store import search


def format_source(meta: dict | None) -> str:
    meta = meta or {}
    source = meta.get("source", "unknown")
    section = meta.get("section", "")
    page = meta.get("page")
    label = source
    if section and section != source:
        label = f"{source} — {section}"
    if page:
        label = f"{label} (p.{page})"
    return label


def retrieve(role: str, question: str, top_k: int = TOP_K) -> list[dict]:
    result = search(role, embed_query(question), top_k)
    docs = (result.get("documents") or [[]])[0]
    metas = (result.get("metadatas") or [[]])[0]
    hits = []
    for doc, meta in zip(docs, metas):
        hits.append(
            {
                "text": doc,
                "source": (meta or {}).get("source", "unknown"),
                "section": (meta or {}).get("section", ""),
                "page": (meta or {}).get("page"),
                "label": format_source(meta),
            }
        )
    return hits


def format_context(hits: list[dict]) -> str:
    if not hits:
        return "(no matching passages)"
    parts = []
    for i, hit in enumerate(hits, 1):
        parts.append(f"[{i}] ({hit['label']})\n{hit['text']}")
    return "\n\n".join(parts)
