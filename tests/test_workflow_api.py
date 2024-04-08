from typing import get_args, Dict

import pytest

from .utils import (
    graph_fixtures,
    GraphValidCases,
    GraphFixableCases,
    GraphInvalidDataCases,
    sorting_key_node,
    sorting_key_edge,
)
from workflow.models.node.factory import NodeFactory
from workflow.models.workflow import Workflow


class TestWorkflowAPI:
    workflows: Dict[str, int] = {}

    def test_workflow_create_empty(self, api_client):
        response = api_client.post(
            "/workflow/",
            json={},
        )
        assert response.status_code == 201
        data = Workflow(**response.json())
        self.workflows["0"] = data.id

    @pytest.mark.parametrize(
        "key, data",
        [
            pytest.param(key, d, id=key)
            for key, d in graph_fixtures.items()
            if key in get_args(GraphFixableCases) + get_args(GraphValidCases)
        ],
    )
    def test_workflow_create_valid(self, api_client, key: str, data: dict):
        response = api_client.post(
            "/workflow/",
            json={"graph_data": data},
        )
        assert response.status_code == 201
        response_json = response.json()
        model = Workflow(**response_json)
        assert model
        data_nodes, model_nodes = [
            sorted(l, key=sorting_key_node)
            for l in (data["nodes"], model.graph_data["nodes"])
        ]
        data_links, model_links = [
            sorted(l, key=sorting_key_edge)
            for l in (data["links"], model.graph_data["links"])
        ]
        assert model_nodes == data_nodes
        assert model_links == data_links
        assert model.graph_data["directed"]
        self.workflows[key] = model.id

    @pytest.mark.parametrize(
        "data",
        [
            pytest.param(d, id=key)
            for key, d in graph_fixtures.items()
            if key in get_args(GraphInvalidDataCases)
        ],
    )
    def test_workflow_create_invalid(self, api_client, data):
        response = api_client.post(
            "/workflow/",
            json={"graph_data": data},
        )
        assert response.status_code == 422

    def test_workflow_list(self, api_client):
        response = api_client.get("/workflow/")
        assert response.status_code == 200
        wokflows_list = response.json()
        wokflows_map = {x["id"]: {**x} for x in wokflows_list}
        for dataindex in (
            tuple(["0"])
            + get_args(GraphFixableCases)
            + get_args(GraphValidCases)
        ):
            current_id = self.workflows[dataindex]
            assert current_id in [x["id"] for x in wokflows_list]
            workflow = wokflows_map[current_id]
            model = Workflow(**workflow)
            if dataindex == "0":
                data = {"nodes": [], "links": []}
            else:
                data = graph_fixtures[dataindex]

            data_nodes, model_nodes = [
                sorted(l, key=sorting_key_node)
                for l in (data["nodes"], model.graph_data["nodes"])
            ]
            data_links, model_links = [
                sorted(l, key=sorting_key_edge)
                for l in (data["links"], model.graph_data["links"])
            ]
            assert model_nodes == data_nodes
            assert model_links == data_links
            assert model.graph_data["directed"]

    def test_workflow_get(self, api_client):
        for key, w_id in self.workflows.items():
            response = api_client.get(f"/workflow/{w_id}/")
            assert response.status_code == 200
            workflow = Workflow(**response.json())
            assert workflow.id == w_id
            if key == "0":
                data = {"nodes": [], "links": []}
            else:
                data = graph_fixtures[key]

            data_nodes, model_nodes = [
                sorted(l, key=sorting_key_node)
                for l in (data["nodes"], workflow.graph_data["nodes"])
            ]
            data_links, model_links = [
                sorted(l, key=sorting_key_edge)
                for l in (data["links"], workflow.graph_data["links"])
            ]
            assert model_nodes == data_nodes
            assert model_links == data_links
            assert workflow.graph_data["directed"]

    def test_workflow_delete(self, api_client):
        to_delete = self.workflows["0"]
        response = api_client.delete(f"/workflow/{to_delete}/")
        assert response.status_code == 204
        response = api_client.get(f"/workflow/{to_delete}/")
        assert response.status_code == 404

    def test_workflow_route(self, api_client):
        key = "no-connected-end"
        to_get = self.workflows[key]
        assert api_client.get(f"/workflow/{to_get}/route/").status_code == 404
        assert (
            api_client.get(f"/workflow/{to_get}/route_string/").status_code
            == 404
        )
        key = "no-connected-start"
        to_get = self.workflows[key]
        assert (
            api_client.delete(f"/workflow/{to_get}/nodes/0").status_code == 204
        )
        assert (
            api_client.get(f"/workflow/{to_get}/route_string/").status_code
            == 400
        )
        assert (
            api_client.get(f"/workflow/{to_get}/route_string/").status_code
            == 400
        )
        key = "simple"
        to_get = self.workflows[key]
        response = api_client.get(f"/workflow/{to_get}/route/")
        assert response.status_code == 200
        assert response.json() == graph_fixtures[key]["path"]
        response = api_client.get(f"/workflow/{to_get}/route_string/")
        assert response.status_code == 200
        route = graph_fixtures[key]["path"]
        route_nodes = [
            NodeFactory.create_node(node_data["type"], **node_data)
            for node_id in route
            for node_data in graph_fixtures[key]["nodes"]
            if node_id == node_data["id"]
        ]
        route_str = "The path to end:\n" + " -> ".join(
            [node.__repr__() for node in route_nodes]
        )
        assert response.text == route_str
