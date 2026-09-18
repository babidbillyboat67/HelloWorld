import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import httpx

import canvas_client


def _transport(handler):
    return httpx.Client(transport=httpx.MockTransport(handler))


def test_classify_assignment_detects_quiz_by_submission_type():
    assert canvas_client.classify_assignment({"submission_types": ["online_quiz"]}) == "test"


def test_classify_assignment_detects_test_by_name():
    assert canvas_client.classify_assignment({"name": "Midterm Exam", "submission_types": []}) == "test"


def test_classify_assignment_defaults_to_assignment():
    assert canvas_client.classify_assignment({"name": "Homework 3", "submission_types": ["online_upload"]}) == "assignment"


def test_get_upcoming_items_merges_courses_and_skips_undated():
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/api/v1/courses":
            return httpx.Response(200, json=[{"id": 1, "name": "Biology"}])
        if request.url.path == "/api/v1/courses/1/assignments":
            return httpx.Response(
                200,
                json=[
                    {"id": 10, "name": "Lab Report", "due_at": "2030-01-02T00:00:00Z", "submission_types": ["online_upload"]},
                    {"id": 11, "name": "No due date", "due_at": None, "submission_types": []},
                    {"id": 12, "name": "Unit Quiz", "due_at": "2030-01-01T00:00:00Z", "submission_types": ["online_quiz"]},
                ],
            )
        raise AssertionError(f"unexpected request {request.url}")

    with _transport(handler) as client:
        items = canvas_client.get_upcoming_items("https://canvas.example.edu", "token", client=client)

    assert [item["id"] for item in items] == ["assignment-12", "assignment-10"]
    assert items[0]["type"] == "test"
    assert items[1]["type"] == "assignment"
    assert all(item["course"] == "Biology" for item in items)


def test_get_upcoming_items_skips_courses_that_error():
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/api/v1/courses":
            return httpx.Response(200, json=[{"id": 1, "name": "Broken"}, {"id": 2, "name": "OK"}])
        if request.url.path == "/api/v1/courses/1/assignments":
            return httpx.Response(403, json={"error": "forbidden"})
        if request.url.path == "/api/v1/courses/2/assignments":
            return httpx.Response(
                200,
                json=[{"id": 20, "name": "Essay", "due_at": "2030-01-01T00:00:00Z", "submission_types": []}],
            )
        raise AssertionError(f"unexpected request {request.url}")

    with _transport(handler) as client:
        items = canvas_client.get_upcoming_items("https://canvas.example.edu", "token", client=client)

    assert [item["id"] for item in items] == ["assignment-20"]


def test_get_active_courses_raises_canvas_error_on_failure():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(401, json={"error": "unauthorized"})

    with _transport(handler) as client:
        try:
            canvas_client.get_active_courses("https://canvas.example.edu", "bad-token", client=client)
            assert False, "expected CanvasError"
        except canvas_client.CanvasError:
            pass
