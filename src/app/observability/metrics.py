"""Prometheus metric definitions. One module, imported everywhere a metric is recorded —
no agent or node ever creates its own Counter/Histogram.
"""

from prometheus_client import Counter, Histogram

# BaseAgent (src/app/agents/base.py)
agent_invocations_total = Counter(
    "agent_invocations_total", "Agent run() calls", ["agent", "status"]
)
agent_latency_seconds = Histogram(
    "agent_latency_seconds", "Agent run() wall-clock latency", ["agent"]
)

# llm_factory.InstrumentedChatModel
llm_calls_total = Counter(
    "llm_calls_total", "Chat model invoke() calls", ["agent", "model", "outcome"]
)
agent_tokens_total = Counter(
    "agent_tokens_total", "Tokens consumed per agent/model", ["agent", "model", "token_type"]
)
agent_cost_usd_total = Counter(
    "agent_cost_usd_total", "Estimated USD cost per agent/model", ["agent", "model"]
)

# cache/base.py
cache_operations_total = Counter(
    "cache_operations_total", "Cache get/get_or_set outcomes", ["namespace", "result"]
)

# ocr/fixture_provider.py, ocr/textract_provider.py
textract_pages_total = Counter(
    "textract_pages_total", "Pages processed by the OCR provider", ["outcome"]
)

# graph/build_graph.py
graph_runs_total = Counter("graph_runs_total", "Completed graph runs", ["outcome"])
graph_run_duration_seconds = Histogram(
    "graph_run_duration_seconds", "Wall-clock duration of a full graph run", ["domain"]
)

# graph/nodes/validate_node.py
validation_failures_total = Counter(
    "validation_failures_total", "Validation rule failures", ["rule"]
)
repair_attempts_total = Counter(
    "repair_attempts_total", "Field repair attempts and their outcome", ["outcome"]
)
