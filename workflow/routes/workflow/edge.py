from typing import List

from fastapi import APIRouter, status
from fastapi.exceptions import HTTPException
from fastapi.responses import Response
from pydantic import ValidationError
from sqlmodel import Session

from workflow.db import ActiveSession
from workflow.models.edge import (
    ConditionEdge,
    ConditionEdgeContext,
    Edge,
    SimpleEdge,
)
from workflow.models.node import NodeIdType
from workflow.models.workflow import WorkflowIDType
from workflow.utils import NotChanged

from .dependencies import use_pathfinder, use_workflow

router = APIRouter(
    tags=["edges"],
)


@router.get("/", response_model=List[Edge], summary="List all edges in workflow")
async def list_edges(
    *, workflow_id: WorkflowIDType, session: Session = ActiveSession
):
    """
    List all edges in the Workflow, related to `workflow_id`
    """
    pathfinder = use_pathfinder(workflow_id, session)
    nodes = [
        (
            ConditionEdge(
                in_node_id=in_node,
                out_node_id=out_node,
                condition=data["condition"],
            )
            if data
            else SimpleEdge(in_node_id=in_node, out_node_id=out_node)
        )
        for (in_node, out_node, data) in pathfinder.graph.edges(data=True)
    ]
    return nodes


@router.get(
    "/{in_node_id}/{out_node_id}", response_model=Edge, summary="Get edge in workflow"
)
async def get_edge(
    *,
    session: Session = ActiveSession,
    workflow_id: WorkflowIDType,
    in_node_id: NodeIdType,
    out_node_id: NodeIdType,
):
    """
    Get an edge by its `in_node_id` and `out_node_id` 
    and Workflow `workflow_id` which it related to
    """
    pathfinder = use_pathfinder(workflow_id, session)
    return pathfinder.get_edge_data(in_node_id, out_node_id)


@router.post("/", response_model=Edge, status_code=status.HTTP_201_CREATED, summary="Create new edge in workflow")
async def create_edge(
    *,
    session: Session = ActiveSession,
    workflow_id: WorkflowIDType,
    edge: Edge,
):
    """
    Create a new edge from:
    - **in_node_id**: ID of the in node
    - **out_node_id**: ID of the out node
    - **condition**: condition to pass the edge (if appliable)
    """
    workflow = use_workflow(workflow_id, session)
    pathfinder = use_pathfinder(workflow_id, session, workflow)
    try:
        if pathfinder.graph.has_edge(edge.in_node_id, edge.out_node_id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Already exists.",
            )
        pathfinder.add_edge(
            edge.in_node_id,
            edge.out_node_id,
            **edge.model_dump(exclude={"in_node_id", "out_node_id"}),
        )
        workflow.graph_data = pathfinder.graph_snapshot
        session.commit()
        session.refresh(workflow)
        return pathfinder.get_edge_data(edge.in_node_id, edge.out_node_id)
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Validation error: {e.title}",
        )


@router.delete(
    "/{in_node_id}/{out_node_id}", status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete edge in workflow"
)
async def delete_edge(
    *,
    session: Session = ActiveSession,
    workflow_id: WorkflowIDType,
    in_node_id: NodeIdType,
    out_node_id: NodeIdType,
):
    """
    Remove an edge in `Workflow` with `workflow_id` by its `in_node_id` and `out_node_id`
    """
    workflow = use_workflow(workflow_id, session)
    pathfinder = use_pathfinder(workflow_id, session, workflow)
    pathfinder.remove_edge(in_node_id, out_node_id)
    workflow.graph_data = pathfinder.graph_snapshot
    session.commit()
    session.refresh(workflow)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.patch(
    "/{in_node_id}/{out_node_id}",
    response_model=Edge,
    summary="Update edge in workflow",
)
async def patch_edge(
    *,
    session: Session = ActiveSession,
    workflow_id: WorkflowIDType,
    in_node_id: NodeIdType,
    out_node_id: NodeIdType,
    edge: ConditionEdgeContext | None = None,
):
    """
    Update an edge in `Workflow` with `workflow_id` by its `in_node_id` and `out_node_id`
    """
    workflow = use_workflow(workflow_id, session)
    pathfinder = use_pathfinder(workflow_id, session, workflow)
    try:
        pathfinder.update_edge(in_node_id, out_node_id, **dict(edge))
        workflow.graph_data = pathfinder.graph_snapshot
        session.commit()
        session.refresh(workflow)
        return pathfinder.get_edge_data(in_node_id, out_node_id)
    except IndexError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="This edge not found"
        )
    except NotChanged:
        raise HTTPException(
            status_code=status.HTTP_304_NOT_MODIFIED,
            detail="This edge is not modified",
        )
