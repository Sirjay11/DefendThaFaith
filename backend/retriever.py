import json
import re
from typing import Dict, Any, List
from backend.database import get_conn, compute_semantic_signature, cosine_similarity, STOPWORDS
from backend.reference_parser import parse_references_detailed


def tokenize_keywords(text: str) -> List[str]:
    tokens = re.findall(r"[a-z0-9']+", text.lower())
    return [t for t in tokens if len(t) > 2 and t not in STOPWORDS]


def hybrid_retrieve(
    question: str,
    research_mode: str = "exegetical_archive",
    parent_context: str = "",
    top_k_chunks: int = 5,
    top_k_scriptures: int = 5,
) -> Dict[str, Any]:
    """
    Executes Hybrid Retrieval with Conversational Context Resolution and the Three Early Adjustments:
      1. Fast-Path Reference Resolution (Bible, Quran, Hadith, and Tafsir exact lookup)
      2. Argument-Aware Role Separation & Mandatory Objection-to-Rebuttal Pairing
      3. Lexical + Semantic Vector Scoring with Conversational Context & Mode Weighting
    """
    conn = get_conn()
    cur = conn.cursor()

    combined_query = f"{question} {parent_context}".strip() if parent_context else question
    parsed_detail = parse_references_detailed(combined_query)
    parsed_refs = set(parsed_detail["all"])

    q_tokens = set(tokenize_keywords(question))
    ctx_tokens = set(tokenize_keywords(parent_context)) if parent_context else set()
    q_vec = compute_semantic_signature(combined_query)

    rows = cur.execute(
        """
        SELECT
            c.id AS chunk_id,
            c.source_id,
            c.chunk_index,
            c.section_title,
            c.discourse_type,
            c.paired_chunk_id,
            c.text_content,
            c.scripture_refs_json,
            c.embedding_json,
            s.title AS source_title,
            s.url AS source_url,
            s.author,
            s.source_type,
            s.media_type,
            s.video_timestamp,
            s.topic,
            s.permission_mode
        FROM document_chunks c
        JOIN sources s ON c.source_id = s.id
        WHERE s.status = 'verified'
        """
    ).fetchall()

    chunk_by_id: Dict[str, Dict[str, Any]] = {}
    scored_chunks: List[Dict[str, Any]] = []
    fast_path_chunk_ids: List[str] = []

    for r in rows:
        chunk_refs = set(json.loads(r["scripture_refs_json"] or "[]"))
        chunk_vec = json.loads(r["embedding_json"] or "[]")
        doc_text = f"{r['source_title']} {r['section_title']} {r['text_content']} {r['topic']}"
        doc_tokens = set(tokenize_keywords(doc_text))

        matched_refs = sorted(parsed_refs.intersection(chunk_refs))
        ref_overlap = len(matched_refs)
        ref_score = min(1.0, ref_overlap * 0.70)

        if q_tokens:
            overlap_count = len(q_tokens.intersection(doc_tokens))
            lex_score = overlap_count / max(1, min(len(q_tokens), 8))
        else:
            lex_score = 0.0

        ctx_score = 0.0
        if ctx_tokens:
            ctx_overlap = len(ctx_tokens.intersection(doc_tokens))
            ctx_score = (ctx_overlap / max(1, min(len(ctx_tokens), 8))) * 0.35

        sem_score = max(0.0, cosine_similarity(q_vec, chunk_vec))

        total_score = (ref_score * 0.55) + (lex_score * 0.55) + (sem_score * 0.35) + ctx_score

        if research_mode == "exegetical_archive" and r["discourse_type"] == "author_argument":
            total_score *= 1.12
        elif research_mode == "comparative_analysis" and r["discourse_type"] == "quoted_objection":
            total_score *= 1.15

        item = {
            "chunk_id": r["chunk_id"],
            "source_id": r["source_id"],
            "chunk_index": r["chunk_index"],
            "section_title": r["section_title"],
            "discourse_type": r["discourse_type"],
            "paired_chunk_id": r["paired_chunk_id"],
            "text_content": r["text_content"],
            "scripture_refs": sorted(chunk_refs),
            "fast_path_matched_refs": matched_refs,
            "source_title": r["source_title"],
            "source_url": r["source_url"],
            "author": r["author"],
            "media_type": r["media_type"] or "article",
            "video_timestamp": r["video_timestamp"],
            "topic": r["topic"],
            "permission_mode": r["permission_mode"],
            "score": round(min(0.99, total_score), 3),
            "paired_rebuttal_enforced": False,
        }
        chunk_by_id[r["chunk_id"]] = item

        if matched_refs:
            fast_path_chunk_ids.append(r["chunk_id"])

        if total_score > 0.14:
            scored_chunks.append(item)

    scored_chunks.sort(key=lambda x: x["score"], reverse=True)
    top_chunks = scored_chunks[:top_k_chunks]
    existing_chunk_ids = {c["chunk_id"] for c in top_chunks}

    paired_rebuttals_added = 0
    for c in list(top_chunks):
        if c["discourse_type"] == "quoted_objection" and c.get("paired_chunk_id"):
            rebuttal_id = c["paired_chunk_id"]
            if rebuttal_id in chunk_by_id and rebuttal_id not in existing_chunk_ids:
                rebuttal_chunk = dict(chunk_by_id[rebuttal_id])
                rebuttal_chunk["paired_rebuttal_enforced"] = True
                rebuttal_chunk["score"] = max(rebuttal_chunk["score"], round(c["score"] * 0.98, 3))
                top_chunks.insert(0, rebuttal_chunk)
                existing_chunk_ids.add(rebuttal_id)
                paired_rebuttals_added += 1
            elif rebuttal_id in existing_chunk_ids:
                for tc in top_chunks:
                    if tc["chunk_id"] == rebuttal_id:
                        tc["paired_rebuttal_enforced"] = True

    top_source_ids = {c["source_id"] for c in top_chunks[:2]}
    for c in scored_chunks:
        if c["source_id"] in top_source_ids and c["chunk_id"] not in existing_chunk_ids:
            if len(top_chunks) < top_k_chunks + 2:
                top_chunks.append(c)
                existing_chunk_ids.add(c["chunk_id"])

    all_target_refs = set(parsed_refs)
    for c in top_chunks[:3]:
        all_target_refs.update(c["scripture_refs"])

    s_rows = cur.execute("SELECT * FROM scripture_passages").fetchall()
    scored_scriptures: List[Dict[str, Any]] = []
    fast_path_scripture_refs: List[str] = []

    for sr in s_rows:
        c_refs = set(json.loads(sr["canonical_refs_json"] or "[]"))
        tags = json.loads(sr["topic_tags_json"] or "[]")
        s_text = f"{sr['reference']} {sr['text_content']} {sr['original_language_note']} {' '.join(tags)}"
        s_tokens = set(tokenize_keywords(s_text))

        direct_q_hit = bool(parsed_refs.intersection(c_refs) or sr["reference"] in parsed_refs)
        expanded_hit = bool(all_target_refs.intersection(c_refs) or sr["reference"] in all_target_refs)

        if direct_q_hit:
            fast_path_scripture_refs.append(sr["reference"])

        ref_hit = 1.0 if direct_q_hit else (0.85 if expanded_hit else 0.0)
        lex_hit = (len(q_tokens.intersection(s_tokens)) / max(1, min(len(q_tokens), 7))) if q_tokens else 0.0
        s_score = (ref_hit * 0.75) + (lex_hit * 0.45)

        if research_mode == "primary_sources":
            s_score *= 1.2

        if s_score > 0.15:
            scored_scriptures.append(
                {
                    "id": sr["id"],
                    "corpus": sr["corpus"],
                    "reference": sr["reference"],
                    "translation": sr["translation"],
                    "text_content": sr["text_content"],
                    "original_language_note": sr["original_language_note"],
                    "topic_tags": tags,
                    "fast_path_direct_hit": direct_q_hit,
                    "score": round(min(0.99, s_score), 3),
                }
            )

    scored_scriptures.sort(key=lambda x: x["score"], reverse=True)
    top_scriptures = scored_scriptures[:top_k_scriptures]

    conn.close()

    best_chunk_score = top_chunks[0]["score"] if top_chunks else 0.0
    best_scripture_score = top_scriptures[0]["score"] if top_scriptures else 0.0
    confidence = round(max(best_chunk_score, best_scripture_score * 0.85), 3)

    abstain = confidence < 0.24 or len(top_chunks) == 0

    return {
        "question": question,
        "parent_context": parent_context,
        "research_mode": research_mode,
        "parsed_scripture_refs": sorted(parsed_refs),
        "fast_path_telemetry": {
            "detected_references": parsed_detail,
            "direct_scripture_hits": fast_path_scripture_refs,
            "direct_chunk_hits": fast_path_chunk_ids,
            "paired_rebuttals_enforced": paired_rebuttals_added,
        },
        "confidence_score": confidence,
        "abstain": abstain,
        "chunks": top_chunks,
        "scriptures": top_scriptures,
    }
