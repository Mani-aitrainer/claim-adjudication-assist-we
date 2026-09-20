# Teaching Plan — Build It File By File

**Audience:** learners who will never see this finished repository. They start from an
empty folder and create one file at a time, in the order below, while you explain *why*
that file exists before they type it. Each phase ends with a checkpoint they can actually
run — that's the proof the explanation was true, not just plausible.

This plan mirrors the phases in [DEVELOPMENT_PLAN.md](DEVELOPMENT_PLAN.md) exactly — same
order, same "done when" checkpoints — because that plan is the contract this codebase was
actually built against. Treat this document as *how to teach that plan*, one file at a
time; treat `DEVELOPMENT_PLAN.md` as the reference you quote from when a learner asks "why
this exact field name" or "what does the finished version look like."

## How to run a session

1. **Don't open this repo.** Learners work in a fresh empty directory.
2. For each file: state the one-liner *before* they create it, let them type or paste the
   content, then explain the interesting lines — don't narrate every line.
3. End every phase at the checkpoint. If it doesn't pass, that's the lesson — debug it
   live rather than skipping ahead.
4. Files marked **(extended)** already exist from an earlier phase and gain new content
   in this one — say so explicitly, so nobody thinks they missed creating it earlier.
5. Test files land right after the code they test, inside the same phase — a learner
   should never write production code and its test more than a few minutes apart.

## Session 0 — Before any repo file exists

Not a phase file, a machine-setup checklist. Confirm each learner has:

- Python 3.12+, `git`, Docker Desktop, `make` (or Git Bash on Windows), VS Code
- An OpenAI API key (used from Phase 2 onward — the only thing that costs money before P13)
- `python -m venv .venv && pip install --upgrade pip` — nothing else yet; dependencies
  arrive with `pyproject.toml` in Phase 0

---

## Phase 0 — Skeleton

**Idea to land:** every cloud dependency will sit behind a small interface with a
`local` and an `aws` implementation, chosen by one setting — `APP_ENV`. Nothing else in
the system needs to know which one is active.

| # | File | One-liner |
|---|---|---|
| 1 | `pyproject.toml` | Project metadata, pinned dependencies, and every tool's config (ruff, mypy, pytest) in one place |
| 2 | `.gitignore` | Keeps `.credentials`, `.env`, `*.pem`, `.local/` out of version control from commit #1 |
| 3 | `.env.example` | Documents every environment variable the app reads — safe to commit because it holds no real values |
| 4 | `.credentials.example` | Template for AWS keys used only by Terraform and local AWS CLI calls — never the real values |
| 5 | `src/app/__init__.py` | Marks `src/app` as an importable package |
| 6 | `src/app/core/__init__.py` | Same, for the `core` subpackage |
| 7 | `src/app/core/exceptions.py` | Custom exception types (e.g. `AgentConfigError`) every later module raises instead of a bare `Exception` |
| 8 | `src/app/core/settings.py` | The `APP_ENV` switch — a `pydantic-settings` class every other module reads config through |
| 9 | `config/agents.yaml` | The one file you edit to change a model or temperature per agent — never hard-coded in Python |
| 10 | `src/app/core/agent_config.py` | Loads `agents.yaml`, deep-merges `defaults` into each agent, applies `AGENT__*` env overrides |
| 11 | `src/app/core/llm_factory.py` | `get_llm(agent_key)` — the *only* place a `ChatOpenAI` is ever constructed anywhere in the codebase |
| 12 | `src/app/core/logging_setup.py` | Structured JSON logging (`structlog`) with a `run_id` on every line |
| 13 | `src/app/api/__init__.py` | Marks the `api` subpackage |
| 14 | `src/app/api/routes_health.py` | `/healthz` (zero dependencies) and `/readyz` (checks DB/cache/secret) |
| 15 | `src/app/main.py` | FastAPI app factory — builds dependencies once at startup, routes never construct their own |
| 16 | `Makefile` | One-word commands (`make run-local`, `make test`) so nobody memorizes long CLI invocations |
| 17 | `docker-compose.local.yml` | Postgres+pgvector, Prometheus, Grafana — deliberately **no Redis** locally |
| 18 | `tests/unit/test_agent_config.py` | Proves the YAML loader merges defaults and env overrides correctly |
| 19 | `tests/unit/test_llm_factory.py` | Proves `get_llm` returns a model built with the YAML's temperature |
| 20 | `tests/unit/test_health.py` | Proves `/healthz` has zero dependencies and `/readyz` fails when a dependency is down |

