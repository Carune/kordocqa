from fastapi import APIRouter

from app.api.v1.admin import router as admin_router
from app.api.v1.health import router as health_router
from app.api.v1.query import router as query_router
from app.api.v1.retrieve import router as retrieve_router

api_router = APIRouter()
api_router.include_router(health_router)
api_router.include_router(admin_router)
api_router.include_router(retrieve_router)
api_router.include_router(query_router)
