"""认证模块测试"""
import pytest
from fastapi.testclient import TestClient
from app import create_app


@pytest.fixture
def client():
    app = create_app()
    return TestClient(app)


def test_login_validation_missing_password(client):
    """密码缺失应返回422"""
    resp = client.post("/api/auth/login", json={"username": "a"})
    assert resp.status_code == 422


def test_me_requires_token(client):
    """未提供token应返回401"""
    resp = client.get("/api/auth/me")
    json_data = resp.json()
    assert json_data["code"] == 401


def test_users_requires_admin(client):
    """未提供token应返回401"""
    resp = client.get("/api/users")
    json_data = resp.json()
    assert json_data["code"] == 401