**Checkpoint:** `make run-local` serves `/healthz`; `get_llm("adjudicator_agent")` returns
a model with the YAML's configured temperature.

---

## Phase 1 — Test data generator

**Idea to land:** nothing downstream can be tested without data, and no real claim data
may ever be used. Ground truth is generated once, in a `dict`, and *both* the fixture PDF
and the expected test outcome are written from that same `dict` — so they can never drift
apart.

| # | File | One-liner |
|---|---|---|
| 1 | `testdata/__init__.py` | Marks the generator as a package |
| 2 | `testdata/seeds/code_catalog.yaml` | The CPT/ICD-10/NDC codes used across every fixture, each chosen to land on a different reasoning path |
| 3 | `testdata/seeds/members.yaml` | Synthetic members and their policy periods |
| 4 | `testdata/seeds/policy_wordings.yaml` | Clause text, benefits, exclusions, sub-limits — every clause carries an explicit `clause_id` |
| 5 | `testdata/seeds/prompts.yaml` | The natural-language prompt set used for demos and retrieval evaluation |
| 6 | `testdata/manifest.yaml` | The single source of truth: every scenario's ground truth, OCR noise, and expected outcome |
| 7 | `testdata/builders/__init__.py` | Marks the builders subpackage |
| 8 | `testdata/builders/policy_builder.py` | Renders the three policy PDFs from `policy_wordings.yaml` with ReportLab |
| 9 | `testdata/builders/noise.py` | Six OCR-corruption functions, each matched to one few-shot repair example built in Phase 4 |
| 10 | `testdata/builders/claim_builder.py` | Renders CMS-1500-style claim PDFs — ground truth is never hand-transcribed into the PDF |
| 11 | `testdata/builders/pharmacy_builder.py` | Renders pharmacy invoice PDFs for the second domain pack |
| 12 | `testdata/builders/textract_builder.py` | Emits Textract-shaped JSON directly from ground truth — no AWS call needed to develop against |
| 13 | `testdata/generate.py` | CLI entrypoint: `policies` / `claims` / `textract` / `prompts` / `verify` subcommands |
| 14 | `tests/unit/test_testdata_generate.py` | Proves regeneration with the same seed is byte-identical, and `verify` catches a broken fixture |

**Checkpoint:** `make fixtures` produces every artifact; `python -m testdata.generate
verify` passes; regenerating produces byte-identical files.

---

## Phase 2 — ClaimIntakeAgent + ClaimValidatorAgent

**Idea to land:** two agents in the roster make **zero** LLM calls. That's deliberate —
not every node in an agentic system needs a model, and `ClaimValidatorAgent` is the
clearest possible proof of it.

