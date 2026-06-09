from app.rag.keyword import bm25_term_score, term_frequencies, tokenize_for_search


def test_tokenize_for_search_handles_code_terms_and_japanese_ngrams() -> None:
    tokens = tokenize_for_search("Pipe FD leak。パイプ処理とCtrl-C")

    assert "pipe" in tokens
    assert "fd" in tokens
    assert "leak" in tokens
    assert "ctrl" in tokens
    assert "c" in tokens
    assert "パイ" in tokens
    assert "パイプ" in tokens


def test_tokenize_for_search_handles_blank_input() -> None:
    assert tokenize_for_search("  。!? ") == []


def test_term_frequencies_counts_repeated_terms() -> None:
    frequencies = term_frequencies("fd fd FD")

    assert frequencies["fd"] == 3


def test_bm25_score_increases_with_exact_term_frequency() -> None:
    weak = bm25_term_score(
        term_frequency=1,
        document_frequency=1,
        total_documents=3,
        document_length=10,
        average_document_length=10,
    )
    strong = bm25_term_score(
        term_frequency=3,
        document_frequency=1,
        total_documents=3,
        document_length=10,
        average_document_length=10,
    )

    assert strong > weak > 0
