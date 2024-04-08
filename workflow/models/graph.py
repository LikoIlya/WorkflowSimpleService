from typing import List, Optional

from networkx import DiGraph, node_link_data
from pydantic import BaseModel, ConfigDict

EMPTY_GRAPH = node_link_data(DiGraph())


class NodeLinkStructure(BaseModel):
    """ """

    nodes: List = []
    links: List = []
    directed: Optional[bool] = True

    model_config = ConfigDict(extra="allow")
