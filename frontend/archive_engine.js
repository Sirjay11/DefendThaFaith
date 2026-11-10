// Standalone Serverless & Client-Side Research Engine for Netlify Deployment
// Mirrors backend/retriever.py, backend/synthesizer.py, and backend/hermes_ops.py

let ARCHIVE_CACHE = null;

const STOPWORDS = new Set([
  "the", "and", "for", "that", "this", "with", "from", "what", "how", "does",
  "did", "are", "was", "were", "have", "has", "had", "not", "but", "you",
  "his", "her", "they", "their", "about", "into", "who", "whom", "whose",
  "why", "when", "where", "which", "can", "could", "would", "should", "will",
  "position", "detailed", "respond", "response", "argument", "teach",
  "say", "says", "said", "call", "calls", "asked", "century"
]);

async function getArchiveData() {
  if (ARCHIVE_CACHE) return ARCHIVE_CACHE;
  const res = await fetch('/archive_data.json');
  ARCHIVE_CACHE = await res.json();
  return ARCHIVE_CACHE;
}

function tokenizeKeywords(text) {
  const matches = String(text || '').toLowerCase().match(/[a-z0-9']+/g) || [];
  return matches.filter(t => t.length > 2 && !STOPWORDS.has(t));
}

function extractReferencesClient(text) {
  if (!text) return [];
  const refs = new Set();
  const s = String(text);

  // Quran numeric e.g. Surah 4:171
  const qRegex = /\b(?:Surah|Sura|Quran|Qur'an|Q\.?)\s*(\d{1,3}):(\d{1,3})(?:[-–—](\d{1,3}))?\b/gi;
  let m;
  while ((m = qRegex.exec(s)) !== null) {
    const surah = parseInt(m[1], 10);
    const start = parseInt(m[2], 10);
    const end = m[3] ? parseInt(m[3], 10) : start;
    refs.add(`Surah ${surah}:${start}`);
    for (let v = start; v <= Math.min(end, start + 15); v++) {
      refs.add(`Surah ${surah}:${v}`);
    }
  }

  // Hadith e.g. Sahih al-Bukhari 3448, Sahih Muslim 2365
  const hRegex = /\b(Sahih\s+al-Bukhari|Bukhari|Sahih\s+Muslim|Muslim)\s*(\d{1,5})\b/gi;
  while ((m = hRegex.exec(s)) !== null) {
    const coll = m[1].toLowerCase().includes('muslim') ? 'Sahih Muslim' : 'Sahih al-Bukhari';
    refs.add(`${coll} ${parseInt(m[2], 10)}`);
  }

  // Bible e.g. Philippians 2:10-11, John 1:1, John 14:28, Mark 10:18, Hebrews 1:8-12
  const bRegex = /\b((?:[123]\s*)?[A-Za-z]+)\.?\s+(\d{1,3}):(\d{1,3})(?:[-–—](\d{1,3}))?\b/g;
  const bookMap = {
    "john": "John", "jn": "John",
    "philippians": "Philippians", "phil": "Philippians",
    "isaiah": "Isaiah", "isa": "Isaiah",
    "hebrews": "Hebrews", "heb": "Hebrews",
    "psalm": "Psalms", "psalms": "Psalms", "ps": "Psalms",
    "mark": "Mark", "mk": "Mark",
    "matthew": "Matthew", "matt": "Matthew",
    "exodus": "Exodus", "ex": "Exodus",
    "1 peter": "1 Peter", "romans": "Romans"
  };
  while ((m = bRegex.exec(s)) !== null) {
    const rawBook = m[1].trim().toLowerCase().replace(/\s+/g, ' ');
    if (['surah', 'sura', 'quran', 'q'].includes(rawBook)) continue;
    const book = bookMap[rawBook];
    if (!book) continue;
    const ch = parseInt(m[2], 10);
    const vStart = parseInt(m[3], 10);
    const vEnd = m[4] ? parseInt(m[4], 10) : vStart;
    refs.add(`${book} ${ch}:${vStart}`);
    for (let v = vStart; v <= Math.min(vEnd, vStart + 15); v++) {
      refs.add(`${book} ${ch}:${v}`);
    }
  }

  return Array.from(refs).sort();
}

async function queryArchiveClient(question, parentContext = '', researchMode = 'exegetical_archive') {
  const archive = await getArchiveData();
  const sources = archive.catalog.sources || [];
  const scriptures = archive.catalog.scriptures || [];
  const rebuttalTrees = archive.rebuttal_trees || {};

  const combinedQuery = parentContext ? `${question} ${parentContext}` : question;
  const parsedRefs = new Set(extractReferencesClient(combinedQuery));
  const qTokens = new Set(tokenizeKeywords(question));
  const ctxTokens = new Set(tokenizeKeywords(parentContext));

  const allChunks = [];
  const chunkById = {};

  for (const src of sources) {
    for (const ch of (src.chunks || [])) {
      const chunkRefs = new Set(ch.scripture_refs || []);
      const docText = `${src.title} ${ch.section_title} ${ch.text_content} ${src.topic}`;
      const docTokens = new Set(tokenizeKeywords(docText));

      const matchedRefs = Array.from(parsedRefs).filter(r => chunkRefs.has(r));
      const refScore = Math.min(1.0, matchedRefs.length * 0.7);

      let lexScore = 0;
      if (qTokens.size > 0) {
        let overlap = 0;
        qTokens.forEach(t => {
          if (docTokens.has(t)) overlap++;
        });
        lexScore = overlap / Math.max(1, Math.min(qTokens.size, 8));
      }

      let ctxScore = 0;
      if (ctxTokens.size > 0) {
        let cOverlap = 0;
        ctxTokens.forEach(t => {
          if (docTokens.has(t)) cOverlap++;
        });
        ctxScore = (cOverlap / Math.max(1, Math.min(ctxTokens.size, 8))) * 0.35;
      }

      let totalScore = (refScore * 0.55) + (lexScore * 0.65) + ctxScore;
      if (researchMode === 'exegetical_archive' && ch.discourse_type === 'author_argument') {
        totalScore *= 1.12;
      }

      const item = {
        chunk_id: ch.id,
        source_id: src.id,
        chunk_index: ch.chunk_index,
        section_title: ch.section_title,
        discourse_type: ch.discourse_type,
        paired_chunk_id: ch.paired_chunk_id,
        text_content: ch.text_content,
        scripture_refs: ch.scripture_refs || [],
        fast_path_matched_refs: matchedRefs,
        source_title: src.title,
        source_url: src.url,
        author: src.author,
        permission_mode: src.permission_mode,
        topic: src.topic,
        score: Number(Math.min(0.99, totalScore).toFixed(3))
      };
      chunkById[item.chunk_id] = item;
      if (totalScore > 0.14) {
        allChunks.push(item);
      }
    }
  }

  allChunks.sort((a, b) => b.score - a.score);
  const topChunks = allChunks.slice(0, 5);
  const existingIds = new Set(topChunks.map(c => c.chunk_id));

  // Enforce Objection-to-Rebuttal Pairing
  for (const c of [...topChunks]) {
    if (c.discourse_type === 'quoted_objection' && c.paired_chunk_id) {
      const reb = chunkById[c.paired_chunk_id];
      if (reb && !existingIds.has(reb.chunk_id)) {
        topChunks.unshift(reb);
        existingIds.add(reb.chunk_id);
      }
    }
  }

  // Include paired objection for top source so Counterargument section is populated
  const topSourceIds = new Set(topChunks.slice(0, 2).map(c => c.source_id));
  for (const c of allChunks) {
    if (topSourceIds.has(c.source_id) && !existingIds.has(c.chunk_id) && topChunks.length < 7) {
      topChunks.push(c);
      existingIds.add(c.chunk_id);
    }
  }

  const targetRefs = new Set(parsedRefs);
  topChunks.slice(0, 3).forEach(c => (c.scripture_refs || []).forEach(r => targetRefs.add(r)));

  const scoredScriptures = [];
  for (const sp of scriptures) {
    const sText = `${sp.reference} ${sp.text_content} ${sp.original_language_note} ${(sp.topic_tags || []).join(' ')}`;
    const sTokens = new Set(tokenizeKeywords(sText));
    let refHit = targetRefs.has(sp.reference) ? 1.0 : 0.0;
    if (!refHit) {
      for (const r of targetRefs) {
        if (sp.reference.startsWith(r) || r.startsWith(sp.reference.split('-')[0])) {
          refHit = 0.85;
          break;
        }
      }
    }
    let lexHit = 0;
    if (qTokens.size > 0) {
      let ov = 0;
      qTokens.forEach(t => { if (sTokens.has(t)) ov++; });
      lexHit = ov / Math.max(1, Math.min(qTokens.size, 7));
    }
    const sScore = (refHit * 0.75) + (lexHit * 0.45);
    if (sScore > 0.15) {
      scoredScriptures.push({
        ...sp,
        score: Number(Math.min(0.99, sScore).toFixed(3))
      });
    }
  }
  scoredScriptures.sort((a, b) => b.score - a.score);
  const topScriptures = scoredScriptures.slice(0, 4);

  const bestChunkScore = topChunks.length ? topChunks[0].score : 0;
  const confidence = Number(Math.max(bestChunkScore, (topScriptures[0]?.score || 0) * 0.85).toFixed(3));
  const abstain = confidence < 0.24 || topChunks.length === 0;

  const defaultBranches = [
    { id: "reb_1", question: "If Jesus is God, why does He pray to the Father?", label: "Objection 1 · Prayer of the Incarnate Son & John 14:28" },
    { id: "reb_2", question: "Why does Jesus call the Father 'the only true God' in John 17:3?", label: "Objection 2 · 'The Only True God' in John 17:3–5" },
    { id: "reb_3", question: "Did Jesus deny being God when He asked 'Why do you call me good?' in Mark 10:18?", label: "Objection 3 · 'Why Do You Call Me Good?' (Mark 10:17–18)" },
    { id: "reb_4", question: "Does Philippians 2:10–11 identify Jesus as Yahweh?", label: "Objection 4 · Every Knee Bowing to Jesus (Isaiah 45:23 & Phil 2:10–11)" }
  ];

  if (abstain) {
    return {
      abstained: true,
      question,
      classification: "Insufficient Verified Evidence · Logged for Archive Expansion",
      confidence_score: confidence,
      direct_answer: "Limitation Notice: The archive did not find verified primary or commentary material in the currently indexed library to substantiate an answer to this specific question. Rather than speculating or citing unverified sources, this question has been logged for future catalog indexing.",
      short_answer: "Limitation Notice: The archive did not find verified primary or commentary material in the currently indexed library to substantiate an answer to this specific question.",
      primary_evidence: topScriptures,
      archive_arguments: [],
      logical_reasoning: [],
      counterargument: null,
      conversation_ready_response: null,
      rebuttal_tree: defaultBranches,
      explore_further: defaultBranches.map(b => b.question)
    };
  }

  const authorChunks = topChunks.filter(c => c.discourse_type === 'author_argument');
  const objectionChunks = topChunks.filter(c => c.discourse_type === 'quoted_objection');
  const primaryChunk = authorChunks[0] || topChunks[0];

  const archiveArguments = (authorChunks.length ? authorChunks : [primaryChunk]).slice(0, 3).map(ac => ({
    section_title: ac.section_title,
    summary: ac.text_content,
    verbatim_quote: ac.text_content,
    how_it_supports: `Connects ${(ac.scripture_refs || []).slice(0, 4).join(', ') || 'the surrounding passage'} directly to the grammatical and historical context in '${ac.source_title}'.`,
    source_id: ac.source_id,
    chunk_id: ac.chunk_id,
    source_title: ac.source_title,
    source_url: ac.source_url,
    author: ac.author,
    permission_mode: ac.permission_mode
  }));

  const logicalReasoning = [];
  if (topScriptures.length > 0) {
    logicalReasoning.push({
      step_type: "Established Textual Fact",
      statement: `${topScriptures[0].reference} (${topScriptures[0].corpus}) states: "${topScriptures[0].text_content}"`
    });
    if (topScriptures[0].original_language_note) {
      logicalReasoning.push({
        step_type: "Linguistic & Contextual Evidence",
        statement: topScriptures[0].original_language_note
      });
    }
  }
  logicalReasoning.push({
    step_type: "Documented Exegetical Argument",
    statement: primaryChunk.text_content
  });
  if (authorChunks.length > 1) {
    logicalReasoning.push({
      step_type: "Theological Conclusion",
      statement: authorChunks[1].text_content
    });
  }

  const obj = objectionChunks[0];
  const pairedReb = obj ? (authorChunks.find(c => c.chunk_id === obj.paired_chunk_id) || authorChunks[authorChunks.length - 1] || primaryChunk) : primaryChunk;
  const counterargument = obj ? {
    objection_title: obj.section_title,
    objection_claim: obj.text_content,
    exegetical_rebuttal: pairedReb.text_content,
    rebuttal_chunk_id: pairedReb.chunk_id,
    source_title: obj.source_title,
    source_url: obj.source_url,
    chunk_id: obj.chunk_id
  } : {
    objection_title: "Competing Interpretation",
    objection_claim: "A critic may argue that high Christological titles or functional submission passages reflect prophetic agency rather than ontological equality with God.",
    exegetical_rebuttal: primaryChunk.text_content,
    rebuttal_chunk_id: primaryChunk.chunk_id,
    source_title: primaryChunk.source_title,
    source_url: primaryChunk.source_url,
    chunk_id: primaryChunk.chunk_id
  };

  const topRefs = topScriptures.slice(0, 2).map(s => s.reference).join(', ') || 'Scripture';
  const conversationReady = `When someone asks this, a clear way to respond is: "Look at ${topRefs} in context. ${primaryChunk.text_content} If we read the whole passage rather than isolating a single verse, the text consistently affirms both Christ's true humanity as a servant and His eternal divine identity alongside the Father."`;

  const branches = (rebuttalTrees[primaryChunk.source_id] || defaultBranches)
    .filter(b => b.question.toLowerCase() !== question.toLowerCase())
    .slice(0, 4);

  return {
    abstained: false,
    question,
    classification: primaryChunk.topic,
    confidence_score: confidence,
    direct_answer: primaryChunk.text_content,
    short_answer: primaryChunk.text_content,
    primary_evidence: topScriptures,
    archive_arguments: archiveArguments,
    logical_reasoning: logicalReasoning,
    counterargument,
    conversation_ready_response: conversationReady,
    rebuttal_tree: branches,
    explore_further: branches.map(b => b.question)
  };
}
