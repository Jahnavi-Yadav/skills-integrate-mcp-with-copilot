"""
High School Management System API

A super simple FastAPI application that allows students to view, sign up,
and manage attendance for extracurricular activities at Mergington High School.
"""

import csv
import os
from io import BytesIO, StringIO
from pathlib import Path
from typing import Optional

import openpyxl
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles

app = FastAPI(
    title="Mergington High School API",
    description="API for viewing, signing up, and managing attendance for extracurricular activities",
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

VALID_ROLES = {"participant", "organizer", "volunteer"}

# Migrate legacy participant strings to structured attendance records
for activity in activities.values():
    activity["participants"] = [
        participant
        if isinstance(participant, dict)
        else {"email": participant, "role": "participant"}
        for participant in activity.get("participants", [])
    ]


def get_activity(activity_name: str):
    if activity_name not in activities:
        raise HTTPException(status_code=404, detail="Activity not found")
    return activities[activity_name]


def validate_role(role: str) -> str:
    normalized = role.strip().lower()
    if normalized not in VALID_ROLES:
        raise HTTPException(
            status_code=400,
            detail="Role must be one of participant, organizer, or volunteer",
        )
    return normalized


def find_attendee(activity: dict, email: str) -> Optional[dict]:
    normalized_email = email.strip().lower()
    return next(
        (item for item in activity["participants"] if item["email"].lower() == normalized_email),
        None,
    )


@app.get("/")
def root():
    return RedirectResponse(url="/static/index.html")


@app.get("/activities")
def get_activities():
    return activities


@app.post("/activities/{activity_name}/signup")
def signup_for_activity(activity_name: str, email: str, role: str = "participant"):
    """Sign up a student for an activity"""
    activity = get_activity(activity_name)
    role = validate_role(role)

    if find_attendee(activity, email):
        raise HTTPException(status_code=400, detail="Student is already signed up")

    if len(activity["participants"]) >= activity["max_participants"]:
        raise HTTPException(status_code=400, detail="Activity is already full")

    activity["participants"].append({"email": email.strip().lower(), "role": role})
    return {"message": f"Signed up {email} for {activity_name}"}


@app.post("/activities/{activity_name}/attendance/upload")
async def upload_attendance(activity_name: str, file: UploadFile = File(...)):
    """Upload attendance records for an activity using Excel or CSV."""
    activity = get_activity(activity_name)
    filename = file.filename or "attendance"
    suffix = Path(filename).suffix.lower()
    content = await file.read()

    rows = []
    if suffix in {".xlsx", ".xlsm", ".xltx", ".xltm"}:
        workbook = openpyxl.load_workbook(filename=BytesIO(content), read_only=True, data_only=True)
        sheet = workbook.active
        rows = [tuple(cell for cell in row) for row in sheet.iter_rows(values_only=True)]
    elif suffix == ".csv":
        rows = list(csv.reader(StringIO(content.decode("utf-8"))))
    else:
        raise HTTPException(status_code=415, detail="Only CSV or Excel uploads are supported")

    if not rows:
        raise HTTPException(status_code=400, detail="Uploaded file is empty")

    header = [str(value).strip().lower() if value is not None else "" for value in rows[0]]
    email_index = 0
    role_index = 1
    if "email" in header:
        email_index = header.index("email")
    if "role" in header:
        role_index = header.index("role")

    added = 0
    skipped = 0
    for values in rows[1:]:
        if not values or len(values) <= email_index:
            continue
        email = str(values[email_index]).strip().lower()
        if not email:
            continue

        role = "participant"
        if len(values) > role_index and values[role_index] is not None:
            role = str(values[role_index]).strip().lower()

        try:
            role = validate_role(role)
        except HTTPException:
            role = "participant"

        if find_attendee(activity, email):
            skipped += 1
            continue

        if len(activity["participants"]) >= activity["max_participants"]:
            skipped += 1
            continue

        activity["participants"].append({"email": email, "role": role})
        added += 1

    return {
        "message": f"Uploaded attendance for {activity_name}",
        "added": added,
        "skipped": skipped,
    }


@app.put("/activities/{activity_name}/attendance/{email}")
def update_attendance_role(activity_name: str, email: str, role: str = Form(...)):
    """Update a registered student's attendance role."""
    activity = get_activity(activity_name)
    attendee = find_attendee(activity, email)
    if attendee is None:
        raise HTTPException(status_code=404, detail="Attendee not found")

    attendee["role"] = validate_role(role)
    return {"message": f"Updated {email} role to {attendee['role']}"}


@app.delete("/activities/{activity_name}/attendance/{email}")
def remove_attendance(activity_name: str, email: str):
    """Remove a student from an activity attendance list."""
    activity = get_activity(activity_name)
    attendee = find_attendee(activity, email)
    if attendee is None:
        raise HTTPException(status_code=404, detail="Attendee not found")

    activity["participants"].remove(attendee)
    return {"message": f"Removed {email} from {activity_name}"}


@app.delete("/activities/{activity_name}/unregister")
def unregister_from_activity(activity_name: str, email: str):
    """Unregister a student from an activity"""
    return remove_attendance(activity_name, email)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app:app", host="127.0.0.1", port=8000, reload=True)
