import re
from typing import get_args

import pytest
from networkx import DiGraph, NetworkXNoPath

from workflow.models.edge import ConditionEdge, SimpleEdge
from workflow.models.node import (
    NodeType,
    StartNode,
    EndNode,
    ConditionNode,
    MessageNode,
)
from workflow.models.node.factory import NodeFactory
from workflow.utils import Pathfinder
from workflow.utils.pathfinder import NotChanged
from workflow.utils.validation import (
    EdgeValidationError,
    GraphValidationError,
    NodeValidationError,
)
from .utils import (
    graph_fixtures,
    load_graph,
    GraphValidCases,
    GraphFixableCases,
    get_graph,
    GraphInvalidDataCases,
)



def fix_graph(key: GraphFixableCases) -> dict:
    fix = dict(graph_fixtures[key]["fix"])
    fixed_edges: list = list(graph_fixtures[key]["links"])
    if fix.get("remove"):
        fixed_edges.remove(fix["remove"])
    if fix.get("add"):
        fixed_edges.append(fix["add"])
    fixed = {**graph_fixtures[key]}
    fixed["links"] = fixed_edges
    return fixed


class TestPathfinder:

    @pytest.mark.parametrize(
        "graph_sample_key,data",
        [
            pytest.param(key, d, id=key)
            for key, d in graph_fixtures.items()
            if key in get_args(GraphFixableCases) + get_args(GraphValidCases)
        ],
    )
    def test_snapshot(self, graph_sample_key: str, data: dict):
        graph = load_graph(graph_sample_key)
        pathfinder = Pathfinder(graph)
        assert isinstance(pathfinder.graph, DiGraph)
        snapshot = pathfinder.graph_snapshot

        def sorting_key_node(x):
            return x["id"]

        assert sorted(snapshot["nodes"], key=sorting_key_node) == sorted(
            data["nodes"], key=sorting_key_node
        )

        def sorting_key_edge(x):
            return x["source"], x["target"], x.get("condition", None)

        assert sorted(snapshot["links"], key=sorting_key_edge) == sorted(
            data["links"], key=sorting_key_edge
        )
        assert snapshot.get("directed", True)
        assert not snapshot.get("multigraph", False)

    @pytest.mark.parametrize(
        "graph_sample_key",
        [
            key
            for key in get_args(GraphInvalidDataCases)
            if key != "invalid-data"  # This case covered in `Workflow` tests
        ],
    )
    def test_import_fail(self, graph_sample_key: str):
        graph = load_graph(graph_sample_key)
        with pytest.raises(GraphValidationError) as graph_error:
            Pathfinder(graph)
        match graph_sample_key:
            case "multigraph":
                graph_error.match("The graph is multigraph.")
            case "multiple-starts":
                graph_error.match("Start must be only one.")
            # This is a bit tricky, because we have to check the cause of the error
            # The graph validation internally raises `NodeValidationError` or `EdgeValidationError`
            # So we have to check the cause of the error in the `graph_error.value.__cause__` to make sure
            # that the error is raised by the validation of the corresponding content
            case "invalid-edges":
                assert isinstance(
                    graph_error.value.__cause__, EdgeValidationError
                )
            case "invalid-nodes":
                assert isinstance(
                    graph_error.value.__cause__, NodeValidationError
                )

    @pytest.mark.parametrize("graph_sample_key", get_args(GraphValidCases))
    def test_find_path_success(self, graph_sample_key: GraphValidCases):
        path = graph_fixtures[graph_sample_key]["path"]
        graph = load_graph(graph_sample_key)
        pathfinder = Pathfinder(graph)
        assert isinstance(pathfinder.graph, DiGraph)
        assert pathfinder.path == path

    @pytest.mark.parametrize("graph_sample_key", get_args(GraphFixableCases))
    def test_no_path_and_fix(self, graph_sample_key: GraphFixableCases):
        graph = load_graph(graph_sample_key)
        pathfinder = Pathfinder(graph)
        assert isinstance(pathfinder.graph, DiGraph)
        if graph_sample_key == "dead-loop":
            with pytest.raises(
                RecursionError, match="There is a loop in the workflow."
            ):
                pathfinder.find_path_recursive()
        else:
            with pytest.raises(NetworkXNoPath, match="No path found"):
                pathfinder.find_path_recursive()
        # fix the graph
        fixed_graph = get_graph(fix_graph(graph_sample_key))
        pathfinder = Pathfinder(fixed_graph)
        assert isinstance(pathfinder.graph, DiGraph)
        path = graph_fixtures[graph_sample_key]["path"]
        assert pathfinder.path == path

    def test_add_node(self):
        """
        This test make sure we can add nodes correctly

        Test perform transform `simple` graph into a `simple-loop`-like graph by adding nodes
        """
        graph = load_graph("simple")
        pathfinder = Pathfinder(graph)
        nodes = [
            StartNode(id=999),  # should be unable to add
            EndNode(id=888),
            ConditionNode(id=777, rule="message_text =~ '.*BlockedPath$'"),
            MessageNode(
                id=666, message_text="Oh, No! BlockedPath", status="opened"
            ),
        ]
        for node in nodes:
            match node:
                case StartNode():  # We can't add start node!
                    with pytest.raises(
                        ValueError, match="Start node has already been added"
                    ):
                        pathfinder.add_node(node)
                    assert node.id not in pathfinder.graph.nodes
                case _:  # But can add the others
                    pathfinder.add_node(node)
                    assert node.id in pathfinder.graph.nodes
        # And make sure nothing brakes here (we don't add edges so nothing should be changed)
        assert pathfinder.path == graph_fixtures["simple"]["path"]

    def test_add_update_edge(self):
        """
        This test make sure we can add edges correctly

        Test perform transform `simple` graph into a `simple-loop` graph by adding nodes
        """
        graph = load_graph("simple")
        pathfinder = Pathfinder(graph)

        nodes = [
            EndNode(id=6),
            ConditionNode(id=5, rule="message_text =~ '.*BlockedPath$'"),
            MessageNode(
                id=3, message_text="Oh, No! BlockedPath", status="opened"
            ),
        ]
        edges = [
            SimpleEdge(in_node_id=3, out_node_id=5),
            ConditionEdge(in_node_id=5, out_node_id=6, condition="No"),
            ConditionEdge(in_node_id=5, out_node_id=4, condition="Yes"),
        ]
        for node in nodes:
            pathfinder.add_node(node)
            assert node.id in pathfinder.graph.nodes
        edge = ConditionEdge(in_node_id=4, out_node_id=3, condition="No")
        with pytest.raises(
            ValueError,
            match=re.escape(
                "Condition node can only have two outgoing edges (Yes/No)."
            ),
        ):
            pathfinder.add_edge(
                edge.in_node_id,
                edge.out_node_id,
                **edge.model_dump(exclude={"in_node_id", "out_node_id"}),
            )
        pathfinder.update_edge(
            edge.in_node_id,
            edge.out_node_id,
            **edge.model_dump(exclude={"in_node_id", "out_node_id"}),
        )
        for edge in edges:
            if isinstance(edge, ConditionEdge):
                with pytest.raises(
                    ValueError,
                    match="Condition node param can only have Yes/No edges.",
                ):
                    # Can't add condition output as simple edge
                    pathfinder.add_edge(
                        edge.in_node_id,
                        edge.out_node_id,
                        **{"condition": "WrongCondition"},
                    )
                pathfinder.add_edge(
                    edge.in_node_id,
                    edge.out_node_id,
                    **edge.model_dump(exclude={"in_node_id", "out_node_id"}),
                )
            elif isinstance(edge, SimpleEdge):
                with pytest.raises(
                    ValueError, match="This edge can't have attributes."
                ):
                    # Can't add condition output as simple edge
                    pathfinder.add_edge(
                        edge.in_node_id,
                        edge.out_node_id,
                        **{"condition": "No"},
                    )
                pathfinder.add_edge(edge.in_node_id, edge.out_node_id)

            assert (
                edge.in_node_id,
                edge.out_node_id,
                (
                    edge.model_dump(exclude={"in_node_id", "out_node_id"})
                    if isinstance(edge, ConditionEdge)
                    else {}
                ),
            ) in pathfinder.graph.edges(data=True)

            if isinstance(edge, ConditionEdge):
                if len(pathfinder.graph.out_edges(edge.in_node_id)) <= 1:
                    with pytest.raises(
                        ValueError,
                        match=f"Only one {edge.condition} path should be exist from node {edge.in_node_id}.",
                    ):
                        # Can't add same condition another time
                        pathfinder.add_edge(
                            edge.in_node_id,
                            3,
                            **edge.model_dump(
                                exclude={"in_node_id", "out_node_id"}
                            ),
                        )
                if len(pathfinder.graph.out_edges(edge.in_node_id)) == 2:
                    with pytest.raises(
                        ValueError,
                        match=re.escape(
                            "Condition node can only have two outgoing edges (Yes/No)."
                        ),
                    ):
                        # Can't add more than two conditions
                        pathfinder.add_edge(
                            edge.in_node_id,
                            3,
                            **edge.model_dump(
                                exclude={"in_node_id", "out_node_id"}
                            ),
                        )
            elif isinstance(edge, SimpleEdge):
                node = pathfinder.get_node(edge.in_node_id)
                if node.type in [NodeType.start, NodeType.message]:
                    with pytest.raises(
                        ValueError,
                        match="Node can only have one outgoing edge.",
                    ):
                        # Can't add more than one output to one-out nodes
                        pathfinder.add_edge(edge.in_node_id, 6)
        with pytest.raises(
            ValueError, match="End node cannot have outgoing edges."
        ):
            # Can't add output to end nodes
            pathfinder.add_edge(6, 3)
        with pytest.raises(
            ValueError, match="Start node cannot have incoming edges."
        ):
            # Can't add input to start nodes
            pathfinder.add_edge(3, 0)

        # Make sure nothing brakes here (we don't add edges so nothing should be changed)
        assert pathfinder.path == graph_fixtures["simple"]["path"]

        # Let's update the node 2 to finish transformation
        pathfinder.update_node(
            MessageNode(id=2, message_text="Text To NOT Match", status="sent")
        )
        # Now it should be `simple-loop` graph
        assert pathfinder.path == graph_fixtures["simple-loop"]["path"]

    def test_from_zero_to_hero(self):
        """
        Test that initialize an empty graph inside `Pathfinder` and utilize it to build a graph
        Than adds nodes and edges between them
                      start
                        ↓
        message(text="zero", status="pending")
                        ↓
        condition(text=="zero" and status=="sent") -(no)-> message(text="anti-hero", status="sent")
                        |                                               |
                      (yes)                                             |
                        ↓                                               |
        message(text="hero", status="opened")                           |
                        ├-----------------------------------------------┘
                        ↓
        condition(text=="hero" or status=="sent") -(no)-> message(text="UNREACHABLE", status="opened")
                        |
                      (yes)
                        ↓
                       end
        """
        graph = DiGraph()
        pathfinder = Pathfinder(graph)
        nodes = [
            {"type": "start", "id": 0},
            {
                "type": "message",
                "id": 1,
                "message_text": "zero",
                "status": "pending",
            },
            {
                "type": "condition",
                "id": 2,
                "rule": "message_text == 'zero' and status == 'sent'",
            },
            {
                "type": "message",
                "id": 3,
                "message_text": "anti-hero",
                "status": "sent",
            },
            {
                "type": "message",
                "id": 4,
                "message_text": "hero",
                "status": "opened",
            },
            {
                "type": "condition",
                "id": 5,
                "rule": "message_text == 'hero' or status == 'sent'",
            },
            {
                "type": "message",
                "id": 6,
                "message_text": "UNREACHABLE",
                "status": "opened",
            },
            {"type": "end", "id": 7},
        ]
        edges = [
            {  # start -> zero (INPATH)
                "source": 0,
                "target": 1,
            },
            {  # zero -> condition (INPATH)
                "source": 1,
                "target": 2,
            },
            {  # condition --(NO)-> anti-hero (INPATH)
                "source": 2,
                "target": 3,
                "condition": "No",
            },
            {  # condition --(YES)-> hero
                "source": 2,
                "target": 4,
                "condition": "Yes",
            },
            {  # anti-hero -> condition (INPATH)
                "source": 3,
                "target": 5,
            },
            {  # hero -> condition
                "source": 4,
                "target": 5,
            },
            {  # condition --(NO)-> UNREACHABLE
                "source": 5,
                "target": 6,
                "condition": "No",
            },
            {  # condition --(YES)-> end (INPATH)
                "source": 5,
                "target": 7,
                "condition": "Yes",
            },
        ]
        expected_path = [0, 1, 2, 3, 5, 7]

        for node in nodes:
            node = NodeFactory.create_node(NodeType(node["type"]), **node)
            pathfinder.add_node(node)
        for edge in edges:
            source = edge["source"]
            target = edge["target"]
            attrs = {
                key: value
                for key, value in edge.items()
                if key not in ("source", "target")
            }
            pathfinder.add_edge(source, target, **attrs)
        assert pathfinder.path == expected_path

    def test_node_edge_deleting(self):
        graph = load_graph("simple")
        pathfinder = Pathfinder(graph)
        # Let's delete the edge 4, 2
        assert (4, 2) in pathfinder.graph.edges
        pathfinder.remove_edge(4, 2)
        assert (4, 2) not in pathfinder.graph.edges
        assert pathfinder.path == graph_fixtures["simple"]["path"]
        # If we remove node 4, the edges (2, 4) (4, 1) should be removed too
        # Also it will break path
        assert (4, 1) in pathfinder.graph.edges
        assert (2, 4) in pathfinder.graph.edges
        pathfinder.remove_node(4)
        assert 4 not in pathfinder.graph.nodes
        assert (4, 1) not in pathfinder.graph.edges
        assert (2, 4) not in pathfinder.graph.edges

    def test_edge_updating(self):
        graph = load_graph("simple")
        pathfinder = Pathfinder(graph)
        # Let's update the edge 4, 1 to the same
        assert (4, 1, {"condition": "Yes"}) in pathfinder.graph.edges(
            data=True
        )
        with pytest.raises(NotChanged):
            pathfinder.update_edge(4, 1, condition="Yes")
        assert (4, 1, {"condition": "Yes"}) in pathfinder.graph.edges(
            data=True
        )
        assert pathfinder.path == graph_fixtures["simple"]["path"]
        # Let's swap conditions the edge 4, 2 and 4, 1, this should make a dead-loop
        pathfinder.update_edge(4, 1, condition="No")
        assert (4, 1, {"condition": "No"}) in pathfinder.graph.edges(data=True)
        assert (4, 2, {"condition": "Yes"}) in pathfinder.graph.edges(
            data=True
        )
        with pytest.raises(
            RecursionError, match="There is a loop in the workflow."
        ):
            pathfinder.find_path_recursive()
        # Let's update the edge 2, 4
        with pytest.raises(EdgeValidationError):
            pathfinder.update_edge(2, 1, condition="Yes")
        pathfinder.update_edge(2, 1)
        assert (2, 1) in pathfinder.graph.edges
        assert (2, 4) not in pathfinder.graph.edges
        assert pathfinder.path == [0, 2, 1]
