import math
import re
from collections import Counter


ASCII_TOKEN_RE = re.compile(r"[a-zA-Z0-9_]+")
JAPANESE_RE = re.compile(r"[\u3040-\u30ff\u3400-\u9fff]+")


def tokenize_for_search(text: str) -> list[str]:
    normalized = text.lower()
    tokens: list[str] = []
    tokens.extend(match.group(0) for match in ASCII_TOKEN_RE.finditer(normalized))
    for match in JAPANESE_RE.finditer(normalized):
        compact = match.group(0)
        if len(compact) == 1:
            tokens.append(compact)
            continue
        tokens.extend(compact[index : index + 2] for index in range(len(compact) - 1))
        if len(compact) >= 3:
            tokens.extend(compact[index : index + 3] for index in range(len(compact) - 2))
    return tokens


def term_frequencies(text: str) -> Counter[str]:
    return Counter(tokenize_for_search(text))


def bm25_term_score(
    term_frequency: int,
    document_frequency: int,
    total_documents: int,
    document_length: int,
    average_document_length: float,
    *,
    k1: float = 1.5,
    b: float = 0.75,
) -> float:
    if (
        term_frequency <= 0
        or document_frequency <= 0
        or total_documents <= 0
        or document_length <= 0
    ):
        return 0.0
    average_document_length = average_document_length or 1.0
    idf = math.log(1.0 + (total_documents - document_frequency + 0.5) / (document_frequency + 0.5))
    denominator = term_frequency + k1 * (
        1.0 - b + b * (document_length / average_document_length)
    )
    return idf * ((term_frequency * (k1 + 1.0)) / denominator)
