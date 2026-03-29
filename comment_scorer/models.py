from dataclasses import dataclass, field
from typing import Any


@dataclass
class ScoreInput:
    language: str
    function_code: str
    comment_text: str
    context: str = ""


@dataclass
class ScoreBreakdown:
    accuracy: float
    completeness: float
    clarity: float
    overall: float

    def to_dict(self) -> dict[str, float]:
        return {
            "accuracy": self.accuracy,
            "completeness": self.completeness,
            "clarity": self.clarity,
            "overall": self.overall,
        }


@dataclass
class Issue:
    issue_type: str
    severity: str
    detail: str

    def to_dict(self) -> dict[str, str]:
        return {
            "issue_type": self.issue_type,
            "severity": self.severity,
            "detail": self.detail,
        }


@dataclass
class ScoreResult:
    language: str
    scores: ScoreBreakdown
    confidence: float
    strengths: list[str] = field(default_factory=list)
    issues: list[Issue] = field(default_factory=list)
    rewrite_suggestion: str = ""
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "language": self.language,
            "scores": self.scores.to_dict(),
            "confidence": self.confidence,
            "strengths": self.strengths,
            "issues": [i.to_dict() for i in self.issues],
            "rewrite_suggestion": self.rewrite_suggestion,
            "notes": self.notes,
        }