from app.retrieval.dense import HashingEmbedder


def test_hashing_embedder_is_deterministic():
    embedder = HashingEmbedder(dims=32)

    first = embedder.embed_query("patience is a virtue")
    second = embedder.embed_query("patience is a virtue")

    assert first == second


def test_hashing_embedder_returns_unit_norm_for_non_empty_text():
    embedder = HashingEmbedder(dims=32)

    vector = embedder.embed_query("knowledge is a lamp in darkness")
    norm = sum(value * value for value in vector) ** 0.5

    assert round(norm, 6) == 1.0
