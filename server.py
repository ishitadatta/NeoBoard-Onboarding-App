#!/usr/bin/env python3
import base64
import json
import math
import re
import sqlite3
import urllib.error
import urllib.request
from collections import Counter
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Dict, List, Tuple
from urllib.parse import parse_qs, unquote, urlparse

ROOT = Path(__file__).resolve().parent
WEB_DIR = ROOT / "web"
DATA_DIR = ROOT / "data"
DB_PATH = DATA_DIR / "neoboard.db"
HOST = "127.0.0.1"
PORT = 8787

DEFAULT_MILESTONES = [
    "Complete training",
    "Unlock all accesses",
    "Debug codebase",
    "Commit to GitHub"
]

DEFAULT_TASKS = [
    {"text": "Install IDE, Git, Docker, and language toolchains", "priority": "high", "phase_rank": 0},
    {"text": "Run project bootstrap and pass smoke tests locally", "priority": "high", "phase_rank": 0},
    {"text": "Read architecture overview and dependency map", "priority": "normal", "phase_rank": 0},
    {"text": "Request baseline IAM permissions and VPN access", "priority": "high", "phase_rank": 1},
    {"text": "Validate cloud sandbox access with least privilege", "priority": "normal", "phase_rank": 1},
    {"text": "Create first access request ticket using template", "priority": "normal", "phase_rank": 1},
    {"text": "Triage one bug and collect logs with request IDs", "priority": "high", "phase_rank": 2},
    {"text": "Write one failing test and implement the fix", "priority": "high", "phase_rank": 2},
    {"text": "Confirm fix with regression checks and peer review", "priority": "normal", "phase_rank": 2},
    {"text": "Create feature branch and open your first PR", "priority": "high", "phase_rank": 3},
    {"text": "Pass CI checks and address review comments", "priority": "high", "phase_rank": 3},
    {"text": "Merge PR and post release verification notes", "priority": "normal", "phase_rank": 3}
]

DEFAULT_DOCS = [
    {
        "title": "Laptop Setup Checklist",
        "phase": "Complete training",
        "kind": "guide",
        "source": "internal",
        "content": "Install IDE, Git, Docker, VPN, and request baseline credentials. Validate access to email, Jira, and GitHub.",
        "tags": ["setup", "tools", "access"]
    },
    {
        "title": "Access Request Playbook",
        "phase": "Unlock all accesses",
        "kind": "policy",
        "source": "internal",
        "content": "Cloud permissions are approved by platform admin and engineering manager. Submit request ticket with team, role, and least privilege scope.",
        "tags": ["permissions", "cloud", "security"]
    },
    {
        "title": "Codebase Debugging Guide",
        "phase": "Debug codebase",
        "kind": "guide",
        "source": "internal",
        "content": "Run unit tests, inspect logs, isolate failing module, and verify fix with regression tests. Pair with a reviewer for system-level issues.",
        "tags": ["debugging", "testing", "codebase"]
    },
    {
        "title": "GitHub Contribution Standards",
        "phase": "Commit to GitHub",
        "kind": "standards",
        "source": "internal",
        "content": "Use feature branches, keep PRs small, include screenshots, and request two reviewers. Merge only after CI passes.",
        "tags": ["github", "pull-request", "ci"]
    },
    {
        "title": "30-60-90 Onboarding Roadmap",
        "phase": "Goals complete",
        "kind": "roadmap",
        "source": "internal",
        "content": "First 30 days complete setup and baseline training. Next 30 days ship production-safe tasks. Final 30 days own a scoped project.",
        "tags": ["onboarding", "goals", "roadmap"]
    },
    {
        "title": "Local Development Environment Runbook",
        "phase": "Complete training",
        "kind": "runbook",
        "source": "internal",
        "content": "Clone repositories, install language toolchains, bootstrap secrets with the vault CLI, run make setup, and verify services with smoke tests.",
        "tags": ["dev-env", "setup", "tooling", "runbook"]
    },
    {
        "title": "Repository Architecture Overview",
        "phase": "Complete training",
        "kind": "architecture",
        "source": "internal",
        "content": "The platform is split into API, worker, and frontend packages. Shared contracts live in libs/contracts and infra manifests are under deploy/",
        "tags": ["architecture", "repo", "services"]
    },
    {
        "title": "Identity and Access Matrix",
        "phase": "Unlock all accesses",
        "kind": "policy",
        "source": "internal",
        "content": "Request least-privilege access by role. Production write access requires manager approval and temporary elevation with expiration.",
        "tags": ["iam", "permissions", "security", "access"]
    },
    {
        "title": "Cloud Account and Sandbox Guide",
        "phase": "Unlock all accesses",
        "kind": "guide",
        "source": "internal",
        "content": "Use sandbox accounts for experimentation, staging for integration checks, and production only through approved pipelines and break-glass processes.",
        "tags": ["cloud", "aws", "sandbox", "staging"]
    },
    {
        "title": "Secrets Management Standards",
        "phase": "Unlock all accesses",
        "kind": "standards",
        "source": "internal",
        "content": "Never commit secrets to git. Store credentials in vault, rotate quarterly, scope by service account, and audit secret usage monthly.",
        "tags": ["secrets", "security", "vault", "compliance"]
    },
    {
        "title": "Service Debugging Workflow",
        "phase": "Debug codebase",
        "kind": "runbook",
        "source": "internal",
        "content": "Reproduce issue, capture request IDs, inspect structured logs, trace downstream dependencies, write failing test, patch, and confirm recovery metrics.",
        "tags": ["debugging", "logs", "tracing", "runbook"]
    },
    {
        "title": "Testing Pyramid for Backend Services",
        "phase": "Debug codebase",
        "kind": "standards",
        "source": "internal",
        "content": "Prioritize unit tests, add contract tests for interfaces, and keep end-to-end tests focused on core customer journeys and critical error cases.",
        "tags": ["testing", "unit", "integration", "quality"]
    },
    {
        "title": "Observability Starter Guide",
        "phase": "Debug codebase",
        "kind": "guide",
        "source": "internal",
        "content": "Dashboards track latency, error rate, saturation, and throughput. Alerts route to on-call with runbook links and escalation policy.",
        "tags": ["observability", "metrics", "alerts", "sre"]
    },
    {
        "title": "Pull Request Quality Checklist",
        "phase": "Commit to GitHub",
        "kind": "checklist",
        "source": "internal",
        "content": "Include problem statement, scope boundaries, tests added, migration notes, and rollback plan. Keep PR under 500 lines where possible.",
        "tags": ["pull-request", "review", "quality", "github"]
    },
    {
        "title": "Code Review Etiquette and SLAs",
        "phase": "Commit to GitHub",
        "kind": "policy",
        "source": "internal",
        "content": "Authors should respond within one business day. Reviewers prioritize correctness, reliability, and maintainability before stylistic feedback.",
        "tags": ["review", "engineering-culture", "sla"]
    },
    {
        "title": "CI/CD Pipeline Troubleshooting",
        "phase": "Commit to GitHub",
        "kind": "runbook",
        "source": "internal",
        "content": "Check failing stage logs, reproduce locally with the same commands, validate artifact versions, and rerun only after fixing root cause.",
        "tags": ["ci", "cd", "pipeline", "troubleshooting"]
    },
    {
        "title": "Incident Response for New Engineers",
        "phase": "Goals complete",
        "kind": "runbook",
        "source": "internal",
        "content": "Acknowledge incident, gather evidence in timeline order, communicate status updates every 15 minutes, and focus on mitigation before root cause.",
        "tags": ["incident", "on-call", "sre", "response"]
    },
    {
        "title": "Production Readiness Checklist",
        "phase": "Goals complete",
        "kind": "checklist",
        "source": "internal",
        "content": "Ensure feature flags exist, dashboards are configured, alerts tuned, load tests executed, security review completed, and rollback plan documented.",
        "tags": ["production", "readiness", "release", "quality"]
    },
    {
        "title": "Ownership and Career Growth Map",
        "phase": "Goals complete",
        "kind": "roadmap",
        "source": "internal",
        "content": "By month three, own a scoped service area, lead one postmortem action stream, and mentor the next onboarding cohort on dev environment setup.",
        "tags": ["growth", "ownership", "mentorship"]
    }
]

