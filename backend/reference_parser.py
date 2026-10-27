import re
from typing import List, Set, Dict, Any

BIBLE_BOOK_ALIASES = {
    "gen": "Genesis", "genesis": "Genesis",
    "ex": "Exodus", "exod": "Exodus", "exodus": "Exodus",
    "lev": "Leviticus", "leviticus": "Leviticus",
    "num": "Numbers", "numbers": "Numbers",
    "deut": "Deuteronomy", "deuteronomy": "Deuteronomy",
    "ps": "Psalms", "psa": "Psalms", "psalm": "Psalms", "psalms": "Psalms",
    "prov": "Proverbs", "proverbs": "Proverbs",
    "isa": "Isaiah", "isaiah": "Isaiah",
    "jer": "Jeremiah", "jeremiah": "Jeremiah",
    "ezek": "Ezekiel", "ezekiel": "Ezekiel",
    "dan": "Daniel", "daniel": "Daniel",
    "hos": "Hosea", "hosea": "Hosea",
    "mic": "Micah", "micah": "Micah",
    "zech": "Zechariah", "zechariah": "Zechariah",
    "mal": "Malachi", "malachi": "Malachi",
    "matt": "Matthew", "mt": "Matthew", "matthew": "Matthew",
    "mk": "Mark", "mark": "Mark",
    "lk": "Luke", "luke": "Luke",
    "jn": "John", "john": "John",
    "acts": "Acts",
    "rom": "Romans", "romans": "Romans",
    "1 cor": "1 Corinthians", "1cor": "1 Corinthians", "1 corinthians": "1 Corinthians",
    "2 cor": "2 Corinthians", "2cor": "2 Corinthians", "2 corinthians": "2 Corinthians",
    "gal": "Galatians", "galatians": "Galatians",
    "eph": "Ephesians", "ephesians": "Ephesians",
    "phil": "Philippians", "philippians": "Philippians",
    "col": "Colossians", "colossians": "Colossians",
    "1 thess": "1 Thessalonians", "1 thessalonians": "1 Thessalonians",
    "1 tim": "1 Timothy", "1 timothy": "1 Timothy",
    "2 tim": "2 Timothy", "2 timothy": "2 Timothy",
    "tit": "Titus", "titus": "Titus",
    "heb": "Hebrews", "hebrews": "Hebrews",
    "1 pet": "1 Peter", "1 peter": "1 Peter",
    "2 pet": "2 Peter", "2 peter": "2 Peter",
    "1 jn": "1 John", "1 john": "1 John",
    "jude": "Jude",
    "rev": "Revelation", "revelation": "Revelation",
}

QURAN_SURAH_NAMES = {
    "al-fatihah": 1, "al-baqarah": 2, "baqarah": 2,
    "al-imran": 3, "ali 'imran": 3, "imran": 3,
    "an-nisa": 4, "nisa": 4,
    "al-ma'idah": 5, "maidah": 5, "al-maidah": 5,
    "at-tawbah": 9, "tawbah": 9,
    "maryam": 19,
    "al-ahzab": 33,
    "az-zukhruf": 43,
    "as-saff": 61,
    "at-tahrim": 66,
    "al-ikhlas": 112, "ikhlas": 112,
}

HADITH_COLLECTIONS = {
    "bukhari": "Sahih al-Bukhari",
    "al-bukhari": "Sahih al-Bukhari",
    "sahih al-bukhari": "Sahih al-Bukhari",
    "sahih bukhari": "Sahih al-Bukhari",
    "muslim": "Sahih Muslim",
    "sahih muslim": "Sahih Muslim",
    "abu dawud": "Sunan Abu Dawud",
    "sunan abu dawud": "Sunan Abu Dawud",
    "tirmidhi": "Jami at-Tirmidhi",
    "at-tirmidhi": "Jami at-Tirmidhi",
    "ibn majah": "Sunan Ibn Majah",
}

BIBLE_REGEX = re.compile(
    r"\b((?:[123]\s*)?[A-Za-z]+)\.?\s+(\d{1,3}):(\d{1,3})(?:[-–—](\d{1,3}))?\b"
)

QURAN_NUM_REGEX = re.compile(
    r"\b(?:Surah|Sura|Quran|Qur'an|Q\.?)\s*(\d{1,3}):(\d{1,3})(?:[-–—](\d{1,3}))?\b",
    re.IGNORECASE,
)

QURAN_NAME_REGEX = re.compile(
    r"\b(?:Surah|Sura)\s+([A-Za-z'\-]+)\s*(?:(\d{1,3}):)?(\d{1,3})(?:[-–—](\d{1,3}))?\b",
    re.IGNORECASE,
)

