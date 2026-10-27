# Defend the Faith — Theological & Historical Research Platform

> **CAN YOU DEFEND WHAT YOU BELIEVE?**  
> Get clear, evidence-based answers to difficult challenges against Christianity. Explore the sources, understand the arguments, and prepare for the questions that come next.

---

## Overview

**Defend the Faith** is a minimalist, source-grounded Christian apologetics and comparative theology research instrument. Every response is structured around primary texts, grammatical and historical context, fair representation of opposing arguments, and an interactive **Expandable Rebuttal Tree** to help users prepare for follow-up objections.

### Core Capabilities

1. **7-Part Structured Research Answers**
   - **A. Direct Answer**: Clear, immediate explanation of the core theological issue.
   - **B. Primary Scriptural Evidence & Exegetical Commentary**: Full passages from the Bible, Quran, and Hadith alongside original-language notes (Greek, Hebrew, Arabic) and links to primary commentaries.
   - **C. Logical Reasoning Structure**: Step-by-step progression distinguishing *Established Textual Facts*, *Linguistic & Contextual Evidence*, *Documented Exegetical Arguments*, and *Theological Conclusions*.
   - **D. Substantial Counterargument**: Fairly stated objections from critics.
   - **E. Exegetical Response**: Contextual and grammatical refutation paired directly to the objection.
   - **F. Conversation-Ready Response**: A concise, respectful spoken summary with one-click copy.
   - **G. Expandable Rebuttal Tree**: Interactive nested branches for likely follow-up objections.

2. **Three Early Architectural Safeguards**
   - **Deterministic Fast-Path Reference Parser (`backend/reference_parser.py`)**: Extracts exact Bible, Quran, Hadith, and Tafsir citations in 0ms alongside lexical and vector similarity.
   - **Argument-Aware Discourse Splitting & Mandatory Rebuttal Pairing (`backend/argument_chunker.py`)**: Separates `quoted_objection` blocks from `author_argument` rebuttals and links them via `paired_chunk_id` so an opposing claim is never mistaken for the archive's conclusion.
   - **Multi-Stage Index Maintenance & Quality Benchmark Suite (`backend/hermes_ops.py`)**: Background catalog discovery, normalization, and automated verification benchmarks with editorial review gates.

---

## Quick Start

```powershell
python -m backend.main
```

Then open **`http://127.0.0.1:8000`** in your browser.
