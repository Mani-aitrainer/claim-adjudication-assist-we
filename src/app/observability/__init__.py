"""Cross-cutting metrics and tracing used by every agent and cache/LLM provider.

Kept minimal on purpose: this project currently ships ClaimIntakeAgent and
ClaimValidatorAgent only (see build_graph.py). The metric names below are a superset
that anticipates the rest of the agent roster (repair/fallback/adjudicator/auditor)
described in DEVELOPMENT_PLAN-style docs so BaseAgent, llm_factory and the cache layer
don't need to change again the moment those agents are added.
"""
