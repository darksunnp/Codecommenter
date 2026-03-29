from __future__ import annotations

from .hackclub_client import HackClubClient
from .models import ScoreBreakdown, ScoreInput, ScoreResult
from .prompts import build_critique_messages, build_judge_messages
from .validators import (
    clamp_confidence,
    clamp_score,
    extract_json_object,
    parse_issues,
    parse_scores,
)


class CommentQualityScorer:
    def __init__(self, client: HackClubClient, dual_pass: bool = True):
        self._client = client
        self._dual_pass = dual_pass

    def evaluate(self, data: ScoreInput, fast: bool = False) -> ScoreResult:
        judge_text = self._client.chat_completion(build_judge_messages(data), temperature=0.0)
        judge_payload = extract_json_object(judge_text)

        judge_scores = parse_scores(judge_payload, key="scores")
        strengths = _as_string_list(judge_payload.get("strengths", []))
        issues = parse_issues(judge_payload)
        rewrite_suggestion = str(judge_payload.get("rewrite_suggestion", "")).strip()

        if fast or not self._dual_pass:
            return ScoreResult(
                language=data.language,
                scores=judge_scores,
                confidence=0.60,
                strengths=strengths,
                issues=issues,
                rewrite_suggestion=rewrite_suggestion,
                notes=["Critique pass skipped (fast mode)."],
            )

        critique_text = self._client.chat_completion(
            build_critique_messages(data, judge_payload),
            temperature=0.0,
        )
        critique_payload = extract_json_object(critique_text)

        revised_scores = parse_scores(critique_payload, key="revised_scores")
        final_scores = _merge_scores(judge_scores, revised_scores)
        confidence = _compute_confidence(
            judge_scores,
            revised_scores,
            critique_payload.get("confidence_adjustment", 0),
        )

        notes: list[str] = []
        agreement_level = str(critique_payload.get("agreement_level", "unknown")).strip()
        if agreement_level:
            notes.append(f"Critique agreement: {agreement_level}")
        critique_note = str(critique_payload.get("notes", "")).strip()
        if critique_note:
            notes.append(critique_note)

        return ScoreResult(
            language=data.language,
            scores=final_scores,
            confidence=confidence,
            strengths=strengths,
            issues=issues,
            rewrite_suggestion=rewrite_suggestion,
            notes=notes,
        )


def _merge_scores(first: ScoreBreakdown, second: ScoreBreakdown) -> ScoreBreakdown:
    def avg(a: float, b: float) -> float:
        return clamp_score((a + b) / 2.0)

    return ScoreBreakdown(
        accuracy=avg(first.accuracy, second.accuracy),
        completeness=avg(first.completeness, second.completeness),
        clarity=avg(first.clarity, second.clarity),
        overall=avg(first.overall, second.overall),
    )


def _compute_confidence(
    first: ScoreBreakdown,
    second: ScoreBreakdown,
    adjustment: float,
) -> float:
    gap = (
        abs(first.accuracy - second.accuracy)
        + abs(first.completeness - second.completeness)
        + abs(first.clarity - second.clarity)
        + abs(first.overall - second.overall)
    ) / 4.0

    base = 0.85 - (gap / 10.0) * 0.60
    return clamp_confidence(base + _coerce_float(adjustment))


def _coerce_float(value: object) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _as_string_list(value: object) -> list[str]:
    if not isinstance(value, list):
        return []

    output: list[str] = []
    for item in value:
        text = str(item).strip()
        if text:
            output.append(text)
    return output