| # | File | One-liner |
|---|---|---|
| 1 | `domains/claims/field_map.yaml` | Maps Textract's raw key names to this project's canonical field names |
| 2 | `domains/claims/validation_rules.yaml` | The nine business rules expressed as data, not as `if` statements |
| 3 | `src/app/ocr/__init__.py` | Marks the OCR subpackage |
| 4 | `src/app/ocr/base.py` | The `OCRProvider` Protocol both implementations satisfy |
| 5 | `src/app/ocr/fixture_provider.py` | **local:** loads a pre-saved Textract JSON fixture instead of calling AWS |
| 6 | `src/app/ocr/textract_provider.py` | **aws:** the real Textract `AnalyzeDocument` call — `boto3` imported lazily inside this file only |
| 7 | `src/app/ocr/parser.py` | Normalises Textract's blocks and tables into `{raw_text, key_values, tables}` |
| 8 | `src/app/agents/__init__.py` | Marks the agents subpackage |
| 9 | `src/app/agents/base.py` | `BaseAgent` — the one place agent instrumentation will live (built out in Phase 9) |
| 10 | `src/app/agents/prompts/__init__.py` | Marks the prompts subpackage |
| 11 | `src/app/agents/prompts/intake_extraction.py` | The zero-shot prompt that maps raw key-values into canonical `ClaimRecord` fields |
| 12 | `src/app/agents/claim_intake_agent.py` | `ClaimIntakeAgent`: OCR → LLM extraction → cached result, keyed by document hash |
| 13 | `src/app/validation/models.py` | `ClaimRecord` — the Pydantic model every extracted claim must satisfy |
| 14 | `src/app/validation/rules.py` | The nine rule functions, each returning a `ValidationIssue` — **no LLM anywhere in this file** |
| 15 | `src/app/agents/claim_validator_agent.py` | `ClaimValidatorAgent`: wraps the rule functions, makes zero model calls |
| 16 | `src/app/cache/__init__.py` | Marks the cache subpackage |
| 17 | `src/app/cache/base.py` | `CacheProvider` Protocol: `get` / `set` / `delete` / `get_or_set` |
| 18 | `src/app/cache/memory_cache.py` | **local:** a dict with expiry timestamps |
| 19 | `src/app/cache/redis_cache.py` | **aws:** same interface, on Redis — `redis` imported lazily so local never needs the package |
| 20 | `tests/unit/test_claim_intake_agent.py` | Proves clean fixtures extract correctly and OCR results are cached by document hash |
| 21 | `tests/unit/test_claim_validator_agent.py` | Proves every dirty fixture trips its named rule code |
| 22 | `tests/unit/test_ocr_parser.py` | Proves Textract blocks/tables parse into the expected `{key_values, tables}` shape |
| 23 | `tests/unit/test_cache.py` | Proves `InMemoryCache` respects TTL and the `get_or_set` contract |

**Checkpoint:** every clean fixture extracts correctly; every dirty fixture trips its
named validation rule.

---

## Phase 3 — Graph v1

**Idea to land:** `ClaimState` is the single shape every node reads and writes — nodes
never share state any other way. This is the smallest possible graph: two nodes, no
branching yet.

| # | File | One-liner |
|---|---|---|
| 1 | `src/app/graph/__init__.py` | Marks the graph subpackage |
| 2 | `src/app/graph/state.py` | `ClaimState` — the `TypedDict` every node reads and writes; append-only lists use `operator.add` |
| 3 | `src/app/graph/nodes/__init__.py` | Marks the nodes subpackage |
| 4 | `src/app/graph/nodes/intake_node.py` | Adapts `ClaimState` to and from `ClaimIntakeAgent.run()` |
| 5 | `src/app/graph/nodes/validate_node.py` | Adapts `ClaimState` to and from `ClaimValidatorAgent.run()` |
| 6 | `src/app/graph/routers.py` | Conditional edge functions — trivial for now, grows real branching in Phase 4 |
| 7 | `src/app/persistence/__init__.py` | Marks the persistence subpackage |
| 8 | `src/app/persistence/checkpointer.py` | `get_checkpointer()` — `AsyncSqliteSaver` locally, `AsyncPostgresSaver` on aws, same call site |
| 9 | `src/app/graph/build_graph.py` | Wires nodes and the checkpointer into one compiled `StateGraph` |
| 10 | `tests/unit/test_build_graph.py` *(first pass)* | Proves `CLM-001` runs `intake → validate → END` and a checkpoint is written |

**Checkpoint:** the graph runs end to end on `CLM-001`; checkpoints are written.

---

