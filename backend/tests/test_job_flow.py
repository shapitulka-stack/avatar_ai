import asyncio
import importlib
from io import BytesIO
from pathlib import Path

from fastapi.testclient import TestClient
from PIL import Image
from sqlmodel import Session, select
from starlette.datastructures import Headers, UploadFile

from app.config import get_settings
from app.db import create_db_and_tables, get_engine
from app.face_profiles import list_face_profiles
from app.jobs import create_job, serialize_job
from app.models import GenerationJob, GenerationResult, JobSource, JobStatus
from app.style_store import get_style
from app.worker import process_next_job


ROOT_DIR = Path(__file__).resolve().parents[2]


def _make_png_bytes(color: tuple[int, int, int] = (32, 72, 140)) -> bytes:
    image = Image.new("RGB", (768, 768), color=color)
    buffer = BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


def _reset_settings(
    monkeypatch,
    tmp_path: Path,
    *,
    queue_max_pending_total: int = 20,
    queue_max_pending_per_user: int = 2,
    queue_estimated_seconds_per_job: int = 90,
) -> None:
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{(tmp_path / 'avatar_test.db').as_posix()}")
    monkeypatch.setenv("STORAGE_ROOT", str(tmp_path / "storage"))
    monkeypatch.setenv("STYLE_DIR", str(ROOT_DIR / "data" / "styles"))
    monkeypatch.setenv("GENERATION_BACKEND", "mock")
    monkeypatch.setenv("FRONTEND_BASE_URL", "http://127.0.0.1:5173")
    monkeypatch.setenv("QUEUE_MAX_PENDING_TOTAL", str(queue_max_pending_total))
    monkeypatch.setenv("QUEUE_MAX_PENDING_PER_USER", str(queue_max_pending_per_user))
    monkeypatch.setenv("QUEUE_ESTIMATED_SECONDS_PER_JOB", str(queue_estimated_seconds_per_job))
    get_settings.cache_clear()
    get_engine.cache_clear()
    create_db_and_tables()


async def _fake_process_next_job() -> bool:
    return False


def _build_client(monkeypatch, tmp_path: Path, **queue_overrides: int) -> TestClient:
    _reset_settings(monkeypatch, tmp_path, **queue_overrides)
    import app.main as app_main

    app_main = importlib.reload(app_main)
    monkeypatch.setattr(app_main, "process_next_job", _fake_process_next_job)
    return TestClient(app_main.app)


def _job_request_data(guest_session_id: str = "guest-1") -> dict[str, str]:
    return {
        "style_id": "cinematic-pro",
        "source": "web",
        "guest_session_id": guest_session_id,
    }


def _create_job_via_api(client: TestClient, guest_session_id: str = "guest-1", color: tuple[int, int, int] = (32, 72, 140)):
    return client.post(
        "/api/jobs",
        data=_job_request_data(guest_session_id),
        files={"photo": ("portrait.png", _make_png_bytes(color), "image/png")},
    )


def _create_face_profile_via_api(client: TestClient, guest_session_id: str = "guest-1"):
    return client.post(
        "/api/me/face-profiles",
        data={"guest_session_id": guest_session_id, "label": "Main face"},
        files={"photo": ("face.png", _make_png_bytes((55, 90, 150)), "image/png")},
    )


def test_mock_job_flow_succeeds(monkeypatch, tmp_path: Path) -> None:
    _reset_settings(monkeypatch, tmp_path)
    settings = get_settings()
    style = get_style(settings.style_dir, "cinematic-pro")
    content = _make_png_bytes()
    upload = UploadFile(file=BytesIO(content), filename="portrait.png", headers=Headers({"content-type": "image/png"}))

    with Session(get_engine()) as session:
        response = create_job(
            session=session,
            settings=settings,
            photo=upload,
            content=content,
            source=JobSource.web,
            style=style,
            guest_session_id=None,
            telegram_user_id=None,
        )

    assert response.status == JobStatus.queued
    assert response.queue_tier.value == "free"
    assert response.queue_position == 1
    assert response.jobs_ahead == 0
    assert response.estimated_wait_seconds == 0
    assert response.user_pending_jobs == 1
    assert response.max_pending_per_user == 2

    asyncio.run(process_next_job())

    with Session(get_engine()) as session:
        job = session.get(GenerationJob, response.job_id)
        results = list(session.exec(select(GenerationResult).where(GenerationResult.job_id == response.job_id)))
        detail = serialize_job(session, settings, job)

    assert job is not None
    assert job.status == JobStatus.succeeded.value
    assert len(results) == 4
    assert detail.queue_position is None
    assert detail.jobs_ahead == 0
    assert detail.user_pending_jobs == 0


