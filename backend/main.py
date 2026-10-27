import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse

from backend.config import HERMES_SETTINGS, OPENROUTER_API_KEY, PROJECT_ROOT
from backend.database import init_db, get_conn
from backend.seed_corpus import seed_initial_corpus
from backend.synthesizer import generate_research_answer_sync
from backend.hermes_ops import (
    run_job_discover,
    run_job_normalize,
    run_job_qa_benchmark,
    run_job_gap_analysis,
    propose_custom_article_ingestion,
    approve_hermes_job,
    reject_hermes_job,
)


def get_system_status() -> dict:
    conn = get_conn()
    cur = conn.cursor()
    sources_count = cur.execute("SELECT COUNT(*) FROM sources").fetchone()[0]
    chunks_count = cur.execute("SELECT COUNT(*) FROM document_chunks").fetchone()[0]
    scriptures_count = cur.execute("SELECT COUNT(*) FROM scripture_passages").fetchone()[0]
    gold_count = cur.execute("SELECT COUNT(*) FROM gold_questions").fetchone()[0]
    pending_approvals = cur.execute(
        "SELECT COUNT(*) FROM hermes_jobs WHERE status = 'needs_approval'"
    ).fetchone()[0]
    conn.close()

    return {
        "status": "online",
        "hermes_openrouter_configured": bool(OPENROUTER_API_KEY),
        "primary_model": HERMES_SETTINGS["default_model"],
        "fallback_models": HERMES_SETTINGS["fallback_models"],
        "counts": {
            "sources": sources_count,
            "chunks": chunks_count,
            "scriptures": scriptures_count,
            "gold_questions": gold_count,
            "pending_approvals": pending_approvals,
        },
    }


def list_sources() -> dict:
    conn = get_conn()
    cur = conn.cursor()
    sources = [dict(r) for r in cur.execute("SELECT * FROM sources ORDER BY id").fetchall()]
    for s in sources:
        chunks = [
            {
                "id": c["id"],
                "chunk_index": c["chunk_index"],
                "section_title": c["section_title"],
                "discourse_type": c["discourse_type"],
                "paired_chunk_id": c["paired_chunk_id"],
                "text_content": c["text_content"],
                "scripture_refs": json.loads(c["scripture_refs_json"] or "[]"),
            }
            for c in cur.execute(
                "SELECT id, chunk_index, section_title, discourse_type, paired_chunk_id, text_content, scripture_refs_json FROM document_chunks WHERE source_id = ? ORDER BY chunk_index",
                (s["id"],),
            ).fetchall()
        ]
        s["chunks"] = chunks

    scriptures = [
        {
            "id": sp["id"],
            "corpus": sp["corpus"],
            "reference": sp["reference"],
            "translation": sp["translation"],
            "text_content": sp["text_content"],
            "original_language_note": sp["original_language_note"],
            "topic_tags": json.loads(sp["topic_tags_json"] or "[]"),
        }
        for sp in cur.execute("SELECT * FROM scripture_passages").fetchall()
    ]
    conn.close()
    return {"sources": sources, "scriptures": scriptures}


def get_hermes_dashboard() -> dict:
    conn = get_conn()
    cur = conn.cursor()
    jobs = []
    for r in cur.execute("SELECT * FROM hermes_jobs ORDER BY created_at DESC LIMIT 20").fetchall():
        d = dict(r)
        d["metrics"] = json.loads(d["metrics_json"] or "{}")
        d["pipeline_steps"] = json.loads(d["pipeline_steps_json"] or "[]") if d.get("pipeline_steps_json") else []
        d["proposed_action"] = json.loads(d["proposed_action_json"]) if d["proposed_action_json"] else None
        jobs.append(d)

    gold_questions = []
    for gq in cur.execute("SELECT * FROM gold_questions").fetchall():
        gd = dict(gq)
        gd["expected_source_ids"] = json.loads(gd["expected_source_ids_json"] or "[]")
        gd["expected_scripture_refs"] = json.loads(gd["expected_scripture_refs_json"] or "[]")
        gold_questions.append(gd)

    conn.close()
    return {"jobs": jobs, "gold_questions": gold_questions}