## Phase 4 — FieldRepairAgent + HeuristicFallbackAgent

**Idea to land:** the retry loop is bounded by a counter *in state*
(`retry_count`), not by LangGraph's recursion limit. The stopping condition has to be
something a test can assert on.

| # | File | One-liner |
|---|---|---|
| 1 | `src/app/agents/prompts/repair_fewshot.py` | The four curated few-shot examples, one per noise function from Phase 1 |
| 2 | `src/app/agents/field_repair_agent.py` | `FieldRepairAgent`: few-shot re-extraction from raw OCR text plus the specific validation errors |
| 3 | `src/app/agents/heuristic_fallback_agent.py` | `HeuristicFallbackAgent`: regex/positional heuristics, **no LLM**, marks the claim degraded |
| 4 | `src/app/graph/nodes/repair_node.py` | Adapts `ClaimState` to and from `FieldRepairAgent.run()`, increments `retry_count` |
| 5 | `src/app/graph/nodes/fallback_node.py` | Adapts `ClaimState` to and from `HeuristicFallbackAgent.run()` |
| 6 | `src/app/graph/routers.py` **(extended)** | Real branching now: valid → adjudicate; invalid + retries left → repair; exhausted → fallback |
| 7 | `src/app/graph/build_graph.py` **(extended)** | Adds the repair/fallback nodes and edges to the compiled graph |
| 8 | `tests/unit/test_field_repair_agent.py` | Proves each noise type is corrected by its matching few-shot example |
| 9 | `tests/unit/test_heuristic_fallback_agent.py` | Proves fallback fills what it can and sets `needs_human_review=True` |

**Checkpoint:** `CLM-006` recovers in one repair loop; `CLM-007` exhausts repair and
falls back; `CLM-014` (genuinely ineligible data, not an OCR problem) is *not* sent to
repair.

---

## Phase 5 — RAG foundation

**Idea to land:** exclusions, waiting periods and sub-limits are *linked* to procedure
codes in a graph — they aren't just co-located in text a similarity search would find.
This phase builds the graph and the vector store side by side so the difference is
visible later.

| # | File | One-liner |
|---|---|---|
| 1 | `src/app/persistence/migrations/001_pgvector.sql` | DDL for `policy_chunks` (with an HNSW index) and `policy_graph_edges` |
| 2 | `src/app/persistence/migrations/002_memory.sql` | DDL for `long_term_memory` |
| 3 | `src/app/persistence/migrations/003_runs.sql` | DDL for `run_audit` |
| 4 | `src/app/persistence/db.py` | Applies migration files in filename order, idempotently |
| 5 | `scripts/run_migrations.py` | CLI wrapper: runs migrations + calls the checkpointer's own `setup()` |
| 6 | `domains/claims/graph_schema.yaml` | The node and edge types the policy graph is allowed to use |
| 7 | `src/app/rag/__init__.py` | Marks the RAG subpackage |
| 8 | `src/app/rag/embeddings.py` | Batched `text-embedding-3-small` calls with retry |
| 9 | `src/app/rag/vector_store.py` | `VectorStore` Protocol |
| 10 | `src/app/rag/pgvector_store.py` | Cosine top-k over Postgres — used both locally (Docker) and on RDS |
| 11 | `src/app/rag/numpy_store.py` | Zero-Docker fallback: in-memory cosine search, same interface |
| 12 | `src/app/rag/graph_store.py` | `PolicyGraphStore` — networkx build/load and `ego_graph` traversal |
| 13 | `src/app/rag/graph_builder.py` | Turns a policy chunk into graph entities/edges validated against `graph_schema.yaml` |
| 14 | `pipelines/__init__.py` | Marks the pipelines package |
| 15 | `pipelines/data_pipeline.py` | CLI: load → chunk → embed → store vectors → build graph → verify, all idempotent |
| 16 | `src/app/rag/hybrid_retriever.py` | Runs graph traversal and vector search **concurrently** (`asyncio.gather`), merges and dedupes |
| 17 | `src/app/api/routes_graph.py` | `GET /v1/graph/subgraph` — the teaching endpoint that shows exactly what was retrieved |
| 18 | `tests/unit/test_data_pipeline.py` | Proves ingest populates chunk and graph counts and a sample query hits |

