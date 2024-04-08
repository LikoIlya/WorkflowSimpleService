import pytest

from .utils import get_dummy_workflow, graph_fixtures


class TestEdgeApi:
    @pytest.fixture(scope="class", name="current_workflow", autouse=True)
    def get_workflow(self, request):
        return get_dummy_workflow(graph_fixtures["simple-loop"], request)

    def test_list_edges(self, api_client, current_workflow):
        response = api_client.get(f"/workflow/{current_workflow.id}/edges/")
        assert response.status_code == 200
        data = response.json()
        sorted_ = [
            sorted(values, key=lambda x: (x["in_node_id"], x["in_node_id"]))
            for values in [
                data,
                [
                    {
                        "in_node_id": x["source"],
                        "out_node_id": x["target"],
                        **dict(
                            {
                                k: v
                                for k, v in x.items()
                                if k not in ["source", "target"]
                            }
                        ),
                    }
                    for x in current_workflow.graph_data["links"]
                ],
            ]
        ]
        assert sorted_[0] == sorted_[1]

    def test_get_edge(self, api_client, current_workflow):
        response = api_client.get(f"/workflow/{current_workflow.id}/edges/0/1")
        assert response.status_code == 404
        response = api_client.get(f"/workflow/{current_workflow.id}/edges/0/2")
        assert response.status_code == 200
        assert response.json() == {"in_node_id": 0, "out_node_id": 2}

    def test_delete_edge(self, api_client, current_workflow):
        response = api_client.delete(
            f"/workflow/{current_workflow.id}/edges/0/1"
        )
        assert response.status_code == 404
        response = api_client.delete(
            f"/workflow/{current_workflow.id}/edges/0/2"
        )
        assert response.status_code == 204
        response = api_client.delete(
            f"/workflow/{current_workflow.id}/edges/0/2"
        )
        assert response.status_code == 404

    def test_create_edge(self, api_client, current_workflow):
        response = api_client.post(
            f"/workflow/{current_workflow.id}/edges/",
            json={"in_node_id": 0, "out_node_id": 2, "condition": "Yes"},
        )
        assert response.status_code == 400  # validation error
        assert response.json() == {
            "details": "This edge can't have attributes.",
            "message": "Well well, we have an error with edge validation. Please try again.",
        }
        response = api_client.post(
            f"/workflow/{current_workflow.id}/edges/",
            json={"in_node_id": 4, "out_node_id": 1, "condition": "Yes"},
        )
        assert response.status_code == 400  # exists
        assert response.json() == {"detail": "Already exists."}
        response = api_client.post(
            f"/workflow/{current_workflow.id}/edges/",
            json={"in_node_id": 0, "out_node_id": 2},
        )
        assert response.json() == {"in_node_id": 0, "out_node_id": 2}

    def test_update_edge(self, api_client, current_workflow):
        response = api_client.patch(
            f"/workflow/{current_workflow.id}/edges/4/1",
            json={"condition": "No"},
        )
        assert response.status_code == 200
        assert response.json() == {
            "in_node_id": 4,
            "out_node_id": 1,
            "condition": "No",
        }
        response = api_client.patch(
            f"/workflow/{current_workflow.id}/edges/0/2",
            json={"condition": "Yes"},
        )
        assert response.status_code == 400  # validation error
        assert response.json() == {
            "details": "This edge can't have attributes.",
            "message": "Well well, we have an error with edge validation. Please try again.",
        }

        response = api_client.patch(
            f"/workflow/{current_workflow.id}/edges/0/1",
            json={"condition": "Yes"},
        )
        assert response.status_code == 400  # Bad request
