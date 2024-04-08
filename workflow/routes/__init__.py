from fastapi import APIRouter

from .workflow import router as workflow_router

main_router = APIRouter()

main_router.include_router(workflow_router, prefix="/workflow")


@main_router.get("/")
async def index():
    return {"message": "Hello World!"}
