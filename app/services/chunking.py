import re

from app.schemas import ReviewInput


TOPIC_KEYWORDS: dict[str, tuple[str, ...]] = {
    "memory_leak": ("メモリリーク", "leak", "free", "解放", "valgrind"),
    "norm": ("norm", "Norm", "ノーム", "規約"),
    "edge_case": ("edge", "境界", "空文字", "NULL", "異常系", "例外"),
    "signal": ("signal", "シグナル", "Ctrl-C", "Ctrl-D", "Ctrl-\\"),
    "pipe": ("pipe", "パイプ", "fd", "file descriptor", "dup2"),
    "parsing": ("parse", "parser", "quote", "クォート", "展開", "heredoc"),
    "algorithm": ("計算量", "アルゴリズム", "ソート", "探索", "最適化"),
    "testing": ("テスト", "ケース", "確認", "網羅", "再現"),
}


def split_review_text(text: str) -> list[str]:
    normalized = re.sub(r"\r\n?", "\n", text).strip()
    if not normalized:
        return []
    paragraphs = [p.strip() for p in re.split(r"\n{2,}", normalized) if p.strip()]
    chunks: list[str] = []
    for paragraph in paragraphs:
        sentences = [s.strip() for s in re.split(r"(?<=[。.!?？])\s*", paragraph) if s.strip()]
        if not sentences:
            continue
        buffer: list[str] = []
        for sentence in sentences:
            buffer.append(sentence)
            if len("".join(buffer)) >= 160:
                chunks.append(" ".join(buffer))
                buffer = []
        if buffer:
            chunks.append(" ".join(buffer))
    return chunks or [normalized]


def topic_label_for(text: str) -> str:
    lowered = text.lower()
    for label, keywords in TOPIC_KEYWORDS.items():
        if any(keyword.lower() in lowered for keyword in keywords):
            return label
    return "general"


def chunk_review(review: ReviewInput) -> list[dict]:
    chunks = []
    for index, text in enumerate(split_review_text(review.raw_text)):
        chunks.append(
            {
                "chunk_text": text,
                "chunk_index": index,
                "topic_label": topic_label_for(text),
                "evaluation_axis": None,
                "language": review.language,
                "token_count": len(text),
            }
        )
    return chunks
