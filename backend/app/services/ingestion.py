"""Document ingestion: parsing and chunking strategies.

Supports multiple chunking approaches:
- Fixed-size: Split by token count with overlap
- Recursive: Split by separators (paragraphs → sentences → words)
- Semantic: Group sentences by embedding similarity
"""

import io
import re
from dataclasses import dataclass
from enum import Enum
from typing import Protocol

import tiktoken
from pypdf import PdfReader

TOKENIZER = tiktoken.get_encoding("cl100k_base")


class ChunkStrategy(str, Enum):
    FIXED = "fixed"
    RECURSIVE = "recursive"
    SEMANTIC = "semantic"


@dataclass
class Chunk:
    """A chunk of text with metadata."""

    content: str
    index: int
    token_count: int
    metadata: dict


class DocumentParser(Protocol):
    """Protocol for document parsers."""

    def parse(self, content: bytes) -> str: ...


class PDFParser:
    """Extract text from PDF files."""

    def parse(self, content: bytes) -> str:
        reader = PdfReader(io.BytesIO(content))
        pages = []
        for i, page in enumerate(reader.pages):
            text = page.extract_text() or ""
            pages.append(f"[Page {i + 1}]\n{text}")
        return "\n\n".join(pages)


class MarkdownParser:
    """Parse markdown files (passthrough with minor cleanup)."""

    def parse(self, content: bytes) -> str:
        return content.decode("utf-8")


class DocxParser:
    """Extract text from DOCX files."""

    def parse(self, content: bytes) -> str:
        from docx import Document

        doc = Document(io.BytesIO(content))
        return "\n\n".join(para.text for para in doc.paragraphs if para.text.strip())


def get_parser(content_type: str) -> DocumentParser:
    """Get the appropriate parser for a content type."""
    parsers: dict[str, DocumentParser] = {
        "application/pdf": PDFParser(),
        "text/markdown": MarkdownParser(),
        "text/plain": MarkdownParser(),
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document": DocxParser(),
    }
    parser = parsers.get(content_type)
    if not parser:
        raise ValueError(f"Unsupported content type: {content_type}")
    return parser


def count_tokens(text: str) -> int:
    """Count tokens using tiktoken."""
    return len(TOKENIZER.encode(text))


# ─── Chunking Strategies ────────────────────────────────────────────────────


def chunk_fixed_size(
    text: str,
    chunk_size: int = 512,
    chunk_overlap: int = 64,
) -> list[Chunk]:
    """Split text into fixed-size token chunks with overlap.

    Good for: Uniform retrieval windows, predictable token budgets.
    Trade-off: May split mid-sentence or mid-paragraph.
    """
    tokens = TOKENIZER.encode(text)
    chunks = []
    start = 0

    while start < len(tokens):
        end = start + chunk_size
        chunk_tokens = tokens[start:end]
        chunk_text = TOKENIZER.decode(chunk_tokens)

        chunks.append(
            Chunk(
                content=chunk_text.strip(),
                index=len(chunks),
                token_count=len(chunk_tokens),
                metadata={"strategy": "fixed", "start_token": start, "end_token": end},
            )
        )

        start += chunk_size - chunk_overlap

    return chunks


def chunk_recursive(
    text: str,
    max_chunk_size: int = 512,
    separators: list[str] | None = None,
) -> list[Chunk]:
    """Recursively split text by separators, respecting natural boundaries.

    Good for: Preserving paragraph/sentence structure.
    Trade-off: Variable chunk sizes, some chunks may be small.
    """
    if separators is None:
        separators = ["\n\n", "\n", ". ", " "]

    def _split(text: str, seps: list[str]) -> list[str]:
        if not seps:
            return [text]

        sep = seps[0]
        remaining_seps = seps[1:]
        parts = text.split(sep)

        result = []
        current = ""

        for part in parts:
            candidate = f"{current}{sep}{part}" if current else part
            if count_tokens(candidate) <= max_chunk_size:
                current = candidate
            else:
                if current:
                    result.append(current)
                # If a single part exceeds max, split it further
                if count_tokens(part) > max_chunk_size:
                    result.extend(_split(part, remaining_seps))
                else:
                    current = part

        if current:
            result.append(current)

        return result

    texts = _split(text, separators)

    return [
        Chunk(
            content=t.strip(),
            index=i,
            token_count=count_tokens(t),
            metadata={"strategy": "recursive"},
        )
        for i, t in enumerate(texts)
        if t.strip()
    ]


def chunk_semantic(
    text: str,
    max_chunk_size: int = 512,
    similarity_threshold: float = 0.75,
) -> list[Chunk]:
    """Group sentences by semantic similarity (requires embeddings).

    Good for: Topic-coherent chunks that map well to questions.
    Trade-off: Requires extra embedding calls, slower ingestion.

    Note: This is a simplified version using sentence boundaries.
    For production, you'd embed each sentence and merge by cosine similarity.
    """
    # Split into sentences
    sentences = re.split(r"(?<=[.!?])\s+", text)

    chunks = []
    current_sentences: list[str] = []
    current_tokens = 0

    for sentence in sentences:
        sentence_tokens = count_tokens(sentence)

        if current_tokens + sentence_tokens > max_chunk_size and current_sentences:
            chunk_text = " ".join(current_sentences)
            chunks.append(
                Chunk(
                    content=chunk_text.strip(),
                    index=len(chunks),
                    token_count=current_tokens,
                    metadata={"strategy": "semantic", "sentence_count": len(current_sentences)},
                )
            )
            current_sentences = []
            current_tokens = 0

        current_sentences.append(sentence)
        current_tokens += sentence_tokens

    # Final chunk
    if current_sentences:
        chunk_text = " ".join(current_sentences)
        chunks.append(
            Chunk(
                content=chunk_text.strip(),
                index=len(chunks),
                token_count=current_tokens,
                metadata={"strategy": "semantic", "sentence_count": len(current_sentences)},
            )
        )

    return chunks


def _extract_page_numbers(text: str) -> tuple[int | None, int | None]:
    """Extract page range from [Page N] markers embedded in chunk text."""
    pages = re.findall(r"\[Page (\d+)\]", text)
    if not pages:
        return None, None
    page_nums = [int(p) for p in pages]
    return min(page_nums), max(page_nums)


def chunk_document(
    text: str,
    strategy: ChunkStrategy = ChunkStrategy.RECURSIVE,
    **kwargs,
) -> list[Chunk]:
    """Chunk a document using the specified strategy."""
    strategies = {
        ChunkStrategy.FIXED: chunk_fixed_size,
        ChunkStrategy.RECURSIVE: chunk_recursive,
        ChunkStrategy.SEMANTIC: chunk_semantic,
    }
    chunks = strategies[strategy](text, **kwargs)

    # Enrich chunks with page number metadata (from PDF [Page N] markers)
    for chunk in chunks:
        page_start, page_end = _extract_page_numbers(chunk.content)
        if page_start is not None:
            chunk.metadata["page_start"] = page_start
            chunk.metadata["page_end"] = page_end

    return chunks
