"""OfflineCopyIntakeLLM — a deterministic stand-in for the real ChatOpenAI call
ClaimIntakeAgent makes.

Mimics the zero-shot prompt's contract (see agents/prompts/intake_extraction.py): map
each canonical field to the first OCR label that has a value, coercing types naively and
never correcting or reformatting noisy input. Used by the CLI (app.cli) when no
OPENAI_API_KEY is configured, and by the unit test suite as ClaimIntakeAgent's fake llm.
"""

import json
import re
from datetime import datetime
from typing import Any

from langchain_core.messages import AIMessage, BaseMessage

_DATE_FORMATS = ["%d-%b-%Y", "%d/%m/%Y", "%B %d, %Y"]


def parse_amount(raw: Any) -> float:
    """Naive numeric coercion: strips thousands separators, gives up (0.0) on anything
    else non-numeric (e.g. "Rs. 800/-") rather than guessing — same contract real LLM
    extraction should follow, since a mis-typed amount must surface as a validation
    failure, not silently vanish."""
    try:
        return float(str(raw).replace(",", "").strip())
    except (TypeError, ValueError):
        return 0.0


def parse_units(raw: Any) -> int:
    try:
        return int(float(str(raw).replace(",", "").strip()))
    except (TypeError, ValueError):
        return 0


def extract_claim_fields(
    key_values: dict[str, str], line_item_table: list[dict[str, str]]
) -> dict[str, Any]:
    def first_value(labels: list[str]) -> str:
        for label in labels:
            if label in key_values and key_values[label]:
                return key_values[label]
        return ""

    line_items = [
        {
            "code": row.get("Code", ""),
            "description": row.get("Description", ""),
            "units": parse_units(row.get("Units", "")),
            "amount": parse_amount(row.get("Amount", "")),
        }
        for row in line_item_table
    ]

    diagnosis_raw = first_value(["Diagnosis Codes"])
    diagnosis_codes = [code.strip() for code in diagnosis_raw.split(",") if code.strip()]

    return {
        "member_id": first_value(["Member ID"]),
        "policy_no": first_value(["Policy Number"]),
        "provider_id": first_value(["Provider ID"]),
        "provider_name": first_value(["Provider Name"]),
        "network_status": first_value(["Network Status"]),
        "service_start_date": first_value(["Service Start Date"]),
        "service_end_date": first_value(["Service End Date"]),
        "diagnosis_codes": diagnosis_codes,
        "procedure_codes": [item["code"] for item in line_items],
        "line_items": line_items,
        "claimed_amount": parse_amount(first_value(["Total Charged", "Invoice Total"])),
        "currency": first_value(["Currency"]),
    }


class OfflineCopyIntakeLLM:
    """A drop-in replacement for the ChatOpenAI client ClaimIntakeAgent.invoke()s."""

    def invoke(self, messages: list[BaseMessage]) -> AIMessage:
        payload = json.loads(str(messages[-1].content))
        fields = extract_claim_fields(payload["key_values"], payload["line_item_table"])
        return AIMessage(content=json.dumps(fields))


def _reformat_date(raw: str) -> str | None:
    for fmt in _DATE_FORMATS:
        try:
            return datetime.strptime(raw.strip(), fmt).date().isoformat()
        except (ValueError, AttributeError):
            continue
    return None


def _fix_id(raw: str) -> str:
    """Undoes digit/letter OCR confusion (O<->0, I<->1). Left unchanged if it contains
    '#' — a dropout smudge, not a recoverable substitution (see repair_fewshot.py)."""
    if "#" in raw:
        return raw
    return raw.replace("O", "0").replace("I", "1")


def _lenient_amount(raw: str) -> float | None:
    """Pulls the first number out of currency-noised text (e.g. "Rs. 800/-" -> 800.0)."""
    match = re.search(r"\d[\d,]*(?:\.\d+)?", raw)
    if not match:
        return None
    return float(match.group(0).replace(",", ""))


class OfflineRepairLLM:
    """A deterministic stand-in for FieldRepairAgent's real ChatOpenAI call. Applies the
    same three fixups called out in repair_fewshot.py's few-shot examples — ID digit/letter
    confusion, non-ISO dates, and currency-noised amounts — straight from the raw OCR
    values, leaving anything it can't confidently recover untouched."""

    def invoke(self, messages: list[BaseMessage]) -> AIMessage:
        payload = json.loads(str(messages[-1].content))
        raw_kv = payload["raw_key_values"]
        raw_table = payload["raw_line_item_table"]
        corrected = dict(payload["current_extraction"])

        if "Member ID" in raw_kv:
            corrected["member_id"] = _fix_id(raw_kv["Member ID"])

        for field, label in (
            ("service_start_date", "Service Start Date"),
            ("service_end_date", "Service End Date"),
        ):
            if label in raw_kv:
                iso = _reformat_date(raw_kv[label])
                if iso is not None:
                    corrected[field] = iso

        line_items = list(corrected.get("line_items") or [])
        for index, row in enumerate(raw_table):
            if index >= len(line_items):
                break
            amount = _lenient_amount(row.get("Amount", ""))
            if amount is not None:
                line_items[index] = {**line_items[index], "amount": amount}
        corrected["line_items"] = line_items

        return AIMessage(content=json.dumps(corrected))
