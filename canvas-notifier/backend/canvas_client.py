"""Thin client for the parts of the Canvas LMS REST API we need:
listing a student's active courses and each course's assignments
(graded quizzes/exams come back from the assignments endpoint too).
"""

import httpx


class CanvasError(Exception):
    pass


def _headers(token):
    return {"Authorization": f"Bearer {token}"}


def get_active_courses(canvas_url, token, client=None):
    close = client is None
    client = client or httpx.Client(timeout=15)
    try:
        resp = client.get(
            f"{canvas_url}/api/v1/courses",
            headers=_headers(token),
            params={"enrollment_state": "active", "per_page": 100},
        )
        resp.raise_for_status()
        return resp.json()
    except httpx.HTTPError as exc:
        raise CanvasError(f"Failed to fetch courses: {exc}") from exc
    finally:
        if close:
            client.close()


def get_course_assignments(canvas_url, token, course_id, client=None):
    close = client is None
    client = client or httpx.Client(timeout=15)
    try:
        resp = client.get(
            f"{canvas_url}/api/v1/courses/{course_id}/assignments",
            headers=_headers(token),
            params={"per_page": 100, "order_by": "due_at"},
        )
        resp.raise_for_status()
        return resp.json()
    except httpx.HTTPError as exc:
        raise CanvasError(
            f"Failed to fetch assignments for course {course_id}: {exc}"
        ) from exc
    finally:
        if close:
            client.close()


def classify_assignment(assignment):
    """Best-effort split between "test-like" items (quizzes/exams) and
    regular assignments, since Canvas returns both from the same endpoint.
    """
    submission_types = assignment.get("submission_types") or []
    name = (assignment.get("name") or "").lower()
    if "online_quiz" in submission_types or assignment.get("is_quiz_assignment"):
        return "test"
    if any(word in name for word in ("exam", "test", "quiz", "midterm", "final")):
        return "test"
    return "assignment"


def get_upcoming_items(canvas_url, token, client=None):
    """Return every future, dated assignment/test across the student's
    active courses, sorted by due date.
    """
    close = client is None
    client = client or httpx.Client(timeout=15)
    try:
        items = []
        courses = get_active_courses(canvas_url, token, client=client)
        for course in courses:
            course_id = course.get("id")
            if course_id is None:
                continue
            course_name = course.get("name") or course.get("course_code") or f"Course {course_id}"
            try:
                course_assignments = get_course_assignments(
                    canvas_url, token, course_id, client=client
                )
            except CanvasError:
                # Skip courses we can't read (e.g. concluded/restricted) rather
                # than failing the whole sync.
                continue
            for a in course_assignments:
                due_at = a.get("due_at")
                if not due_at:
                    continue
                items.append(
                    {
                        "id": f"assignment-{a.get('id')}",
                        "course": course_name,
                        "name": a.get("name"),
                        "due_at": due_at,
                        "type": classify_assignment(a),
                        "html_url": a.get("html_url"),
                    }
                )
        items.sort(key=lambda item: item["due_at"])
        return items
    finally:
        if close:
            client.close()
