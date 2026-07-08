import pytest
from fastapi import APIRouter
from fastapi.testclient import TestClient
from loguru import logger
from starlette_context import context
from app.main import app

# Create a test router (avoiding prefix "test_" so pytest doesn't collect it as a test)
api_test_router = APIRouter()

@api_test_router.get("/read-starlette-context")
def read_starlette_context():
    # Read the Request ID stored in starlette-context by RequestIdPlugin
    req_id = context.get("X-Request-ID")
    logger.info(f"Inside test route, starlette-context request ID is {req_id}")
    return {"request_id": req_id}

# Dynamically mount the test router
app.include_router(api_test_router)

@pytest.fixture
def log_capture():
    """
    Fixture to capture loguru log messages.
    """
    captured_logs = []
    
    # Add a temporary sink to capture formatting and extra dict
    handler_id = logger.add(
        captured_logs.append,
        format="[{extra[X-Request-ID]}] - {message}"
    )
    yield captured_logs
    
    # Remove the sink after the test completes
    logger.remove(handler_id)

def test_starlette_context_auto_generation(client: TestClient, log_capture):
    """
    Test that a request ID is automatically generated, returned in response headers,
    and correctly outputted in log messages.
    """
    response = client.get("/read-starlette-context")
    assert response.status_code == 200
    
    # Verify request ID header is returned by RequestIdPlugin
    assert "X-Request-ID" in response.headers
    req_id = response.headers["X-Request-ID"]
    assert len(req_id) > 0
    
    # Verify the endpoint successfully fetched the context request ID
    assert response.json()["request_id"] == req_id
    
    # Verify that the logs captured the correct request ID
    log_messages = [str(log) for log in log_capture]
    expected_log = f"[{req_id}] - Inside test route, starlette-context request ID is {req_id}"
    assert any(expected_log in msg for msg in log_messages)

def test_starlette_context_propagation(client: TestClient, log_capture):
    """
    Test that a client-supplied request ID is preserved, returned in response headers,
    and outputted in log messages.
    """
    custom_id = "test-custom-correlation-id-999"
    headers = {"X-Request-ID": custom_id}
    
    response = client.get("/read-starlette-context", headers=headers)
    assert response.status_code == 200
    
    # Verify response contains the exact custom ID we sent
    assert response.headers.get("X-Request-ID") == custom_id
    assert response.json()["request_id"] == custom_id
    
    # Verify that the logs captured the custom request ID
    log_messages = [str(log) for log in log_capture]
    expected_log = f"[{custom_id}] - Inside test route, starlette-context request ID is {custom_id}"
    assert any(expected_log in msg for msg in log_messages)
