"""Load .pdf, .md, and .txt policy files into page-level text blocks."""

import re
from dataclasses import dataclass, field
from pathlib import Path

import pymupdf

SUPPORTED_SUFFIXES = {".pdf", ".txt", ".md"}


@dataclass
class TextBlock:
    page: int
    text: str
    links: list[str] = field(default_factory=list)


@dataclass
class LoadedDocument:
    filename: str
    blocks: list[TextBlock]


def _normalize(text: str) -> str:
    text = text.replace("\u00a0", " ").replace("\ufeff", "")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _relocate_form_link(text: str) -> str:
    match = re.search(r"^Form link: .+$", text, re.MULTILINE)
    if not match or "How to claim" not in text:
        return text
    form_line = match.group(0)
    text = text.replace(form_line, "", 1).strip()
    return text.replace("How to claim", f"How to claim\n{form_line}", 1)


def _inline_links(text: str, links: list[str]) -> str:
    if not links:
        return text

    form_links = [url for url in links if "forms.google" in url or "/forms/" in url]

    if form_links and re.search(r"Form link:\s*Click here", text, re.IGNORECASE):
        text = re.sub(
            r"Form link:\s*Click here",
            f"Form link: {form_links[0]}",
            text,
            flags=re.IGNORECASE,
        )

    missing = [url for url in links if url and url not in text]
    if missing:
        text = f"{text}\n\n[LINKS] {' | '.join(missing)}"
    return text


def load_pdf(path: Path) -> LoadedDocument:
    doc = pymupdf.open(path)
    blocks: list[TextBlock] = []
    try:
        for page_num, page in enumerate(doc, start=1):
            text = _normalize(page.get_text())
            links = [link["uri"] for link in page.get_links() if link.get("uri")]
            text = _inline_links(text, links)
            text = _relocate_form_link(text)
            if text:
                blocks.append(TextBlock(page=page_num, text=text, links=links))
    finally:
        doc.close()
    return LoadedDocument(filename=path.name, blocks=blocks)


def load_text_file(path: Path) -> LoadedDocument:
    text = _normalize(path.read_text(encoding="utf-8"))
    if not text:
        return LoadedDocument(filename=path.name, blocks=[])
    return LoadedDocument(filename=path.name, blocks=[TextBlock(page=1, text=text, links=[])])


def load_document(path: Path) -> LoadedDocument:
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        return load_pdf(path)
    if suffix in {".txt", ".md"}:
        return load_text_file(path)
    raise ValueError(f"Unsupported file type: {path.suffix}")