def test_job_api_reports_queue_metadata(monkeypatch, tmp_path: Path) -> None:
    with _build_client(monkeypatch, tmp_path) as client:
        first = _create_job_via_api(client, "debug-user", (40, 70, 130))
        second = _create_job_via_api(client, "debug-user", (70, 50, 120))

        assert first.status_code == 200
        assert second.status_code == 200
        first_body = first.json()
        second_body = second.json()

        assert first_body["queue_position"] == 1
        assert first_body["jobs_ahead"] == 0
        assert first_body["user_pending_jobs"] == 1
        assert second_body["queue_position"] == 2
        assert second_body["jobs_ahead"] == 1
        assert second_body["estimated_wait_seconds"] == 90
        assert second_body["user_pending_jobs"] == 2
        assert second_body["max_pending_per_user"] == 2

        detail = client.get(f"/api/jobs/{second_body['job_id']}")
        assert detail.status_code == 200
        detail_body = detail.json()
        assert detail_body["queue_tier"] == "free"
        assert detail_body["queue_position"] == 2
        assert detail_body["jobs_ahead"] == 1
        assert detail_body["estimated_wait_seconds"] == 90

        history = client.get("/api/me/jobs", params={"guest_session_id": "debug-user"})
        assert history.status_code == 200
        items = history.json()["items"]
        assert len(items) == 2
        current = next(item for item in items if item["job_id"] == second_body["job_id"])
        assert current["queue_position"] == 2
        assert current["user_pending_jobs"] == 2


def test_user_pending_limit_rejects_third_job(monkeypatch, tmp_path: Path) -> None:
    with _build_client(monkeypatch, tmp_path, queue_max_pending_total=10, queue_max_pending_per_user=2) as client:
        assert _create_job_via_api(client, "guest-limit-1").status_code == 200
        assert _create_job_via_api(client, "guest-limit-1", (70, 55, 120)).status_code == 200

        rejected = _create_job_via_api(client, "guest-limit-1", (100, 80, 90))
        assert rejected.status_code == 400
        assert "2 active jobs" in rejected.json()["detail"]


def test_global_queue_limit_rejects_new_job(monkeypatch, tmp_path: Path) -> None:
    with _build_client(monkeypatch, tmp_path, queue_max_pending_total=2, queue_max_pending_per_user=5) as client:
        assert _create_job_via_api(client, "guest-a").status_code == 200
        assert _create_job_via_api(client, "guest-b", (90, 60, 120)).status_code == 200

        rejected = _create_job_via_api(client, "guest-c", (120, 60, 100))
        assert rejected.status_code == 400
        assert "queue is full" in rejected.json()["detail"]


def test_saved_face_profile_can_be_reused_without_new_upload(monkeypatch, tmp_path: Path) -> None:
    with _build_client(monkeypatch, tmp_path) as client:
        profile_response = _create_face_profile_via_api(client, "guest-face")
        assert profile_response.status_code == 200
        profile_id = profile_response.json()["id"]

        job_response = client.post(
            "/api/jobs",
            data={
                "style_id": "cinematic-pro",
                "source": "web",
                "guest_session_id": "guest-face",
                "face_profile_id": profile_id,
            },
        )

        assert job_response.status_code == 200
        body = job_response.json()
        assert body["queue_position"] == 1
        assert body["user_pending_jobs"] == 1

        profiles = client.get("/api/me/face-profiles", params={"guest_session_id": "guest-face"})
        assert profiles.status_code == 200
        assert len(profiles.json()["items"]) == 1


def test_temporary_override_does_not_create_new_face_profile(monkeypatch, tmp_path: Path) -> None:
    _reset_settings(monkeypatch, tmp_path)
    settings = get_settings()

    with _build_client(monkeypatch, tmp_path) as client:
        assert _create_face_profile_via_api(client, "guest-override").status_code == 200
        before = client.get("/api/me/face-profiles", params={"guest_session_id": "guest-override"}).json()["items"]
        assert len(before) == 1

        override_job = _create_job_via_api(client, "guest-override", (150, 90, 70))
        assert override_job.status_code == 200

        after = client.get("/api/me/face-profiles", params={"guest_session_id": "guest-override"}).json()["items"]
        assert len(after) == 1

        with Session(get_engine()) as session:
            profiles = list_face_profiles(session, "guest-override", None)
            assert len(profiles) == 1
            jobs = list(session.exec(select(GenerationJob).where(GenerationJob.guest_session_id == "guest-override")))
            assert len(jobs) == 1
            assert jobs[0].input_image_key.startswith("uploads/")
            assert settings.queue_max_pending_per_user == 2
