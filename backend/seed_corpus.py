import json
import hashlib
from backend.database import get_conn, compute_semantic_signature, now_iso
from backend.reference_parser import extract_scripture_references

INITIAL_SCRIPTURE_PASSAGES = [
    {
        "id": "scr_phil_2_6_11",
        "corpus": "Bible",
        "reference": "Philippians 2:6-11",
        "canonical_refs": [
            "Philippians 2:6", "Philippians 2:7", "Philippians 2:8",
            "Philippians 2:9", "Philippians 2:10", "Philippians 2:11"
        ],
        "translation": "ESV / KJV Comparative",
        "text_content": (
            "Who, though he was in the form of God (en morphē theou), did not count equality with God "
            "a thing to be grasped, but emptied himself, by taking the form of a servant... Therefore God "
            "has highly exalted him and bestowed on him the name that is above every name, so that at the "
            "name of Jesus every knee should bow, in heaven and on earth and under the earth, and every "
            "tongue confess that Jesus Christ is Lord (Kyrios), to the glory of God the Father."
        ),
        "original_language_note": (
            "Greek: 'en morphē theou' (in the essential nature/form of God) and 'morphēn doulou labōn' "
            "(taking the form of a servant) — explains both why the Incarnate Son prays to the Father as "
            "a true servant and why every knee bows to Him as YHWH (Isaiah 45:23)."
        ),
        "topic_tags": ["Christology", "Deity of Christ", "Yahweh", "Incarnation", "Prayer of Jesus"],
    },
    {
        "id": "scr_isa_45_21_23",
        "corpus": "Bible",
        "reference": "Isaiah 45:21-23",
        "canonical_refs": ["Isaiah 45:21", "Isaiah 45:22", "Isaiah 45:23"],
        "translation": "ESV / LXX Comparative",
        "text_content": (
            "There is no other god besides me, a righteous God and a Savior; there is none besides me. "
            "Turn to me and be saved, all the ends of the earth! For I am God, and there is no other. "
            "By myself I have sworn; from my mouth has gone out in righteousness a word that shall not return: "
            "'To me every knee shall bow, every tongue shall swear allegiance.'"
        ),
        "original_language_note": (
            "Hebrew: YHWH swears by Himself that every knee will bow to Him alone. Paul applies this "
            "unmistakable YHWH-text to the risen Jesus in Philippians 2:10-11."
        ),
        "topic_tags": ["Monotheism", "Yahweh", "Old Testament Fulfillment", "Deity of Christ"],
    },
    {
        "id": "scr_john_14_28",
        "corpus": "Bible",
        "reference": "John 14:28",
        "canonical_refs": ["John 14:28", "John 14:23", "John 10:30"],
        "translation": "ESV",
        "text_content": (
            "You heard me say to you, 'I am going away, and I will come to you.' If you loved me, you "
            "would have rejoiced, because I am going to the Father, for the Father is greater than I "
            "(ho Patēr meizōn mou estin)."
        ),
        "original_language_note": (
            "Greek: 'meizōn' (greater in position/glory) vs 'beltiōn' (better in nature). Jesus speaks "
            "from His state of earthly humiliation and incarnate servanthood before returning to the "
            "Father's heavenly glory (cf. John 17:5; Hebrews 2:9)."
        ),
        "topic_tags": ["John 14:28", "Father Greater Than I", "Prayer of Jesus", "Subordination"],
    },
    {
        "id": "scr_john_1_1_3",
        "corpus": "Bible",
        "reference": "John 1:1-3, 14",
        "canonical_refs": ["John 1:1", "John 1:2", "John 1:3", "John 1:14"],
        "translation": "ESV / Greek Interlinear",
        "text_content": (
            "In the beginning was the Word (Logos), and the Word was with God (pros ton Theon), and the "
            "Word was God (kai Theos ēn ho Logos). He was in the beginning with God. All things were made "
            "through him, and without him was not any thing made that was made... And the Word became flesh "
            "(sarx egeneto) and dwelt among us, and we have seen his glory."
        ),
        "original_language_note": (
            "Greek: 'pros ton Theon' distinguishes the personal identity of the Logos from the Father, while "
            "the qualitative predicate nominative 'Theos ēn ho Logos' (Colwell's construction) identifies the "
            "Logos as fully divine by nature."
        ),
        "topic_tags": ["Logos", "Word of God", "Deity of Christ", "Incarnation"],
    },
    {
        "id": "scr_heb_1_8_12",
        "corpus": "Bible",
        "reference": "Hebrews 1:8-12",
        "canonical_refs": [
            "Hebrews 1:8", "Hebrews 1:9", "Hebrews 1:10", "Hebrews 1:11", "Hebrews 1:12",
            "Psalms 102:25", "Psalms 102:26", "Psalms 102:27", "Psalms 45:6"
        ],
        "translation": "ESV",
        "text_content": (
            "But of the Son he says, 'Your throne, O God (ho Theos), is forever and ever, the scepter of "
            "uprightness is the scepter of your kingdom.' ... And, 'You, Lord, laid the foundation of the "
            "earth in the beginning, and the heavens are the work of your hands; they will perish, but you "
            "remain... But you are the same, and your years will have no end.'"
        ),
        "original_language_note": (
            "Applies Psalm 45:6-7 and Psalm 102:25-27 (a prayer addressed directly to YHWH the uncreated "
            "Creator) directly to the Son by the Father Himself."
        ),
        "topic_tags": ["Deity of Christ", "Creator", "Yahweh", "Hebrews"],
    },
    {
        "id": "scr_john_17_3_5",
        "corpus": "Bible",
        "reference": "John 17:3-5",
        "canonical_refs": ["John 17:3", "John 17:4", "John 17:5"],
        "translation": "ESV",
        "text_content": (
            "And this is eternal life, that they know you, the only true God, and Jesus Christ whom you "
            "have sent. I glorified you on earth, having accomplished the work that you gave me to do. "
            "And now, Father, glorify me in your own presence with the glory that I had with you before "
            "the world existed."
        ),
        "original_language_note": (
            "Greek: 'para seautō' and 'pro tou ton kosmon einai' — in His high-priestly prayer, Jesus claims "
            "pre-cosmic, eternal divine glory alongside the Father before creation."
        ),
        "topic_tags": ["John 17:3", "Pre-existence", "Deity of Christ", "Prayer of Jesus"],
    },
    {
        "id": "scr_mark_10_17_18",
        "corpus": "Bible",
        "reference": "Mark 10:17-18",
        "canonical_refs": ["Mark 10:17", "Mark 10:18"],
        "translation": "ESV",
        "text_content": (
            "And as he was setting out on his journey, a man ran up and knelt before him and asked him, "
            "'Good Teacher, what must I do to inherit eternal life?' And Jesus said to him, 'Why do you "
            "call me good? No one is good except God alone.'"
        ),
        "original_language_note": (
            "Greek: 'ei mē heis ho Theos' — Jesus does not deny being good (in John 10:11 He calls Himself "
            "the Good Shepherd, 'ho poimēn ho kalos'); rather, He challenges the rich ruler to recognize the "
            "implication of his own title."
        ),
        "topic_tags": ["Mark 10:18", "Synoptic Christology", "Objections"],
    },
    {
        "id": "scr_quran_5_46_47",
        "corpus": "Quran",
        "reference": "Surah 5:46-47",
        "canonical_refs": ["Surah 5:46", "Surah 5:47", "Surah 3:3", "Surah 10:94"],
        "translation": "Sahih International",
        "text_content": (
            "And We sent, following in their footsteps, Jesus, the son of Mary, confirming that which came "
            "before him in the Torah; and We gave him the Gospel (al-Injīl), in which was guidance and light "
            "and confirming that which preceded it of the Torah... And let the People of the Gospel judge "
            "by what Allah has revealed therein (wa-l-yaḥkum ahlu l-injīli bimā anzala Allāhu fīhi)."
        ),
        "original_language_note": (
            "Arabic: Commands 7th-century Christians ('People of the Gospel') to judge by the Gospel in "
            "their possession, creating a foundational textual dilemma when compared with New Testament Christology."
        ),
        "topic_tags": ["Islamic Dilemma", "Quran Affirming the Bible", "Surah 5:47", "Surah 10:94"],
    },
    {
        "id": "scr_quran_4_171",
        "corpus": "Quran",
        "reference": "Surah 4:171",
        "canonical_refs": ["Surah 4:171"],
        "translation": "Sahih International / Pickthall",
        "text_content": (
            "O People of the Scripture, do not commit excess in your religion or say about Allah except "
            "the truth. The Messiah, Jesus, the son of Mary, was but a messenger of Allah and His word "
            "(Kalimatuhu) which He directed to Mary and a spirit from Him (wa Rūḥun minhu). So believe in "
            "Allah and His messengers. And do not say, 'Three'; desist - it is better for you."
        ),
        "original_language_note": (
            "Arabic: 'Kalimatuhu' (His Word) and 'Rūḥun minhu' (a Spirit from Him). Uniquely in the Quran, "
            "Jesus is personally titled both the Word of Allah and a Spirit proceeding from Him."
        ),
        "topic_tags": ["Quranic Christology", "Word of God", "Kalimatullah", "Spirit from God"],
    },
    {
        "id": "scr_quran_3_45",
        "corpus": "Quran",
        "reference": "Surah 3:45",
        "canonical_refs": ["Surah 3:45"],
        "translation": "Sahih International",
        "text_content": (
            "[And mention] when the angels said, 'O Mary, indeed Allah gives you good tidings of a word "
            "from Him (bi-Kalimatin minhu), whose name will be the Messiah, Jesus, the son of Mary - "
            "distinguished in this world and the Hereafter and among those brought near [to Allah].'"
        ),
        "original_language_note": (
            "Arabic: 'bi-Kalimatin minhu' (a Word from Him), 'wajīhan fī al-dunyā wa-al-ākhirah' (illustrious "
            "in this world and the next)."
        ),
        "topic_tags": ["Quranic Christology", "Word of God", "Messiah"],
    },
    {
        "id": "scr_quran_5_116",
        "corpus": "Quran",
        "reference": "Surah 5:116",
        "canonical_refs": ["Surah 5:116"],
        "translation": "Sahih International",
        "text_content": (
            "And [beware the Day] when Allah will say, 'O Jesus, Son of Mary, did you say to the people, "
            "\"Take me and my mother as deities besides Allah?\"' He will say, 'Exalted are You! It was "
            "not for me to say that to which I have no right.'"
        ),
        "original_language_note": (
            "Arabic: 'ittakhidhūnī wa-ummiya ilāhayni min dūni Allāhi' (take me and my mother as two gods "
            "besides Allah) — addresses a triad of Allah, Jesus, and Mary rather than the historic Christian "
            "Trinity of Father, Son, and Holy Spirit."
        ),
        "topic_tags": ["Trinity in the Quran", "Surah 5:116", "Islamic Objections"],
    },
    {
        "id": "scr_bukhari_3448",
        "corpus": "Hadith",
        "reference": "Sahih al-Bukhari 3448",
        "canonical_refs": ["Sahih al-Bukhari 3448"],
        "translation": "Sunnah.com / Book of Prophets",
        "text_content": (
            "Narrated 'Ubada: The Prophet said, 'If anyone testifies that None has the right to be "
            "worshipped but Allah Alone Who has no partners, and that Muhammad is His Slave and His "
            "Apostle, and that Jesus is Allah's Slave and His Apostle and His Word (Kalimatuhu) which He "
            "bestowed on Mary and a Spirit created from Him (wa Rūḥun minhu), and that Paradise is true, "
            "and Hell is true, Allah will admit him into Paradise with the deeds which he had done even "
            "if those deeds were few.'"
        ),
        "original_language_note": (
            "Authentic (Sahih) Hadith affirming Surah 4:171's unique titles for Jesus as 'Kalimatuhu' "
            "(His Word) and 'Rūḥun minhu' (a Spirit from Him), often examined alongside Tafsir Ibn Kathir."
        ),
        "topic_tags": ["Hadith", "Sahih al-Bukhari 3448", "Kalimatullah", "Spirit from God"],
    },
    {
        "id": "scr_muslim_2365",
        "corpus": "Hadith",
        "reference": "Sahih Muslim 2365",
        "canonical_refs": ["Sahih Muslim 2365"],
        "translation": "Sunnah.com / Book of Virtues",
        "text_content": (
            "Abu Huraira reported Allah's Messenger as saying: 'No child is born but he is pricked by "
            "the Satan and he begins to weep because of the pricking of the Satan, except the son of "
            "Mary and his mother.'"
        ),
        "original_language_note": (
            "Authentic (Sahih) Hadith confirming the sinless preservation of Jesus (cf. Surah 19:19, "
            "'zakiyyan' — a pure/faultless son) in contrast to all other human prophets."
        ),
        "topic_tags": ["Hadith", "Sahih Muslim 2365", "Sinlessness of Jesus", "Surah 19:19"],
    },
]


