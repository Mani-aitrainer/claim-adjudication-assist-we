"""StateGraph wiring.

    START -> intake -> [validate | fallback]        (route_after_intake)
             validate -> [repair | fallback | done]  (route_after_validate)
             repair -> validate
             fallback -> END
             done -> END

Only ClaimIntakeAgent, ClaimValidatorAgent, FieldRepairAgent and HeuristicFallbackAgent
are implemented so far. When PolicyAdjudicatorAgent and DecisionAuditorAgent are built,
extend this graph (and routers.py / state.py) rather than wiring them in ahead of time —
a graph should only reference agents and nodes that actually exist.
"""

import time
from typing import Any

from langgraph.graph import END, START, StateGraph

from app.agents.claim_intake_agent import ClaimIntakeAgent
from app.agents.claim_validator_agent import ClaimValidatorAgent
from app.agents.field_repair_agent import FieldRepairAgent
from app.agents.heuristic_fallback_agent import HeuristicFallbackAgent
from app.cache.base import CacheProvider
from app.graph.nodes.fallback_node import make_fallback_node
from app.graph.nodes.intake_node import make_intake_node
from app.graph.nodes.repair_node import make_repair_node
from app.graph.nodes.validate_node import make_validate_node
from app.graph.routers import route_after_intake, route_after_validate
from app.graph.state import ClaimState
from app.observability.metrics import graph_run_duration_seconds, graph_runs_total
from app.ocr.base import OCRProvider


def build_graph(
    checkpointer: Any,
    ocr_provider: OCRProvider,
    intake_llm: Any = None,
    repair_llm: Any = None,
    cache: CacheProvider | None = None,
) -> Any:
    """*_llm overrides the real OpenAI clients — used by tests and by the CLI's offline
    mode."""
    graph = StateGraph(ClaimState)
    graph.add_node(
        "intake", make_intake_node(ClaimIntakeAgent(ocr_provider, llm=intake_llm, cache=cache))
    )
    graph.add_node("validate", make_validate_node(ClaimValidatorAgent()))
    graph.add_node("repair", make_repair_node(FieldRepairAgent(llm=repair_llm)))
    graph.add_node("fallback", make_fallback_node(HeuristicFallbackAgent()))

    graph.add_edge(START, "intake")
    graph.add_conditional_edges(
        "intake", route_after_intake, {"validate": "validate", "fallback": "fallback"}
    )
    graph.add_conditional_edges(
        "validate", route_after_validate, {"repair": "repair", "fallback": "fallback", "done": END}
    )
    graph.add_edge("repair", "validate")
    graph.add_edge("fallback", END)

    return graph.compile(checkpointer=checkpointer)


async def run_graph(
    graph: Any, initial_state: dict[str, Any] | None, config: dict[str, Any]
) -> Any:
    """Thin wrapper any caller uses to invoke a compiled graph — records
    graph_runs_total{outcome} and graph_run_duration_seconds{domain} in one place.
    initial_state=None resumes an existing thread_id from its last checkpoint."""
    domain = (initial_state or {}).get("domain", "claims")
    start = time.perf_counter()
    try:
        final_state = await graph.ainvoke(initial_state, config=config)
    except Exception:
        graph_runs_total.labels(outcome="error").inc()
        raise
    finally:
        graph_run_duration_seconds.labels(domain=domain).observe(time.perf_counter() - start)

    if final_state.get("fallback_used"):
        outcome = "fallback"
    elif final_state.get("errors") and "validation" not in final_state:
        outcome = "error"
    else:
        outcome = "valid" if final_state.get("validation", {}).get("is_valid") else "invalid"
    graph_runs_total.labels(outcome=outcome).inc()
    return final_state