**Checkpoint:** ingesting the generated policy PDFs populates chunks and the graph; the
retriever returns triples carrying `clause_id`s.

---

## Phase 6 — PolicyAdjudicatorAgent

**Idea to land:** the payable amount is a genuine multi-step calculation — eligibility →
coverage → exclusions → sub-limit → co-pay — and the chain-of-thought prompt makes each
step explicit and citable.

| # | File | One-liner |
|---|---|---|
| 1 | `src/app/agents/prompts/adjudication_cot.py` | The six numbered reasoning steps, ending in a strict JSON decision |
| 2 | `src/app/agents/policy_adjudicator_agent.py` | `PolicyAdjudicatorAgent`: retrieval + CoT reasoning + payable-amount computation |
| 3 | `src/app/graph/nodes/adjudicate_node.py` | Adapts `ClaimState` to and from `PolicyAdjudicatorAgent.run()`, widens retrieval on a heal loop |
| 4 | `src/app/graph/build_graph.py` **(extended)** | Adds the adjudicate node to the graph |
| 5 | `tests/unit/test_policy_adjudicator_agent.py` | Proves each scenario produces its expected `status`/`payable_amount`/citations |

**Checkpoint:** `CLM-001` through `CLM-005` and `CLM-013` produce their expected
decisions.

---

## Phase 7 — DecisionAuditorAgent

**Idea to land:** cheap deterministic checks run *before* the expensive LLM critique —
and a failed deterministic check caps the quality score before the model even sees the
decision.

| # | File | One-liner |
|---|---|---|
| 1 | `src/app/agents/prompts/audit_critique.py` | The critique prompt returning `{quality_score, issues, suggested_fix}` |
| 2 | `src/app/agents/decision_auditor_agent.py` | Deterministic citation/arithmetic checks first, one LLM critique call second |
| 3 | `src/app/graph/nodes/audit_node.py` | Adapts `ClaimState` to and from `DecisionAuditorAgent.run()` |
| 4 | `src/app/graph/routers.py` **(extended)** | Heal-loop routing: `quality_score >= 0.75` → END, else loop back with `critique` in state |
| 5 | `src/app/graph/build_graph.py` **(extended)** | Closes the heal loop: `audit → adjudicate → audit` |

**Checkpoint:** `CLM-012` triggers exactly one heal loop, and the second decision
actually improves.

---

## Phase 8 — Tradeoff + cache

**Idea to land:** context, history and memory are three *different* things with
different lifetimes and different failure modes — conflating them is the most common
mistake in agent systems, so each gets its own budget and its own knob.

| # | File | One-liner |
|---|---|---|
| 1 | `config/tradeoff.yaml` | Context/history/memory token budgets, expressed as data |
| 2 | `src/app/memory/__init__.py` | Marks the memory subpackage |
| 3 | `src/app/memory/history.py` | Windowing plus rolling summary for in-run message history |
| 4 | `src/app/memory/long_term.py` | Durable facts store scoped by `member_id`, SQLite locally / Postgres on aws |
| 5 | `src/app/memory/policy.py` | `assemble_prompt_payload()` — the one function every LLM-calling agent goes through |
| 6 | `scripts/tradeoff_demo.py` | Runs one claim at `lean` / `balanced` / `generous` budgets and prints the difference |
| 7 | `tests/unit/test_memory_policy.py` | Proves truncation priority is memory → history → context |
| 8 | `tests/unit/test_long_term_memory.py` | Proves facts are scoped, TTL'd, and queryable |
| 9 | `tests/unit/test_tradeoff_demo.py` | Proves the three profiles produce genuinely different token counts |

