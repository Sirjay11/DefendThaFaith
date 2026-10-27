import json
import urllib.request
import urllib.error
import asyncio
from typing import Dict, Any, List
from backend.config import HERMES_SETTINGS, OPENROUTER_API_KEY
from backend.database import get_conn, now_iso


TOPIC_REBUTTAL_TREES: Dict[str, List[Dict[str, str]]] = {
    "src_archive_jesus_prays": [
        {
            "id": "reb_subordinate",
            "question": "Does this mean Jesus is subordinate to the Father?",
            "label": "Objection 1 · Ontological vs. Functional Subordination",
        },
        {
            "id": "reb_john14_28",
            "question": "Why does Jesus say that the Father is greater than He is in John 14:28?",
            "label": "Objection 2 · 'The Father Is Greater Than I' (John 14:28)",
        },
        {
            "id": "reb_mark13_32",
            "question": "Why does Jesus say that He does not know the hour in Mark 13:32?",
            "label": "Objection 3 · Omniscience & the Incarnation (Mark 13:32)",
        },
        {
            "id": "reb_jesus_die",
            "question": "If Jesus is God, how can He die on the cross?",
            "label": "Objection 4 · Divine Immortality & the Crucifixion",
        },
    ],
    "src_archive_islamic_dilemma": [
        {
            "id": "reb_tahrif",
            "question": "Didn't the Quran only affirm the original Injil given to Jesus before it was corrupted?",
            "label": "Objection 1 · Claim of Textual Corruption (Taḥrīf) vs. Surah 5:47",
        },
        {
            "id": "reb_surah2_79",
            "question": "Doesn't Surah 2:79 say 'Woe to those who write the book with their hands'?",
            "label": "Objection 2 · Examining Surah 2:75–79 in Context",
        },
        {
            "id": "reb_quran_trinity",
            "question": "How does the Quran's description of the Trinity in Surah 5:116 compare with the New Testament?",
            "label": "Objection 3 · Surah 5:116 & the Triad Misconception",
        },
    ],
    "src_archive_phil2": [
        {
            "id": "reb_phil2_exalted",
            "question": "If God highly exalted Jesus in Philippians 2:9, doesn't that prove He wasn't God Almighty already?",
            "label": "Objection 1 · Pre-Incarnate Glory (Phil 2:6) vs. Exaltation (Phil 2:9)",
        },
        {
            "id": "reb_john17_3_from_phil2",
            "question": "How does Philippians 2:10–11 harmonize with John 17:3 where the Father is called 'the only true God'?",
            "label": "Objection 2 · Harmonizing Isaiah 45:23, Philippians 2:11, and John 17:3",
        },
        {
            "id": "reb_heb1_from_phil2",
            "question": "Where else does the New Testament apply Old Testament Yahweh passages directly to Jesus?",
            "label": "Follow-Up 3 · Hebrews 1:8–12 & Psalm 102:25–27",
        },
    ],
    "src_archive_quran_word": [
        {
            "id": "reb_kun_command",
            "question": "Doesn't 'Word from Allah' in Surah 3:45 and 4:171 just mean Allah's creative command 'Be!' (Kun) as in Surah 3:59?",
            "label": "Objection 1 · The 'Kun' (Be!) Reduction vs. Personal Title",
        },
        {
            "id": "reb_bukhari_spirit",
            "question": "What does Sahih al-Bukhari 3448 mean by calling Jesus both Allah's Word (Kalimatuhu) and a Spirit from Him?",
            "label": "Objection 2 · Hadith Evidence in Sahih al-Bukhari 3448",
        },
        {
            "id": "reb_john1_logos",
            "question": "How does John 1:1–14 explain what it means for Jesus to be the eternal Word (Logos) made flesh?",
            "label": "Follow-Up 3 · The Johannine Prologue (John 1:1–14)",
        },
    ],
}


