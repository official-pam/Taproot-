"""Taproot demo server: credit API and bank dashboard, no database or WhatsApp keys needed.

Run: ``uvicorn demo_main:app --port 8001`` then open http://localhost:8001/dashboard
"""

from fastapi import FastAPI

from app.api.routes import credit

app = FastAPI(title="Taproot demo", description="Explainable SME credit from everyday business records.")
app.include_router(credit.router, tags=["credit"])
