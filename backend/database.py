import sqlite3
import json
import hashlib
import math
import re
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from backend.config import DATABASE_PATH

STOPWORDS = {
    "the", "and", "for", "that", "this", "with", "from", "what", "how", "does",
    "did", "are", "was", "were", "have", "has", "had", "not", "but", "you",
    "his", "her", "they", "their", "about", "into", "who", "whom", "whose",
    "why", "when", "where", "which", "can", "could", "would", "should", "will",
    "sam", "shamoun", "shamoun's", "position", "detailed", "respond", "response",
    "argument", "teach", "say", "says", "said", "call", "calls", "asked", "century"
}


def compute_semantic_signature(text: str, dim: int = 128) -> List[float]:
    """
    Computes a lightweight deterministic feature-hashed L2-normalized embedding
    over unigrams, theological stems, and character n-grams so semantic similarity
    works offline and online with zero latency, and upgrades cleanly to dense pgvector.
    """
    vec = [0.0] * dim
    tokens = re.findall(r"[a-z0-9']+", text.lower())
    filtered = [t for t in tokens if len(t) > 2 and t not in STOPWORDS]
    if not filtered:
        return vec

    features: List[tuple[str, float]] = []
    for idx, tok in enumerate(filtered):
        features.append((f"u:{tok}", 1.5))
        if len(tok) >= 5:
            features.append((f"stem:{tok[:5]}", 1.0))
        if idx + 1 < len(filtered):
            features.append((f"bi:{tok}_{filtered[idx+1]}", 1.2))

    for feat, weight in features:
        h = int(hashlib.md5(feat.encode("utf-8")).hexdigest(), 16)
        bucket = h % dim
        sign = 1.0 if ((h >> 8) & 1) == 0 else -1.0
        vec[bucket] += sign * weight

    norm = math.sqrt(sum(x * x for x in vec))
    if norm > 0:
        vec = [round(x / norm, 5) for x in vec]
    return vec


def cosine_similarity(v1: List[float], v2: List[float]) -> float:
    if not v1 or not v2 or len(v1) != len(v2):
        return 0.0
    return sum(a * b for a, b in zip(v1, v2))


def get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DATABASE_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def init_db() -> None:
    conn = get_conn()
    cur = conn.cursor()

    cur.executescript(
        """
        CREATE TABLE IF NOT EXISTS sources (
            id TEXT PRIMARY KEY,
            url TEXT NOT NULL UNIQUE,
            canonical_url TEXT NOT NULL,
            title TEXT NOT NULL,
            author TEXT NOT NULL,
            source_type TEXT NOT NULL, -- shamoun_article | shamoun_video | bible | quran | hadith
            media_type TEXT NOT NULL DEFAULT 'article', -- article | video
            video_timestamp TEXT,
            topic TEXT NOT NULL,
            permission_mode TEXT NOT NULL DEFAULT 'snippet_link_only', -- full_text | snippet_link_only | metadata_only
            published_date TEXT,
            content_hash TEXT,
            status TEXT NOT NULL DEFAULT 'verified',
            last_crawled_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS document_chunks (
            id TEXT PRIMARY KEY,
            source_id TEXT NOT NULL,
            chunk_index INTEGER NOT NULL,
            section_title TEXT NOT NULL,
            discourse_type TEXT NOT NULL, -- author_argument | quoted_objection | primary_scripture
            paired_chunk_id TEXT, -- Links quoted_objection directly to its author_argument rebuttal
            text_content TEXT NOT NULL,
            scripture_refs_json TEXT NOT NULL,
            embedding_json TEXT NOT NULL,
            FOREIGN KEY (source_id) REFERENCES sources(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS scripture_passages (
            id TEXT PRIMARY KEY,
            corpus TEXT NOT NULL, -- Bible | Quran | Hadith
            reference TEXT NOT NULL UNIQUE,
            canonical_refs_json TEXT NOT NULL,
            translation TEXT NOT NULL,
            text_content TEXT NOT NULL,
            original_language_note TEXT,
            topic_tags_json TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS gold_questions (
            id TEXT PRIMARY KEY,
            question TEXT NOT NULL,
            category TEXT NOT NULL,
            expected_source_ids_json TEXT NOT NULL,
            expected_scripture_refs_json TEXT NOT NULL,
            should_abstain INTEGER NOT NULL DEFAULT 0,
            last_status TEXT DEFAULT 'untested',
            last_score REAL DEFAULT 0.0,
            last_tested_at TEXT
        );

        CREATE TABLE IF NOT EXISTS hermes_jobs (
            id TEXT PRIMARY KEY,
            job_type TEXT NOT NULL, -- discover | normalize | qa_benchmark | gap_analysis
            title TEXT NOT NULL,
            status TEXT NOT NULL, -- completed | needs_approval | approved | rejected
            summary TEXT NOT NULL,
            metrics_json TEXT NOT NULL,
            pipeline_steps_json TEXT, -- Deterministic stage-by-stage execution trace
            proposed_action_json TEXT,
            created_at TEXT NOT NULL,
            reviewed_at TEXT
        );

        CREATE TABLE IF NOT EXISTS query_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            question TEXT NOT NULL,
            research_mode TEXT NOT NULL,
            confidence_score REAL NOT NULL,
            abstained INTEGER NOT NULL DEFAULT 0,
            cited_source_ids_json TEXT NOT NULL,
            user_feedback TEXT,
            created_at TEXT NOT NULL
        );
        """
    )

    # Safe migrations if upgrading existing tables
    src_cols = {r["name"] for r in cur.execute("PRAGMA table_info(sources)").fetchall()}
    if "media_type" not in src_cols:
        cur.execute("ALTER TABLE sources ADD COLUMN media_type TEXT NOT NULL DEFAULT 'article';")
    if "video_timestamp" not in src_cols:
        cur.execute("ALTER TABLE sources ADD COLUMN video_timestamp TEXT;")

    chunk_cols = {r["name"] for r in cur.execute("PRAGMA table_info(document_chunks)").fetchall()}
    if "paired_chunk_id" not in chunk_cols:
        cur.execute("ALTER TABLE document_chunks ADD COLUMN paired_chunk_id TEXT;")

    job_cols = {r["name"] for r in cur.execute("PRAGMA table_info(hermes_jobs)").fetchall()}
    if "pipeline_steps_json" not in job_cols:
        cur.execute("ALTER TABLE hermes_jobs ADD COLUMN pipeline_steps_json TEXT;")

    conn.commit()
    conn.close()


def now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
