"""USD cost estimation for a single LLM call, from config/agents.yaml pricing blocks
(USD per 1M tokens)."""


def compute_cost_usd(input_tokens: int, output_tokens: int, pricing: dict[str, float]) -> float:
    input_rate = pricing.get("input_per_1m", 0.0)
    output_rate = pricing.get("output_per_1m", 0.0)
    return (input_tokens / 1_000_000) * input_rate + (output_tokens / 1_000_000) * output_rate
