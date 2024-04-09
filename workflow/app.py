import os

from fastapi import FastAPI, Request
from fastapi.concurrency import asynccontextmanager
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse
from sqlmodel import Session

from .config import settings
from .db import create_db_and_tables, engine
from .routes import main_router
from .utils import (
    EdgeValidationError,
    GraphValidationError,
    NodeValidationError,
    raise_validation_errors,
)


def read(*paths, **kwargs):
    """Read the contents of a text file safely.

    >>> read("VERSION")
    """
    content = ""
    with open(
        os.path.join(os.path.dirname(__file__), *paths),
        encoding=kwargs.get("encoding", "utf8"),
    ) as open_file:
        content = open_file.read().strip()
    return content


@asynccontextmanager
async def lifespan(app: FastAPI):
    create_db_and_tables(engine)
    yield
    Session.close_all()
    return


description = """
workflow API helps you do awesome stuff. 🚀
"""

app = FastAPI(
    title="workflow",
    description=description,
    version=read("VERSION"),
    terms_of_service="http://workflow.service/terms/",
    contact={
        "name": "LikoIlya",
        "url": "http://workflow.service/contact/",
        "email": "LikoIlya@workflow.service",
    },
    license_info={
        "name": "The Unlicense",
        "url": "https://unlicense.org",
    },
    lifespan=lifespan,
)

if settings.server and settings.server.get("cors_origins", None):
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.server.cors_origins,
        allow_credentials=settings.get("server.cors_allow_credentials", True),
        allow_methods=settings.get("server.cors_allow_methods", ["*"]),
        allow_headers=settings.get("server.cors_allow_headers", ["*"]),
    )

app.include_router(main_router)


@app.exception_handler(GraphValidationError)
async def graph_exception_handler(request: Request, exc: GraphValidationError):
    return raise_validation_errors("Oops! The workflow graph is invalid.", exc)


@app.exception_handler(NodeValidationError)
async def node_exception_handler(request: Request, exc: NodeValidationError):
    return raise_validation_errors(
        "Oh dear! The workflow node is invalid.", exc
    )


@app.exception_handler(EdgeValidationError)
async def edge_exception_handler(request: Request, exc: EdgeValidationError):
    return raise_validation_errors(
        "Well well, we have an error with edge validation. Please try again.",
        exc,
    )


@app.exception_handler(IndexError)
async def index_exception_handler(request: Request, exc: IndexError):
    return PlainTextResponse(status_code=404, content=str(exc))


# @app.exception_handler(RequestValidationError)
# async def validation_exception_handler(request, exc):
#     return PlainTextResponse(str(exc), status_code=400)
