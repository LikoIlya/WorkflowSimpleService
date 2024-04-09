from fastapi import HTTPException
from sqlmodel import Session

from workflow.db import ActiveSession
from workflow.models.workflow import Workflow, WorkflowIDType
from workflow.utils import Pathfinder


def use_workflow(
    workflow_id: WorkflowIDType, session: Session = ActiveSession
) -> Workflow:
    """

    :param workflow_id: WorkflowIDType:
    :param session: Session:  (Default value = ActiveSession)
    :param workflow_id: WorkflowIDType:
    :param session: Session:  (Default value = ActiveSession)

    """
    workflow = session.get(Workflow, workflow_id)
    if workflow is None:
        raise HTTPException(status_code=404, detail="Workflow not found")
    return workflow


def use_pathfinder(
    workflow_id: WorkflowIDType,
    session: Session = ActiveSession,
    workflow: Workflow | None = None,
):
    """

    :param workflow_id: WorkflowIDType:
    :param session: Session:  (Default value = ActiveSession)
    :param workflow: Optional[Workflow]:  (Default value = None)
    :param workflow_id: WorkflowIDType:
    :param session: Session:  (Default value = ActiveSession)
    :param workflow: Optional[Workflow]:  (Default value = None)

    """
    if workflow is None:
        workflow = use_workflow(workflow_id, session)
    if not workflow.graph_data:
        raise HTTPException(status_code=400, detail="Initiated graph is empty")
    pathfinder = Pathfinder(workflow.__graph__)
    return pathfinder
