import logging
from typing import Unpack

from networkx import (
    DiGraph,
    NetworkXError,
    node_link_data,
    node_link_graph,
    set_edge_attributes,
)

from workflow.models.edge import ConditionEdge, Edge, EdgeContext, SimpleEdge
from workflow.models.graph import NodeLinkStructure
from workflow.models.node import NodeFactory, NodeIdType, NodeType, ValidNode
from workflow.utils.exceptions import (
    EdgeValidationError,
    GraphValidationError,
    NodeValidationError,
)


def edge_validation(
    graph: DiGraph,
    from_node_id: NodeIdType,
    to_node_id: NodeIdType,
    **edge_data: Unpack[EdgeContext],
) -> Edge:
    """Validates the edge between two nodes in the workflow graph.

    :param graph: DiGraph: The graph to be validated
    :type graph: DiGraph
    :param from_node_id: NodeID: The ID of the source node.
    :type from_node_id: NodeIdType
    :param to_node_id: NodeID: The ID of the target node.
    :type to_node_id: NodeIdType
    :param edge_data: EdgeContext: Additional data associated with the edge.
    :type edge_data: EdgeContext
    :param graph: DiGraph:
    :param from_node_id: NodeIdType:
    :param to_node_id: NodeIdType:
    :param **edge_data: Unpack[EdgeContext]:
    :returns: Edge: The edge associated with the edge
    :raises EdgeValidationError: If the edge violates any of the defined rules.

    """
    if (from_node_id, to_node_id) not in graph.edges:
        snapshot = node_link_data(graph)
        updated_graph = node_link_graph(
            snapshot, directed=True, multigraph=False
        )
        # add it
        updated_graph.add_edge(from_node_id, to_node_id, **edge_data)
    else:
        snapshot = node_link_data(graph)
        updated_graph = node_link_graph(
            snapshot, directed=True, multigraph=False
        )
        # update it
        set_edge_attributes(
            updated_graph, {(from_node_id, to_node_id): {**edge_data}}
        )
    edge: Edge = None
    try:
        # Edge rules validation
        match (
            updated_graph.nodes[from_node_id]["type"],
            updated_graph.nodes[to_node_id]["type"],
        ):
            case _, "start":  # [Start Node] Не може мати вхідних ребер
                raise EdgeValidationError(
                    "Start node cannot have incoming edges."
                )
            case "end", _:  # [End Node] Не може мати вихідних ребер.
                raise EdgeValidationError(
                    "End node cannot have outgoing edges."
                )
            case (
                "start",
                "condition",
            ):  # [Condition Node]
                # Може бути з'єднана з Message Node або іншою Condition Node
                raise EdgeValidationError(
                    "Condition node cannot go directly from the start node."
                )
            case (
                "start"
                | "message",
                _,
            ):  # [Start Node/Message Node] Може мати лише одне вихідне ребро
                assert (
                    len(list(updated_graph.out_edges(from_node_id))) <= 1
                ), "Node can only have one outgoing edge."
            case (
                "condition",
                _,
            ):  # [Condition Node] Може мати два вихідних ребра: Yes та No.
                assert (
                    len(list(updated_graph.out_edges(from_node_id))) <= 2
                ), "Condition node can only have two outgoing edges (Yes/No)."

        # Edge attributes validation
        match updated_graph.nodes[from_node_id]["type"]:
            case "condition":
                assert edge_data.get("condition", None) in [
                    "Yes",
                    "No",
                ], "Condition node param can only have Yes/No edges."
                try:
                    edge = ConditionEdge(
                        in_node_id=from_node_id,
                        out_node_id=to_node_id,
                        condition=edge_data["condition"],
                    )
                except AssertionError as e:
                    raise EdgeValidationError(str(e)) from e
                assert all(
                    ConditionEdge(
                        in_node_id=f,
                        out_node_id=t,
                        condition=edge_d["condition"],
                    )
                    for (f, t, edge_d) in updated_graph.out_edges(
                        from_node_id, data=True
                    )
                ), "Condition node can only have Condition edges."
                for condition in ["Yes", "No"]:
                    assert (
                        len(
                            [
                                ConditionEdge(
                                    in_node_id=f,
                                    out_node_id=t,
                                    condition=edge_d["condition"],
                                )
                                for (f, t, edge_d) in updated_graph.out_edges(
                                    from_node_id, data=True
                                )
                                if edge_d.get("condition") == condition
                            ]
                        )
                        <= 1
                    ), (
                        f"Only one {condition} path should be exist "
                        + f"from node {from_node_id}."
                    )
            case _:
                assert (
                    not edge_data or edge_data == {}
                ), "This edge can't have attributes."
                edge = SimpleEdge(
                    in_node_id=from_node_id, out_node_id=to_node_id
                )
    except AssertionError as e:
        raise EdgeValidationError(str(e)) from e

    return edge


