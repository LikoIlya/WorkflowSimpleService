from typing import Annotated

from networkx import DiGraph, node_link_graph
from pydantic import AfterValidator, BeforeValidator
from sqlmodel import JSON, Column, Field, SQLModel

from workflow.models.graph import EMPTY_GRAPH
from workflow.utils import validate_graph_data
from workflow.utils.validation import validate_node_link_data

WorkflowIDType = int

# region Graph Example
graph_data_example = {
    "directed": True,
    "multigraph": False,
    "graph": {},
    "nodes": [
        {"type": "start", "id": 0},
        {"type": "end", "id": 1},
        {
            "type": "message",
            "id": 2,
            "message_text": "Example Text",
            "status": "sent",
        },
        {
            "type": "message",
            "id": 3,
            "message_text": "Oh, No! BlockedPath",
            "status": "sent",
        },
        {
            "type": "condition",
            "id": 4,
            "rule": "message_text == 'Example Text' or status == 'opened'",
        },
    ],
    "links": [
        {"source": 0, "target": 2},
        {"source": 2, "target": 4},
        {"source": 4, "target": 1, "condition": "Yes"},
        {"source": 4, "target": 3, "condition": "No"},
        {"source": 3, "target": 1},
    ],
}

# endregion


class WorkflowData(SQLModel):
    """`Workflow` serializer used for POST/PATCH requests
    `graph_data` should be valid node-link dictionary or `None`


    """

    graph_data: Annotated[
        dict,
        BeforeValidator(validate_graph_data),
        AfterValidator(validate_node_link_data),
    ] = Field(sa_column=Column(JSON), default=EMPTY_GRAPH)
    """ Graph data representing workflow in node-link data format. """

    model_config = {
        "json_schema_extra": {"examples": [{"graph_data": graph_data_example}]}
    }


class Workflow(WorkflowData, table=True):
    """Represents a `Workflow` model consisting:
    id of `Workflow`,
    nodes with edges of a corresponding workflow graph in  `graph_data`.


    """

    # region Fields - there are what to be saved into DB

    id: Annotated[WorkflowIDType, Field(primary_key=True, default=None)]
    """ Unique identifier of the workflow """

    model_config = {
        "json_schema_extra": {
            "examples": [{"id": 1, "graph_data": graph_data_example}]
        }
    }

    @property
    def __graph__(self) -> DiGraph:
        """Converts the graph data into a fully manageable
        directed graph instance.


        :returns: DiGraph representation of the workflow `graph_data`

        :rtype: DiGraph

        """
        return node_link_graph(
            dict(self.graph_data), directed=True, multigraph=False
        )

    # endregion
