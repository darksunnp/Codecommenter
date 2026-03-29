from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from .config import AppConfig
from .hackclub_client import HackClubClient, HackClubClientError
from .models import ScoreInput
from .scorer import CommentQualityScorer


WEB_DIR = Path(__file__).resolve().parent.parent / "web"


class ScoreRequest(BaseModel):
    api_key: str = Field(min_length=8, max_length=300)
    language: str = Field(default="unknown", max_length=80)
    function_code: str = Field(min_length=1, max_length=60000)
    comment_text: str = Field(min_length=1, max_length=20000)
    context: str = Field(default="", max_length=20000)
    model: str | None = Field(default=None, max_length=120)
    base_url: str | None = Field(default=None, max_length=250)
    timeout_seconds: int = Field(default=30, ge=5, le=120)
    max_retries: int = Field(default=2, ge=0, le=5)
    fast: bool = False


app = FastAPI(
    title="Nitpicker Studio",
    version="1.0.0",
    docs_url="/api/docs",
)

app.mount("/assets", StaticFiles(directory=WEB_DIR), name="assets")


@app.get("/", include_in_schema=False)
def index() -> FileResponse:
    return FileResponse(WEB_DIR / "index.html")


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/score")
def score_comment(request: ScoreRequest) -> dict:
    api_key = request.api_key.strip()
    if not api_key:
        raise HTTPException(status_code=400, detail="api_key is required")

    config = AppConfig(
        api_key=api_key,
        base_url=(request.base_url or AppConfig(api_key="").base_url).strip(),
        model=(request.model or AppConfig(api_key="").model).strip(),
        timeout_seconds=request.timeout_seconds,
        max_retries=request.max_retries,
    )

    payload = ScoreInput(
        language=request.language.strip() or "unknown",
        function_code=request.function_code,
        comment_text=request.comment_text,
        context=request.context,
    )

    try:
        scorer = CommentQualityScorer(HackClubClient(config), dual_pass=True)
        result = scorer.evaluate(payload, fast=request.fast)
        return result.to_dict()
    except HackClubClientError as exc:
        raise HTTPException(status_code=502, detail=f"Model API failure: {exc}") from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Unexpected server error: {exc}") from exc


def run_web_server(host: str = "127.0.0.1", port: int = 8000, reload: bool = False) -> int:
    try:
        import uvicorn
    except ImportError as exc:
        raise RuntimeError(
            "uvicorn is required for the web server. Install dependencies from requirements.txt."
        ) from exc

    uvicorn.run("comment_scorer.web:app", host=host, port=port, reload=reload)
    return 0
