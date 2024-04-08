from typing import List

from fastapi import APIRouter, Request, status
from fastapi.exceptions import HTTPException
from fastapi.responses import PlainTextResponse, Response
from networkx import NetworkXNoPath
from pydantic import ValidationError
from sqlmodel import Session, select

from workflow.db import ActiveSession
from workflow.models.node import NodeType
from workflow.models.workflow import Workflow, WorkflowData, WorkflowIDType

from .dependencies import use_pathfinder, use_workflow

router = APIRouter(tags=["workflow"])


@router.get("/", response_model=List[Workflow], summary="List all workflows")
async def list_workflows(*, session: Session = ActiveSession):
    """
    List all workflows:
    List of `Workflow` items with:
    - **id**=`workflow_id`: ID of the workflow
    - **graph_data**: json node-link structure of the graph
    """
    statement = select(Workflow)
    workflows = session.scalars(statement).all()
    return workflows


@router.get("/{workflow_id}/", response_model=Workflow, summary="Get workflow")
async def get_workflow(
    *, workflow_id: WorkflowIDType, session: Session = ActiveSession
):
    """
    Get a workflow by its `workflow_id`:

    - **id**=`workflow_id`: ID of the workflow
    - **graph_data**: json node-link structure of the graph
    """
    return use_workflow(workflow_id, session)


@router.post("/", 
             response_model=Workflow, 
             status_code=status.HTTP_201_CREATED, 
             summary="Create new workflow"
             )
async def create_workflow(
    *,
    session: Session = ActiveSession,
    request: Request,
    workflow: WorkflowData,
) -> Workflow:
    """
    Create a new workflow from:

    - **graph_data**: json node-link structure of the graph
    """
    try:
        db_content = Workflow.model_validate(workflow)
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Wrong data type"
        ) from e
    session.add(db_content)
    session.commit()
    session.refresh(db_content)
    return db_content


@router.delete("/{workflow_id}/", summary="Delete workflow")
def delete_workflow(
    *,
    session: Session = ActiveSession,
    workflow_id: WorkflowIDType,
    status_code=status.HTTP_204_NO_CONTENT,
):
    """
    Delete a workflow by its `workflow_id`

    - **id**=`workflow_id`: ID of the workflow
    """

    workflow: Workflow = use_workflow(workflow_id, session)
    session.delete(workflow)
    session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/{workflow_id}/route", summary="Get path of the workflow as node ID list")
def workflow_route(
    *, session: Session = ActiveSession, workflow_id: WorkflowIDType
):
    """
    Get the correct path of the workflow as list of node ids
    """
    workflow: Workflow = use_workflow(workflow_id, session)
    pf = use_pathfinder(workflow.id, session, workflow)
    if pf.start_node_id is None:
        raise HTTPException(status_code=400, detail="No start node found")
    try:
        return pf.path
    except NetworkXNoPath as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="No path found"
        ) from e


@router.get(
        "/{workflow_id}/route_string",
        response_class=PlainTextResponse,
        summary="Get path of the workflow as string"
    )
def workflow_route_str(
    *, session: Session = ActiveSession, workflow_id: WorkflowIDType
):
    """
    Get the correct path of the workflow as `Node -> Node` representation
    """
    pf = use_pathfinder(workflow_id, session)
    if pf.start_node_id is None:
        raise HTTPException(status_code=400, detail="No start node found")
    try:
        path = pf.path
        nodes = pf.__to_models_repr__(*path)
    except NetworkXNoPath as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="No path found"
        ) from e
    path = ""
    for node in nodes:
        path += f"{node.__repr__()}" + (
            " -> " if node.type != NodeType.end else ""
        )
    return "The path to end:\n" + path
