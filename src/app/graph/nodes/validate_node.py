"""validate_node — adapts ClaimState <-> ClaimValidatorAgent. Deterministic, no LLM.

Emits validation_failures_total{rule} for each failing rule.
"""

from typing import Any

from app.agents.claim_validator_agent import ClaimValidatorAgent
from app.graph.state import ClaimState
from app.observability.metrics import validation_failures_total


def make_validate_node(agent: ClaimValidatorAgent) -> Any:
    def validate_node(state: ClaimState) -> dict[str, Any]:
        result = agent.run(state.get("extracted_fields", {}))

        for error in result.get("errors", []):
            validation_failures_total.labels(rule=error["code"]).inc()

        return {"validation": dict(result)}

    return validate_node
