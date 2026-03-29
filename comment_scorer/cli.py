from __future__ import annotations

import argparse
import json
from pathlib import Path

from .config import AppConfig
from .hackclub_client import HackClubClient, HackClubClientError
from .models import ScoreInput
from .scorer import CommentQualityScorer


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    if args.command is None:
        parser.print_help()
        return 0

    cfg = AppConfig.from_env()
    client = HackClubClient(cfg)
    scorer = CommentQualityScorer(client=client, dual_pass=True)

    try:
        if args.command == "web":
            from .web import run_web_server

            return run_web_server(host=args.host, port=args.port, reload=args.reload)

        if args.command == "score":
            result = _run_single(args, scorer)
            _print_single(result, args.output)
            return 0

        if args.command == "batch":
            return _run_batch(args, scorer)

        raise ValueError(f"Unknown command: {args.command}")
    except (HackClubClientError, ValueError, FileNotFoundError) as exc:
        print(f"Error: {exc}")
        return 1


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="comment-scorer",
        description="Score code comments/docstrings for quality and accuracy.",
    )

    subparsers = parser.add_subparsers(dest="command")

    score_parser = subparsers.add_parser("score", help="Score one sample")
    score_parser.add_argument("--language", default="unknown")
    score_parser.add_argument("--function-text")
    score_parser.add_argument("--function-file")
    score_parser.add_argument("--comment-text")
    score_parser.add_argument("--comment-file")
    score_parser.add_argument("--context-text", default="")
    score_parser.add_argument("--output", choices=["pretty", "json"], default="pretty")
    score_parser.add_argument("--fast", action="store_true", help="Skip critique pass")

    batch_parser = subparsers.add_parser("batch", help="Score a JSONL dataset")
    batch_parser.add_argument("--input", required=True, help="Input JSONL path")
    batch_parser.add_argument("--output-file", help="Optional output JSONL path")
    batch_parser.add_argument("--fast", action="store_true", help="Skip critique pass")

    web_parser = subparsers.add_parser("web", help="Run the web app")
    web_parser.add_argument("--host", default="127.0.0.1")
    web_parser.add_argument("--port", type=int, default=8000)
    web_parser.add_argument("--reload", action="store_true")

    return parser


def _run_single(args: argparse.Namespace, scorer: CommentQualityScorer) -> dict:
    function_code = _read_value(args.function_text, args.function_file, "function")
    comment_text = _read_value(args.comment_text, args.comment_file, "comment")

    payload = ScoreInput(
        language=args.language,
        function_code=function_code,
        comment_text=comment_text,
        context=args.context_text,
    )
    return scorer.evaluate(payload, fast=args.fast).to_dict()


def _run_batch(args: argparse.Namespace, scorer: CommentQualityScorer) -> int:
    records = _load_jsonl(Path(args.input))
    results: list[dict] = []

    for idx, record in enumerate(records, start=1):
        payload = ScoreInput(
            language=str(record.get("language", "unknown")),
            function_code=str(record.get("function_code", "")),
            comment_text=str(record.get("comment_text", "")),
            context=str(record.get("context", "")),
        )
        if not payload.function_code.strip() or not payload.comment_text.strip():
            print(f"Skipping record {idx}: missing function_code or comment_text")
            continue

        scored = scorer.evaluate(payload, fast=args.fast).to_dict()
        scored["record_index"] = idx
        results.append(scored)

    if args.output_file:
        lines = [json.dumps(item, ensure_ascii=True) for item in results]
        Path(args.output_file).write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")

    _print_batch_summary(results)
    return 0


def _read_value(inline_value: str | None, file_value: str | None, label: str) -> str:
    if inline_value and inline_value.strip():
        return inline_value

    if file_value and file_value.strip():
        path = Path(file_value)
        if not path.exists():
            raise FileNotFoundError(f"{label} file not found: {path}")
        return path.read_text(encoding="utf-8")

    raise ValueError(f"Missing {label} input. Use --{label}-text or --{label}-file")


def _load_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        raise FileNotFoundError(f"Input file not found: {path}")

    output: list[dict] = []
    for line_num, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        item = line.strip()
        if not item:
            continue
        try:
            parsed = json.loads(item)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Invalid JSONL at line {line_num}: {exc}") from exc
        if not isinstance(parsed, dict):
            raise ValueError(f"Invalid JSONL at line {line_num}: expected object")
        output.append(parsed)

    return output


def _print_single(result: dict, mode: str) -> None:
    if mode == "json":
        print(json.dumps(result, indent=2, ensure_ascii=True))
        return

    print("Comment Quality Score")
    print("=" * 24)
    print(f"Language: {result['language']}")
    print(f"Accuracy: {result['scores']['accuracy']}")
    print(f"Completeness: {result['scores']['completeness']}")
    print(f"Clarity: {result['scores']['clarity']}")
    print(f"Overall: {result['scores']['overall']}")
    print(f"Confidence: {result['confidence']}")

    strengths = result.get("strengths", [])
    if strengths:
        print("Strengths:")
        for item in strengths:
            print(f"- {item}")

    issues = result.get("issues", [])
    if issues:
        print("Issues:")
        for item in issues:
            print(f"- [{item['severity']}] {item['issue_type']}: {item['detail']}")

    rewrite = result.get("rewrite_suggestion", "")
    if rewrite:
        print("Rewrite Suggestion:")
        print(rewrite)

    notes = result.get("notes", [])
    if notes:
        print("Notes:")
        for item in notes:
            print(f"- {item}")


def _print_batch_summary(results: list[dict]) -> None:
    print(f"Processed records: {len(results)}")
    if not results:
        return

    def avg(key: str) -> float:
        return round(sum(float(item["scores"][key]) for item in results) / len(results), 2)

    print(f"Average accuracy: {avg('accuracy')}")
    print(f"Average completeness: {avg('completeness')}")
    print(f"Average clarity: {avg('clarity')}")
    print(f"Average overall: {avg('overall')}")

    low_conf = [item for item in results if float(item.get("confidence", 0)) < 0.5]
    print(f"Low-confidence records: {len(low_conf)}")
