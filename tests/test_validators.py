from comment_scorer.validators import clamp_confidence, clamp_score, extract_json_object, parse_scores


def test_extract_json_object_from_fenced_output() -> None:
    payload = """```json
    {"scores": {"accuracy": 9.1, "completeness": 8.2, "clarity": 7.4, "overall": 8.2}}
    ```"""
    parsed = extract_json_object(payload)
    assert parsed["scores"]["accuracy"] == 9.1


def test_score_clamping() -> None:
    assert clamp_score(20) == 10.0
    assert clamp_score(-5) == 0.0


def test_confidence_clamping() -> None:
    assert clamp_confidence(9) == 1.0
    assert clamp_confidence(-2) == 0.0


def test_parse_scores_uses_defaults() -> None:
    score = parse_scores({"scores": {"accuracy": 6.8}}, key="scores")
    assert score.accuracy == 6.8
    assert score.completeness == 0.0
    assert score.clarity == 0.0
    assert isinstance(score.overall, float)