STOPWORDS = {
    "a", "an", "and", "the", "is", "are", "to", "for", "of", "in", "on", "with", "at", "from",
    "by", "be", "or", "as", "this", "that", "it", "how", "what", "where", "when", "who", "why",
    "i", "you", "we", "they", "can", "do", "does", "did", "am", "my", "our", "your"
}


def utc_now() -> str:
    return datetime.utcnow().isoformat(timespec="seconds") + "Z"


def tokenize(text: str) -> List[str]:
    tokens = re.findall(r"[a-zA-Z0-9]+", (text or "").lower())
    return [t for t in tokens if t not in STOPWORDS and len(t) > 1]


def split_sentences(text: str) -> List[str]:
    parts = re.split(r"(?<=[.!?])\s+", text.strip())
    return [p.strip() for p in parts if p.strip()]


def cosine_similarity(a: Dict[str, float], b: Dict[str, float]) -> float:
    if not a or not b:
        return 0.0
    shared = set(a.keys()) & set(b.keys())
    dot = sum(a[k] * b[k] for k in shared)
    norm_a = math.sqrt(sum(v * v for v in a.values()))
    norm_b = math.sqrt(sum(v * v for v in b.values()))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


def tfidf_vectors(texts: List[str]) -> List[Dict[str, float]]:
    docs_tokens = [tokenize(t) for t in texts]
    df = Counter()
    for tokens in docs_tokens:
        for tok in set(tokens):
            df[tok] += 1
    total_docs = max(1, len(docs_tokens))

    vectors = []
    for tokens in docs_tokens:
        tf = Counter(tokens)
        max_tf = max(tf.values()) if tf else 1
        vec = {}
        for tok, count in tf.items():
            tf_weight = count / max_tf
            idf_weight = math.log((1 + total_docs) / (1 + df[tok])) + 1
            vec[tok] = tf_weight * idf_weight
        vectors.append(vec)
    return vectors


def extractive_summary(text: str, max_sentences: int = 3) -> str:
    sentences = split_sentences(text)
    if len(sentences) <= max_sentences:
        return " ".join(sentences)

    sentence_vectors = tfidf_vectors(sentences)
    doc_vector = tfidf_vectors([text])[0]
    scored = []
    for idx, sentence in enumerate(sentences):
        score = cosine_similarity(sentence_vectors[idx], doc_vector)
        scored.append((score, idx, sentence))

    best = sorted(scored, key=lambda x: x[0], reverse=True)[:max_sentences]
    ordered = sorted(best, key=lambda x: x[1])
    return " ".join(s[2] for s in ordered)


def ensure_dirs():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    WEB_DIR.mkdir(parents=True, exist_ok=True)


def connect_db() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def table_columns(cur: sqlite3.Cursor, table: str) -> set:
    cur.execute(f"PRAGMA table_info({table})")
    return {row[1] for row in cur.fetchall()}


def default_anchors(title: str) -> List[Dict]:
    anchor_map = {
        "Laptop Setup Checklist": [
            {"topic": "install", "page": 4, "paragraph": 2, "note": "IDE, Git, Docker installation steps"},
            {"topic": "credentials", "page": 9, "paragraph": 1, "note": "Baseline account access checklist"}
        ],
        "Access Request Playbook": [
            {"topic": "permissions", "page": 33, "paragraph": 4, "note": "Approval chain for cloud access"},
            {"topic": "ticket-template", "page": 36, "paragraph": 2, "note": "Required fields for request ticket"}
        ],
        "Identity and Access Matrix": [
            {"topic": "access-matrix", "page": 29, "paragraph": 2, "note": "Role to permission matrix"},
            {"topic": "elevation", "page": 31, "paragraph": 5, "note": "Temporary elevated access policy"}
        ],
        "Cloud Account and Sandbox Guide": [
            {"topic": "sandbox", "page": 22, "paragraph": 3, "note": "Sandbox account setup and constraints"},
            {"topic": "staging-production", "page": 26, "paragraph": 4, "note": "Promotion gates from staging to production"}
        ],
        "Service Debugging Workflow": [
            {"topic": "logs", "page": 55, "paragraph": 3, "note": "Trace and log correlation flow"},
            {"topic": "regression", "page": 58, "paragraph": 1, "note": "Regression validation checklist"}
        ],
        "CI/CD Pipeline Troubleshooting": [
            {"topic": "pipeline-failures", "page": 41, "paragraph": 2, "note": "Common failing stages and causes"},
            {"topic": "artifact-checks", "page": 44, "paragraph": 5, "note": "Artifact mismatch diagnosis"}
        ]
    }
    if title in anchor_map:
        return anchor_map[title]
    return [{"topic": "overview", "page": 12, "paragraph": 1, "note": "Document overview and key steps"}]


