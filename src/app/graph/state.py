"""ClaimState — the shared state every node in the LangGraph StateGraph reads from and
writes to.

Only the fields ClaimIntakeAgent and ClaimValidatorAgent actually produce are declared
here. When FieldRepairAgent, HeuristicFallbackAgent, PolicyAdjudicatorAgent and
DecisionAuditorAgent are built, extend this TypedDict (and build_graph.py / routers.py)
rather than pre-declaring their fields now.
"""

import operator
from typing import Annotated, Literal, TypedDict


class ValidationIssue(TypedDict):
    field: str
    code: str
    message: str
    severity: Literal["error", "warning"]


class AgentMetric(TypedDict):
    agent: str
    input_tokens: int
    output_tokens: int
    latency_ms: float
    cost_usd: float
    model: str
    cache_hit: bool


class ClaimState(TypedDict, total=False):
    # identity
    run_id: str
    document_id: str
    source_uri: str
    domain: str  # "claims" | "pharmacy"

    # ClaimIntakeAgent
    ocr_result: dict
    extracted_fields: dict
    extraction_source: str  # intake_llm | ocr_failed

    # ClaimValidatorAgent
    validation: dict

    # cross-cutting
    metrics: Annotated[list[AgentMetric], operator.add]
    errors: Annotated[list[dict], operator.add]