INITIAL_SOURCES_AND_CHUNKS = [
    {
        "id": "src_archive_jesus_prays",
        "url": "https://biblehub.com/commentaries/john/14-28.htm",
        "canonical_url": "https://biblehub.com/commentaries/john/14-28.htm",
        "title": "If Jesus Is God, Why Does He Pray to the Father? Incarnation, Trinitarian Communion, and John 14:28",
        "author": "Exegetical Research Archive",
        "source_type": "archive_article",
        "media_type": "article",
        "video_timestamp": None,
        "topic": "Incarnation · Trinity · Prayer of Jesus & John 14:28",
        "permission_mode": "snippet_link_only",
        "published_date": "2024-05-18",
        "chunks": [
            {
                "section_title": "Why the Incarnate Son Prays to the Father (Philippians 2:6-8 & Hebrews 5:7)",
                "discourse_type": "author_argument",
                "paired_chunk_index": None,
                "text_content": (
                    "When critics ask, 'If Jesus is God, why does He pray? Does God pray to God?', they "
                    "confuse Unitarian modalism (the idea that the Father and the Son are a single "
                    "person) with historic Trinitarian theology and the Incarnation. In biblical "
                    "Christianity, the one eternal Being of God exists as three distinct, co-eternal "
                    "Persons: the Father, the Son (Word), and the Holy Spirit (John 1:1; Matthew 28:19). "
                    "Furthermore, in the Incarnation, the eternal Son genuinely assumed a complete human "
                    "nature (John 1:14; Philippians 2:6-8: 'taking the form of a servant'). As a true, "
                    "sinless man and our High Priest (Hebrews 5:7), Jesus prayed to His Father both to "
                    "model perfect human dependence on God and to express the eternal interpersonal "
                    "communion of love between the Son and the Father (John 17:1-5)."
                ),
            },
            {
                "section_title": "Objection: Does Jesus Praying and Saying 'The Father Is Greater Than I' (John 14:28) Prove Subordination?",
                "discourse_type": "quoted_objection",
                "paired_chunk_index": 3,
                "text_content": (
                    "Critics object: 'Prayer is an act of worship from an inferior creature to a superior "
                    "Creator. Moreover, in John 14:28 Jesus explicitly says, \"The Father is greater than "
                    "I,\" and in Mark 13:32 He says only the Father knows the hour. Therefore Jesus is "
                    "ontologically subordinate to God and cannot be co-equal with the Father.'"
                ),
            },
            {
                "section_title": "Exegetical Rebuttal on Functional Submission vs. Ontological Equality (John 14:28, Mark 13:32, John 17:5)",
                "discourse_type": "author_argument",
                "paired_chunk_index": None,
                "text_content": (
                    "Classical Christian exegesis refutes this objection by distinguishing ontological nature (what someone IS) "
                    "from positional/functional role (what office someone assumes). In John 14:28, Jesus "
                    "explains WHY the Father is 'greater' (meizōn, greater in position/glory, not beltiōn, "
                    "better in nature): 'because I am going to the Father, for the Father is greater than I.' "
                    "While Jesus walked the earth in the humble state of a servant facing crucifixion, the "
                    "Father reigned in unvarnished heavenly glory. That is why in John 17:5—inside His very "
                    "prayer!—Jesus asks the Father to restore Him to 'the glory that I had with You before "
                    "the world existed.' A mere creature never shared pre-cosmic divine glory with YHWH "
                    "(Isaiah 42:8). Likewise, in His voluntary kenosis (Philippians 2:7), the Son refrained "
                    "from exercising certain divine prerogatives according to His human nature (Mark 13:32) "
                    "and experienced physical death in His humanity (1 Peter 3:18; Hebrews 2:9, 14) while "
                    "remaining the eternal Lord of glory who raises Himself from the dead (John 2:19-21; 10:17-18)."
                ),
            },
        ],
    },
    {
        "id": "src_archive_islamic_dilemma",
        "url": "https://quran.com/5/47",
        "canonical_url": "https://quran.com/5/47",
        "title": "Does the Quran Affirm the Bible or Contradict It? Examining Surah 3:3, 5:46-48, and 10:94",
        "author": "Comparative Theology Archive",
        "source_type": "archive_article",
        "media_type": "article",
        "video_timestamp": None,
        "topic": "Quran & Bible · Textual Authority",
        "permission_mode": "snippet_link_only",
        "published_date": "2024-01-24",
        "chunks": [
            {
                "section_title": "The Quran Explicitly Confirms the Preservation and Authority of the Torah and Gospel (Injīl)",
                "discourse_type": "author_argument",
                "paired_chunk_index": None,
                "text_content": (
                    "Textual comparison demonstrates that the Quran places its readers in an inescapable logical bind "
                    "regarding the Bible. Throughout the Quran, the text claims to confirm the previous "
                    "Scriptures—the Torah (Tawrāt) and the Gospel (Injīl)—that were actively in the hands "
                    "of Jews and Christians in the 7th century (Surah 2:41, 2:89, 3:3, 5:43-48). In Surah "
                    "5:47, the Quran commands Christians ('the People of the Gospel') to judge by what "
                    "Allah revealed in the Gospel. In Surah 10:94, Muhammad himself is instructed that if "
                    "he is in doubt about what was revealed to him, he must ask those who have been reading "
                    "the Scripture before him. Moreover, Surah 6:115 and Surah 18:27 declare that 'none can "
                    "change the Words of Allah.'"
                ),
            },
            {
                "section_title": "Objection Claiming the Bible Was Textually Corrupted (Taḥrīf)",
                "discourse_type": "quoted_objection",
                "paired_chunk_index": 3,
                "text_content": (
                    "Critics object that the Quran only affirms the 'original' Torah given "
                    "to Moses and the 'original' Injīl given to Jesus, arguing based on Surah 2:75-79 that "
                    "Jews and Christians corrupted (taḥrīf) the text of the Bible before the 7th century."
                ),
            },
            {
                "section_title": "Rebuttal: Why Textual Corruption (Taḥrīf al-Lafẓ) Contradicts Both Surah 5:47 and Manuscript History",
                "discourse_type": "author_argument",
                "paired_chunk_index": None,
                "text_content": (
                    "Historical and textual evidence shows that the 'corrupted before the 7th century' claim contradicts both the Quran "
                    "and manuscript history. First, one cannot command 7th-century Christians to judge by "
                    "a book they no longer possess (Surah 5:47, 5:68), nor can one verify "
                    "revelation against corrupted scriptures (Surah 10:94). Second, full New "
                    "Testament manuscripts (such as Codex Sinaiticus and Codex Vaticanus) date centuries "
                    "before the 7th century (4th century AD), proving the Gospel in the 7th century is the exact "
                    "same New Testament read today—which teaches that Jesus is the divine Son of God who "
                    "died and rose again. Therefore: if the Bible is true, any text that contradicts it cannot be true; "
                    "and if the Bible were corrupted, any text affirming its 7th-century preservation would still be undermined."
                ),
            },
        ],
    },
    {
        "id": "src_archive_phil2",
        "url": "https://biblehub.com/commentaries/philippians/2-6.htm",
        "canonical_url": "https://biblehub.com/commentaries/philippians/2-6.htm",
        "title": "Jesus Christ as the Sovereign Lord (Kyrios) and Yahweh in Paul's Christology (Philippians 2:6-11)",
        "author": "Exegetical Research Archive",
        "source_type": "archive_article",
        "media_type": "article",
        "video_timestamp": None,
        "topic": "Deity of Christ · Biblical Exegesis",
        "permission_mode": "snippet_link_only",
        "published_date": "2024-04-15",
        "chunks": [
            {
                "section_title": "Paul's Application of Isaiah 45:23 to Jesus in Philippians 2:10-11",
                "discourse_type": "author_argument",
                "paired_chunk_index": None,
                "text_content": (
                    "In Philippians 2:6-11, the Apostle Paul does not merely ascribe a high angelic or "
                    "prophetic status to the Lord Jesus. By quoting Isaiah 45:23—a passage in which Yahweh "
                    "emphatically swears by Himself that 'there is no other God besides Me' and that 'to Me "
                    "every knee shall bow and every tongue confess'—Paul identifies Jesus within the unique "
                    "sovereign identity of Yahweh Himself. The ‘name above every name’ bestowed upon the "
                    "incarnate, risen Christ in Philippians 2:9-11 is Kyrios (Lord), the Greek Septuagint "
                    "rendering of the Tetragrammaton (YHWH)."
                ),
            },
            {
                "section_title": "Common Objection on 'God Exalted Him'",
                "discourse_type": "quoted_objection",
                "paired_chunk_index": 3,
                "text_content": (
                    "Opponents object: 'If Philippians 2:9 says God highly exalted Jesus and gave Him the "
                    "name above every name as a reward for His obedience, then Jesus could not have been "
                    "God Almighty from eternity, because Almighty God cannot be exalted or given something "
                    "He did not already possess.'"
                ),
            },
            {
                "section_title": "Rebuttal: Pre-Incarnate Glory vs. Incarnate Exaltation",
                "discourse_type": "author_argument",
                "paired_chunk_index": None,
                "text_content": (
                    "Exegetical analysis shows that this objection ignores the flow of Philippians 2:6-8 and parallel "
                    "texts like John 17:5. Verse 6 explicitly establishes that prior to becoming flesh, "
                    "Christ eternally existed 'in the form of God' (en morphē theou) and possessed equality "
                    "with God. Because He humbled Himself by assuming a true human nature ('taking the form "
                    "of a servant'), His subsequent exaltation in verses 9-11 is the enthronement of the "
                    "God-Man in His resurrected humanity to the very glory He shared with the Father before "
                    "the world existed (John 17:5)."
                ),
            },
        ],
    },
    {
        "id": "src_archive_quran_word",
        "url": "https://biblehub.com/commentaries/john/1-1.htm",
        "canonical_url": "https://biblehub.com/commentaries/john/1-1.htm",
        "title": "Jesus as the Word of God (Logos / Kalimatullah) and Spirit from God in Comparative Perspective",
        "author": "Comparative Theology Archive",
        "source_type": "archive_article",
        "media_type": "article",
        "video_timestamp": None,
        "topic": "Comparative Christology · John 1:1, Surah 4:171 & Sahih al-Bukhari 3448",
        "permission_mode": "snippet_link_only",
        "published_date": "2024-08-20",
        "chunks": [
            {
                "section_title": "Comparing Surah 3:45, Surah 4:171, and Sahih al-Bukhari 3448 with John 1:1-14",
                "discourse_type": "author_argument",
                "paired_chunk_index": None,
                "text_content": (
                    "Both the New Testament (John 1:1, 1:14; Revelation 19:13) and the Quran (Surah 3:39, "
                    "Surah 3:45, Surah 4:171) alongside Sahih al-Bukhari 3448 uniquely call Jesus the 'Word "
                    "of God' (Logos / Kalimatullah) and 'a Spirit from Him' (wa-Rūḥun minhu), while Sahih "
                    "Muslim 2365 and Surah 19:19 affirm his sinless purity. In classical Sunni theology, "
                    "Allah's Word (Kalām) and Spirit are eternal uncreated attributes, yet commentators "
                    "confronting Surah 4:171 and Sahih al-Bukhari 3448 often attempt to reduce 'Word' to "
                    "merely the creative command 'Be!' (Kun)."
                ),
            },
            {
                "section_title": "Competing Explanation of 'Kalimatullah' as 'Kun' (Be!)",
                "discourse_type": "quoted_objection",
                "paired_chunk_index": 3,
                "text_content": (
                    "Commentators (citing Tafsir Ibn Kathir on Surah 3:59) argue that Jesus is only "
                    "called 'a Word from Allah' because he was created without a human father by Allah's "
                    "spoken command 'Be!' (Kun), just as Adam was created from dust by the command 'Be!'"
                ),
            },
            {
                "section_title": "Counter-Analysis of Surah 3:45, 4:171, and Sahih al-Bukhari 3448",
                "discourse_type": "author_argument",
                "paired_chunk_index": None,
                "text_content": (
                    "Grammatical analysis shows why the 'Kun' reduction fails on the texts' own terms: "
                    "First, everything in creation comes into existence by 'Kun', yet neither Adam nor any "
                    "other prophet is ever personally named 'the Word of Allah' (Kalimatuhu) or 'a Spirit from "
                    "Him' (Rūḥun minhu) as Jesus is in Surah 4:171 and Sahih al-Bukhari 3448. Second, in "
                    "Surah 3:45 the grammar identifies the Word personally as the Messiah ('a Word from Him, "
                    "whose name is the Messiah, Jesus son of Mary'). In John 1:1-14, the rationale is explicit: "
                    "Jesus is the eternal Logos who was with the Father in the beginning, through whom all "
                    "things were created, and who entered human history in the Incarnation."
                ),
            },
        ],
    },
    {
        "id": "src_archive_john17_3",
        "url": "https://biblehub.com/commentaries/john/17-3.htm",
        "canonical_url": "https://biblehub.com/commentaries/john/17-3.htm",
        "title": "Does John 17:3 Disprove the Deity of Christ? Examining 'The Only True God'",
        "author": "Exegetical Research Archive",
        "source_type": "archive_article",
        "media_type": "article",
        "video_timestamp": None,
        "topic": "Deity of Christ · Exegetical Rebuttals",
        "permission_mode": "snippet_link_only",
        "published_date": "2024-11-12",
        "chunks": [
            {
                "section_title": "The Objection from John 17:3 ('You, the Only True God')",
                "discourse_type": "quoted_objection",
                "paired_chunk_index": 2,
                "text_content": (
                    "Critics of the Trinity frequently cite John 17:3, where Jesus prays to the Father: "
                    "'And this is eternal life, that they know You, the only true God, and Jesus Christ "
                    "whom You have sent.' They argue that since the Father is called the 'only true God' "
                    "in distinction from Jesus Christ, Jesus is excluded from being the true God."
                ),
            },
            {
                "section_title": "Contextual and Grammatical Refutation (John 17:1-5 & 1 John 5:20)",
                "discourse_type": "author_argument",
                "paired_chunk_index": None,
                "text_content": (
                    "Contextual exegesis reveals three fatal flaws in this reading of John 17:3. First, by the exact "
                    "same logic, since Jude 1:4 calls Jesus 'our only Master and Lord (monon Despotēn kai "
                    "Kyrion)', one would have to exclude the Father from being Master and Lord! In biblical "
                    "idiom, calling the Father 'the only true God' contrasts Him with false pagan idols "
                    "(1 Thessalonians 1:9), not with His own eternal Word and Son. Second, in John 17:3 "
                    "itself, eternal life requires knowing BOTH the Father AND Jesus Christ equally. Third, "
                    "just two verses later in John 17:5, Jesus asks the Father to glorify Him 'in Your own "
                    "presence with the glory that I had with You before the world existed'—a pre-cosmic "
                    "divine glory that Yahweh in Isaiah 42:8 and 48:11 never shares with a mere creature."
                ),
            },
        ],
    },
    {
        "id": "src_archive_mark10_18",
        "url": "https://biblehub.com/commentaries/mark/10-18.htm",
        "canonical_url": "https://biblehub.com/commentaries/mark/10-18.htm",
        "title": "Why Do You Call Me Good? Jesus' Question to the Rich Young Ruler in Mark 10:17-18",
        "author": "Exegetical Research Archive",
        "source_type": "archive_article",
        "media_type": "article",
        "video_timestamp": None,
        "topic": "Synoptic Christology · Exegetical Rebuttals",
        "permission_mode": "snippet_link_only",
        "published_date": "2024-06-03",
        "chunks": [
            {
                "section_title": "The Skeptical Claim on Mark 10:18",
                "discourse_type": "quoted_objection",
                "paired_chunk_index": 2,
                "text_content": (
                    "In Mark 10:17-18, when a man addresses Jesus as 'Good Teacher', Jesus replies: "
                    "'Why do you call me good? No one is good except God alone.' Critics claim Jesus is "
                    "rebuking the man and denying His own deity by contrasting Himself with God."
                ),
            },
            {
                "section_title": "Socratic Analysis of Mark 10:17-22",
                "discourse_type": "author_argument",
                "paired_chunk_index": None,
                "text_content": (
                    "Textual analysis notes that Jesus never says, 'I am not good, do not call me good.' "
                    "Rather, He asks a diagnostic question: 'Why do you call me good? No one is good "
                    "except God alone.' In the Gospel of Mark, Jesus repeatedly claims prerogatives "
                    "belonging exclusively to God—forgiving sins (Mark 2:5-12, where the scribes ask "
                    "'Who can forgive sins but God alone?'), being Lord of the Sabbath (Mark 2:28), and "
                    "demanding absolute allegiance above family and possessions (Mark 10:21). By stating "
                    "that God alone is intrinsically good, Jesus invites the ruler to connect the dots: "
                    "if Jesus is truly 'Good', then He is not merely a human teacher, and following Him "
                    "requires forsaking the man's idol of wealth (Mark 10:21-22)."
                ),
            },
        ],
    },
    {
        "id": "src_archive_heb1_ps102",
        "url": "https://biblehub.com/commentaries/hebrews/1-8.htm",
        "canonical_url": "https://biblehub.com/commentaries/hebrews/1-8.htm",
        "title": "The Father Calls the Son God and Yahweh the Creator in Hebrews 1:8-12",
        "author": "Exegetical Research Archive",
        "source_type": "archive_article",
        "media_type": "article",
        "video_timestamp": None,
        "topic": "Deity of Christ · Old Testament in the New",
        "permission_mode": "snippet_link_only",
        "published_date": "2024-02-19",
        "chunks": [
            {
                "section_title": "Hebrews 1:10-12 Applies Psalm 102:25-27 Directly to Jesus",
                "discourse_type": "author_argument",
                "paired_chunk_index": None,
                "text_content": (
                    "One of the most decisive proofs of the Deity of Christ in the New Testament is "
                    "Hebrews 1:8-12. After quoting Psalm 45:6-7 ('Your throne, O God, is forever and ever') "
                    "as the Father's direct address to the Son, the author of Hebrews quotes Psalm 102:25-27: "
                    "'You, Lord, laid the foundation of the earth in the beginning, and the heavens are "
                    "the work of Your hands; they will perish, but You remain... You are the same, and "
                    "Your years will have no end.' In Psalm 102 (verses 1, 12, 21-22), the psalmist is "
                    "speaking exclusively to Yahweh God of Israel. By applying this passage to the Son, "
                    "Hebrews 1 identifies Jesus as Yahweh the immutable, uncreated Creator of heaven and earth."
                ),
            },
        ],
    },
    {
        "id": "src_archive_quran_trinity",
        "url": "https://quran.com/5/116",
        "canonical_url": "https://quran.com/5/116",
        "title": "The Quranic View of the Christian Trinity: Examining Surah 5:73, 5:116, and 4:171",
        "author": "Comparative Theology Archive",
        "source_type": "archive_article",
        "media_type": "article",
        "video_timestamp": None,
        "topic": "Trinity · Comparative Analysis",
        "permission_mode": "snippet_link_only",
        "published_date": "2024-09-10",
        "chunks": [
            {
                "section_title": "Surah 5:116 and the Misrepresentation of Historic Trinitarian Theology",
                "discourse_type": "author_argument",
                "paired_chunk_index": None,
                "text_content": (
                    "In Surah 5:116, Allah asks Jesus whether he told mankind: 'Take me and my mother as "
                    "two gods besides Allah (ilāhayni min dūni Allāhi).' Historical theology highlights that "
                    "biblical Christianity has never taught tritheism (three separate gods) nor has it ever "
                    "included Mary as a goddess in the Godhead. Rather, Christians believe in one eternal "
                    "Being of God (Deuteronomy 6:4; Matthew 28:19) existing eternally as Father, Word/Son, "
                    "and Holy Spirit. Consequently, the critique in Surah 5:116 and Surah 5:73 "
                    "('Allah is the third of three') addresses a triad misconception rather than the actual "
                    "New Testament doctrine of the Triune God."
                ),
            },
        ],
    },
]


