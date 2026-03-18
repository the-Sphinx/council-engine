from __future__ import annotations

from sqlalchemy import text

from app.db.session import Base


def ensure_database_ready(engine) -> None:
    import app.db.models  # noqa: F401

    Base.metadata.create_all(bind=engine)
    _ensure_query_debug_artifact_columns(engine)


def _ensure_query_debug_artifact_columns(engine) -> None:
    if engine.dialect.name != "sqlite":
        return

    with engine.begin() as conn:
        tables = {
            row[0]
            for row in conn.execute(
                text("SELECT name FROM sqlite_master WHERE type='table'")
            )
        }
        if "query_debug_artifacts" not in tables:
            return

        columns = {
            row[1]
            for row in conn.execute(text("PRAGMA table_info(query_debug_artifacts)"))
        }
        missing = {
            "original_query": "TEXT",
            "lexical_query": "TEXT",
            "expanded_terms_json": "TEXT NOT NULL DEFAULT '[]'",
            "retrieval_config_json": "TEXT NOT NULL DEFAULT '{}'",
        }
        for column_name, column_ddl in missing.items():
            if column_name not in columns:
                conn.execute(
                    text(
                        "ALTER TABLE query_debug_artifacts "
                        f"ADD COLUMN {column_name} {column_ddl}"
                    )
                )