def node_validation(graph: DiGraph, node: ValidNode) -> ValidNode:
    """Validate a node in the workflow graph.

    :param graph: DiGraph: The workflow graph.
    :type graph: DiGraph
    :param node: ValidNode: The ID of the node to validate.
    :type node: ValidNode
    :param graph: DiGraph:
    :param node: ValidNode:
    :returns: None
    :raises NodeValidationError: If the node violates any of the defined rules.

    """
    if node.id not in graph.nodes():
        snapshot = node_link_data(graph)
        updated_graph = node_link_graph(
            snapshot, directed=True, multigraph=False
        )
        params = {**node.model_dump(exclude=["id"]), "type": node.type}
        updated_graph.add_node(node.id, **params)
    else:
        updated_graph = graph

    if "type" not in updated_graph.nodes[node.id]:
        raise NodeValidationError(f"Node {node.id} has no type.")
    node = NodeFactory.create_node(
        updated_graph.nodes[node.id]["type"],
        id=node.id,
        **updated_graph.nodes[node.id],
    )
    try:
        match node.type:
            case NodeType.condition:
                assert (
                    "rule" in updated_graph.nodes[node.id]
                ), "Invalid configuration of node condition."
                assert len(list(updated_graph.out_edges(node.id))) <= 2
            case NodeType.end:
                assert (
                    len(list(updated_graph.out_edges(node.id))) == 0
                ), "End node cannot have outgoing edges."
            case NodeType.start:
                assert (
                    len(list(updated_graph.in_edges(node.id))) == 0
                ), "Start node cannot have incoming edges."
                assert (
                    len(list(updated_graph.out_edges(node.id))) <= 1
                ), "Node can only have one outgoing edge."
            case NodeType.message:
                assert (
                    "message_text" in updated_graph.nodes[node.id]
                    or "status" in updated_graph.nodes[node.id]
                ), "Invalid configuration of node message."
                assert (
                    len(list(updated_graph.out_edges(node.id))) <= 1
                ), "Node can only have one outgoing edge."
    except NetworkXError:
        logging.debug(
            "No nodes found as out_edges for node to check.\n"
            + "Nothing serious here"
        )
    except AssertionError as e:
        raise NodeValidationError(str(e)) from e
    return node


def validate_graph_data(graph_data: dict) -> dict:
    """Validate the workflow graph data represented as a node-link dictionary.

    :param graph_data: dict: The workflow graph data as node-link dictionary.
    :type graph_data: dict
    :param graph_data: dict:
    :returns: dict: The validated workflow graph data as dict.
    :raises GraphValidationError: If the graph violates any of defined rules

    """
    try:
        graph = node_link_graph(
            dict(graph_data), directed=True, multigraph=False
        )
    except Exception as e:
        raise GraphValidationError("Invalid graph data") from e
    graph = validate_graph(graph)
    return node_link_data(graph)


def validate_node_link_data(node_link_data_dict: dict) -> NodeLinkStructure:
    """Validate the workflow graph data represented as a node-link dictionary.

    :param node_link_data_dict: dict: Graph data as node-link dictionary.
    :type node_link_data_dict: dict: dict
    :param node_link_data_dict: dict:
    :returns: NodeLinkStructure: The validated node-link structure.
    :raises GraphValidationError: If the graph violates any defined rules

    """
    try:
        graph = node_link_graph(
            dict(node_link_data_dict), directed=True, multigraph=False
        )
    except Exception as e:
        raise GraphValidationError("Invalid graph data") from e
    graph = validate_graph(graph)
    return NodeLinkStructure(**node_link_data(graph))


def validate_graph(graph: DiGraph) -> DiGraph:
    """Validate the workflow graph.

    :param graph: DiGraph: The workflow graph.
    :type graph: DiGraph
    :param graph: DiGraph:
    :returns: DiGraph: The validated workflow graph.
    :raises GraphValidationError: If the graph violates any defined rules

    """
    try:
        if not graph.is_directed() or not isinstance(graph, DiGraph):
            raise GraphValidationError("The graph is not a DiGraph")
        if graph.is_multigraph():
            raise GraphValidationError("The graph is multigraph.")
        for node, data in graph.nodes(data=True):
            node = NodeFactory.create_node(data["type"], id=node, **data)
            node_validation(graph, node)
        for in_id, to_id, data in graph.edges(data=True):
            edge_validation(graph, in_id, to_id, **data)
        assert (
            len(
                [
                    node
                    for node, data in graph.nodes(data=True)
                    if data["type"] == "start"
                ]
            )
            <= 1
        ), "Start must be only one."
    except (NodeValidationError, EdgeValidationError, AssertionError) as e:
        raise GraphValidationError(str(e)) from e
    return graph
