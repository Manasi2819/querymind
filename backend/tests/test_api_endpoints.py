import pytest
from fastapi.testclient import TestClient
from main import app
from config import get_settings

settings = get_settings()
client = TestClient(app)

def test_health_endpoint():
    response = client.get("/chat/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}

def test_admin_token_flow():
    # Invalid login
    res_err = client.post("/admin/token", data={"username": "wrong", "password": "password"})
    assert res_err.status_code == 401
    
    # Valid login
    res_ok = client.post("/admin/token", data={"username": settings.admin_username, "password": settings.admin_password})
    assert res_ok.status_code == 200
    assert "access_token" in res_ok.json()

def test_chat_generates_response(mocker):
    # Mock LLM and intent evaluation to ensure fast execution without API costs
    mocker.patch('routers.chat.classify_intent', return_value='general')
    mocker.patch('routers.chat.save_turn')
    mocker.patch('routers.chat.get_relevant_history', return_value="")
    
    mock_llm = mocker.MagicMock()
    mock_llm.invoke.return_value.content = "Mocked LLM reply"
    mocker.patch('routers.chat.get_llm', return_value=mock_llm)

    response = client.post("/chat", json={
        "message": "Hello test",
        "session_id": "test_session_123"
    })
    
    assert response.status_code == 200
    data = response.json()
    assert data["answer"] == "Mocked LLM reply"
    assert data["source"] == "general"
    assert data["session_id"] == "test_session_123"
