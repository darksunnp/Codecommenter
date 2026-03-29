from __future__ import annotations

import traceback

from fastapi import FastAPI
from fastapi.responses import JSONResponse


def _build_fallback_app(error: Exception) -> FastAPI:
	fallback = FastAPI(title="Nitpicker Fallback")
	details = {
		"error": str(error),
		"traceback": traceback.format_exc(),
	}

	@fallback.get("/{path:path}")
	def show_error(path: str) -> JSONResponse:
		_ = path
		return JSONResponse(
			{
				"status": "startup_error",
				"detail": details,
			},
			status_code=500,
		)

	return fallback


try:
	from comment_scorer.web import app  # type: ignore
except Exception as exc:  # pragma: no cover
	app = _build_fallback_app(exc)