def build_rebuttal_tree_for_source(primary_source_id: str, current_question: str) -> List[Dict[str, str]]:
    branches = TOPIC_REBUTTAL_TREES.get(primary_source_id)
    if not branches:
        branches = [
            {
                "id": "reb_gen_1",
                "question": "If Jesus is God, why does He pray to the Father?",
                "label": "Objection 1 · Prayer of the Incarnate Son & John 14:28",
            },
            {
                "id": "reb_gen_2",
                "question": "Why does Jesus call the Father 'the only true God' in John 17:3?",
                "label": "Objection 2 · 'The Only True God' in John 17:3–5",
            },
            {
                "id": "reb_gen_3",
                "question": "Did Jesus deny being God when He asked 'Why do you call me good?' in Mark 10:18?",
                "label": "Objection 3 · 'Why Do You Call Me Good?' (Mark 10:17–18)",
            },
            {
                "id": "reb_gen_4",
                "question": "Does Philippians 2:10–11 identify Jesus as Yahweh?",
                "label": "Objection 4 · Every Knee Bowing to Jesus (Isaiah 45:23 & Phil 2:10–11)",
            },
        ]
    return [b for b in branches if b["question"].lower() != current_question.lower()][:4]


def verify_response_citations(response_data: Dict[str, Any]) -> Dict[str, Any]:
    retrieved_map = {c["chunk_id"]: c for c in response_data.get("retrieved_chunks", [])}
    verified_args = []
    role_violations_blocked = 0

    for arg in response_data.get("archive_arguments", []):
        cid = arg.get("chunk_id")
        db_chunk = retrieved_map.get(cid)
        if not db_chunk:
            continue
        if db_chunk["discourse_type"] == "quoted_objection":
            role_violations_blocked += 1
            continue
        verified_args.append(arg)

    response_data["archive_arguments"] = verified_args
    response_data["citation_verification"] = {
        "verified_chunk_citations": len(verified_args),
        "verified_primary_passages": len(response_data.get("primary_evidence", [])),
        "role_separation_verified": True,
        "role_violations_blocked": role_violations_blocked,
    }
    return response_data


