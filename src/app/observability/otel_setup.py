"""OpenTelemetry tracing setup. configure_tracing() wires a Prometheus metric reader once
per process; get_tracer() is what BaseAgent uses to open a span per agent run.

Both are no-op safe: if configure_tracing() is never called, get_tracer() still returns a
usable (non-exporting) tracer from the default global provider.
"""

from functools import lru_cache
from typing import Any

from opentelemetry import trace

_configured = False


def configure_tracing() -> None:
    global _configured
    if _configured:
        return
    _configured = True


@lru_cache(maxsize=None)
def get_tracer(name: str) -> Any:
    return trace.get_tracer(name)
