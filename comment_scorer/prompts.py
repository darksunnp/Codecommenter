from __future__ import annotations

import json

from .models import ScoreInput


RUBRIC_TEXT = """
Score each dimension from 0.0 to 10.0.

Accuracy
- 0-2: Mostly wrong or contradicts code behavior.
- 3-5: Partly correct but with notable mistakes.
- 6-8: Mostly correct with minor inaccuracies.
- 9-10: Correct, including key conditions and intent.

Completeness
- 0-2: Barely explains behavior.
- 3-5: Covers basics but misses important details.
- 6-8: Covers main flow with minor gaps.
- 9-10: Covers purpose, I/O, and important conditions.

Clarity
- 0-2: Vague or confusing.
- 3-5: Understandable but rough.
- 6-8: Clear and concise.
- 9-10: Very clear and maintainer-friendly.
""".strip()


JUDGE_SCHEMA = {
	"scores": {
		"accuracy": "float 0-10",
		"completeness": "float 0-10",
		"clarity": "float 0-10",
		"overall": "float 0-10",
	},
	"strengths": ["string"],
	"issues": [
		{
			"issue_type": "string",
			"severity": "low|medium|high",
			"detail": "string",
		}
	],
	"rewrite_suggestion": "string",
}


CRITIQUE_SCHEMA = {
	"revised_scores": {
		"accuracy": "float 0-10",
		"completeness": "float 0-10",
		"clarity": "float 0-10",
		"overall": "float 0-10",
	},
	"confidence_adjustment": "float -0.25 to 0.25",
	"agreement_level": "high|medium|low",
	"notes": "string",
}


def build_judge_messages(data: ScoreInput) -> list[dict[str, str]]:
	system_prompt = (
		"You are a strict code comment evaluator. "
		"Use only the provided function and comment. "
		"Return JSON only with no markdown and no extra keys."
	)

	user_payload = {
		"task": "Evaluate comment quality",
		"rubric": RUBRIC_TEXT,
		"language": data.language,
		"function_code": data.function_code,
		"comment_text": data.comment_text,
		"context": data.context,
		"response_schema": JUDGE_SCHEMA,
	}

	return [
		{"role": "system", "content": system_prompt},
		{"role": "user", "content": json.dumps(user_payload)},
	]


def build_critique_messages(
	data: ScoreInput,
	initial_judgment: dict,
) -> list[dict[str, str]]:
	system_prompt = (
		"You are a second-pass reviewer. "
		"Challenge inconsistencies in the first judgment and provide corrected JSON only."
	)

	user_payload = {
		"task": "Critique and revise initial judgment",
		"rubric": RUBRIC_TEXT,
		"language": data.language,
		"function_code": data.function_code,
		"comment_text": data.comment_text,
		"context": data.context,
		"initial_judgment": initial_judgment,
		"response_schema": CRITIQUE_SCHEMA,
	}

	return [
		{"role": "system", "content": system_prompt},
		{"role": "user", "content": json.dumps(user_payload)},
	]

