import pytest

from .utils import get_dummy_workflow, sorting_key_node, graph_fixtures


class TestNodeApi:

    @pytest.fixture(scope="class", name="current_workflow", autouse=True)
    def get_workflow(self, request):
        return get_dummy_workflow(graph_fixtures["simple-loop"], request)

    def test_list_nodes(self, api_client, current_workflow):
        response = api_client.get(f"/workflow/{current_workflow.id}/nodes/")
        assert response.status_code == 200
        data = response.json()
        sorted_ = [
            sorted(values, key=sorting_key_node)
            for values in [data, current_workflow.graph_data["nodes"]]
        ]
        assert sorted_[0] == sorted_[1]

    def test_get_node(self, api_client, current_workflow):
        response = api_client.get(f"/workflow/{current_workflow.id}/nodes/7")
        assert response.status_code == 404
        response = api_client.get(f"/workflow/{current_workflow.id}/nodes/0")
        assert response.status_code == 200
        assert response.json() == {"id": 0, "type": "start"}

    def test_delete_node(self, api_client, current_workflow):
        response = api_client.delete(
            f"/workflow/{current_workflow.id}/nodes/7"
        )
        assert response.status_code == 404
        response = api_client.delete(
            f"/workflow/{current_workflow.id}/nodes/1"
        )
        assert response.status_code == 204
        assert (
            api_client.get(
                f"/workflow/{current_workflow.id}/nodes/1"
            ).status_code
            == 404
        )
        # Edge should be deleted as well
        assert (
            api_client.get(
                f"/workflow/{current_workflow.id}/edges/4/1"
            ).status_code
            == 404
        )

    def test_create_node(self, api_client, current_workflow):
        response = api_client.post(
            f"/workflow/{current_workflow.id}/nodes/?node_type=start",
            json={
                "rule": "Yes"
            },  # invalid but filtered out in validation by node type
        )
        assert response.status_code == 400  # validation error multiple starts
        assert response.json() == {
            "details": "Start node has already been added",
            "message": "Oh dear! The workflow node is invalid.",
        }
        response = api_client.post(
            f"/workflow/{current_workflow.id}/nodes/?node_type=condition",
            json={"rule": "some_rule==True"},
        )
        assert response.json() == {
            "type": "condition",
            "rule": "some_rule==True",
            "id": 7,
        }
        response = api_client.post(
            f"/workflow/{current_workflow.id}/nodes/?node_type=message",
            json={
                "message_text": "some_text",
                "status": "sent",
                "rule": "some_rule==True",  # must be filtered out
            },
        )
        assert response.json() == {
            "type": "message",
            "message_text": "some_text",
            "status": "sent",
            "id": 8,
        }
        response = api_client.post(
            f"/workflow/{current_workflow.id}/nodes/?node_type=end",
            json={
                "message_text": "some_text",  # must be filtered out
                "status": "sent",  # must be filtered out
                "rule": "some_rule==True",  # must be filtered out
            },
        )
        assert response.json() == {
            "type": "end",
            "id": 9,
        }

    def test_update_node(self, api_client, current_workflow):
        response = api_client.patch(
            f"/workflow/{current_workflow.id}/nodes/3",
            json={"message_text": "No", "status": "sent"},
        )
        assert response.status_code == 200
        assert response.json() == {
            "id": 3,
            "type": "message",
            "message_text": "No",
            "status": "sent",
        }
        response = api_client.patch(
            f"/workflow/{current_workflow.id}/nodes/4",
            json={"message_text": "No"},
        )
        assert response.status_code == 400  # Bad request
        response = api_client.patch(
            f"/workflow/{current_workflow.id}/nodes/4",
            json={"message_text": "No", "status": "sent"},
        )
        assert response.status_code == 400  # validation error
        response = api_client.patch(
            f"/workflow/{current_workflow.id}/nodes/10", json={"rule": "Yes"}
        )
        assert response.status_code == 404
