# Claim Adjudication Assist

A LangGraph multi-agent pipeline for health insurance claim intake and validation.

**Currently implemented:** two agents, wired into a graph (`src/app/graph/build_graph.py`):

```
START -> ClaimIntakeAgent -> ClaimValidatorAgent -> END
              (OCR + LLM field           (deterministic business-rule
               extraction)                validation, no LLM)
```

If OCR/intake fails, the graph routes straight to `END` instead of validating. Everything
else described in the original design (FieldRepairAgent, HeuristicFallbackAgent,
PolicyAdjudicatorAgent, DecisionAuditorAgent, and the FastAPI adjudication/RAG endpoints)
is future work and intentionally not wired in yet — the graph only references agents that
exist.

## Requirements

- Python 3.12+
- A virtual environment (this repo already has one at `.venv/` — see below)

## Setup

```bash
# from the repo root
python -m venv .venv                # skip if .venv/ already exists
.venv\Scripts\activate               # Windows PowerShell/cmd
# source .venv/bin/activate          # macOS/Linux

pip install -e ".[dev]"
```

Copy `.env.example` to `.env` if you don't already have one. The two required knobs are:

| Variable        | Purpose                                                                 |
|-----------------|--------------------------------------------------------------------------|
| `OPENAI_API_KEY`| Only needed if you want real LLM-based extraction. Leave empty to run fully offline (see below). |
| `FIXTURE_DIR`   | Where OCR fixtures live. Defaults to `./tests/fixtures/textract`.        |

No AWS, Postgres, or Redis is required to run locally — `APP_ENV=local` (the default)
uses fixture OCR data, an in-memory cache, and a SQLite checkpointer.

## Run it — the CLA command line

`CLA` (`src/app/cli.py`) is the primary way to run the pipeline. It builds the graph once,
runs one or more claim documents through it, and prints a pass/fail summary.

```bash
# run a single fixture claim
python -m app.cli run tests/fixtures/claims/CLM-001.pdf

# run every fixture claim under tests/fixtures/claims/
python -m app.cli run-all

# force the deterministic offline extractor (no API key needed) and get raw JSON
python -m app.cli --offline --json run-all
```

If `pip install -e .` was run, the same commands are also available as a console script:

```bash
cla run tests/fixtures/claims/CLM-001.pdf
cla run-all
```

**LLM mode:** `CLA` automatically uses the real OpenAI model configured in
`config/agents.yaml` when `OPENAI_API_KEY` is set, and otherwise falls back to
`OfflineCopyIntakeLLM` (`src/app/agents/offline_llm.py`) — a deterministic stand-in that
mimics the zero-shot extraction contract (copies OCR values into canonical fields without
correcting anything) so the whole pipeline runs with no network access and no cost. Pass
`--offline` / `--no-offline` to force either mode regardless of whether a key is set.

Global flags (`--offline`, `--domain`, `--json`) must come **before** the subcommand:

```bash
python -m app.cli --offline --json run-all
```

### Example output

```
CLA - running intake -> validate  [llm mode: offline (rule-based copy)]

[CLM-001] VALID  (extraction_source=intake_llm)
  member_id='MEM1001' policy_no='POL100001' claimed_amount=1200.0

[CLM-006] INVALID  (extraction_source=intake_llm)
  member_id='MEMIOOI' policy_no='POL100001' claimed_amount=1200.0
  - MEMBER_ID_FORMAT: 'MEMIOOI' does not match the expected member ID format
  - DATE_SANITY: service dates are not valid ISO dates
...
9/18 claims passed validation.
```

`tests/fixtures/claims/` ships 14 synthetic claims-domain PDFs (`CLM-*`, some clean, some
deliberately noisy) plus 4 pharmacy-domain ones (`PHR-*`, expected to fail claims-domain
validation rules — pharmacy support isn't built yet). Their pre-captured Textract output
lives in `tests/fixtures/textract/`, so no real OCR call happens locally.

## Run the test suite

```bash
pytest
```

All 32 unit tests should pass. They cover the intake agent's field mapping, the
validator's business rules, agent/LLM config loading, caching, and the FastAPI health
endpoints — using the same `OfflineCopyIntakeLLM` the CLI falls back to (aliased as
`FakeCopyIntakeLLM` in `tests/conftest.py`).

## Run the API server (optional)

A minimal FastAPI app (`src/app/main.py`) exposes the same two-agent graph over HTTP,
plus `/healthz`, `/readyz`, and `/metrics` (Prometheus). It's not required for the CLI
workflow above, but if you want it running:

```bash
uvicorn app.main:app --reload
```

## Project layout

```
src/app/
  agents/            ClaimIntakeAgent, ClaimValidatorAgent, OfflineCopyIntakeLLM
  graph/              build_graph.py (the wiring), state.py, routers.py, nodes/
  ocr/                OCR provider interface + fixture/Textract implementations
  validation/         business rules (domains/claims/validation_rules.yaml)
  cache/, core/       cache providers, settings, agent config, LLM factory
  observability/      Prometheus metrics + tracing used by every agent
  cli.py              CLA — the command-line runner described above
  main.py             optional FastAPI app
domains/claims/       field_map.yaml, validation_rules.yaml
tests/fixtures/       synthetic claim PDFs, Textract JSON, expected outputs
config/agents.yaml    per-agent model/temperature/pricing configuration
```
