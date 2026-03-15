from app.api.documents import _infer_passage_strategy


def test_infer_passage_strategy_prefers_natural_units_for_line_corpora():
    text = "\n".join(
        [
            "Line one.",
            "Line two.",
            "Line three.",
            "Line four.",
        ]
    )

    assert _infer_passage_strategy(text) == "natural_units"


def test_infer_passage_strategy_prefers_paragraphs_for_prose():
    text = (
        "This is a prose paragraph with several sentences and more natural wrapping.\n\n"
        "This is another prose paragraph that should stay paragraph-based."
    )

    assert _infer_passage_strategy(text) == "paragraph"


def test_infer_passage_strategy_handles_line_corpus_with_small_footer_gap():
    text = "\n".join([f"ayah {i}" for i in range(1, 11)]) + "\n\nfooter metadata"

    assert _infer_passage_strategy(text) == "natural_units"
