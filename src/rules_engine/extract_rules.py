
from __future__ import annotations

import json
import re
from pathlib import Path

from src.llm.client import get_llm


PROJECT_ROOT = Path(__file__).resolve().parents[2]

INTERVIEW_PATH = (
    PROJECT_ROOT
    / "data"
    / "static"
    / "dispatcher_interview.txt"
)

OUTPUT_PATH = (
    PROJECT_ROOT
    / "rules"
    / "extracted_rules_draft.json"
)


EXTRACTION_PROMPT = """
You are extracting operational rules from a dispatcher
interview for the Meridian logistics system.

Your job is NOT to invent policies.

Extract only rules that are explicitly supported by the
interview.

For every rule return:

{{
  "rule_id": "...",
  "condition": "...",
  "action": "...",
  "source_quote": "..."
}}

Important:

1. Preserve the meaning of the dispatcher.
2. Do not infer policies that were not stated.
3. Do not combine unrelated rules.
4. If a rule has an exception or override, include it.
5. Keep conditions and actions operational and testable.
6. Include the shortest useful supporting quote.

Return ONLY valid JSON.

Expected format:

{{
  "rules": [
    {{
      "rule_id": "RULE_NAME",
      "condition": "...",
      "action": "...",
      "source_quote": "..."
    }}
  ]
}}

DISPATCHER INTERVIEW:

{interview}
"""


def extract_rules() -> list[dict]:
    if not INTERVIEW_PATH.exists():
        raise FileNotFoundError(
            f"Interview not found: {INTERVIEW_PATH}"
        )

    interview = INTERVIEW_PATH.read_text(
        encoding="utf-8"
    )

    llm = get_llm()

    prompt = EXTRACTION_PROMPT.format(
        interview=interview
    )

    response = llm.invoke(prompt)

    content = (
        response.content
        if hasattr(response, "content")
        else str(response)
    )

    # ---------------------------------------------------------
    # Remove accidental markdown code fences.
    # ---------------------------------------------------------

    content = content.strip()

    content = re.sub(
        r"^```json\s*",
        "",
        content,
        flags=re.IGNORECASE,
    )

    content = re.sub(
        r"^```\s*",
        "",
        content,
    )

    content = re.sub(
        r"\s*```$",
        "",
        content,
    )

    content = content.strip()

    # ---------------------------------------------------------
    # Parse LLM JSON response.
    # ---------------------------------------------------------

    try:
        data = json.loads(content)
    except json.JSONDecodeError as exc:
        raise ValueError(
            "LLM returned invalid JSON.\n\n"
            f"Raw response:\n{content}"
        ) from exc

    rules = data.get("rules", [])

    if not isinstance(rules, list):
        raise ValueError(
            "LLM output does not contain a valid "
            "'rules' list."
        )

    # ---------------------------------------------------------
    # Save extracted rules.
    # ---------------------------------------------------------

    OUTPUT_PATH.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    OUTPUT_PATH.write_text(
        json.dumps(
            rules,
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    return rules


if __name__ == "__main__":
    rules = extract_rules()

    print(
        f"Extracted {len(rules)} candidate rules."
    )

    print(
        f"Saved draft to: {OUTPUT_PATH}"
    )

