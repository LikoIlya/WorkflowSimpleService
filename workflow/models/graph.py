from networkx import DiGraph, node_link_data
from pydantic import BaseModel, ConfigDict

EMPTY_GRAPH = node_link_data(DiGraph())


class NodeLinkStructure(BaseModel):
    """ """

    nodes: list = []
    links: list = []
    directed: bool | None = True

    model_config = ConfigDict(extra="allow")
