"""
Shared test fixtures:
- in-memory SQLite DB
- 20-passage test corpus
- FakeLLMClient
"""

from __future__ import annotations

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.interfaces import (
    AnswerDraftDomain,
    CitationDomain,
    ClaimDomain,
    EvidenceBundleDomain,
    VerificationReportDomain,
)
from app.db.session import Base


# ---------------------------------------------------------------------------
# In-memory SQLite session
# ---------------------------------------------------------------------------

@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


# ---------------------------------------------------------------------------
# Test corpus
# ---------------------------------------------------------------------------

SAMPLE_CORPUS_LINES = [
    "In the beginning, there was light.",
    "The sun rose over the mountains.",
    "Rain fell on the fields.",
    "The rivers flowed to the sea.",
    "All living things depend on water.",
    "Patience is a virtue found in stillness.",
    "The wise speak little and observe much.",
    "Hardship strengthens the spirit.",
    "Those who seek will find.",
    "Gratitude opens the heart.",
    "Prayer is the conversation of the soul.",
    "Fasting teaches restraint and compassion.",
    "Charity purifies wealth.",
    "Justice requires courage.",
    "Peace comes from within.",
    "Knowledge is a lamp in darkness.",
    "Time is the most precious gift.",
    "The stars guide those who are lost.",
    "Mercy triumphs over judgment.",
    "All things return to their origin.",
]

SAMPLE_CORPUS = "\n".join(SAMPLE_CORPUS_LINES)


# ---------------------------------------------------------------------------
# Fake LLM client
# ---------------------------------------------------------------------------

class FakeLLMClient:
    """Returns hardcoded valid JSON responses for testing."""

    ANSWER_RESPONSE = """{
  "final_answer": "The text describes patience as a virtue.",
  "claims": [
    {
      "claim_id": "c1",
      "statement": "Patience is a virtue.",
      "supporting_passage_ids": ["PLACEHOLDER"],
      "support_type": "direct"
    }
  ],
  "supporting_citations": [
    {
      "passage_id": "PLACEHOLDER",
      "quote": "Patience is a virtue found in stillness."
    }
  ],
  "objections_raised": [],
  "confidence_notes": "Direct textual support found."
}"""

    VERIFIER_RESPONSE = """{
  "status": "pass",
  "supported_claims": ["c1"],
  "unsupported_claims": [],
  "citation_issues": [],
  "notes": "All claims verified."
}"""

    def __init__(self, passage_id: str = "test-passage"):
        self.passage_id = passage_id

    def chat(self, system: str, user: str, temperature: float = 0.0) -> str:
        if "verification" in system.lower() or "verify" in system.lower():
            return self.VERIFIER_RESPONSE.replace("PLACEHOLDER", self.passage_id)
        return self.ANSWER_RESPONSE.replace("PLACEHOLDER", self.passage_id)
