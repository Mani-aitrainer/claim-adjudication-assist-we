"""Conditional edge functions.

Only one branch exists today: if OCR/intake failed, skip validation (there is nothing to
validate) and end the run. When FieldRepairAgent and HeuristicFallbackAgent are added,
route_after_validate (repair / fallback / done) belongs back here.
"""

from app.graph.state import ClaimState


def route_after_intake(state: ClaimState) -> str:
    if state.get("errors"):
        return "end"
    return "validate"
