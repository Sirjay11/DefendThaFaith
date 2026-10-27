# Defend the Faith — Engineering Roadmap & Architecture

> **Vision:** A trustworthy, source-grounded Christian apologetics and comparative theology research platform backed by primary Scripture, historical texts, classical commentary, and an automated index maintenance pipeline with editorial review gates.

---

## 1. Architectural Pillars

1. **Traceable Evidence First (Zero Uncited Claims)**
   - Every theological claim or interpretation cites an explicit retrieved source chunk (`source_id`, `chunk_id`, verbatim excerpt, and canonical URL).
   - Strict separation between:
     - **Primary Scripture & Historical Texts** (Bible passages, Quranic ayahs, Hadith/Tafsir references)
     - **Exegetical Commentary** (direct reasoning from indexed studies)
     - **Counterarguments / Objections** (distinguishing an opponent's quoted claim from the exegetical rebuttal)
2. **Permission-Aware Source Catalog**
   - Every source tracks `permission_mode` (`full_text`, `snippet_link_only`, `metadata_only`) and links directly to the reference study.
3. **Hybrid Retrieval Engine**
   - **Reference Fast-Path**: Deterministic parser extracts references (`John 1:1`, `Philippians 2:10-11`, `Isaiah 45:23`, `Surah 4:171`, `Sahih al-Bukhari 3448`, etc.) for exact lookup.
   - **Lexical + Semantic Search**: Matches exact theological terms and conceptual queries.
4. **Automated Index Maintenance Pipeline**
   - Executes four measurable, review-gated tasks:
     - **Task A (`discover`)**: Scans registered catalog indexes for unindexed studies.
     - **Task B (`normalize`)**: Splits studies into argument-aware chunks (`author_argument` vs `quoted_objection`) and links objections to rebuttals.
     - **Task C (`qa_benchmark`)**: Runs the Verification Benchmark Suite to score Retrieval Recall, Citation Accuracy, and Abstention Accuracy.
     - **Task D (`gap_analysis`)**: Analyzes unanswered or low-confidence user queries to recommend future additions.
