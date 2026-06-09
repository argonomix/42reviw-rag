from app.services.normalization import normalize_record, stable_hash


def test_stable_hash_is_deterministic() -> None:
    assert stable_hash("student-login") == stable_hash("student-login")
    assert stable_hash("student-login").startswith("hash_")


def test_normalize_record_defaults_to_42tokyo_ja() -> None:
    record = normalize_record(
        {
            "project": "Minishell",
            "reviewer_id": "reviewer-login",
            "reviewee_id": "reviewee-login",
            "feedback": "quote の edge case が不足している。",
        }
    )

    assert record.project_name == "minishell"
    assert record.campus == "42tokyo"
    assert record.language == "ja"
    assert record.raw_text.startswith("quote")
    assert record.reviewer_id_hash.startswith("hash_")
