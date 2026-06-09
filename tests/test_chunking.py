from app.schemas import ReviewInput
from app.services.chunking import chunk_review, topic_label_for


def test_chunking_preserves_language_and_metadata_shape() -> None:
    review = ReviewInput(project_name="minishell", raw_text="fd が閉じられていない。pipe でリークする。")

    chunks = chunk_review(review)

    assert chunks
    assert chunks[0]["language"] == "ja"
    assert chunks[0]["topic_label"] == "pipe"
    assert chunks[0]["chunk_index"] == 0


def test_topic_label_for_memory_leak() -> None:
    assert topic_label_for("ft_split でメモリリークがある") == "memory_leak"