**Checkpoint:** `tradeoff_demo.py` prints three distinct profiles; `CLM-010` (a duplicate
of `CLM-001`) gets a memory hit.

---

## Phase 9 — Observability

**Idea to land:** all instrumentation lives in **one place** — a decorator — so no
node body ever calls `metric.inc()` itself.

| # | File | One-liner |
|---|---|---|
| 1 | `src/app/observability/__init__.py` | Marks the observability subpackage |
| 2 | `src/app/observability/metrics.py` | Every Prometheus metric name and label set, defined exactly once |
| 3 | `src/app/observability/cost.py` | `cost = tokens / 1e6 * price`, prices read from `agents.yaml` |
| 4 | `src/app/observability/otel_setup.py` | OpenTelemetry tracing — console exporter locally, OTLP on aws |
| 5 | `src/app/graph/nodes/metrics_wrapper.py` | Decorator that appends a real-latency `AgentMetric` to whatever a node returns |
| 6 | `src/app/main.py` **(extended)** | Adds the `/metrics` endpoint |
| 7 | `monitoring/prometheus.local.yml` | Scrape config pointed at `host.docker.internal:8000` |
| 8 | `tests/unit/test_observability.py` | Proves cost arithmetic and metric labels are correct |
| 9 | `tests/unit/test_metrics_endpoint.py` | Proves `/metrics` reflects a full fixture run |

**Checkpoint:** the Grafana dashboard populates after running all fourteen fixtures.

---

## Phase 10 — API

**Idea to land:** the API streams graph execution as it happens
(`astream_events`) rather than waiting for the final decision — and every dependency is
built once at startup (`app.state`), never inside a route.

| # | File | One-liner |
|---|---|---|
| 1 | `src/app/api/schemas.py` | Request/response Pydantic models for every endpoint |
| 2 | `src/app/persistence/run_audit.py` | Reads and writes the `run_audit` table |
| 3 | `src/app/api/routes_adjudicate.py` | `POST /v1/claims/adjudicate` — SSE stream mapped from `astream_events` |
| 4 | `src/app/api/routes_runs.py` | `GET /v1/runs/{run_id}` and `/resume` — reads from the checkpointer |
| 5 | `src/app/main.py` **(extended)** | Wires the new routers and the lifespan-based dependency injection |
| 6 | `scripts/stream_client.py` | Pretty-prints the SSE stream from the terminal, no browser needed |
| 7 | `tests/unit/test_routes_adjudicate.py` | Proves node/token events stream in order and resume reaches the same decision |

**Checkpoint:** the SSE stream shows `node_start`/`node_end`/`final` events; resume
picks up from the last checkpoint.

---

## Phase 11 — Full test suite

**Idea to land:** every LLM-calling component accepts an injectable `llm` — the fake
doubles simulate "what a well-behaved LLM call would return," reading only what the real
prompt provides, so the tests can't accidentally peek at the answer key.

| # | File | One-liner |
|---|---|---|
| 1 | `tests/__init__.py`, `tests/unit/__init__.py`, `tests/e2e/__init__.py` | Mark the test packages |
| 2 | `tests/conftest.py` | Every fake LLM double plus shared fixtures (temp sqlite, graph/vector stores), in one file |
| 3 | `tests/e2e/test_full_workflow.py` | Parametrised over every scenario in `manifest.yaml` — adding a scenario means adding one YAML block |
| 4 | `tests/fixtures/prompts/claim_queries.yaml` | Generated by `make fixtures`, committed so CI needs no network |
| 5 | `.github/workflows/ci.yml` | ruff + mypy + pytest + `testdata.generate verify`, with a coverage gate |

**Checkpoint:** `pytest` is green in CI with zero network calls.

---

## Phase 12 — Containerise

**Idea to land:** the *same* test suite that passes on a laptop must pass inside the
built image — a Dockerfile that only "looks" like the app is a bug waiting to ship.

