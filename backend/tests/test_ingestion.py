"""Tests for document ingestion and chunking strategies."""

import pytest

from app.services.ingestion import (
    ChunkStrategy,
    chunk_document,
    chunk_fixed_size,
    chunk_recursive,
    chunk_semantic,
    count_tokens,
)


SAMPLE_TEXT = """
Introduction to Machine Learning

Machine learning is a subset of artificial intelligence that provides systems the ability to learn and improve from experience. It focuses on the development of computer programs that can access data and use it to learn for themselves.

The process of learning begins with observations or data, such as examples, direct experience, or instruction. The goal is to allow computers to learn automatically without human intervention or assistance.

Types of Machine Learning

There are three main types of machine learning:

1. Supervised Learning: The algorithm is trained on labeled data. It learns a function that maps inputs to outputs based on example input-output pairs.

2. Unsupervised Learning: The algorithm is given data without explicit labels. It must find structure in the data on its own, such as clustering similar data points.

3. Reinforcement Learning: The algorithm learns through interaction with an environment. It receives rewards or penalties for actions and adjusts its strategy accordingly.

Applications

Machine learning has numerous real-world applications including spam detection, recommendation systems, medical diagnosis, speech recognition, and autonomous vehicles.
"""


class TestTokenCounting:
    def test_count_tokens_basic(self):
        assert count_tokens("hello world") > 0

    def test_count_tokens_empty(self):
        assert count_tokens("") == 0

    def test_count_tokens_consistency(self):
        tokens = count_tokens("The quick brown fox")
        assert count_tokens("The quick brown fox") == tokens


class TestFixedSizeChunking:
    def test_basic_chunking(self):
        chunks = chunk_fixed_size(SAMPLE_TEXT, chunk_size=100, chunk_overlap=20)
        assert len(chunks) > 1
        assert all(c.token_count <= 100 for c in chunks)

    def test_chunk_indices_sequential(self):
        chunks = chunk_fixed_size(SAMPLE_TEXT, chunk_size=50)
        indices = [c.index for c in chunks]
        assert indices == list(range(len(chunks)))

    def test_overlap_creates_more_chunks(self):
        no_overlap = chunk_fixed_size(SAMPLE_TEXT, chunk_size=100, chunk_overlap=0)
        with_overlap = chunk_fixed_size(SAMPLE_TEXT, chunk_size=100, chunk_overlap=50)
        assert len(with_overlap) > len(no_overlap)

    def test_metadata_includes_strategy(self):
        chunks = chunk_fixed_size(SAMPLE_TEXT, chunk_size=100)
        assert all(c.metadata["strategy"] == "fixed" for c in chunks)


class TestRecursiveChunking:
    def test_basic_chunking(self):
        chunks = chunk_recursive(SAMPLE_TEXT, max_chunk_size=100)
        assert len(chunks) > 1

    def test_respects_max_size(self):
        chunks = chunk_recursive(SAMPLE_TEXT, max_chunk_size=100)
        # Most chunks should be within bounds (some may slightly exceed due to splitting)
        oversized = [c for c in chunks if c.token_count > 120]
        assert len(oversized) == 0

    def test_preserves_content(self):
        chunks = chunk_recursive(SAMPLE_TEXT, max_chunk_size=200)
        combined = " ".join(c.content for c in chunks)
        # Key content should be preserved
        assert "Machine learning" in combined
        assert "Supervised Learning" in combined

    def test_no_empty_chunks(self):
        chunks = chunk_recursive(SAMPLE_TEXT, max_chunk_size=100)
        assert all(len(c.content.strip()) > 0 for c in chunks)


class TestSemanticChunking:
    def test_basic_chunking(self):
        chunks = chunk_semantic(SAMPLE_TEXT, max_chunk_size=150)
        assert len(chunks) > 1

    def test_metadata_includes_sentence_count(self):
        chunks = chunk_semantic(SAMPLE_TEXT, max_chunk_size=150)
        assert all("sentence_count" in c.metadata for c in chunks)

    def test_respects_token_budget(self):
        chunks = chunk_semantic(SAMPLE_TEXT, max_chunk_size=100)
        # Chunks should stay within budget
        assert all(c.token_count <= 100 for c in chunks)


class TestChunkDocument:
    def test_fixed_strategy(self):
        chunks = chunk_document(SAMPLE_TEXT, strategy=ChunkStrategy.FIXED)
        assert len(chunks) > 0
        assert all(c.metadata["strategy"] == "fixed" for c in chunks)

    def test_recursive_strategy(self):
        chunks = chunk_document(SAMPLE_TEXT, strategy=ChunkStrategy.RECURSIVE)
        assert len(chunks) > 0
        assert all(c.metadata["strategy"] == "recursive" for c in chunks)

    def test_semantic_strategy(self):
        chunks = chunk_document(SAMPLE_TEXT, strategy=ChunkStrategy.SEMANTIC)
        assert len(chunks) > 0
        assert all(c.metadata["strategy"] == "semantic" for c in chunks)