def build_deterministic_grounded_response(retrieval: Dict[str, Any]) -> Dict[str, Any]:
    chunks = retrieval["chunks"]
    scriptures = retrieval["scriptures"]

    author_chunks = [c for c in chunks if c["discourse_type"] == "author_argument"]
    objection_chunks = [c for c in chunks if c["discourse_type"] == "quoted_objection"]
    primary_chunk = author_chunks[0] if author_chunks else chunks[0]

    classification = primary_chunk.get("topic", "Christology · Biblical & Historical Exegesis")

    # A. Direct Answer
    direct_answer = primary_chunk["text_content"]

    # B. Evidence & Sources
    archive_arguments = []
    for ac in (author_chunks or [primary_chunk])[:3]:
        refs_str = ", ".join(ac.get("scripture_refs", [])[:4]) or "the surrounding passage"
        archive_arguments.append(
            {
                "section_title": ac["section_title"],
                "summary": ac["text_content"],
                "verbatim_quote": ac["text_content"],
                "how_it_supports": (
                    f"Connects {refs_str} directly to the grammatical and historical context in "
                    f"the archive commentary ('{ac['source_title']}'), distinguishing the primary "
                    f"exegetical argument from opposing claims."
                ),
                "source_id": ac["source_id"],
                "chunk_id": ac["chunk_id"],
                "source_title": ac["source_title"],
                "source_url": ac["source_url"],
                "author": ac.get("author", "Exegetical Research Archive"),
                "media_type": ac.get("media_type", "article"),
                "video_timestamp": ac.get("video_timestamp"),
                "permission_mode": ac["permission_mode"],
                "fast_path_matched_refs": ac.get("fast_path_matched_refs", []),
                "paired_rebuttal_enforced": ac.get("paired_rebuttal_enforced", False),
            }
        )

    # C. Logical Reasoning Sequence
    logical_reasoning = []
    if scriptures:
        sp0 = scriptures[0]
        logical_reasoning.append(
            {
                "step_type": "Established Textual Fact",
                "statement": f"{sp0['reference']} ({sp0['corpus']}) states: \"{sp0['text_content']}\"",
            }
        )
        if sp0.get("original_language_note"):
            logical_reasoning.append(
                {
                    "step_type": "Linguistic & Contextual Evidence",
                    "statement": sp0["original_language_note"],
                }
            )
    logical_reasoning.append(
        {
            "step_type": "Documented Exegetical Argument",
            "statement": primary_chunk["text_content"],
        }
    )
    if len(author_chunks) > 1:
        logical_reasoning.append(
            {
                "step_type": "Theological Conclusion",
                "statement": author_chunks[1]["text_content"],
            }
        )

    # D & E. Counterargument & Exegetical Response
    if objection_chunks:
        obj = objection_chunks[0]
        paired_id = obj.get("paired_chunk_id")
        paired_rebuttal_chunk = next(
            (c for c in author_chunks if c["chunk_id"] == paired_id),
            author_chunks[-1] if len(author_chunks) > 1 else primary_chunk,
        )
        counterargument = {
            "objection_title": obj["section_title"],
            "objection_claim": obj["text_content"],
            "exegetical_rebuttal": paired_rebuttal_chunk["text_content"],
            "rebuttal_chunk_id": paired_rebuttal_chunk["chunk_id"],
            "source_title": obj["source_title"],
            "source_url": obj["source_url"],
            "chunk_id": obj["chunk_id"],
        }
    else:
        counterargument = {
            "objection_title": "Competing Unitarian / Skeptical Interpretation",
            "objection_claim": (
                "A knowledgeable critic may argue that high Christological titles or functional submission "
                "passages reflect prophetic agency rather than ontological equality with God."
            ),
            "exegetical_rebuttal": primary_chunk["text_content"],
            "rebuttal_chunk_id": primary_chunk["chunk_id"],
            "source_title": primary_chunk["source_title"],
            "source_url": primary_chunk["source_url"],
            "chunk_id": primary_chunk["chunk_id"],
        }

    # F. Conversation-Ready Response
    top_refs = ", ".join(s["reference"] for s in scriptures[:2]) or "Scripture"
    conversation_ready = (
        f"When someone asks this, a clear way to respond is: \"Look at {top_refs} in context. "
        f"{primary_chunk['text_content']} If we read the whole passage rather than isolating a single "
        f"verse, the text consistently affirms both Christ's true humanity as a servant and His eternal "
        f"divine identity alongside the Father.\""
    )

    # G. Rebuttal Tree & Further Research
    rebuttal_tree = build_rebuttal_tree_for_source(primary_chunk["source_id"], retrieval["question"])
    explore_further = [b["question"] for b in rebuttal_tree]

    resp = {
        "abstained": False,
        "question": retrieval["question"],
        "parent_context": retrieval.get("parent_context", ""),
        "research_mode": retrieval["research_mode"],
        "classification": classification,
        "confidence_score": retrieval["confidence_score"],
        "fast_path_telemetry": retrieval.get("fast_path_telemetry", {}),
        "model_used": "archive-synthesis-engine",
        "short_answer": direct_answer,
        "direct_answer": direct_answer,
        "primary_evidence": scriptures,
        "archive_arguments": archive_arguments,
        "logical_reasoning": logical_reasoning,
        "counterargument": counterargument,
        "conversation_ready_response": conversation_ready,
        "rebuttal_tree": rebuttal_tree,
        "explore_further": explore_further,
        "retrieved_chunks": chunks,
    }
    return verify_response_citations(resp)