INITIAL_GOLD_QUESTIONS = [
    {
        "id": "gq_jesus_prays",
        "question": "If Jesus is God, why does He pray to the Father?",
        "category": "Incarnation & Trinity · Core Objection",
        "expected_source_ids": ["src_archive_jesus_prays"],
        "expected_scripture_refs": ["Philippians 2:6-11", "John 14:28", "John 17:3-5"],
        "should_abstain": 0,
    },
    {
        "id": "gq_islamic_dilemma",
        "question": "Does the Quran affirm the Bible or contradict it?",
        "category": "Comparative Theology · Textual Authority",
        "expected_source_ids": ["src_archive_islamic_dilemma"],
        "expected_scripture_refs": ["Surah 5:46-47"],
        "should_abstain": 0,
    },
    {
        "id": "gq_phil2",
        "question": "Does Philippians 2:10-11 identify Jesus as Yahweh?",
        "category": "Christology · Biblical Exegesis",
        "expected_source_ids": ["src_archive_phil2"],
        "expected_scripture_refs": ["Philippians 2:6-11", "Isaiah 45:21-23"],
        "should_abstain": 0,
    },
    {
        "id": "gq_quran_word",
        "question": "Does the Quran and Sahih al-Bukhari 3448 teach that Jesus is the Word of God in Surah 4:171, and how does that compare with John 1:1?",
        "category": "Comparative Theology · Quran, Hadith & Bible",
        "expected_source_ids": ["src_archive_quran_word"],
        "expected_scripture_refs": ["Surah 4:171", "Sahih al-Bukhari 3448", "John 1:1-3, 14"],
        "should_abstain": 0,
    },
    {
        "id": "gq_john17_3",
        "question": "Why does Jesus call the Father 'the only true God' in John 17:3?",
        "category": "Apologetics · Rebuttals",
        "expected_source_ids": ["src_archive_john17_3"],
        "expected_scripture_refs": ["John 17:3-5"],
        "should_abstain": 0,
    },
    {
        "id": "gq_mark10_18",
        "question": "Did Jesus deny being God when He asked 'Why do you call me good?' in Mark 10:18?",
        "category": "Synoptic Christology · Rebuttals",
        "expected_source_ids": ["src_archive_mark10_18"],
        "expected_scripture_refs": ["Mark 10:17-18"],
        "should_abstain": 0,
    },
    {
        "id": "gq_heb1_ps102",
        "question": "How does Hebrews 1:8-12 use Psalm 102:25-27 to prove Jesus is Yahweh the Creator?",
        "category": "Christology · Old Testament in the New",
        "expected_source_ids": ["src_archive_heb1_ps102"],
        "expected_scripture_refs": ["Hebrews 1:8-12"],
        "should_abstain": 0,
    },
    {
        "id": "gq_abstain_test",
        "question": "What is the detailed position on 16th-century Dutch Infralapsarian vs Supralapsarian church synod minutes?",
        "category": "Abstention & Boundary Verification",
        "expected_source_ids": [],
        "expected_scripture_refs": [],
        "should_abstain": 1,
    },
]


