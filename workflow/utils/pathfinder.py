import json
import logging
from functools import reduce
from typing import List, Optional, Set, Tuple, Unpack
from uuid import UUID, uuid4

from networkx import (
    DiGraph,
    NetworkXError,
    NetworkXNoPath,
    has_path,
    node_link_data,
    set_edge_attributes,
    set_node_attributes,
)
from pydantic import BaseModel, computed_field

from workflow.models.edge import Edge, EdgeContext
from workflow.models.edge.condition import ConditionEdge
from workflow.models.node import (
    ConditionNode,
    EndNode,
    MessageNode,
    NodeFactory,
    NodeIdType,
    NodeType,
    StartNode,
    ValidNode,
)

from .exceptions import EdgeValidationError, NodeValidationError
from .validation import edge_validation, node_validation, validate_graph


class NotChanged(Exception):
    """Represents error when update is called with no changes
    a.k.a. HTTP 304 Not Modified


    """


class SearchContext(BaseModel):
    """Represents search context to access stored values in execution"""

    last_message: Optional[MessageNode] = None


class Pathfinder:
    """Module responsible for finding paths in graph
    ------
    Also this module provides a
    CRUD-like operations over the nodes and edges
    of the graph with validation of rules of Workflow


    """

    # region Fields
    _graph: DiGraph
    context: SearchContext = SearchContext()

    # region Graph access get/set
    @property
    def graph(self) -> DiGraph:
        """The graph of the workflow"""
        return self._graph

    @graph.setter
    def graph(self, graph: DiGraph):
        """The graph of the workflow
        performs a validation before updating the graph

        :param graph: DiGraph:
        :param graph: DiGraph:

        """
        validate_graph(graph)
        self._graph = graph

    # endregion
    # endregion

    def __init__(self, graph: DiGraph):
        """

        :param graph: DiGraph:

        """
        self.graph = graph

    # region Node related private helpers

    def __to_models_repr__(
        self, *nodes_list: List[NodeIdType]
    ) -> List[ValidNode]:
        """Converts provided node ids into valid Nodes instances
        if None of IDs are provided, calculates the valid path from start to end

        :param nodes_list: List[NodeIdType]:  (Default value = None)
        :param *nodes_list: List[NodeIdType]:

        """
        nodes_list = [
            self.__node_to_model__(node_id)
            for node_id in (nodes_list if nodes_list else self.path)
        ]
        return nodes_list

    def __node_to_model__(self, node_id: NodeIdType) -> ValidNode:
        """Retrieve the node instance for the given node ID.

        :param node_id: The ID of the node.
        :type node_id: NodeIdT
        :param node_id: NodeIdType:
        :param node_id: NodeIdType:
        :param node_id: NodeIdType:
        :returns: The node model.
        :rtype: Node

        """
        if node_id in self.graph.nodes:
            node = NodeFactory.create_node(
                self.graph.nodes[node_id]["type"], **self.graph.nodes[node_id]
            )
            if node.id is None:
                node.id = node_id
            return node
        else:
            raise IndexError(
                f"Node with ID {node_id} does not exist in current Workflow."
            )

    # endregion

    # region Computed Fields (Graph related)
    @computed_field
    @property
    def graph_snapshot(self) -> dict:
        """Returns the snapshot of the current workflow graph in node-link format"""
        return node_link_data(self.graph)

    @computed_field
    @property
    def path(self) -> List[NodeIdType]:
        """Shortcut to retrieve the calculated path"""
        return self.find_path_recursive()

    @computed_field
    @property
    def start_node_id(self) -> NodeIdType:
        """fast access to start node id"""
        return next(  # There is no more than one start node at graph
            iter(
                node_id
                for node_id in self.graph.nodes
                if self.graph.nodes[node_id]["type"] == "start"
            ),
            None,
        )

    # endregion

    # region Search module (recursive)
    def find_path_recursive(self) -> List[NodeIdType]:
        """Finds a path from the start node to the end node in the workflow.
        using recursive depth first perform findings


        :returns: The path from the start node to the end node, or `None` if no path is found.

        :rtype: list[NodeID] or None
        :raises RecursionError: If a recursion reached the same state as was in history path
        :raises NetworkXNoPath: If no path found

        """
        # Validate that we have path between `start` and any `end` nodes at all
        if not any(
            has_path(
                self.graph, self.start_node_id, end_node_id
            )  # Check theoretic path to the `end` node
            for (end_node_id, data) in self.graph.nodes(data=True)
            if data["type"] == "end"  # Filtered `end` nodes
        ):
            raise NetworkXNoPath("No path found")

        StateType = Tuple[NodeIdType, Unpack[SearchContext]]
        path = []
        context = SearchContext()
        visited: Set[StateType] = set()

        # region State Guard
        def not_visited_validator(entry: StateType) -> bool:
            """Checks if the entry is in visited set
            In simple, the guard of recursion in workflow

            the implementation minds that the workflow nodes has static conditions in execution context
            so the state handle that any of execution states will be executed not more than once

            :param entry: StateType: The node and current ctx to check in the workflow.
            :param entry: StateType:

            """
            if entry in visited:
                raise RecursionError("There is a loop in the workflow.")
            return True

        # endregion

        # region Recursive finder
        def search(current_node_id: NodeIdType, **ctx: Unpack[SearchContext]):
            """Searches for the next step in the workflow based on the current node and last message.

            :param current_node_id: NodeID: The current node in the workflow.
            :type current_node_id: NodeIdType
            :param ctx: SearchContext: The context of the search
            :type ctx: SearchContext
            :param current_node_id: NodeIdType:
            :param **ctx: Unpack[SearchContext]:
            :returns: True` if the next step is found, `False` otherwise.
            :rtype: bool

            """
            # region Mark node+ctx_state as visited
            current_state: StateType = (
                current_node_id,
                tuple(
                    [
                        json.dumps(dict(ctx_e_data)) if ctx_e_data else None
                        for ctx_e_data in ctx.values()
                    ]
                ),
            )
            visited.add(current_state)
            # endregion
            current_node = self.__node_to_model__(current_node_id)
            # region Next edge claiming...
            match current_node.type:
                case "start" | "message":
                    out_node_id = next(
                        iter(
                            node_id
                            for (_, node_id) in self.graph.out_edges(
                                current_node_id
                            )
                        ),
                        None,
                    )  # [Start Node/Message Node] Може мати лише одне вихідне ребро
                    if current_node.type == "message":
                        ctx["last_message"] = (
                            current_node  # write the last_message to context
                        )
                case (
                    "condition"
                ):  # When met a condition, we need to execute condition rule based on last_message
                    condition_result = current_node.execute_condition(
                        ctx.get("last_message", None)
                    )  # Yes/No
                    out_node_id = next(
                        iter(
                            node_id
                            for (_, node_id, data) in self.graph.out_edges(
                                current_node_id, data=True
                            )
                            if data.get("condition", None) == condition_result
                        ),
                        None,
                    )  # Get the right path
                case "end":
                    logging.debug("Recursive end here (inner)")
                    return True  # Recursive end here (inner) success
                case _:
                    raise NotImplementedError(
                        f"Unknown node type: {current_node.__class__.__name__}"
                    )
                    # OR Try to handle unknown node?
                    # for (_, out_node_id, data) in self.graph.out_edges(current_node_id, data=True):
                    #     (if we can have some multiple output paths)
                    #     if next_step(out_node_id):
                    #         return True # Recursive end here (inner)
                    #     else:
                    #         continue
                    # return False
            if out_node_id is None:
                # Claim failed
                return False  # Recursive end here (inner) fail
            # endregion
            # region Move to next step (deeper)
            next_state = (
                out_node_id,
                tuple(
                    [
                        json.dumps(dict(ctx_e_data)) if ctx_e_data else None
                        for ctx_e_data in ctx.values()
                    ]
                ),
            )
            if not_visited_validator(next_state) and search(
                out_node_id, **ctx
            ):  # Recursive call in here (search)
                path.append(out_node_id)
                # The first added node here will be `end` node
                # The second - previous before end, and so on
                # Meaning that the resulting `path` will be reversed
                logging.debug("Recursive end here (outer)")
                return True  # Recursive end here (outer) success
            # endregion
            # or exit if deep-dive fails
            return False  # Recursive end here (outer) fail

        # endregion

        if search(self.start_node_id, **context.model_dump()):
            path.append(
                self.start_node_id
            )  # Adding to the end of the list start node
            path.reverse()
            return path
        raise NetworkXNoPath("No path found")

    # endregion

    # region Nodes manipulations (CRUD)

    # C

    def add_node(self, node: ValidNode) -> None:
        """Adds a node to the workflow.

        :param node: Node: The node to be added.
        :type node: Node
        :param node: ValidNode:
        :param node: ValidNode:
        :raises IndexError: If the start node does not have an ID and cant guess next instance.

        """
        if node.id is None:
            if issubclass(NodeIdType, int):
                node.id = max(
                    len(self.graph.nodes),
                    1
                    + reduce(
                        lambda a, b: a if a > b else b, list(self.graph.nodes)
                    ),
                )
            elif issubclass(NodeIdType, UUID):
                node.id = uuid4()
            else:
                raise IndexError("Unknown node id, provide one.")
        try:
            if isinstance(node, StartNode):
                if [
                    n
                    for n, d in self.graph.nodes(data=True)
                    if d["type"] == "start"
                ]:
                    raise NodeValidationError(
                        "Start node has already been added"
                    )
                if any(self.graph.in_edges(node.id)):
                    raise NodeValidationError(
                        "Start node cannot have incoming edges."
                    )
            elif isinstance(node, EndNode):
                if any(self.graph.out_edges(node.id)):
                    raise NodeValidationError(
                        "End node cannot have outgoing edges."
                    )
        except NetworkXError:
            logging.debug("No nodes found in the workflow.")
        node_data = node.model_dump(exclude=["id"])
        node_data["type"] = node.type
        node_validation(self.graph, node)
        self.graph.add_node(node.id, **node_data)

    # R

    def get_node(self, node_id: NodeIdType) -> ValidNode:
        """Retrieve the node by its id

        :param node_id: NodeIdType: NodeID: The ID of the node.
        :param node_id: NodeIdType:
        :returns: ValidNode: Node instance
        :rtype: ValidNode
        :raises NodeValidationError: If the node is not valid
        :raises IndexError: If the node ID in not in the workflow nodes

        """
        return self.__node_to_model__(node_id)

    # U

    def update_node(self, node: ValidNode) -> None:
        """Update a node in the workflow.

        :param node: Node: The node to be updated.
        :type node: Node
        :param node: ValidNode:
        :param node: ValidNode:
        :raises NodeValidationError: If the node is a StartNode or EndNode, it cannot be updated.
        :raises IndexError: If the node does not exist in the graph.

        """
        if node.id in self.graph.nodes:
            new_node_data = node.model_dump()
            new_node_data["type"] = node.type
            old_node = self.__node_to_model__(node.id)
            if old_node.type == node.type and node != old_node:
                if (
                    old_node.type in [NodeType.start, NodeType.end]
                    and len(new_node_data) == 1
                ):
                    raise NodeValidationError(
                        "This node can't be updated."
                    )  # Only `type` must be here
                node = node_validation(self.graph, node)
                set_node_attributes(self.graph, {node.id: {**new_node_data}})
        else:
            raise IndexError("This node does not exist.")

    # D
    def remove_node(self, node_id: NodeIdType) -> None:
        """Removes a node from the workflow graph.

        :param node_id: NodeIdType: The ID of the node to be removed.
        :type node_id: NodeIdType
        :param node_id: NodeIdType:

        """
        if node_id not in self.graph.nodes:
            raise IndexError("Can't remove unexisting node")
        self.graph.remove_node(node_id)

    # endregion

    # region Edge manipulations (CRUD)

    # C

    def add_edge(
        self,
        from_node_id: NodeIdType,
        to_node_id: NodeIdType,
        **edge_data: Unpack[EdgeContext],
    ) -> None:
        """Adds an edge between two nodes in the workflow graph.

        :param from_node_id: NodeID: The ID of the node where the edge starts.
        :type from_node_id: NodeIdType
        :param to_node_id: NodeID: The ID of the node where the edge ends.
        :type to_node_id: NodeIdType
        :param edge_data: EdgeContext: Additional data associated with the edge.
        :type edge_data: EdgeContext
        :param from_node_id: NodeIdType:
        :param to_node_id: NodeIdType:
        :param **edge_data: Unpack[EdgeContext]:
        :returns: None
        :raises EdgeValidationError: If the start node has incoming edges, the end node has outgoing edges,
                the start node has more than one outgoing edge (for StartNode and MessageNode),
                the condition node has more than two outgoing edges (for Yes/No),
                or the condition node has an invalid condition value.

        """
        edge = edge_validation(
            self.graph, from_node_id, to_node_id, **edge_data
        )  # Validate new path
        if isinstance(edge, ConditionEdge):
            res = self.graph.add_edge(
                edge.in_node_id,
                edge.out_node_id,
                **edge.model_dump(exclude={"in_node_id", "out_node_id"}),
            )
        else:
            res = self.graph.add_edge(edge.in_node_id, edge.out_node_id)
        return res

    # R

    def get_edge_data(self, from_node_id, to_node_id) -> Edge:
        """Retrieves the edge from graph

        :param from_node_id: NodeID: The ID of the node where the edge starts.
        :type from_node_id: NodeIdType
        :param to_node_id: NodeID: The ID of the node where the edge ends.
        :type to_node_id: NodeIdType

        """
        if (from_node_id, to_node_id) not in self.graph.edges:
            raise IndexError("The edge does not exist in the graph")
        edge = edge_validation(
            self.graph,
            from_node_id,
            to_node_id,
            **self.graph.edges[from_node_id, to_node_id],
        )
        return edge

    # U

    def update_edge(
        self,
        from_node_id: NodeIdType,
        to_node_id: NodeIdType,
        **edge_data: Unpack[EdgeContext],
    ) -> None:
        """Updates the attributes or target of an existing edge in the workflow graph.

        Currently, only can be updated:
          - [ConditionNode] condition edge attribute - when changed,
                swaps out conditions between out edges.

          - any other edge attributes - when changed,
                updates the edge attributes. (for your inspiration)

        It also handles the case when
        the edge is changed target to another node for a single-out nodes type:
            - tries to guess the original edge if it was changed,
            but it's not guaranteed to be correct
            (guessing is based on the first matched edge with the same attributes).

        :param from_node_id: NodeID: The ID of the node where the edge starts.
        :type from_node_id: NodeIdType
        :param to_node_id: NodeID: The ID of the node where the edge ends.
        :type to_node_id: NodeIdType
        :param edge_data: EdgeContext: Additional data associated with the edge.
        :type edge_data: EdgeContext
        :param from_node_id: NodeIdType:
        :param to_node_id: NodeIdType:
        :param **edge_data: Unpack[EdgeContext]:
        :returns: None
        :raises NotChanged: If the edge attributes are not changed.
        :raises EdgeValidationError: If the edge cannot be found or updated.

        """
        from_mod = self.__node_to_model__(from_node_id)
        # Handle the updating of existing path
        if (from_node_id, to_node_id) in self.graph.out_edges(
            from_node_id
        ):  # then updating of attributes
            if self.graph.out_edges[from_node_id, to_node_id] == edge_data:
                raise NotChanged()
            attr = {(from_node_id, to_node_id): edge_data}
            if isinstance(
                from_mod, ConditionNode
            ):  # Condition Node attributes
                if edge_data.get("condition") not in ["Yes", "No"]:
                    raise EdgeValidationError(
                        "Condition node out edges can only have Yes or No values"
                    )
                if self.graph.out_edges[from_node_id, to_node_id].get(
                    "condition"
                ) != edge_data.get("condition"):
                    attr = {
                        (u, v): {
                            **data,
                            "condition": (
                                "Yes"
                                if data.get("condition") == "No"
                                else "No"
                            ),
                        }
                        for (u, v, data) in self.graph.out_edges(
                            from_node_id, data=True
                        )
                    }
                    assert attr[from_node_id, to_node_id].get(
                        "condition"
                    ) == edge_data.get("condition")
                else:
                    raise NotChanged()  # Should be unreachable here
            set_edge_attributes(self.graph, attr)
        # Else path was changed (there is no one here), trying to resolve it
        elif (
            len(self.graph.out_edges(from_node_id)) == 1
        ):  # Handle single-out nodes that changed end of the edge
            u, v = next(
                (u, v)
                for (u, v, _) in self.graph.out_edges(from_node_id, data=True)
            )  # Get old one
            backup = self.graph.edges[u, v]
            try:
                self.graph.remove_edge(u, v)  # Remove it
                edge_validation(
                    self.graph, from_node_id, to_node_id, **edge_data
                )  # Validate new path
            except EdgeValidationError as e:
                self.graph.add_edge(u, v, **backup)  # Revert old node
                raise e
            self.graph.add_edge(
                from_node_id, to_node_id, **edge_data
            )  # Add brand-new edge path here
        elif (
            edge_data is not None
            and (
                matched := next(
                    iter(
                        [
                            (u, v, d)
                            for (u, v, d) in self.graph.out_edges(
                                from_node_id, data=True
                            )
                            if d == edge_data
                        ]
                    ),
                    None,
                )
            )
            is not None
        ):
            # We caught the equal attributes edge, and it's not None one :)
            # Note that we caught only first entry equal attributes
            (u, old_to_node, backup) = matched
            try:
                self.graph.remove_edge(u, old_to_node)  # Remove it
                edge_validation(
                    self.graph, from_node_id, to_node_id, **edge_data
                )  # Validate new path
            except EdgeValidationError as e:
                self.graph.add_edge(
                    u, old_to_node, **backup
                )  # Revert old node
                raise e
            self.graph.add_edge(
                from_node_id, to_node_id, **edge_data
            )  # Add brand-new edge path here
        else:  # We can't guess what's the original edge it was. Is it bad data or smth not implemented?
            raise EdgeValidationError("Can't guess edge to update")

    # D

    def remove_edge(
        self, from_node_id: NodeIdType, to_node_id: NodeIdType
    ) -> None:
        """Removes an edge between two nodes in the graph.

        :param from_node_id: NodeID: The ID of the node where the edge starts.
        :type from_node_id: NodeIdType
        :param to_node_id: NodeID: The ID of the node where the edge ends.
        :type to_node_id: NodeIdType
        :param from_node_id: NodeIdType:
        :param to_node_id: NodeIdType:

        """
        if (from_node_id, to_node_id) not in self.graph.edges:
            raise IndexError("Can't remove unexisting edge")
        self.graph.remove_edge(from_node_id, to_node_id)

    # endregion
