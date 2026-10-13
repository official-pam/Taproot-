"""Taproot demo server: credit API and bank dashboard, no database or WhatsApp needed.

Run:  uvicorn demo_main:app --reload --port 8001
Open: http://localhost:8001/dashboard   (API docs at /docs)
"""

from fastapi import FastAPI
from fastapi.responses import RedirectResponse

from app.api.routes import credit

app = FastAPI(title="Taproot", description="Credit rooted in how Nigerian SMEs really do business.")
app.include_router(credit.router, tags=["credit"])


@app.get("/", include_in_schema=False)
def home() -> RedirectResponse:
    return RedirectResponse("/dashboard")
