# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

DatasetAgent is an agentic workflow for automated data discovery, web scraping, and structured metadata storage. It uses LangGraph state machines, local LLM inference via vLLM, Tavily search, and Scrapy+Playwright scraping. The output is a SQLite database with vector embeddings (sqlite-vec) for deduplication and similarity search.

## Development Environment

- **Python**: 3.12+ (`.python-version`)
- **Dependency manager**: `uv` (see `uv.lock`)
- **Install/upgrade deps**: `uv sync`
- **Virtual env**: `.venv/` (ignored in git)
- **Config**: `.env` for API keys (TAVILY_API_KEY required; GOOGLE_API_KEY, LANGSMITH_API_KEY optional)
- **LLM server**: vLLM, served locally on port 9000 (see `scripts/vllm_serve.sh`)

## Running the Project

### CLI entry point
```bash
python -m DatasetAgent.main --config configs/dataset_agent.yaml --target 20
```
- `--config` (default: `configs/dataset_agent.yaml`) — YAML config with LLM settings, prompts, and pipeline parameters
- `--target` — override target number of datasets
- `--timeout` — vLLM readiness check timeout (default: 300s)

The CLI will: wait for vLLM, build and invoke the LangGraph state graph, save the SQLite DB, and generate an interactive HTML visualization of discovered datasets.

### Jupyter notebook
```bash
jupyter notebook examples/run_pipeline.ipynb
```
Same pipeline, interactive.

### vLLM server
```bash
bash scripts/vllm_serve.sh start   # starts vLLM on port 9000
bash scripts/vllm_serve.sh stop
bash scripts/vllm_serve.sh restart
```
Default model: `Qwen/Qwen3.5-9B`. The config's `llm.model_name` must match the served model name.

## Architecture

### Workflow pipeline (LangGraph StateGraph)

```
discover → crawl_extract → resolve_datasets → (loop|rescrape|summary) → END
```

1. **discover** (`nodes/discovery.py`) — Generates search queries via LLM, runs Tavily search, inserts sources into the DB. Loads a leukocyte ontology cache (Wikidata SPARQL, cached locally) to guide queries.
2. **crawl_extract** (`nodes/crawl_extract.py`) — Spawns the Scrapy+Playwright spider (`scripts/spider.py`) per source, extracts structured observations (title, description, DOI, license, etc.), computes embeddings, checks for duplicates (DOI exact, title exact, embedding cosine similarity), and inserts observations.
3. **resolve_datasets** (`nodes/resolve_datasets.py`) — For each new observation, embeds it and searches existing datasets via sqlite-vec cosine distance. If no close match, creates a new dataset from the observation. If candidates exist, uses an LLM agent to decide if they are the same dataset. Low-confidence observations (<0.75) are ignored.
4. **summary** (`nodes/summary.py`) — Generates a markdown summary of all discovered datasets aligned with the dataset goal.
5. **Router** (`nodes/routers.py`) — After `resolve_datasets`: loops back to `discover` if more sources needed; goes to `rescrape` (re-scrape already-processed sources) if rescrape budget remains; otherwise ends with `summary`.

### Key components

| Directory | Purpose |
|---|---|
| `DatasetAgent/agents/` | LLM agent builders and structured output schemas (Pydantic). Discovery agent (Tavily search), crawl agent (web scraping), resolve agent (dataset matching). |
| `DatasetAgent/nodes/` | LangGraph node functions — the four pipeline steps plus the router. |
| `DatasetAgent/db/db.py` | SQLite schema (searches, sources, datasets, observations tables), init, insert, update, and read functions. Uses `sqlite-vec` for vector similarity. |
| `DatasetAgent/utils/` | LLM client wrapper (`ChatOpenAI` compatible), embedder (`google/embeddinggemma-300M`), logging, URL type inference, observation confidence scoring, parsing helpers. |
| `scripts/spider.py` | Scrapy+Playwright spider for multi-page crawling with JS rendering, JSON-LD extraction, download detection, and content hashing. |
| `scripts/wait_for_server.py` | Polls vLLM `/models` endpoint until the target model is ready. |
| `scripts/visualize_connections.py` | Reads the SQLite DB and generates an interactive HTML graph (vis-network) showing search→source→observation→dataset relationships. |

### State (DatasetState)

Defined in `agents/state.py`, extends `langchain.agents.AgentState`. Key fields:
- `db` — sqlite3 connection (passed through the graph)
- `embedder` — SentenceTransformer model
- `phase`, `step_count`, `max_steps`, `rescrape_step_count` — control flow
- `dataset_goal` — the domain objective
- `candidate_urls` — pending URLs for the discovery loop
- `search_ids`, `source_ids`, `observation_ids`, `matched_dataset_ids`, `new_dataset_ids` — DB references accumulated per step
- `scratchpad` — ephemeral working memory (visited domains, stats)

### Configuration (YAML)

`configs/dataset_agent.yaml` controls:
- `llm.base_url`, `llm.model_name`, `llm.temperature`
- `target_sources`, `max_steps`, `target_datasets`, `rescrape_steps`
- `dataset_goal` — domain description
- `prompts.discovery_human` — human prompt template with `{dataset_goal}` placeholder
- `prompts` are injected into system prompts at runtime (see `agents/prompts.py`)

### Prompts

All prompts are in `agents/prompts.py`:
- `DISCOVERY_SYSTEM` — role, rules, prohibited domains, ontology injection
- `CRAWL_EXTRACT_SYSTEM` — instructs the crawl agent to extract structured observations
- `RESOLVE_SYSTEM` — dataset matching decision
- `SUMMARY_SYSTEM` — data synthesis and markdown report generation
- `RESCRAPE_SYSTEM` / `RESCRAPE_HUMAN` — re-extraction of poorly-scraped sources

### Data flow

```
Tavily search → sources (URLs) → spider.py (scrape) → observations (entities)
  → resolve_datasets (embed + LLM matching) → datasets (canonical records)
  → summary (markdown report)
```

Embeddings are stored as FLOAT blobs in SQLite and queried via `vec_distance_cosine`.

## Important Notes

- The project root for running commands is `DatasetAgent/` (the inner directory).
- The `data/` directory contains the SQLite DB (`datasets.db`) — it is gitignored.
- The `logs/`, `pids/`, `raw_output.txt`, and `leukocyte_ontology_cache.json` are all gitignored.
- The mount script at the repo root (`mount_kabre.sh`) SSHFS-mounts a remote directory — not needed for local development.
- The `scripts/spider.py` spider runs as a subprocess from the crawl agent, outputs JSON Lines to `/tmp/`, then reads and cleans results.
- Duplicate detection uses a 3-tier approach: DOI exact match → title exact match → embedding cosine similarity (threshold 0.92).
- The `url.py` module classifies URLs into source types (dataset_portal, paper, repository, etc.) via domain and path heuristics.
- `confidence_score.py` computes a 0–1 confidence score for each observation based on field completeness and entity type quality.
