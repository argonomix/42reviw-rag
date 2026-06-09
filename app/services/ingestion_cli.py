import argparse

from app.core.config import get_settings
from app.db.session import SessionLocal, run_schema_migrations
from app.services.ingestion import ingest_path, reset_data


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Ingest review data into ReviewRAG.")
    parser.add_argument(
        "--path",
        default=None,
        help="Path to a JSON or JSONL review data file. Defaults to SEED_DATA_PATH.",
    )
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Delete existing reviews, chunks, terms, and embeddings before ingestion.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    settings = get_settings()
    path = args.path or settings.seed_data_path

    run_schema_migrations()
    db = SessionLocal()
    try:
        if args.reset:
            reset_data(db)
        reviews, chunks = ingest_path(db, path)
    finally:
        db.close()

    print(f"Ingested {reviews} reviews and {chunks} chunks from {path}.")


if __name__ == "__main__":
    main()
