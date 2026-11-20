"""Tests for the embedder. They use the fake embedder, so they run offline."""

import pytest

from app.agent.embeddings import EMBEDDING_DIM, EmbeddingError, FakeEmbedder, _check


def cosine(a, b):
    # the fake vectors have length 1, so the dot product is the cosine similarity
    return sum(x * y for x, y in zip(a, b))


def test_vectors_have_the_size_the_database_expects():
    assert len(FakeEmbedder().embed_query("my phone is broken")) == EMBEDDING_DIM


def test_same_text_gives_the_same_vector():
    embedder = FakeEmbedder()

    assert embedder.embed_query("late order") == embedder.embed_query("late order")


def test_documents_and_queries_use_the_same_space():
    embedder = FakeEmbedder()

    assert embedder.embed_documents(["late order"])[0] == embedder.embed_query("late order")


def test_texts_sharing_words_are_closer_than_unrelated_texts():
    embedder = FakeEmbedder()
    query = embedder.embed_query("report a damaged phone")
    close = embedder.embed_query("damaged phone report window")
    far = embedder.embed_query("refund money bank account")

    assert cosine(query, close) > cosine(query, far)


def test_wrong_sized_vector_is_rejected():
    with pytest.raises(EmbeddingError):
        _check([0.1, 0.2])


def test_empty_text_gives_a_zero_vector_not_a_crash():
    assert FakeEmbedder().embed_query("") == [0.0] * EMBEDDING_DIM
