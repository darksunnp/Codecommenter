from __future__ import annotations

from fastapi import FastAPI

from comment_scorer.web import app as web_app

app = FastAPI(title="Nitpicker API Entrypoint")
app.mount("/", web_app)
