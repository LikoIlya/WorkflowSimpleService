# flake8: noqa
from fastapi import APIRouter

from .dependencies import use_pathfinder, use_workflow
from .edge import router as edges_router
from .node import router as nodes_router
from .root import router as root_router

router = APIRouter()

router.include_router(root_router)

router.include_router(
    nodes_router,
    prefix="/{workflow_id}/nodes",
)
router.include_router(
    edges_router,
    prefix="/{workflow_id}/edges",
)