def _sync_call_openrouter(
    question: str,
    research_mode: str,
    base_response: Dict[str, Any],
) -> Dict[str, Any]:
    if not OPENROUTER_API_KEY:
        return base_response

    models_to_try = [HERMES_SETTINGS["default_model"]] + HERMES_SETTINGS["fallback_models"]
    evidence_digest = "\n\n".join(
        [
            f"[{c['chunk_id']} | ROLE={c['discourse_type']} | {c['source_title']}]\n{c['text_content']}"
            for c in base_response["retrieved_chunks"][:4]
        ]
    )
    scripture_digest = "\n".join(
        [f"- {s['reference']} ({s['corpus']}): {s['text_content']}" for s in base_response["primary_evidence"]]
    )

    system_prompt = (
        "You are a rigorous, source-grounded Christian apologetics research writer. "
        "Do NOT mention any specific modern apologist's name, do NOT mention AI, and NEVER confuse a "
        "chunk marked ROLE=quoted_objection with the archive's position (ROLE=author_argument). "
        "Using ONLY the provided retrieved source chunks and scripture passages, return a JSON object with keys:\n"
        '1. "direct_answer": A clear, scholarly 3-4 sentence direct answer addressing the core theological issue.\n'
        '2. "conversation_ready_response": A natural, respectful 2-3 sentence explanation the user can speak aloud in a real conversation.\n'
        "Respond with valid JSON only."
    )
    user_prompt = (
        f"Question: {question}\nResearch Mode: {research_mode}\n\n"
        f"Retrieved Primary Passages:\n{scripture_digest}\n\n"
        f"Retrieved Chunks:\n{evidence_digest}"
    )

    for model_name in models_to_try:
        try:
            payload = json.dumps(
                {
                    "model": model_name,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    "temperature": 0.15,
                }
            ).encode("utf-8")
            req = urllib.request.Request(
                f"{HERMES_SETTINGS['base_url']}/chat/completions",
                data=payload,
                headers={
                    "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                    "Content-Type": "application/json",
                    "HTTP-Referer": "http://localhost:8000",
                    "X-Title": "Defend the Faith Research Archive",
                },
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=14) as resp:
                if resp.status == 200:
                    data = json.loads(resp.read().decode("utf-8"))
                    content = (
                        data.get("choices", [{}])[0]
                        .get("message", {})
                        .get("content", "")
                        .strip()
                    )
                    if content:
                        if "```" in content:
                            parts = content.split("```")
                            for p in parts:
                                p_clean = p.removeprefix("json").strip()
                                if p_clean.startswith("{") and p_clean.endswith("}"):
                                    content = p_clean
                                    break
                        parsed = json.loads(content)
                        if parsed.get("direct_answer"):
                            base_response["direct_answer"] = parsed["direct_answer"]
                            base_response["short_answer"] = parsed["direct_answer"]
                        elif parsed.get("short_answer"):
                            base_response["direct_answer"] = parsed["short_answer"]
                            base_response["short_answer"] = parsed["short_answer"]
                        if parsed.get("conversation_ready_response"):
                            base_response["conversation_ready_response"] = parsed["conversation_ready_response"]
                        base_response["model_used"] = "verified-source-synthesis"
                        return verify_response_citations(base_response)
        except Exception:
            continue

    return verify_response_citations(base_response)


def generate_research_answer_sync(
    question: str,
    research_mode: str = "exegetical_archive",
    parent_context: str = "",
    use_llm: bool = True,
) -> Dict[str, Any]:
    from backend.retriever import hybrid_retrieve

    retrieval = hybrid_retrieve(
        question,
        research_mode=research_mode,
        parent_context=parent_context,
    )

    cited_ids = sorted({c["source_id"] for c in retrieval["chunks"]})
    conn = get_conn()
    conn.execute(
        """
        INSERT INTO query_logs (question, research_mode, confidence_score, abstained, cited_source_ids_json, created_at)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            question,
            research_mode,
            retrieval["confidence_score"],
            1 if retrieval["abstain"] else 0,
            json.dumps(cited_ids),
            now_iso(),
        ),
    )
    conn.commit()
    conn.close()

    if retrieval["abstain"]:
        fallback_branches = build_rebuttal_tree_for_source("", question)
        return {
            "abstained": True,
            "question": question,
            "parent_context": parent_context,
            "research_mode": research_mode,
            "classification": "Insufficient Verified Evidence · Logged for Archive Expansion",
            "confidence_score": retrieval["confidence_score"],
            "fast_path_telemetry": retrieval.get("fast_path_telemetry", {}),
            "model_used": "evidence-sufficiency-gate",
            "short_answer": (
                "Limitation Notice: The archive did not find verified primary or commentary material in the "
                "currently indexed library to substantiate an answer to this specific question. Rather than "
                "speculating or citing unverified sources, this question has been logged for future "
                "catalog indexing."
            ),
            "direct_answer": (
                "Limitation Notice: The archive did not find verified primary or commentary material in the "
                "currently indexed library to substantiate an answer to this specific question. Rather than "
                "speculating or citing unverified sources, this question has been logged for future "
                "catalog indexing."
            ),
            "primary_evidence": retrieval["scriptures"],
            "archive_arguments": [],
            "logical_reasoning": [],
            "counterargument": None,
            "conversation_ready_response": None,
            "rebuttal_tree": fallback_branches,
            "explore_further": [b["question"] for b in fallback_branches],
            "retrieved_chunks": [],
        }

    base_response = build_deterministic_grounded_response(retrieval)
    if use_llm:
        base_response = _sync_call_openrouter(question, research_mode, base_response)
    return base_response


async def generate_research_answer(
    question: str,
    research_mode: str = "exegetical_archive",
    parent_context: str = "",
    use_llm: bool = True,
) -> Dict[str, Any]:
    return await asyncio.to_thread(
        generate_research_answer_sync, question, research_mode, parent_context, use_llm
    )
