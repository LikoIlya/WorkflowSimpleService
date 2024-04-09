import json
import os
from collections.abc import Mapping
from typing import Literal, get_args

from networkx import DiGraph, node_link_graph

from tests.conftest import FIX_DIR, db
from workflow.models.node import NodeIdType
from workflow.models.workflow import Workflow

GraphValidCases = Literal[
    "empty",
    "simple",
    "simple-loop",
    "multiple-ends",
]

GraphInvalidDataCases = Literal[
    "multiple-starts",
    "invalid-data",
    "invalid-nodes",
    "invalid-edges",
    "multigraph",
]

GraphFixableCases = Literal[
    "dead-loop", "no-connected-end", "no-connected-start"
]

GraphCases = Literal[GraphValidCases, GraphFixableCases, GraphInvalidDataCases]


def load_graph_data(path: str) -> dict:
    """
    Load the graph data from a JSON file.

    :param path: The path to the JSON file.
    :type path: str
    :return: The graph data.
    :rtype: dict
    """
    # Ensure the path is a valid JSON file
    if not path.endswith(".json"):
        raise ValueError("Invalid file format. Only JSON files are supported.")
    with open(path) as json_graph_repr:
        dict_graph_repr = json.load(json_graph_repr)
    return dict_graph_repr


def sorting_key_node(x: dict) -> NodeIdType:
    """Sorting key for `sorted` call of nodes list by node ID"""
    return NodeIdType(x["id"])


def sorting_key_edge(x) -> tuple[NodeIdType, NodeIdType, str | None]:
    from_id, to_id = NodeIdType(x["source"]), NodeIdType(x["target"])
    attrs = {
        key: value
        for key, value in x.items()
        if key != "source" or key != "target"
    }
    return from_id, to_id, str(attrs)


def get_dummy_workflow(key: GraphCases, request) -> Workflow:
    """
    Get a dummy workflow based on the provided key.

    :param key: The key to the graph data.
    :type key: GraphCases
    :return: A dummy workflow.
    :rtype: Workflow
    """
    model = Workflow.model_validate(
        {"graph_data": graph_fixtures["simple-loop"]}
    )
    with db.Session(db.engine) as session:
        session.add(model)
        session.commit()
        session.refresh(model)

        def finalize():
            session.delete(model)
            session.commit()
            session.close()

        request.addfinalizer(finalize)
    return model


def get_graph(data: dict) -> DiGraph:
    """
    Get a directed graph based on the provided data.

    :param data: A dictionary containing the graph data.
    :type data: dict
    :return: A directed graph.
    :rtype: DiGraph
    """
    return node_link_graph(data, directed=True, multigraph=False)


def load_graph(case: GraphCases) -> DiGraph:
    """
    Loads the graph data from the fixture
    Assumes that the fixture is a valid node-link JSON file
    That means it is a dictionary with at least two keys:

    ```python {
        "nodes" : list[{
            "id": int,
            **other_attributes # optional, related to the node type
        }],
        "links" : list[{
            "source": int,
            "target": int,
            **other_attributes # optional, related to the edge type
        }]
    }```

    :param case: GraphCases: The case to load
    :type case: GraphCases
    :returns: DiGraph: The graph object
    """
    return get_graph(graph_fixtures[case])


graph_fixtures: Mapping[str, dict] = {
    case: load_graph_data(os.path.join(FIX_DIR, f"graph-{case}.json"))
    for case in get_args(GraphCases)
}