def seed_initial_corpus(force_reseed: bool = False) -> dict:
    conn = get_conn()
    cur = conn.cursor()

    if force_reseed:
        cur.executescript(
            """
            DELETE FROM document_chunks;
            DELETE FROM sources;
            DELETE FROM gold_questions;
            DELETE FROM hermes_jobs;
            """
        )

    ts = now_iso()

    for sp in INITIAL_SCRIPTURE_PASSAGES:
        cur.execute(
            """
            INSERT OR REPLACE INTO scripture_passages
            (id, corpus, reference, canonical_refs_json, translation, text_content, original_language_note, topic_tags_json)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                sp["id"],
                sp["corpus"],
                sp["reference"],
                json.dumps(sp["canonical_refs"]),
                sp["translation"],
                sp["text_content"],
                sp["original_language_note"],
                json.dumps(sp["topic_tags"]),
            ),
        )

    for src in INITIAL_SOURCES_AND_CHUNKS:
        full_concat = " ".join(c["text_content"] for c in src["chunks"])
        chash = hashlib.sha256(full_concat.encode("utf-8")).hexdigest()[:16]
        cur.execute(
            """
            INSERT OR REPLACE INTO sources
            (id, url, canonical_url, title, author, source_type, media_type, video_timestamp, topic, permission_mode, published_date, content_hash, status, last_crawled_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'verified', ?)
            """,
            (
                src["id"],
                src["url"],
                src["canonical_url"],
                src["title"],
                src["author"],
                src["source_type"],
                src.get("media_type", "article"),
                src.get("video_timestamp"),
                src["topic"],
                src["permission_mode"],
                src["published_date"],
                chash,
                ts,
            ),
        )

        for idx, ch in enumerate(src["chunks"]):
            chunk_id = f"{src['id']}_ch{idx+1}"
            paired_idx = ch.get("paired_chunk_index")
            paired_chunk_id = f"{src['id']}_ch{paired_idx}" if paired_idx else None
            refs = extract_scripture_references(
                f"{ch['section_title']} {ch['text_content']}"
            )
            emb = compute_semantic_signature(
                f"{src['title']} {ch['section_title']} {ch['text_content']}"
            )
            cur.execute(
                """
                INSERT OR REPLACE INTO document_chunks
                (id, source_id, chunk_index, section_title, discourse_type, paired_chunk_id, text_content, scripture_refs_json, embedding_json)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    chunk_id,
                    src["id"],
                    idx + 1,
                    ch["section_title"],
                    ch["discourse_type"],
                    paired_chunk_id,
                    ch["text_content"],
                    json.dumps(refs),
                    json.dumps(emb),
                ),
            )

    for gq in INITIAL_GOLD_QUESTIONS:
        cur.execute(
            """
            INSERT OR REPLACE INTO gold_questions
            (id, question, category, expected_source_ids_json, expected_scripture_refs_json, should_abstain)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                gq["id"],
                gq["question"],
                gq["category"],
                json.dumps(gq["expected_source_ids"]),
                json.dumps(gq["expected_scripture_refs"]),
                gq["should_abstain"],
            ),
        )

    cur.execute(
        """
        INSERT OR IGNORE INTO hermes_jobs
        (id, job_type, title, status, summary, metrics_json, pipeline_steps_json, proposed_action_json, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            "job_init_discovery_01",
            "discover",
            "Discovered Unindexed Study: Jesus' Divine Claim in John 8:58 ('Before Abraham Was, I Am')",
            "needs_approval",
            "Background scanner checked the Christology index and identified a study on John 8:58 & Exodus 3:14 ('Ego Eimi') ready for argument-aware normalization.",
            json.dumps({"urls_checked": 18, "new_candidates": 1, "broken_links": 0}),
            json.dumps(
                [
                    {"stage": "1. Sitemap & Hash Diff", "status": "PASS", "detail": "Checked 18 catalog URLs against SQLite content_hash index; found 1 unindexed URL."},
                    {"stage": "2. Argument-Aware Splitter", "status": "PASS", "detail": "Split candidate into 3 chunks (2 author_argument, 1 quoted_objection linked to rebuttal ch3)."},
                    {"stage": "3. Reference Fast-Path Extractor", "status": "PASS", "detail": "Extracted Bible tags: John 8:58, John 8:59, Exodus 3:14, Isaiah 43:10, John 9:9."},
                    {"stage": "4. Editorial Approval Gate", "status": "AWAITING_APPROVAL", "detail": "Paused before database write; awaiting reviewer approval."},
                ]
            ),
            json.dumps(
                {
                    "action": "ingest_source",
                    "source": {
                        "id": "src_archive_john8_58",
                        "url": "https://biblehub.com/commentaries/john/8-58.htm",
                        "canonical_url": "https://biblehub.com/commentaries/john/8-58.htm",
                        "title": "Jesus' Claim to be the Eternal 'I AM' in John 8:58 and Exodus 3:14",
                        "author": "Exegetical Research Archive",
                        "source_type": "archive_article",
                        "media_type": "article",
                        "topic": "Deity of Christ · John 8:58",
                        "permission_mode": "snippet_link_only",
                        "published_date": "2024-03-14",
                        "chunks": [
                            {
                                "section_title": "John 8:58 ('Before Abraham Was, I Am') and the Septuagint of Exodus 3:14 & Isaiah 43:10",
                                "discourse_type": "author_argument",
                                "paired_chunk_index": None,
                                "text_content": (
                                    "In John 8:58, Jesus declares to His opponents, 'Truly, truly, I say "
                                    "to you, before Abraham was born, I am (prin Abraam genesthai egō eimi).' "
                                    "Grammatical analysis demonstrates that Jesus does not merely say 'I existed before Abraham' "
                                    "(which would require the imperfect 'ēmēn' as in John 1:1); instead, He uses the "
                                    "present-tense absolute 'egō eimi', echoing Yahweh's self-designation in "
                                    "Exodus 3:14 and Isaiah 43:10-13 ('before day was, I am He'). That is why the "
                                    "audience immediately picked up stones to stone Him for blasphemy (John 8:59; "
                                    "cf. John 10:30-33)."
                                ),
                            },
                            {
                                "section_title": "Objection That 'Ego Eimi' Only Means 'I Am He (the Beggar)' in John 9:9",
                                "discourse_type": "quoted_objection",
                                "paired_chunk_index": 3,
                                "text_content": (
                                    "Critics point to John 9:9 (where the healed blind man says 'egō eimi') to argue that "
                                    "the phrase in John 8:58 merely means 'I am the one' rather than the divine name of Exodus 3:14."
                                ),
                            },
                            {
                                "section_title": "Rebuttal on the Syntactical Contrast in John 8:58",
                                "discourse_type": "author_argument",
                                "paired_chunk_index": None,
                                "text_content": (
                                    "Context and syntax govern meaning: in John 9:9 the blind man is simply "
                                    "identifying himself as the beggar, whereas in John 8:58 Jesus contrasts Abraham's coming into "
                                    "existence ('genesthai', aorist infinitive of 'ginomai') with His own timeless, eternal existence "
                                    "('egō eimi', present indicative). Combined with John 8:24 and John 13:19, this directly echoes "
                                    "Yahweh's self-disclosure in Isaiah 43:10."
                                ),
                            },
                        ],
                    },
                }
            ),
            ts,
        ),
    )

    conn.commit()
    conn.close()
    return {"seeded": True, "message": "Seeded neutral Exegetical Research Archive corpus, Scripture/Quran/Hadith index, and Rebuttal Tree."}
