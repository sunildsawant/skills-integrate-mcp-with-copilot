"""
High School Management System API

A super simple FastAPI application that allows students to view and sign up
for extracurricular activities at Mergington High School.
"""

import json
import os
import secrets
from pathlib import Path
from typing import Any

from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.responses import RedirectResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel


class LoginRequest(BaseModel):
    email: str
    password: str


USERS_FILE = Path(
    os.environ.get(
        "USERS_FILE",
        str(Path(__file__).resolve().parents[1] / "data" / "users.json"),
    )
)

security = HTTPBearer(auto_error=False)

ACTIVE_TOKENS: dict[str, dict[str, Any]] = {}


def load_default_users() -> dict[str, dict[str, Any]]:
    return {
        "student@mergington.edu": {
            "email": "student@mergington.edu",
            "password": "student123",
            "role": "student",
            "name": "Student User",
        },
        "organizer@mergington.edu": {
            "email": "organizer@mergington.edu",
            "password": "organizer123",
            "role": "organizer",
            "name": "Club Organizer",
        },
        "admin@mergington.edu": {
            "email": "admin@mergington.edu",
            "password": "admin123",
            "role": "admin",
            "name": "School Admin",
        },
    }


def ensure_users_file() -> Path:
    USERS_FILE.parent.mkdir(parents=True, exist_ok=True)
    if not USERS_FILE.exists():
        USERS_FILE.write_text(json.dumps(load_default_users(), indent=2))
    return USERS_FILE


def load_users() -> dict[str, dict[str, Any]]:
    ensure_users_file()
    try:
        return json.loads(USERS_FILE.read_text())
    except json.JSONDecodeError as exc:
        raise HTTPException(
            status_code=500,
            detail="User data file is invalid JSON.",
        ) from exc


def save_users(users: dict[str, dict[str, Any]]) -> None:
    ensure_users_file()
    USERS_FILE.write_text(json.dumps(users, indent=2))


def sanitize_user(user: dict[str, Any]) -> dict[str, Any]:
    return {
        "email": user["email"],
        "role": user["role"],
        "name": user.get("name", user["email"]),
    }


def authenticate_user(email: str, password: str) -> dict[str, Any]:
    users = load_users()
    user = users.get(email.lower())
    if not user or user.get("password") != password:
        raise HTTPException(status_code=401, detail="Invalid email or password")
    return sanitize_user(user)


def create_session(user: dict[str, Any]) -> dict[str, Any]:
    token = secrets.token_urlsafe(32)
    ACTIVE_TOKENS[token] = user
    return {"token": token, **user}


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
) -> dict[str, Any]:
    if credentials is None or not credentials.credentials:
        raise HTTPException(
            status_code=401,
            detail="Authentication required",
        )

    user = ACTIVE_TOKENS.get(credentials.credentials)
    if user is None:
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired session",
        )
    return user


def require_roles(*allowed_roles: str):
    def dependency(current_user: dict[str, Any] = Depends(get_current_user)) -> dict[str, Any]:
        if current_user["role"] not in allowed_roles:
            raise HTTPException(
                status_code=403,
                detail="You do not have permission to perform this action.",
            )
        return current_user

    return dependency


app = FastAPI(
    title="Mergington High School API",
    description="API for viewing and signing up for extracurricular activities",
)

# Mount the static files directory
current_dir = Path(__file__).parent
app.mount(
    "/static",
    StaticFiles(directory=os.path.join(Path(__file__).parent, "static")),
    name="static",
)

