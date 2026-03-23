# tests/test_update.py
import pytest
from fastapi.testclient import TestClient
from a2a.types import AgentCard
from agent_registry.server import app


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def mock_registry(mocker):
    return mocker.patch('agent_registry.core.RegistryCore')


@pytest.fixture
def valid_agent_data():
    return {
        "name": "TestAgent",
        "provider": {
            "organization": "TestOrg",
            "url": "https://test.org"
        },
        "description": "Test Description",
        "capabilities": {
            "skills": ["text-generation", "code-generation"],
            "input_modes": ["text/plain", "application/json"],
            "output_modes": ["text/plain", "application/json"]
        },
        "default_input_modes": ["text/plain"],
        "default_output_modes": ["text/plain"],
        "url": "https://agent.test",
        "version": "1.0.0",
        "skills": [
            {
                "id": "skill-1",
                "name": "TestSkill",
                "description": "Test Skill Description",
                "tags": ["test", "skill"],
                "input_modes": ["text/plain"],
                "output_modes": ["text/plain"]
            }
        ]
    }


def test_update_agent_success(client, mock_registry, valid_agent_data):
    # 创建一个测试客户端
    agent = AgentCard(**valid_agent_data)
    mock_registry.return_value.update.return_value = True

    # 发送 PUT 请求进行更新
    response = client.put(
        f"/rest/a2a-t/v1/update_agent/{agent.name}",
        params={"organization": agent.provider.organization},
        json=valid_agent_data
    )

    # 验证响应
    assert response.status_code == 200
    assert response.json() is True


def test_update_agent_not_found(client, mock_registry, valid_agent_data):
    # 模拟更新一个不存在的 Agent
    mock_registry.return_value.update.return_value = False

    # 发送 PUT 请求进行更新
    response = client.put(
        "/rest/a2a-t/v1/update_agent/NonExistentAgent",
        params={"organization": "TestOrg"},
        json=valid_agent_data
    )

    # 验证响应
    assert response.status_code == 404
    assert response.json() == {"detail": "Agent not found"}


def test_update_agent_invalid_data(client, mock_registry, valid_agent_data):
    # 创建一个缺少必填字段的测试数据
    invalid_data = {k: v for k, v in valid_agent_data.items() if k != "name"}

    # 发送 PUT 请求进行更新
    response = client.put(
        "/rest/a2a-t/v1/update_agent/TestAgent",
        params={"organization": "TestOrg"},
        json=invalid_data
    )

    # 验证响应
    assert response.status_code == 422
    assert "Field required" in response.json()["detail"][0]["msg"]


def test_update_agent_change_primary_key(client, mock_registry, valid_agent_data):
    # 创建一个尝试更改主键的测试数据
    modified_data = valid_agent_data.copy()
    modified_data["name"] = "NewName"

    # 发送 PUT 请求进行更新
    response = client.put(
        f"/rest/a2a-t/v1/update_agent/{valid_agent_data['name']}",
        params={"organization": valid_agent_data['provider']['organization']},
        json=modified_data
    )

    # 验证响应
    assert response.status_code == 400
    assert "Cannot change primary key" in response.json()["detail"]