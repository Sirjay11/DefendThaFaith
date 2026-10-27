import re
from typing import List, Dict, Any
from backend.reference_parser import extract_scripture_references

OBJECTION_PATTERNS = [
    r"\b(?:opponents?|critics?|muslims?|unitarians?|apologists?|skeptics?)\s+(?:object|claim|argue|assert|allege|say|cite|contend)s?\b",
    r"\b(?:common\s+objection|muslim\s+objection|unitarian\s+objection|the\s+claim|objection\s*:)\b",
    r"^>\s+",
    r"\b(?:some\s+commentators\s+argue|they\s+argue\s+that)\b",
]

REBUTTAL_PATTERNS = [
    r"\b(?:shamoun\s+(?:responds|replies|demonstrates|shows|points\s+out|refutes)|response\s*:|rebuttal\s*:|refutation\s*:|our\s+response)\b",
    r"\b(?:this\s+objection\s+(?:fails|ignores|overlooks)|fatal\s+flaws?\s+in\s+this\s+reading)\b",
]

SCRIPTURE_QUOTE_PATTERNS = [
    r"^(?:\"[A-Z].*\"|\'[A-Z].*\')\s*\((?:[123]?\s*[A-Za-z]+\s+\d+:\d+|Surah\s+\d+:\d+|Sahih\s+[A-Za-z\-]+\s+\d+)\)",
]


def classify_paragraph_discourse(heading: str, paragraph: str) -> str:
    """
    Classifies a paragraph or section into:
      - 'quoted_objection': An opponent's argument quoted for refutation
      - 'primary_scripture': Direct scripture/hadith block quotation
      - 'author_argument': Sam Shamoun's own exegetical argument or rebuttal
    """
    combined = f"{heading}\n{paragraph}".strip()
    lower = combined.lower()

    # If explicitly marked as rebuttal/refutation even when mentioning critics, it's author_argument
    for pat in REBUTTAL_PATTERNS:
        if re.search(pat, lower, re.IGNORECASE):
            return "author_argument"

    for pat in OBJECTION_PATTERNS:
        if re.search(pat, lower, re.IGNORECASE | re.MULTILINE):
            return "quoted_objection"

    for pat in SCRIPTURE_QUOTE_PATTERNS:
        if re.search(pat, combined, re.IGNORECASE):
            return "primary_scripture"

    return "author_argument"


def split_article_argument_aware(
    raw_text: str,
    default_title: str = "Apologetics Analysis",
) -> List[Dict[str, Any]]:
    """
    Splits raw apologetics articles into argument-aware chunks instead of naive fixed-token windows.
    - Preserves section headings
    - Classifies each block into ('author_argument' | 'quoted_objection' | 'primary_scripture')
    - Links every 'quoted_objection' to its adjacent 'author_argument' rebuttal (paired_chunk_index)
      so an opponent's objection can NEVER be retrieved without Shamoun's rebuttal.
    """
    if not raw_text or not raw_text.strip():
        return []

    lines = raw_text.strip().splitlines()
    sections: List[Dict[str, str]] = []
    current_heading = default_title
    current_buffer: List[str] = []

    for line in lines:
        stripped = line.strip()
        if not stripped:
            if current_buffer:
                sections.append(
                    {
                        "heading": current_heading,
                        "text": " ".join(current_buffer).strip(),
                    }
                )
                current_buffer = []
            continue

        # Detect markdown or explicit section headers
        if stripped.startswith("#") or (
            len(stripped) < 95
            and stripped.endswith(":")
            and not stripped.startswith(">")
        ):
            if current_buffer:
                sections.append(
                    {
                        "heading": current_heading,
                        "text": " ".join(current_buffer).strip(),
                    }
                )
                current_buffer = []
            current_heading = stripped.lstrip("#").rstrip(":").strip()
        else:
            current_buffer.append(stripped)

    if current_buffer:
        sections.append(
            {
                "heading": current_heading,
                "text": " ".join(current_buffer).strip(),
            }
        )

    chunks: List[Dict[str, Any]] = []
    for idx, sec in enumerate(sections):
        text = sec["text"]
        heading = sec["heading"]
        discourse_type = classify_paragraph_discourse(heading, text)
        refs = extract_scripture_references(f"{heading} {text}")

        chunks.append(
            {
                "chunk_index": idx + 1,
                "section_title": heading,
                "discourse_type": discourse_type,
                "text_content": text,
                "scripture_refs": refs,
                "paired_chunk_index": None,
            }
        )

    # Link every quoted_objection to the immediately following (or preceding) author_argument
    for i, ch in enumerate(chunks):
        if ch["discourse_type"] == "quoted_objection":
            # Look forward first for the rebuttal
            paired_idx = None
            for j in range(i + 1, len(chunks)):
                if chunks[j]["discourse_type"] == "author_argument":
                    paired_idx = chunks[j]["chunk_index"]
                    break
            if paired_idx is None:
                for j in range(i - 1, -1, -1):
                    if chunks[j]["discourse_type"] == "author_argument":
                        paired_idx = chunks[j]["chunk_index"]
                        break
            ch["paired_chunk_index"] = paired_idx

    return chunks
