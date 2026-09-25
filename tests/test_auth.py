import importlib
import os
import sys

from fastapi.testclient import TestClient


def make_client(tmp_path):
    users_file = tmp_path / "users.json"
    users_file.write_text(
        """
        {
          "student@mergington.edu": {
            "email": "student@mergington.edu",
            "password": "student123",
            "role": "student",
            "name": "Student User"
          },
          "organizer@mergington.edu": {
            "email": "organizer@mergington.edu",
            "password": "organizer123",
            "role": "organizer",
            "name": "Club Organizer"
          },
          "admin@mergington.edu": {
            "email": "admin@mergington.edu",
            "password": "admin123",
            "role": "admin",
            "name": "School Admin"
          }
        }
        """.strip()
    )
    os.environ["USERS_FILE"] = str(users_file)
    sys.modules.pop("src.app", None)
    app_module = importlib.import_module("src.app")
    return TestClient(app_module.app)


def test_student_login_and_session(tmp_path):
    client = make_client(tmp_path)

    response = client.post(
        "/login",
        json={"email": "student@mergington.edu", "password": "student123"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["role"] == "student"
    assert "token" in payload

    me_response = client.get(
        "/me",
        headers={"Authorization": f"Bearer {payload['token']}"},
    )
    assert me_response.status_code == 200
    assert me_response.json()["email"] == "student@mergington.edu"


def test_student_cannot_unregister_activity(tmp_path):
    client = make_client(tmp_path)
    login = client.post(
        "/login",
        json={"email": "student@mergington.edu", "password": "student123"},
    )
    token = login.json()["token"]

    response = client.delete(
        "/activities/Chess Club/unregister?email=michael@mergington.edu",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 403


def test_organizer_can_unregister_activity(tmp_path):
    client = make_client(tmp_path)
    login = client.post(
        "/login",
        json={"email": "organizer@mergington.edu", "password": "organizer123"},
    )
    token = login.json()["token"]

    response = client.delete(
        "/activities/Chess Club/unregister?email=michael@mergington.edu",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    assert "Unregistered" in response.json()["message"]


def test_admin_can_access_dashboard(tmp_path):
    client = make_client(tmp_path)
    login = client.post(
        "/login",
        json={"email": "admin@mergington.edu", "password": "admin123"},
    )
    token = login.json()["token"]

    response = client.get(
        "/admin",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    assert response.json()["role"] == "admin"
