from typing import Annotated, List

from fastapi import APIRouter, status
from fastapi.exceptions import HTTPException
from fastapi.params import Body
from fastapi.responses import Response
from sqlmodel import Session

from workflow.db import ActiveSession
from workflow.models.node import (
    NodeBody,
    NodeFactory,
    NodeIdType,
    NodeType,
    ValidNode,
)
from workflow.models.workflow import WorkflowIDType

from .dependencies import use_pathfinder, use_workflow

router = APIRouter(
    tags=["nodes"],
)


@router.get("/", summary="List all nodes in workflow")
def list_nodes(
    *, session: Session = ActiveSession, workflow_id: WorkflowIDType
) -> List[ValidNode]:
    """
    List all nodes in the Workflow, related to `workflow_id`
    """
    pathfinder = use_pathfinder(workflow_id, session)
    nodes = [
        pathfinder.get_node(node_id) for node_id in pathfinder.graph.nodes
    ]
    return nodes


@router.get("/{node_id}/", summary="Get node in workflow")
def get_node(
    *,
    session: Session = ActiveSession,
    workflow_id: WorkflowIDType,
    node_id: NodeIdType,
) -> ValidNode:
    """
    Get a node by its `node_id` and Workflow `workflow_id` which it related to
    """
    pathfinder = use_pathfinder(workflow_id, session)
    try:
        return pathfinder.get_node(node_id)
    except IndexError:
        raise HTTPException(status_code=404, detail="This node not found")


@router.post(
    "/",
    status_code=status.HTTP_201_CREATED,
    summary="Create new node in workflow",
)
def create_node(
    *,
    session: Session = ActiveSession,
    workflow_id: WorkflowIDType,
    node_type: NodeType,
    node: Annotated[NodeBody, Body()],
) -> ValidNode:
    """
    Create a new node in the `Workflow` with ID=`workflow_id`
    """
    workflow = use_workflow(workflow_id, session)
    pathfinder = use_pathfinder(workflow_id, session, workflow)
    node = NodeFactory.create_node(node_type, **node.model_dump())
    pathfinder.add_node(node)
    workflow.graph_data = pathfinder.graph_snapshot
    session.commit()
    session.refresh(workflow)
    return node


@router.delete(
    "/{node_id}/",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete node in workflow",
)
def delete_node(
    *,
    session: Session = ActiveSession,
    workflow_id: WorkflowIDType,
    node_id: NodeIdType,
):
    """
    Remove a node by its `node_id` and Workflow `workflow_id` which related to
    """
    workflow = use_workflow(workflow_id, session)
    pathfinder = use_pathfinder(workflow_id, session, workflow)
    pathfinder.remove_node(node_id)
    workflow.graph_data = pathfinder.graph_snapshot
    session.commit()
    session.refresh(workflow)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.patch("/{node_id}/", summary="Update node in workflow")
def patch_node(
    *,
    session: Session = ActiveSession,
    workflow_id: WorkflowIDType,
    node_id: NodeIdType,
    node: Annotated[NodeBody, Body()],
) -> ValidNode:
    """
    Update an existing node by its `node_id`
    and Workflow `workflow_id` which it related to
    """
    workflow = use_workflow(workflow_id, session)
    pathfinder = use_pathfinder(workflow_id, session, workflow)
    node = NodeFactory.create_node(
        pathfinder.get_node(node_id).type, id=node_id, **node.model_dump()
    )
    pathfinder.update_node(node)
    workflow.graph_data = pathfinder.graph_snapshot
    session.commit()
    session.refresh(workflow)
    upd_node = pathfinder.get_node(node_id)
    return upd_node
