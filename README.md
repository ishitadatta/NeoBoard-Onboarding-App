# NeoBoard Full Application

This is a full multi-page onboarding dashboard with a local Python backend, local ML retrieval, document graph linking, and optional local LLM integration.

## Features
- Dashboard + top 4 feature pages:
  - `progress.html`
  - `tasks.html`
  - `docs.html` (KB lookup page with summary + page/paragraph guidance)
  - `assistant.html` (AI assistant)
- Fixed global search behavior: top search routes to docs search (`docs.html?q=...`)
- SQLite persistence for milestones, tasks, documents, links, and chat history
- Local ML components (no cloud requirement):
  - TF-IDF retrieval for semantic document search
  - Similarity-based document linking graph
  - Extractive summary generation
- Documentation linker behavior:
  - SWE cannot create docs from the Docs page
  - Query returns an AI summary first
  - Then returns exact lookup path (document -> page -> paragraph), including cross-document fallback guidance
- Interlinked progress behavior:
  - Completing tasks increases progress
  - Marking documents as read increases progress
  - Weekly plans completion increases progress
  - Dedicated Progress page includes activity calendar + weekly plans
- Pre-seeded SWE onboarding knowledge base
- Optional local LLM via Ollama (if running on your machine)

## Run
From this folder:

```bash
python3 server.py
```

Open [http://127.0.0.1:8787](http://127.0.0.1:8787)

## Optional local model integrations
- For PDF ingestion: `pip install pypdf`
- For DOCX ingestion: `pip install docx2txt`
- For local LLM answers: install and run Ollama, then pull a model (example `llama3.2`)