class DefendThaFaithHandler(BaseHTTPRequestHandler):
    def _send_json(self, data: dict, status: int = 200):
        body = json.dumps(data).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def _send_text(self, text: str, content_type: str = "text/html; charset=utf-8", status: int = 200):
        body = text.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        path = urlparse(self.path).path
        if path in ("/", "/index.html"):
            html_path = PROJECT_ROOT / "frontend" / "index.html"
            self._send_text(html_path.read_text(encoding="utf-8"), "text/html; charset=utf-8")
        elif path == "/styles.css":
            css_path = PROJECT_ROOT / "frontend" / "styles.css"
            if css_path.exists():
                self._send_text(css_path.read_text(encoding="utf-8"), "text/css; charset=utf-8")
            else:
                self._send_text("", "text/css; charset=utf-8", status=404)
        elif path == "/api/status":
            self._send_json(get_system_status())
        elif path == "/api/sources":
            self._send_json(list_sources())
        elif path == "/api/hermes/dashboard":
            self._send_json(get_hermes_dashboard())
        else:
            self._send_json({"error": "Not found"}, status=404)

    def do_POST(self):
        path = urlparse(self.path).path
        content_len = int(self.headers.get("Content-Length", 0))
        raw_body = self.rfile.read(content_len).decode("utf-8") if content_len > 0 else "{}"
        try:
            payload = json.loads(raw_body) if raw_body.strip() else {}
        except Exception:
            payload = {}

        if path == "/api/research/query":
            question = payload.get("question", "").strip()
            if not question:
                self._send_json({"error": "Question is required"}, status=400)
                return
            mode = payload.get("research_mode", "exegetical_archive")
            parent_context = payload.get("parent_context", "").strip()
            use_llm = bool(payload.get("use_llm", True))
            res = generate_research_answer_sync(
                question,
                research_mode=mode,
                parent_context=parent_context,
                use_llm=use_llm,
            )
            self._send_json(res)
            return

        if path == "/api/hermes/ingest-preview":
            try:
                res = propose_custom_article_ingestion(
                    title=payload.get("title", "Custom Archive Study").strip(),
                    url=payload.get("url", "").strip(),
                    topic=payload.get("topic", "Christology · Exegesis").strip(),
                    raw_text=payload.get("raw_text", "").strip(),
                    permission_mode=payload.get("permission_mode", "snippet_link_only"),
                )
                self._send_json(res)
            except Exception as e:
                self._send_json({"error": str(e)}, status=400)
            return

        if path.startswith("/api/hermes/run/"):
            job_type = path.split("/api/hermes/run/")[-1].strip("/")
            if job_type == "discover":
                self._send_json(run_job_discover())
            elif job_type == "normalize":
                self._send_json(run_job_normalize())
            elif job_type == "qa_benchmark":
                self._send_json(run_job_qa_benchmark())
            elif job_type == "gap_analysis":
                self._send_json(run_job_gap_analysis())
            else:
                self._send_json({"error": f"Unknown job type: {job_type}"}, status=400)
            return

        if path.startswith("/api/hermes/jobs/") and path.endswith("/approve"):
            job_id = path.split("/api/hermes/jobs/")[-1].removesuffix("/approve").strip("/")
            self._send_json(approve_hermes_job(job_id))
            return

        if path.startswith("/api/hermes/jobs/") and path.endswith("/reject"):
            job_id = path.split("/api/hermes/jobs/")[-1].removesuffix("/reject").strip("/")
            self._send_json(reject_hermes_job(job_id))
            return

        self._send_json({"error": "Endpoint not found"}, status=404)


def run_server(host: str = "127.0.0.1", port: int = 8000):
    init_db()
    seed_initial_corpus()
    server = ThreadingHTTPServer((host, port), DefendThaFaithHandler)
    print(f"Defend the Faith server listening on http://{host}:{port}")
    server.serve_forever()


if __name__ == "__main__":
    run_server()