def select_anchor(doc: Dict, query: str) -> Dict:
    anchors = doc.get("anchors") or []
    if not anchors:
        return {"page": 1, "paragraph": 1, "note": "overview"}

    query_tokens = set(tokenize(query))
    best = anchors[0]
    best_score = -1
    for anchor in anchors:
        topic_tokens = set(tokenize(anchor.get("topic", "")))
        note_tokens = set(tokenize(anchor.get("note", "")))
        score = len(query_tokens & topic_tokens) * 2 + len(query_tokens & note_tokens)
        if score > best_score:
            best_score = score
            best = anchor
    return best


def seed_documents(conn: sqlite3.Connection, docs: List[Dict]) -> int:
    cur = conn.cursor()
    cur.execute("SELECT LOWER(title) AS title FROM documents")
    existing = {row["title"] for row in cur.fetchall()}

    inserted = 0
    for doc in docs:
        key = doc["title"].strip().lower()
        if key in existing:
            continue
        cur.execute(
            """
            INSERT INTO documents (title, phase, kind, source, content, tags, anchors, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                doc["title"],
                doc["phase"],
                doc["kind"],
                doc["source"],
                doc["content"],
                json.dumps(doc["tags"]),
                json.dumps(doc.get("anchors") or default_anchors(doc["title"])),
                utc_now()
            )
        )
        inserted += 1
        existing.add(key)
    return inserted


def seed_tasks(conn: sqlite3.Connection, tasks: List[Dict]) -> int:
    cur = conn.cursor()
    cur.execute("SELECT LOWER(text) AS text FROM tasks")
    existing = {row["text"] for row in cur.fetchall()}
    inserted = 0
    for task in tasks:
        key = task["text"].strip().lower()
        if key in existing:
            continue
        cur.execute(
            """
            INSERT INTO tasks (text, done, priority, phase_rank, created_at, completed_at)
            VALUES (?, 0, ?, ?, ?, NULL)
            """,
            (task["text"], task["priority"], task["phase_rank"], utc_now())
        )
        inserted += 1
        existing.add(key)
    return inserted


def init_db():
    ensure_dirs()
    conn = connect_db()
    cur = conn.cursor()

    cur.executescript(
        """
        CREATE TABLE IF NOT EXISTS milestones (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            label TEXT NOT NULL,
            done INTEGER NOT NULL DEFAULT 0,
            rank INTEGER NOT NULL,
            created_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            text TEXT NOT NULL,
            done INTEGER NOT NULL DEFAULT 0,
            priority TEXT NOT NULL DEFAULT 'normal',
            phase_rank INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL,
            completed_at TEXT
        );

        CREATE TABLE IF NOT EXISTS documents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            phase TEXT NOT NULL,
            kind TEXT NOT NULL,
            source TEXT NOT NULL,
            content TEXT NOT NULL,
            tags TEXT NOT NULL,
            anchors TEXT NOT NULL DEFAULT '[]',
            created_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS doc_links (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            from_doc_id INTEGER NOT NULL,
            to_doc_id INTEGER NOT NULL,
            score REAL NOT NULL,
            reason TEXT NOT NULL,
            created_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS chat_messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sender TEXT NOT NULL,
            message TEXT NOT NULL,
            created_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS doc_reads (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            doc_id INTEGER NOT NULL,
            created_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS weekly_plans (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            week_label TEXT NOT NULL,
            plan_text TEXT NOT NULL,
            done INTEGER NOT NULL DEFAULT 0,
            rank INTEGER NOT NULL,
            created_at TEXT NOT NULL
        );
        """
    )

    doc_cols = table_columns(cur, "documents")
    if "anchors" not in doc_cols:
        cur.execute("ALTER TABLE documents ADD COLUMN anchors TEXT NOT NULL DEFAULT '[]'")

    task_cols = table_columns(cur, "tasks")
    if "completed_at" not in task_cols:
        cur.execute("ALTER TABLE tasks ADD COLUMN completed_at TEXT")
    if "phase_rank" not in task_cols:
        cur.execute("ALTER TABLE tasks ADD COLUMN phase_rank INTEGER NOT NULL DEFAULT 0")

    cur.execute("SELECT id, title, anchors FROM documents")
    for row in cur.fetchall():
        anchors_raw = row["anchors"] if "anchors" in row.keys() else "[]"
        try:
            anchors = json.loads(anchors_raw or "[]")
        except Exception:
            anchors = []
        preferred = default_anchors(row["title"])
        has_specific_preferred = preferred and preferred[0].get("topic") != "overview"
        has_only_overview = anchors and anchors[0].get("topic") == "overview"
        if anchors and not (has_specific_preferred and has_only_overview):
            continue
        cur.execute(
            "UPDATE documents SET anchors = ? WHERE id = ?",
            (json.dumps(preferred), row["id"])
        )

    cur.execute("SELECT COUNT(*) AS c FROM milestones")
    if cur.fetchone()["c"] == 0:
        for rank, label in enumerate(DEFAULT_MILESTONES):
            cur.execute(
                "INSERT INTO milestones (label, done, rank, created_at) VALUES (?, 0, ?, ?)",
                (label, rank, utc_now())
            )

    seed_tasks(conn, DEFAULT_TASKS)

    inserted = seed_documents(conn, DEFAULT_DOCS)
    cur.execute("SELECT COUNT(*) AS c FROM weekly_plans")
    if cur.fetchone()["c"] == 0:
        default_plans = [
            "Week 1: Setup environment, accounts, and run first local service.",
            "Week 2: Read architecture docs and ship first test-only PR.",
            "Week 3: Own one bug-fix task from triage to merge.",
            "Week 4: Present onboarding learnings and reliability checklist."
        ]
        for idx, plan in enumerate(default_plans):
            cur.execute(
                "INSERT INTO weekly_plans (week_label, plan_text, done, rank, created_at) VALUES (?, ?, 0, ?, ?)",
                (f"Week {idx + 1}", plan, idx, utc_now())
            )
    cur.execute("SELECT COUNT(*) AS c FROM doc_links")
    link_count = cur.fetchone()["c"]
    conn.commit()
    sync_milestones_from_phases(conn)
    if inserted > 0 or link_count == 0:
        build_doc_links(conn, threshold=0.12)
    conn.close()


def row_to_task(row: sqlite3.Row) -> Dict:
    rank = int(row["phase_rank"] or 0)
    return {
        "id": row["id"],
        "text": row["text"],
        "done": bool(row["done"]),
        "priority": row["priority"],
        "phase_rank": rank,
        "phase_label": phase_label(rank),
        "created_at": row["created_at"],
        "completed_at": row["completed_at"]
    }


def row_to_doc(row: sqlite3.Row) -> Dict:
    tags = []
    anchors = []
    try:
        tags = json.loads(row["tags"])
    except Exception:
        tags = []
    try:
        anchors = json.loads(row["anchors"] or "[]")
    except Exception:
        anchors = []
    return {
        "id": row["id"],
        "title": row["title"],
        "phase": row["phase"],
        "kind": row["kind"],
        "source": row["source"],
        "content": row["content"],
        "tags": tags,
        "anchors": anchors,
        "created_at": row["created_at"]
    }


def get_current_phase(conn: sqlite3.Connection) -> str:
    cur = conn.cursor()
    cur.execute("SELECT label, done FROM milestones ORDER BY rank ASC")
    rows = cur.fetchall()
    for row in rows:
        if not row["done"]:
            return row["label"]
    return "Goals complete"


def phase_label(phase_rank: int) -> str:
    if 0 <= phase_rank < len(DEFAULT_MILESTONES):
        return DEFAULT_MILESTONES[phase_rank]
    return "General"


def unlocked_phase_rank(conn: sqlite3.Connection) -> int:
    cur = conn.cursor()
    max_rank = len(DEFAULT_MILESTONES) - 1
    for rank in range(len(DEFAULT_MILESTONES)):
        cur.execute("SELECT COUNT(*) AS total, SUM(done) AS done FROM tasks WHERE phase_rank = ?", (rank,))
        row = cur.fetchone()
        total = row["total"] or 0
        done = row["done"] or 0
        if total == 0:
            return min(rank, max_rank)
        if done < total:
            return min(rank, max_rank)
    return max_rank


def sync_milestones_from_phases(conn: sqlite3.Connection):
    cur = conn.cursor()
    for rank, _label in enumerate(DEFAULT_MILESTONES):
        cur.execute("SELECT COUNT(*) AS total, SUM(done) AS done FROM tasks WHERE phase_rank = ?", (rank,))
        row = cur.fetchone()
        total = row["total"] or 0
        done = row["done"] or 0
        is_done = 1 if total > 0 and done >= total else 0
        cur.execute("UPDATE milestones SET done = ? WHERE rank = ?", (is_done, rank))
    conn.commit()


def progress_overview(conn: sqlite3.Connection) -> Dict:
    cur = conn.cursor()

    cur.execute("SELECT COUNT(*) AS total, SUM(done) AS done FROM milestones")
    m = cur.fetchone()
    milestone_ratio = (m["done"] or 0) / max(1, m["total"] or 0)

    cur.execute("SELECT COUNT(*) AS total, SUM(done) AS done FROM tasks")
    t = cur.fetchone()
    task_ratio = (t["done"] or 0) / max(1, t["total"] or 0)

    cur.execute("SELECT COUNT(DISTINCT doc_id) AS c FROM doc_reads")
    unique_reads = cur.fetchone()["c"] or 0
    cur.execute("SELECT COUNT(*) AS c FROM documents")
    total_docs = cur.fetchone()["c"] or 0
    read_target = max(4, min(10, total_docs))
    docs_ratio = min(1.0, unique_reads / max(1, read_target))

    cur.execute("SELECT COUNT(*) AS total, SUM(done) AS done FROM weekly_plans")
    p = cur.fetchone()
    plan_ratio = (p["done"] or 0) / max(1, p["total"] or 0)

    weighted = milestone_ratio * 0.35 + task_ratio * 0.35 + docs_ratio * 0.2 + plan_ratio * 0.1
    percent = int(round(weighted * 100))

    cur.execute(
        """
        SELECT day, SUM(tasks_done) AS tasks_done, SUM(docs_read) AS docs_read
        FROM (
          SELECT substr(completed_at, 1, 10) AS day, COUNT(*) AS tasks_done, 0 AS docs_read
          FROM tasks
          WHERE completed_at IS NOT NULL
          GROUP BY substr(completed_at, 1, 10)
          UNION ALL
          SELECT substr(created_at, 1, 10) AS day, 0 AS tasks_done, COUNT(*) AS docs_read
          FROM doc_reads
          GROUP BY substr(created_at, 1, 10)
        )
        GROUP BY day
        ORDER BY day DESC
        LIMIT 42
        """
    )
    calendar = [dict(r) for r in cur.fetchall()]

    cur.execute("SELECT id, week_label, plan_text, done, rank FROM weekly_plans ORDER BY rank ASC")
    plans = [dict(r) for r in cur.fetchall()]

    return {
        "progress": percent,
        "phase": get_current_phase(conn),
        "components": {
            "milestones": round(milestone_ratio, 3),
            "tasks": round(task_ratio, 3),
            "docs_read": round(docs_ratio, 3),
            "weekly_plans": round(plan_ratio, 3)
        },
        "calendar": calendar,
        "weekly_plans": plans
    }


def build_doc_links(conn: sqlite3.Connection, threshold: float = 0.18) -> int:
    cur = conn.cursor()
    cur.execute("DELETE FROM doc_links")

    cur.execute("SELECT * FROM documents ORDER BY id ASC")
    docs = [row_to_doc(r) for r in cur.fetchall()]
    if len(docs) < 2:
        conn.commit()
        return 0

    texts = [f"{d['title']} {d['content']} {' '.join(d['tags'])}" for d in docs]
    vectors = tfidf_vectors(texts)
    inserts = 0

    for i in range(len(docs)):
        for j in range(i + 1, len(docs)):
            score = cosine_similarity(vectors[i], vectors[j])
            if score < threshold:
                continue

            reason_parts = []
            shared_tags = set(docs[i]["tags"]) & set(docs[j]["tags"])
            if shared_tags:
                reason_parts.append(f"shared tags: {', '.join(sorted(shared_tags))}")
            if docs[i]["phase"] == docs[j]["phase"]:
                reason_parts.append(f"same phase: {docs[i]['phase']}")
            if not reason_parts:
                reason_parts.append("semantic similarity")
            reason = "; ".join(reason_parts)

            cur.execute(
                """
                INSERT INTO doc_links (from_doc_id, to_doc_id, score, reason, created_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (docs[i]["id"], docs[j]["id"], round(score, 4), reason, utc_now())
            )
            inserts += 1

    conn.commit()
    return inserts


def retrieve_docs(conn: sqlite3.Connection, query: str, top_k: int = 4) -> List[Dict]:
    cur = conn.cursor()
    cur.execute("SELECT * FROM documents ORDER BY id ASC")
    docs = [row_to_doc(r) for r in cur.fetchall()]
    if not docs:
        return []

    texts = [f"{d['title']} {d['phase']} {' '.join(d['tags'])} {d['content']}" for d in docs]
    vectors = tfidf_vectors([query] + texts)
    query_vec = vectors[0]
    doc_vecs = vectors[1:]

    scored = []
    for idx, doc in enumerate(docs):
        sim = cosine_similarity(query_vec, doc_vecs[idx])
        if sim > 0:
            scored.append((sim, doc))

    scored.sort(key=lambda x: x[0], reverse=True)
    out = []
    for score, doc in scored[: max(1, top_k)]:
        out.append({**doc, "score": round(score, 4)})
    return out


def generate_answer_with_ollama(model: str, question: str, context: str, temperature: float = 0.2) -> Tuple[bool, str, str]:
    payload = {
        "model": model,
        "stream": False,
        "prompt": (
            "You are an onboarding documentation assistant. "
            "Answer only from the provided context. If uncertain, say what is missing.\n\n"
            f"Question: {question}\n\n"
            f"Context:\n{context}\n"
        ),
        "options": {
            "temperature": temperature
        }
    }

    request = urllib.request.Request(
        "http://127.0.0.1:11434/api/generate",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST"
    )

    try:
        with urllib.request.urlopen(request, timeout=30) as resp:
            body = json.loads(resp.read().decode("utf-8"))
            text = (body.get("response") or "").strip()
            if text:
                return True, text, "ollama"
            return False, "Ollama returned an empty response.", "ollama"
    except Exception as err:
        return False, f"Ollama unavailable: {err}", "ollama"


def discover_ollama_models() -> List[str]:
    request = urllib.request.Request("http://127.0.0.1:11434/api/tags", method="GET")
    try:
        with urllib.request.urlopen(request, timeout=2) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return [m.get("name") for m in data.get("models", []) if m.get("name")]
    except Exception:
        return []


def fallback_answer(question: str, docs: List[Dict]) -> str:
    if not docs:
        return "I could not find matching documentation. Add docs in Generative Documentation and ask again."

    lead = docs[0]
    summary = extractive_summary(lead["content"], max_sentences=2)
    related_titles = ", ".join([d["title"] for d in docs[1:3]]) if len(docs) > 1 else "none"
    return (
        f"Best match: {lead['title']} (phase: {lead['phase']}). "
        f"{summary} Related docs: {related_titles}."
    )


def parse_uploaded_content(filename: str, payload: str) -> Tuple[str, str]:
    raw = base64.b64decode(payload)
    ext = Path(filename).suffix.lower()

    if ext in {".txt", ".md", ".csv", ".json", ".log"}:
        text = raw.decode("utf-8", errors="ignore")
        return text, ext[1:]

    if ext == ".pdf":
        try:
            from pypdf import PdfReader

            temp = DATA_DIR / "_upload_tmp.pdf"
            temp.write_bytes(raw)
            reader = PdfReader(str(temp))
            text = "\n".join((page.extract_text() or "") for page in reader.pages)
            temp.unlink(missing_ok=True)
            return text, "pdf"
        except Exception as err:
            raise ValueError(f"PDF parsing requires pypdf installed. ({err})")

    if ext == ".docx":
        try:
            import docx2txt

            temp = DATA_DIR / "_upload_tmp.docx"
            temp.write_bytes(raw)
            text = docx2txt.process(str(temp)) or ""
            temp.unlink(missing_ok=True)
            return text, "docx"
        except Exception as err:
            raise ValueError(f"DOCX parsing requires docx2txt installed. ({err})")

    raise ValueError("Unsupported file type. Supported: txt, md, csv, json, log. Optional: pdf/docx with extra libs.")


class Handler(BaseHTTPRequestHandler):
    server_version = "NeoBoard/1.0"

    def log_message(self, fmt, *args):
        return

    def _json(self, payload: Dict, status: int = 200):
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _read_json(self) -> Dict:
        length = int(self.headers.get("Content-Length", 0))
        raw = self.rfile.read(length) if length > 0 else b"{}"
        try:
            return json.loads(raw.decode("utf-8"))
        except Exception:
            return {}

    def _serve_static(self, route_path: str):
        path = unquote(route_path.split("?", 1)[0])
        if path == "/":
            path = "/index.html"

        requested = (WEB_DIR / path.lstrip("/")).resolve()
        if WEB_DIR not in requested.parents and requested != WEB_DIR:
            self.send_error(403)
            return

        if requested.is_dir():
            requested = requested / "index.html"

        if not requested.exists() or not requested.is_file():
            self.send_error(404)
            return

        content_type = "text/plain; charset=utf-8"
        suffix = requested.suffix.lower()
        if suffix == ".html":
            content_type = "text/html; charset=utf-8"
        elif suffix == ".css":
            content_type = "text/css; charset=utf-8"
        elif suffix == ".js":
            content_type = "application/javascript; charset=utf-8"

        data = requested.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        parsed = urlparse(self.path)
        conn = connect_db()

        try:
            if parsed.path == "/api/health":
                self._json({"ok": True, "service": "neoboard", "time": utc_now()})
                return

            if parsed.path == "/api/models":
                models = discover_ollama_models()
                self._json({"local_llm_provider": "ollama", "models": models})
                return

            if parsed.path == "/api/progress":
                self._json(progress_overview(conn))
                return

            if parsed.path == "/api/milestones":
                cur = conn.cursor()
                cur.execute("SELECT id, label, done, rank, created_at FROM milestones ORDER BY rank ASC")
                rows = cur.fetchall()
                milestones = [
                    {
                        "id": r["id"],
                        "label": r["label"],
                        "done": bool(r["done"]),
                        "rank": r["rank"],
                        "created_at": r["created_at"]
                    }
                    for r in rows
                ]
                done_count = sum(1 for r in milestones if r["done"])
                progress = int(round((done_count / max(1, len(milestones))) * 100))
                self._json({"milestones": milestones, "progress": progress, "phase": get_current_phase(conn)})
                return

            if parsed.path == "/api/tasks":
                query = parse_qs(parsed.query)
                search = (query.get("search", [""])[0] or "").strip().lower()

                cur = conn.cursor()
                cur.execute("SELECT * FROM tasks ORDER BY phase_rank ASC, id ASC")
                tasks = [row_to_task(r) for r in cur.fetchall()]
                if search:
                    tasks = [t for t in tasks if search in t["text"].lower()]

                unlocked = unlocked_phase_rank(conn)
                for task in tasks:
                    task["unlocked"] = task["phase_rank"] <= unlocked

                self._json({"tasks": tasks, "count": len(tasks), "unlocked_phase_rank": unlocked, "unlocked_phase_label": phase_label(unlocked)})
                return

            if parsed.path == "/api/documents":
                query = parse_qs(parsed.query)
                search = (query.get("search", [""])[0] or "").strip().lower()
                phase = (query.get("phase", [""])[0] or "").strip()

                cur = conn.cursor()
                cur.execute("SELECT * FROM documents ORDER BY id DESC")
                docs = [row_to_doc(r) for r in cur.fetchall()]
                cur.execute("SELECT doc_id, COUNT(*) AS c FROM doc_reads GROUP BY doc_id")
                reads_by_doc = {r["doc_id"]: r["c"] for r in cur.fetchall()}
                for doc in docs:
                    doc["read_count"] = reads_by_doc.get(doc["id"], 0)

                if phase:
                    docs = [d for d in docs if d["phase"] == phase]
                if search:
                    docs = [
                        d
                        for d in docs
                        if search in d["title"].lower()
                        or search in d["content"].lower()
                        or any(search in tag.lower() for tag in d["tags"])
                    ]

                cur.execute(
                    """
                    SELECT l.from_doc_id, l.to_doc_id, l.score, l.reason,
                           d1.title AS from_title, d2.title AS to_title
                    FROM doc_links l
                    JOIN documents d1 ON d1.id = l.from_doc_id
                    JOIN documents d2 ON d2.id = l.to_doc_id
                    ORDER BY l.score DESC
                    LIMIT 200
                    """
                )
                links = [dict(r) for r in cur.fetchall()]

                self._json({"documents": docs, "links": links, "count": len(docs)})
                return

            if parsed.path == "/api/chat":
                cur = conn.cursor()
                cur.execute("SELECT sender, message, created_at FROM chat_messages ORDER BY id ASC LIMIT 200")
                chat = [dict(r) for r in cur.fetchall()]
                self._json({"messages": chat})
                return

            self._serve_static(parsed.path)
        finally:
            conn.close()

    def do_POST(self):
        parsed = urlparse(self.path)
        payload = self._read_json()
        conn = connect_db()

        try:
            if parsed.path == "/api/tasks":
                text = (payload.get("text") or "").strip()
                priority = (payload.get("priority") or "normal").strip().lower()
                phase_rank = payload.get("phase_rank")
                if not text:
                    self._json({"error": "Task text is required."}, status=400)
                    return
                if priority not in {"low", "normal", "high"}:
                    priority = "normal"
                try:
                    phase_rank = int(phase_rank) if phase_rank is not None else unlocked_phase_rank(conn)
                except Exception:
                    phase_rank = unlocked_phase_rank(conn)
                phase_rank = max(0, min(phase_rank, len(DEFAULT_MILESTONES) - 1))

                cur = conn.cursor()
                cur.execute(
                    "INSERT INTO tasks (text, done, priority, phase_rank, created_at) VALUES (?, 0, ?, ?, ?)",
                    (text[:160], priority, phase_rank, utc_now())
                )
                conn.commit()
                self._json({"ok": True, "task_id": cur.lastrowid})
                return

            if parsed.path == "/api/milestones/sync_from_tasks":
                sync_milestones_from_phases(conn)
                self._json({"ok": True})
                return

            if parsed.path == "/api/documents":
                title = (payload.get("title") or "").strip()
                phase = (payload.get("phase") or "General").strip()
                kind = (payload.get("kind") or "note").strip()
                source = (payload.get("source") or "manual").strip()
                content = (payload.get("content") or "").strip()
                tags = payload.get("tags") or []

                if not title or not content:
                    self._json({"error": "title and content are required"}, status=400)
                    return

                if isinstance(tags, str):
                    tags = [t.strip() for t in tags.split(",") if t.strip()]
                tags = [str(t).strip().lower() for t in tags if str(t).strip()]

                cur = conn.cursor()
                cur.execute(
                    """
                    INSERT INTO documents (title, phase, kind, source, content, tags, anchors, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        title[:180],
                        phase[:80],
                        kind[:80],
                        source[:120],
                        content,
                        json.dumps(tags),
                        json.dumps(default_anchors(title[:180])),
                        utc_now()
                    )
                )
                conn.commit()
                self._json({"ok": True, "document_id": cur.lastrowid})
                return

            if parsed.path == "/api/documents/upload":
                filename = (payload.get("filename") or "").strip()
                encoded = payload.get("content_b64")
                phase = (payload.get("phase") or "General").strip()

                if not filename or not encoded:
                    self._json({"error": "filename and content_b64 required"}, status=400)
                    return

                try:
                    text, detected_kind = parse_uploaded_content(filename, encoded)
                except ValueError as err:
                    self._json({"error": str(err)}, status=400)
                    return

                if not text.strip():
                    self._json({"error": "Uploaded file has no extractable text."}, status=400)
                    return

                title = Path(filename).stem
                tags = tokenize(title)[:5]

                cur = conn.cursor()
                cur.execute(
                    """
                    INSERT INTO documents (title, phase, kind, source, content, tags, anchors, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        title[:180],
                        phase[:80],
                        detected_kind,
                        "upload",
                        text,
                        json.dumps(tags),
                        json.dumps([{"topic": "overview", "page": 1, "paragraph": 1, "note": "Uploaded file opening section"}]),
                        utc_now()
                    )
                )
                conn.commit()
                self._json({"ok": True, "document_id": cur.lastrowid, "chars": len(text)})
                return

            if parsed.path == "/api/documents/build_links":
                threshold = payload.get("threshold", 0.18)
                try:
                    threshold = float(threshold)
                except Exception:
                    threshold = 0.18
                inserted = build_doc_links(conn, threshold=max(0.05, min(0.95, threshold)))
                self._json({"ok": True, "links_created": inserted})
                return

            if parsed.path == "/api/documents/seed":
                inserted = seed_documents(conn, DEFAULT_DOCS)
                links_created = build_doc_links(conn, threshold=0.12)
                conn.commit()
                self._json({"ok": True, "seeded": inserted, "links_created": links_created})
                return

            if parsed.path == "/api/documents/generate_summary":
                doc_id = payload.get("doc_id")
                if not doc_id:
                    self._json({"error": "doc_id required"}, status=400)
                    return

                cur = conn.cursor()
                cur.execute("SELECT * FROM documents WHERE id = ?", (int(doc_id),))
                row = cur.fetchone()
                if not row:
                    self._json({"error": "Document not found"}, status=404)
                    return

                doc = row_to_doc(row)
                summary = extractive_summary(doc["content"], max_sentences=3)
                self._json({"ok": True, "doc_id": doc["id"], "summary": summary})
                return

            if parsed.path == "/api/documents/mark_read":
                doc_id = payload.get("doc_id")
                if not doc_id:
                    self._json({"error": "doc_id required"}, status=400)
                    return
                cur = conn.cursor()
                cur.execute("SELECT id FROM documents WHERE id = ?", (int(doc_id),))
                if not cur.fetchone():
                    self._json({"error": "Document not found"}, status=404)
                    return
                cur.execute("INSERT INTO doc_reads (doc_id, created_at) VALUES (?, ?)", (int(doc_id), utc_now()))
                conn.commit()
                self._json({"ok": True})
                return

            if parsed.path == "/api/kb/lookup":
                question = (payload.get("question") or "").strip()
                if not question:
                    self._json({"error": "question required"}, status=400)
                    return

                docs = retrieve_docs(conn, question, top_k=4)
                if not docs:
                    self._json({"ok": True, "summary": "No matching document found.", "guide_steps": [], "citations": []})
                    return

                lead = docs[0]
                summary = extractive_summary(lead["content"], max_sentences=2)
                steps = []
                for idx, doc in enumerate(docs[:3]):
                    anchor = select_anchor(doc, question)
                    steps.append(
                        {
                            "step": idx + 1,
                            "doc_id": doc["id"],
                            "doc_title": doc["title"],
                            "page": int(anchor.get("page", 1)),
                            "paragraph": int(anchor.get("paragraph", 1)),
                            "note": anchor.get("note", "See overview"),
                            "score": doc.get("score", 0)
                        }
                    )

                guide_text = ""
                if len(steps) >= 2:
                    guide_text = (
                        f"Start with {steps[0]['doc_title']} around page {steps[0]['page']} paragraph {steps[0]['paragraph']}. "
                        f"If unresolved after that section, refer to paragraph {steps[1]['paragraph']} on page {steps[1]['page']} in {steps[1]['doc_title']}."
                    )
                else:
                    guide_text = (
                        f"Start with {steps[0]['doc_title']} page {steps[0]['page']} paragraph {steps[0]['paragraph']}."
                    )

                self._json(
                    {
                        "ok": True,
                        "summary": summary,
                        "guide_text": guide_text,
                        "guide_steps": steps,
                        "citations": [
                            {"id": d["id"], "title": d["title"], "phase": d["phase"], "score": d.get("score", 0)}
                            for d in docs
                        ]
                    }
                )
                return

            if parsed.path == "/api/ask":
                question = (payload.get("question") or "").strip()
                model = (payload.get("model") or "").strip()
                top_k = payload.get("top_k", 4)
                temperature = payload.get("temperature", 0.2)

                if not question:
                    self._json({"error": "question required"}, status=400)
                    return

                try:
                    top_k = int(top_k)
                except Exception:
                    top_k = 4

                docs = retrieve_docs(conn, question, top_k=max(1, min(top_k, 8)))
                context = "\n\n".join(
                    [
                        f"[{i+1}] {d['title']} | phase={d['phase']} | tags={','.join(d['tags'])}\n{d['content'][:2000]}"
                        for i, d in enumerate(docs)
                    ]
                )

                source = "local_retriever"
                used_model = None
                if model:
                    ok, answer_or_error, source = generate_answer_with_ollama(
                        model=model,
                        question=question,
                        context=context,
                        temperature=float(temperature)
                    )
                    if ok:
                        answer = answer_or_error
                        used_model = model
                    else:
                        answer = f"{fallback_answer(question, docs)} (LLM fallback reason: {answer_or_error})"
                else:
                    answer = fallback_answer(question, docs)

                cur = conn.cursor()
                cur.execute("INSERT INTO chat_messages (sender, message, created_at) VALUES (?, ?, ?)", ("user", question, utc_now()))
                cur.execute("INSERT INTO chat_messages (sender, message, created_at) VALUES (?, ?, ?)", ("assistant", answer, utc_now()))
                conn.commit()

                citations = [
                    {
                        "id": d["id"],
                        "title": d["title"],
                        "phase": d["phase"],
                        "score": d.get("score", 0)
                    }
                    for d in docs
                ]

                self._json(
                    {
                        "ok": True,
                        "answer": answer,
                        "source": source,
                        "model": used_model,
                        "citations": citations
                    }
                )
                return

            if parsed.path == "/api/weekly_plans":
                week_label = (payload.get("week_label") or "").strip()
                plan_text = (payload.get("plan_text") or "").strip()
                if not week_label or not plan_text:
                    self._json({"error": "week_label and plan_text required"}, status=400)
                    return
                cur = conn.cursor()
                cur.execute("SELECT COALESCE(MAX(rank), -1) + 1 AS next_rank FROM weekly_plans")
                next_rank = cur.fetchone()["next_rank"]
                cur.execute(
                    "INSERT INTO weekly_plans (week_label, plan_text, done, rank, created_at) VALUES (?, ?, 0, ?, ?)",
                    (week_label[:60], plan_text[:300], next_rank, utc_now())
                )
                conn.commit()
                self._json({"ok": True, "plan_id": cur.lastrowid})
                return

            self._json({"error": "Not found"}, status=404)
        finally:
            conn.close()

    def do_PATCH(self):
        parsed = urlparse(self.path)
        payload = self._read_json()
        conn = connect_db()
        try:
            if parsed.path.startswith("/api/tasks/"):
                task_id = parsed.path.rsplit("/", 1)[-1]
                try:
                    task_id = int(task_id)
                except Exception:
                    self._json({"error": "Invalid task id"}, status=400)
                    return

                cur = conn.cursor()
                cur.execute("SELECT * FROM tasks WHERE id = ?", (task_id,))
                current = cur.fetchone()
                if not current:
                    self._json({"error": "Task not found"}, status=404)
                    return

                updates = []
                params = []
                if "text" in payload:
                    updates.append("text = ?")
                    params.append(str(payload.get("text", "")).strip()[:160])
                if "done" in payload:
                    target_done = bool(payload.get("done"))
                    phase_rank = int(current["phase_rank"] or 0)
                    if target_done and phase_rank > unlocked_phase_rank(conn):
                        self._json(
                            {
                                "error": f"Task is locked. Complete all tasks in {phase_label(phase_rank - 1)} first.",
                                "locked_phase": phase_label(phase_rank)
                            },
                            status=409
                        )
                        return
                    updates.append("done = ?")
                    params.append(1 if target_done else 0)
                    updates.append("completed_at = ?")
                    params.append(utc_now() if target_done else None)
                if "priority" in payload:
                    val = str(payload.get("priority") or "normal").lower()
                    if val not in {"low", "normal", "high"}:
                        val = "normal"
                    updates.append("priority = ?")
                    params.append(val)

                if not updates:
                    self._json({"error": "No updates provided"}, status=400)
                    return

                params.append(task_id)
                cur.execute(f"UPDATE tasks SET {', '.join(updates)} WHERE id = ?", tuple(params))
                conn.commit()
                sync_milestones_from_phases(conn)
                self._json({"ok": True})
                return

            if parsed.path.startswith("/api/milestones/"):
                milestone_id = parsed.path.rsplit("/", 1)[-1]
                try:
                    milestone_id = int(milestone_id)
                except Exception:
                    self._json({"error": "Invalid milestone id"}, status=400)
                    return

                if "done" not in payload:
                    self._json({"error": "done field required"}, status=400)
                    return

                cur = conn.cursor()
                cur.execute("UPDATE milestones SET done = ? WHERE id = ?", (1 if payload.get("done") else 0, milestone_id))
                conn.commit()
                self._json({"ok": True})
                return

            if parsed.path.startswith("/api/weekly_plans/"):
                plan_id = parsed.path.rsplit("/", 1)[-1]
                try:
                    plan_id = int(plan_id)
                except Exception:
                    self._json({"error": "Invalid plan id"}, status=400)
                    return

                updates = []
                params = []
                if "week_label" in payload:
                    updates.append("week_label = ?")
                    params.append(str(payload.get("week_label") or "").strip()[:60])
                if "plan_text" in payload:
                    updates.append("plan_text = ?")
                    params.append(str(payload.get("plan_text") or "").strip()[:300])
                if "done" in payload:
                    updates.append("done = ?")
                    params.append(1 if payload.get("done") else 0)
                if "rank" in payload:
                    updates.append("rank = ?")
                    params.append(int(payload.get("rank")))

                if not updates:
                    self._json({"error": "No updates provided"}, status=400)
                    return

                params.append(plan_id)
                cur = conn.cursor()
                cur.execute(f"UPDATE weekly_plans SET {', '.join(updates)} WHERE id = ?", tuple(params))
                conn.commit()
                self._json({"ok": True})
                return

            self._json({"error": "Not found"}, status=404)
        finally:
            conn.close()

    def do_DELETE(self):
        parsed = urlparse(self.path)
        conn = connect_db()
        try:
            if parsed.path.startswith("/api/tasks/"):
                task_id = parsed.path.rsplit("/", 1)[-1]
                try:
                    task_id = int(task_id)
                except Exception:
                    self._json({"error": "Invalid task id"}, status=400)
                    return

                cur = conn.cursor()
                cur.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
                conn.commit()
                sync_milestones_from_phases(conn)
                self._json({"ok": True})
                return

            if parsed.path.startswith("/api/documents/"):
                doc_id = parsed.path.rsplit("/", 1)[-1]
                try:
                    doc_id = int(doc_id)
                except Exception:
                    self._json({"error": "Invalid document id"}, status=400)
                    return

                cur = conn.cursor()
                cur.execute("DELETE FROM documents WHERE id = ?", (doc_id,))
                cur.execute("DELETE FROM doc_links WHERE from_doc_id = ? OR to_doc_id = ?", (doc_id, doc_id))
                conn.commit()
                self._json({"ok": True})
                return

            if parsed.path.startswith("/api/weekly_plans/"):
                plan_id = parsed.path.rsplit("/", 1)[-1]
                try:
                    plan_id = int(plan_id)
                except Exception:
                    self._json({"error": "Invalid plan id"}, status=400)
                    return
                cur = conn.cursor()
                cur.execute("DELETE FROM weekly_plans WHERE id = ?", (plan_id,))
                conn.commit()
                self._json({"ok": True})
                return

            if parsed.path == "/api/reset":
                cur = conn.cursor()
                cur.executescript(
                    """
                    DELETE FROM tasks;
                    DELETE FROM milestones;
                    DELETE FROM documents;
                    DELETE FROM doc_links;
                    DELETE FROM chat_messages;
                    DELETE FROM doc_reads;
                    DELETE FROM weekly_plans;
                    """
                )
                conn.commit()
                conn.close()
                conn = None
                init_db()
                self._json({"ok": True})
                return

            self._json({"error": "Not found"}, status=404)
        finally:
            if conn:
                conn.close()


def main():
    init_db()
    print(f"NeoBoard running on http://{HOST}:{PORT}")
    server = ThreadingHTTPServer((HOST, PORT), Handler)
    server.serve_forever()


if __name__ == "__main__":
    main()
