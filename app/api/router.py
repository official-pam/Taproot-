"""Top-level router that aggregates all route modules."""

from fastapi import APIRouter

from app.api.routes import credit, webhook

api_router = APIRouter()
api_router.include_router(webhook.router, tags=["webhook"])
api_router.include_router(credit.router, tags=["credit"])
api_router.include_router(credit.router, tags=["credit"])