# In-memory activity database
activities = {
    "Chess Club": {
        "description": "Learn strategies and compete in chess tournaments",
        "schedule": "Fridays, 3:30 PM - 5:00 PM",
        "max_participants": 12,
        "participants": ["michael@mergington.edu", "daniel@mergington.edu"],
    },
    "Programming Class": {
        "description": "Learn programming fundamentals and build software projects",
        "schedule": "Tuesdays and Thursdays, 3:30 PM - 4:30 PM",
        "max_participants": 20,
        "participants": ["emma@mergington.edu", "sophia@mergington.edu"],
    },
    "Gym Class": {
        "description": "Physical education and sports activities",
        "schedule": "Mondays, Wednesdays, Fridays, 2:00 PM - 3:00 PM",
        "max_participants": 30,
        "participants": ["john@mergington.edu", "olivia@mergington.edu"],
    },
    "Soccer Team": {
        "description": "Join the school soccer team and compete in matches",
        "schedule": "Tuesdays and Thursdays, 4:00 PM - 5:30 PM",
        "max_participants": 22,
        "participants": ["liam@mergington.edu", "noah@mergington.edu"],
    },
    "Basketball Team": {
        "description": "Practice and play basketball with the school team",
        "schedule": "Wednesdays and Fridays, 3:30 PM - 5:00 PM",
        "max_participants": 15,
        "participants": ["ava@mergington.edu", "mia@mergington.edu"],
    },
    "Art Club": {
        "description": "Explore your creativity through painting and drawing",
        "schedule": "Thursdays, 3:30 PM - 5:00 PM",
        "max_participants": 15,
        "participants": ["amelia@mergington.edu", "harper@mergington.edu"],
    },
    "Drama Club": {
        "description": "Act, direct, and produce plays and performances",
        "schedule": "Mondays and Wednesdays, 4:00 PM - 5:30 PM",
        "max_participants": 20,
        "participants": ["ella@mergington.edu", "scarlett@mergington.edu"],
    },
    "Math Club": {
        "description": "Solve challenging problems and participate in math competitions",
        "schedule": "Tuesdays, 3:30 PM - 4:30 PM",
        "max_participants": 10,
        "participants": ["james@mergington.edu", "benjamin@mergington.edu"],
    },
    "Debate Team": {
        "description": "Develop public speaking and argumentation skills",
        "schedule": "Fridays, 4:00 PM - 5:30 PM",
        "max_participants": 12,
        "participants": ["charlotte@mergington.edu", "henry@mergington.edu"],
    },
}


@app.get("/")
def root():
    return RedirectResponse(url="/static/index.html")


@app.post("/login")
def login(payload: LoginRequest):
    user = authenticate_user(payload.email.lower(), payload.password)
    return create_session(user)


@app.get("/me")
def get_me(current_user: dict[str, Any] = Depends(get_current_user)):
    return current_user


@app.get("/admin")
def admin_dashboard(current_user: dict[str, Any] = Depends(require_roles("admin"))):
    return {
        "role": current_user["role"],
        "email": current_user["email"],
        "message": "Admin dashboard access granted",
    }


@app.get("/activities")
def get_activities():
    return activities


@app.post("/activities/{activity_name}/signup")
def signup_for_activity(
    activity_name: str,
    email: str,
    current_user: dict[str, Any] = Depends(require_roles("student", "organizer", "admin")),
):
    """Sign up a student for an activity."""
    if current_user["role"] == "student" and email.lower() != current_user["email"]:
        raise HTTPException(
            status_code=403,
            detail="Students can only sign up themselves.",
        )

    if activity_name not in activities:
        raise HTTPException(status_code=404, detail="Activity not found")

    activity = activities[activity_name]

    if email.lower() in activity["participants"]:
        raise HTTPException(
            status_code=400,
            detail="Student is already signed up",
        )

    activity["participants"].append(email.lower())
    return {"message": f"Signed up {email} for {activity_name}"}


@app.delete("/activities/{activity_name}/unregister")
def unregister_from_activity(
    activity_name: str,
    email: str,
    current_user: dict[str, Any] = Depends(require_roles("organizer", "admin")),
):
    """Unregister a student from an activity."""
    if activity_name not in activities:
        raise HTTPException(status_code=404, detail="Activity not found")

    activity = activities[activity_name]

    normalized_email = email.lower()
    if normalized_email not in activity["participants"]:
        raise HTTPException(
            status_code=400,
            detail="Student is not signed up for this activity",
        )

    activity["participants"].remove(normalized_email)
    return {
        "message": f"Unregistered {normalized_email} from {activity_name}",
        "actor": current_user["email"],
    }
