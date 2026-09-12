"""Shared test doubles."""

from app.agents.offline_llm import OfflineCopyIntakeLLM as FakeCopyIntakeLLM
from app.agents.offline_llm import OfflineRepairLLM as FakeRepairLLM

__all__ = ["FakeCopyIntakeLLM", "FakeRepairLLM"]