| # | File | One-liner |
|---|---|---|
| 1 | `docker/Dockerfile` | Multi-stage: `builder` → `test` (runs pytest inside the image) → `runtime` (slim, non-root) |
| 2 | `docker/entrypoint.sh` | The `uvicorn` launch command, workers configurable via env |
| 3 | `.dockerignore` | Keeps `.env`, `.credentials`, and dev-only files out of the build context |
| 4 | `docker-compose.local.yml` **(extended)** | Adds an `app` service behind a `profile` so the containerized app can run alongside Postgres/Prometheus/Grafana |
| 5 | `Makefile` **(extended)** | `docker-build` / `docker-test` / `docker-run` targets |

**Checkpoint:** `make docker-test` runs the full suite inside the built image and it
passes.

---

## Phase 13 — Terraform

**This is where AWS credentials get configured on your machine — do this before
creating any `.tf` file.** Everything up to here has been free; from `terraform apply`
onward this costs real money (~$150–200/month if left running).

### AWS credential setup (machine-level, not a repo file)

1. Create (or reuse) an AWS account and sign in as the root user *once*, only to create
   an IAM identity — never use root credentials day to day.
2. Create an IAM user (or, better, an IAM Identity Center / SSO permission set) with
   least-privilege access to VPC, EKS, RDS, ElastiCache, S3, ECR, IAM and Secrets
   Manager — enough to run this project's Terraform, nothing broader.
3. Install the AWS CLI v2: `aws --version` to confirm.
4. `aws configure` — access key, secret key, default region (`us-east-1`, which is
   what this project's Terraform defaults to; it has full Textract FORMS/TABLES
   coverage). This writes `~/.aws/credentials`, **outside this repo**.
5. Verify: `aws sts get-caller-identity` — confirms you're the account/identity you
   expect before anything gets created.
6. Copy `.credentials.example` → `.credentials` (already gitignored) and fill in the
   same values — this file is what Terraform and local scripts read from in this
   project's convention; `export $(grep -v '^#' .credentials | xargs)` loads it into
   the shell.
7. Install Terraform ≥1.6: `terraform -version`.

### Files, in order

| # | File | One-liner |
|---|---|---|
| 1 | `infra/terraform/bootstrap/main.tf` | One-time, run separately: creates the S3 state bucket + DynamoDB lock table |
| 2 | `infra/terraform/providers.tf` | Declares the `aws`/`tls`/`http` provider requirements and default tags |
| 3 | `infra/terraform/variables.tf` | Every input variable, with sane defaults for a learning deployment |
| 4 | `infra/terraform/backend.tf` | Points at the S3 bucket + DynamoDB table the bootstrap step created |
| 5 | `infra/terraform/modules/network/*.tf` | VPC, 2 public + 2 private subnets, **one** NAT gateway (a documented cost tradeoff) |
| 6 | `infra/terraform/modules/s3/*.tf` | The documents bucket — versioned, encrypted, public access blocked |
| 7 | `infra/terraform/modules/ecr/*.tf` | Container repository with a keep-last-5-images lifecycle policy |
| 8 | `infra/terraform/modules/eks/*.tf` | The cluster, one managed node group, the OIDC provider IRSA depends on |
| 9 | `infra/terraform/modules/rds/*.tf` | Postgres 16, private, `force_ssl`, RDS-managed master password |
| 10 | `infra/terraform/modules/elasticache/*.tf` | Single-node Redis with transit encryption |
| 11 | `infra/terraform/modules/secrets/*.tf` | Creates the Secrets Manager **shell** only — the OpenAI key is injected out-of-band, never in `.tf` |
| 12 | `infra/terraform/modules/iam/*.tf` | IRSA roles: the app pod (Secrets Manager/Textract/S3) and the ALB controller |
| 13 | `infra/terraform/modules/budget/*.tf` | A $50/month AWS Budget alert — a guardrail, not a hard stop |
| 14 | `infra/terraform/main.tf` | Wires every module together with the right inputs/outputs |
| 15 | `infra/terraform/outputs.tf` | Every value `render_k8s_config.sh` will need in Phase 14 |
| 16 | `infra/terraform/envs/learning.tfvars` | The learning-profile variable values (region, budget threshold, alert email) |

