from fastapi import status
from app.schemas.common import BizCode
from app.core.constants import SESSION_COOKIE_KEY

def test_register_success(client):
    """
    Test registration success flow.
    """
    payload = {
        "email": "test_user@example.com",
        "password": "securepassword123",
        "password_confirmation": "securepassword123"
    }
    response = client.post("/api/v1/auth/register", json=payload)
    
    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    assert data["code"] == BizCode.SUCCESS
    assert data["message"] == "User created successfully"


def test_register_passwords_dont_match(client):
    """
    Test validation error when passwords do not match (triggers Pydantic validator).
    """
    payload = {
        "email": "test_user@example.com",
        "password": "securepassword123",
        "password_confirmation": "differentpassword"
    }
    response = client.post("/api/v1/auth/register", json=payload)
    
    # Pydantic validation fails, FastAPI returns 422 Unprocessable Entity by default
    assert response.status_code == status.HTTP_422_UNPRODUCT_CONTENT if hasattr(status, "HTTP_422_UNPRODUCT_CONTENT") else status.HTTP_422_UNPROCESSABLE_ENTITY
    
    # Assert that the detail error message contains "Passwords do not match"
    errors = response.json().get("detail", [])
    assert any("Passwords do not match" in err.get("msg", "") for err in errors)


def test_register_invalid_email(client):
    """
    Test validation error with an invalid email address.
    """
    payload = {
        "email": "not-an-email",
        "password": "securepassword123",
        "password_confirmation": "securepassword123"
    }
    response = client.post("/api/v1/auth/register", json=payload)
    
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


def test_login_success(client):
    """
    Test successful login flow and verify the sessionid cookie is set.
    """
    # 1. Register a user first
    email = "login_test@example.com"
    password = "securepassword123"
    register_payload = {
        "email": email,
        "password": password,
        "password_confirmation": password
    }
    client.post("/api/v1/auth/register", json=register_payload)

    # 2. Attempt login
    login_payload = {
        "email": email,
        "password": password
    }
    response = client.post("/api/v1/auth/login", json=login_payload)

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["code"] == BizCode.SUCCESS
    
    # 3. Verify cookie is set correctly
    assert SESSION_COOKIE_KEY in response.cookies
    assert response.cookies[SESSION_COOKIE_KEY] != ""


def test_login_invalid_password(client):
    """
    Test login failure due to incorrect password.
    """
    email = "login_fail@example.com"
    register_payload = {
        "email": email,
        "password": "correct_password",
        "password_confirmation": "correct_password"
    }
    client.post("/api/v1/auth/register", json=register_payload)

    # Attempt login with the wrong password
    login_payload = {
        "email": email,
        "password": "wrong_password"
    }
    response = client.post("/api/v1/auth/login", json=login_payload)
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_login_user_not_found(client):
    """
    Test login failure when the user does not exist.
    """
    login_payload = {
        "email": "non_existent@example.com",
        "password": "some_password"
    }
    response = client.post("/api/v1/auth/login", json=login_payload)
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_dummy_auth_flow(client):
    """
    Test dummy auth flow: register, login, then access dummy endpoint.
    """
    email = "dummy_flow@example.com"
    password = "securepassword123"
    
    # 1. Register
    register_payload = {
        "email": email,
        "password": password,
        "password_confirmation": password
    }
    register_resp = client.post("https://testserver/api/v1/auth/register", json=register_payload)
    assert register_resp.status_code == status.HTTP_201_CREATED

    # 2. Login (sets the cookie on the test client)
    login_payload = {
        "email": email,
        "password": password
    }
    login_resp = client.post("https://testserver/api/v1/auth/login", json=login_payload)
    assert login_resp.status_code == status.HTTP_200_OK
    assert SESSION_COOKIE_KEY in login_resp.cookies

    # 3. Call dummy API
    response = client.get("https://testserver/api/v1/auth/dummy")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["code"] == BizCode.SUCCESS
    assert data["message"] == "Auth dummy successfully"


def test_dummy_auth_without_login(client):
    """
    Test accessing dummy API without logging in (should return 401).
    """
    response = client.get("https://testserver/api/v1/auth/dummy")
    assert response.status_code == status.HTTP_401_UNAUTHORIZED




