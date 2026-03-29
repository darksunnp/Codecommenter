from comment_scorer.models import ScoreInput
from comment_scorer.scorer import CommentQualityScorer


class FakeClient:
    def __init__(self, responses: list[str]):
        self._responses = responses

    def chat_completion(self, messages, temperature=0.0):
        _ = (messages, temperature)
        if not self._responses:
            raise RuntimeError("No fake responses left")
        return self._responses.pop(0)


def test_dual_pass_evaluation() -> None:
    judge_output = (
        '{"scores":{"accuracy":9,"completeness":8,"clarity":7,"overall":8},'
        '"strengths":["Good summary"],"issues":[],"rewrite_suggestion":"Looks good"}'
    )
    critique_output = (
        '{"revised_scores":{"accuracy":8,"completeness":8,"clarity":8,"overall":8},'
        '"confidence_adjustment":0.05,"agreement_level":"high","notes":"Minor correction"}'
    )

    scorer = CommentQualityScorer(FakeClient([judge_output, critique_output]), dual_pass=True)
    result = scorer.evaluate(
        ScoreInput(
            language="python",
            function_code="def add(a, b): return a + b",
            comment_text="Adds two numbers",
        )
    )

    assert result.scores.accuracy == 8.5
    assert result.scores.clarity == 7.5
    assert result.confidence > 0.0
    assert result.notes


def test_fast_mode_skips_critique() -> None:
    judge_output = (
        '{"scores":{"accuracy":9,"completeness":8,"clarity":7,"overall":8},'
        '"strengths":[],"issues":[],"rewrite_suggestion":""}'
    )
    scorer = CommentQualityScorer(FakeClient([judge_output]), dual_pass=True)

    result = scorer.evaluate(
        ScoreInput(
            language="python",
            function_code="def add(a, b): return a + b",
            comment_text="Adds two numbers",
        ),
        fast=True,
    )

    assert result.confidence == 0.6
    assert "fast mode" in result.notes[0].lower()