**Checkpoint:** `terraform validate` and `terraform plan -var-file=envs/learning.tfvars`
are clean; `terraform apply` succeeds in a throwaway region if you choose to actually
provision it.

---

## Phase 14 — Kubernetes + pipeline

**Idea to land:** no endpoint or credential is ever typed by hand into a manifest —
everything flows from `terraform output` through one render script.

| # | File | One-liner |
|---|---|---|
| 1 | `k8s/namespace.yaml` | The `claim-adjudication` namespace everything else lives in |
| 2 | `k8s/serviceaccount.yaml` | Template carrying a placeholder IRSA role ARN, substituted at render time |
| 3 | `scripts/render_k8s_config.sh` | Turns `terraform output -json` + `config/*.yaml` into `k8s/configmap.yaml` and the rendered ServiceAccount |
| 4 | `k8s/job-db-migrate.yaml` | Runs migrations + checkpointer setup once against RDS — never on every pod start |
| 5 | `k8s/job-seed-data.yaml` | Ingests the policy corpus into pgvector before the app can serve real decisions |
| 6 | `k8s/deployment.yaml` | 2 replicas, resource limits, liveness/readiness probes, non-root, read-only root filesystem |
| 7 | `k8s/service.yaml` | ClusterIP in front of the Deployment |
| 8 | `k8s/ingress.yaml` | Internet-facing ALB via the AWS Load Balancer Controller |
| 9 | `k8s/hpa.yaml` | Scales 2→5 replicas on 70% CPU |
| 10 | `k8s/servicemonitor.yaml` | Tells kube-prometheus-stack to scrape `/metrics` |
| 11 | `.github/workflows/infra-deploy.yml` | OIDC role assumption → `terraform apply` → build/push → migrate → seed → deploy → smoke test, gated behind manual approval |
| 12 | `scripts/smoke_test.sh` | Curls `/healthz`/`/readyz`, submits `CLM-001`, asserts a `final` SSE event arrives |

**Checkpoint:** the smoke test passes against the real ALB URL.

---

## Phase 15 — Textract capture + docs

**Idea to land:** any test that passes on synthetic Textract fixtures and fails on
*real* captured Textract output has found a genuine parser bug — that comparison is a
deliberate, valuable exercise, not busywork.

| # | File | One-liner |
|---|---|---|
| 1 | `testdata/generate.py` **(extended)** | `--mode capture` path: calls real Textract once per PDF, saves the raw response |
| 2 | `scripts/destroy_all.sh` | The ordered teardown `terraform destroy` alone can't do safely (Ingress → LBs → S3 versions → ECR images → secrets → destroy → log groups) |
| 3 | `.github/workflows/infra-destroy.yml` | `workflow_dispatch` only, requires typing `destroy` to confirm |
| 4 | `README.md` | The front door: quickstart, status, links to everything else |
| 5 | `docs/ARCHITECTURE.md` | The graph diagram, retrieval design, deployment topology |
| 6 | `docs/TEACHING_NOTES.md` | Which fixture proves which agent actually does its job, and why |

**Checkpoint:** the suite passes against captured (real) Textract fixtures if you choose
to run capture; `./scripts/destroy_all.sh` leaves zero resources tagged
`Project=claim-adjudication`.

---

## Full file-count reference

Roughly 20 files in P0–P2, another 25 through P3–P5, another 20 through P6–P9, another
20 through P10–P12, and about 45 across the AWS phases (P13–P15) — call it ~15 teaching
sessions of 45–90 minutes each if you want one phase per session, or compress P0–P2 and
P13–P15 into double-length sessions since their files are more mechanical and less
conceptually new once the pattern (Protocol + local/aws pair) has landed once.
