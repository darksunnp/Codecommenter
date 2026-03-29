from __future__ import annotations

import json
from typing import Any

from .models import Issue, ScoreBreakdown


def clamp(value: float, low: float, high: float) -> float:
	return max(low, min(high, value))


def clamp_score(value: Any) -> float:
	try:
		parsed = float(value)
	except (TypeError, ValueError):
		parsed = 0.0
	return round(clamp(parsed, 0.0, 10.0), 1)


def clamp_confidence(value: Any) -> float:
	try:
		parsed = float(value)
	except (TypeError, ValueError):
		parsed = 0.0
	return round(clamp(parsed, 0.0, 1.0), 2)


def extract_json_object(text: str) -> dict[str, Any]:
	value = text.strip()
	if value.startswith("```"):
		value = value.strip("`").strip()
		if value.startswith("json"):
			value = value[4:].strip()

	try:
		parsed = json.loads(value)
		if isinstance(parsed, dict):
			return parsed
	except json.JSONDecodeError:
		pass

	start = value.find("{")
	if start < 0:
		raise ValueError("No JSON object found in model output")

	depth = 0
	for idx in range(start, len(value)):
		char = value[idx]
		if char == "{":
			depth += 1
		elif char == "}":
			depth -= 1
			if depth == 0:
				candidate = value[start : idx + 1]
				parsed = json.loads(candidate)
				if isinstance(parsed, dict):
					return parsed
				break

	raise ValueError("Unable to parse JSON object from model output")


def parse_scores(payload: dict[str, Any], key: str = "scores") -> ScoreBreakdown:
	raw_scores = payload.get(key, {})
	if not isinstance(raw_scores, dict):
		raw_scores = {}

	accuracy = clamp_score(raw_scores.get("accuracy", 0))
	completeness = clamp_score(raw_scores.get("completeness", 0))
	clarity = clamp_score(raw_scores.get("clarity", 0))
	overall = clamp_score(raw_scores.get("overall", (accuracy + completeness + clarity) / 3.0))

	return ScoreBreakdown(
		accuracy=accuracy,
		completeness=completeness,
		clarity=clarity,
		overall=overall,
	)


def parse_issues(payload: dict[str, Any]) -> list[Issue]:
	raw_issues = payload.get("issues", [])
	if not isinstance(raw_issues, list):
		return []

	normalized: list[Issue] = []
	for item in raw_issues:
		if not isinstance(item, dict):
			continue

		severity = str(item.get("severity", "medium")).strip().lower()
		if severity not in {"low", "medium", "high"}:
			severity = "medium"

		normalized.append(
			Issue(
				issue_type=str(item.get("issue_type", "unspecified")).strip() or "unspecified",
				severity=severity,
				detail=str(item.get("detail", "")).strip(),
			)
		)

	return normalized