HADITH_REGEX = re.compile(
    r"\b(Sahih\s+al-Bukhari|Sahih\s+Bukhari|al-Bukhari|Bukhari|Sahih\s+Muslim|Sunan\s+Abu\s+Dawud|Abu\s+Dawud|Jami\s+at-Tirmidhi|at-Tirmidhi|Tirmidhi|Sunan\s+Ibn\s+Majah|Ibn\s+Majah)\s*(?:,?\s*(?:Vol\.?\s*\d+,?\s*)?(?:Book\s*\d+,?\s*)?(?:Hadith|No\.?|#)?\s*)?(\d{1,5})\b",
    re.IGNORECASE,
)

TAFSIR_REGEX = re.compile(
    r"\b(Tafsir\s+Ibn\s+Kathir|Ibn\s+Kathir|Tafsir\s+al-Tabari|al-Tabari|Tafsir\s+al-Qurtubi|al-Qurtubi|Tafsir\s+al-Jalalayn|al-Jalalayn)\b",
    re.IGNORECASE,
)


def parse_references_detailed(text: str) -> Dict[str, List[str]]:
    """
    Adjustment #1: Deterministic Fast-Path Reference Parser.
    Extracts Bible verses, Quranic ayahs, Hadith numbers, and classical Tafsir citations
    so exact numerical citations never rely on approximate vector embeddings alone.
    """
    if not text:
        return {"all": [], "bible": [], "quran": [], "hadith": [], "tafsir": []}

    bible_refs: Set[str] = set()
    quran_refs: Set[str] = set()
    hadith_refs: Set[str] = set()
    tafsir_refs: Set[str] = set()

    # 1. Quranic numeric citations (e.g., Surah 4:171, Q. 3:45)
    for match in QURAN_NUM_REGEX.finditer(text):
        surah = int(match.group(1))
        ayah_start = int(match.group(2))
        ayah_end = int(match.group(3)) if match.group(3) else ayah_start
        quran_refs.add(f"Surah {surah}:{ayah_start}")
        if ayah_end > ayah_start and (ayah_end - ayah_start) <= 15:
            for v in range(ayah_start, ayah_end + 1):
                quran_refs.add(f"Surah {surah}:{v}")

    # 2. Quranic named citations (e.g., Surah An-Nisa 4:171 or Surah Maryam 19:19)
    for match in QURAN_NAME_REGEX.finditer(text):
        raw_name = match.group(1).lower().strip()
        if raw_name in QURAN_SURAH_NAMES:
            surah = QURAN_SURAH_NAMES[raw_name]
            ayah_start = int(match.group(3))
            quran_refs.add(f"Surah {surah}:{ayah_start}")

    # 3. Hadith citations (e.g., Sahih al-Bukhari 3448, Sahih Muslim 2365)
    for match in HADITH_REGEX.finditer(text):
        raw_coll = re.sub(r"\s+", " ", match.group(1).lower().strip())
        canonical_coll = HADITH_COLLECTIONS.get(raw_coll, "Sahih al-Bukhari")
        hadith_num = int(match.group(2))
        hadith_refs.add(f"{canonical_coll} {hadith_num}")

    # 4. Classical Tafsir citations (e.g., Tafsir Ibn Kathir, al-Tabari)
    for match in TAFSIR_REGEX.finditer(text):
        raw_t = re.sub(r"\s+", " ", match.group(1).lower().strip())
        if "kathir" in raw_t:
            tafsir_refs.add("Tafsir Ibn Kathir")
        elif "tabari" in raw_t:
            tafsir_refs.add("Tafsir al-Tabari")
        elif "qurtubi" in raw_t:
            tafsir_refs.add("Tafsir al-Qurtubi")
        elif "jalalayn" in raw_t:
            tafsir_refs.add("Tafsir al-Jalalayn")

    # 5. Bible citations (e.g., John 1:1, Philippians 2:10-11, Isa 45:23)
    for match in BIBLE_REGEX.finditer(text):
        raw_book = re.sub(r"\s+", " ", match.group(1).strip().lower())
        if raw_book in ("surah", "sura", "quran", "q"):
            continue
        canonical_book = BIBLE_BOOK_ALIASES.get(raw_book)
        if not canonical_book:
            continue
        chapter = int(match.group(2))
        v_start = int(match.group(3))
        v_end = int(match.group(4)) if match.group(4) else v_start
        bible_refs.add(f"{canonical_book} {chapter}:{v_start}")
        if v_end > v_start and (v_end - v_start) <= 15:
            for v in range(v_start, v_end + 1):
                bible_refs.add(f"{canonical_book} {chapter}:{v}")

    all_refs = sorted(bible_refs | quran_refs | hadith_refs | tafsir_refs)
    return {
        "all": all_refs,
        "bible": sorted(bible_refs),
        "quran": sorted(quran_refs),
        "hadith": sorted(hadith_refs),
        "tafsir": sorted(tafsir_refs),
    }


def extract_scripture_references(text: str) -> List[str]:
    return parse_references_detailed(text)["all"]
