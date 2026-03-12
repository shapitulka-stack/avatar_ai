from io import BytesIO
import logging
from pathlib import Path

from fastapi import BackgroundTasks, Depends, FastAPI, File, Form, HTTPException, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
from sqlmodel import Session
from starlette.datastructures import Headers

from app.avatar_store import AvatarNotFoundError, list_avatars, load_avatar
from app.chat_session_store import (
    ChatSessionNotFoundError,
    append_message,
    get_or_create_chat_session,
    load_chat_session,
    refresh_memory,
    save_chat_session,
)
from app.config import Settings, get_settings
from app.db import create_db_and_tables, get_session
from app.face_profiles import (
    FaceProfileValidationError,
    build_face_profile_response,
    create_face_profile,
    get_face_profile_or_404,
    list_face_profiles,
)
from app.integrations.github_client import GitHubService
from app.integrations.notion_client import NotionService
from app.integrations.research_client import ResearchToolingService
from app.integrations.server_client import ServerService
from app.jobs import (
    JobValidationError,
    create_job,
    get_job_or_404,
    list_jobs_for_identity,
    serialize_job,
    serialize_job_results,
)
from app.llm_client import generate_reply
from app.models import (
    AvatarProfile,
    ChatRequest,
    ChatResponse,
    ChatSessionSnapshot,
    FaceProfileListResponse,
    FaceProfileResponse,
    JobCreateResponse,
    JobDetailResponse,
    JobListResponse,
    JobResultsResponse,
    JobSource,
    StyleCard,
)
from app.storage import StorageError, get_storage
from app.style_store import StyleNotFoundError, get_style, public_styles
from app.telegram_bot import build_application as build_telegram_application, start_polling_application, stop_polling_application
from app.telegram_client import TelegramAuthError, TelegramBotService
from app.telemetry import monitoring_status, setup_logging
from app.worker import process_next_job


settings = get_settings()
setup_logging(settings.log_level)
logger = logging.getLogger("avatar_ai.main")
STYLE_PREVIEW_DIR = settings.frontend_public_dir / "style-previews"
FRONTEND_ASSET_DIR = settings.frontend_dist_dir / "assets"

app = FastAPI(
    title="avatar_ai",
    description="Local-first avatar AI backend",
    version="0.6.0",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_cors_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
create_db_and_tables()

if STYLE_PREVIEW_DIR.exists():
    app.mount("/style-previews", StaticFiles(directory=str(STYLE_PREVIEW_DIR)), name="style-previews")
if FRONTEND_ASSET_DIR.exists():
    app.mount("/assets", StaticFiles(directory=str(FRONTEND_ASSET_DIR)), name="frontend-assets")


@app.on_event("startup")
async def startup() -> None:
    create_db_and_tables()
    app.state.telegram_application = None
    if settings.telegram_bot_polling_enabled and settings.telegram_bot_token:
        try:
            telegram_application = build_telegram_application(settings)
            await start_polling_application(telegram_application)
            app.state.telegram_application = telegram_application
        except Exception:  # noqa: BLE001
            logger.exception("Telegram polling failed to start")


@app.on_event("shutdown")
async def shutdown() -> None:
    telegram_application = getattr(app.state, "telegram_application", None)
    if telegram_application is None:
        return
    try:
        await stop_polling_application(telegram_application)
    except Exception:  # noqa: BLE001
        logger.exception("Telegram polling failed to stop cleanly")


def resolve_request_identity(
    settings: Settings,
    guest_session_id: str | None,
    telegram_init_data: str | None,
) -> tuple[str | None, int | None]:
    if telegram_init_data:
        try:
            identity = TelegramBotService(settings).validate_init_data(telegram_init_data)
        except TelegramAuthError as exc:
            raise HTTPException(status_code=401, detail=str(exc)) from exc
        return guest_session_id, identity.user_id
    return guest_session_id, None


@app.get("/")
def read_root() -> dict[str, str]:
    return {
        "name": "avatar_ai",
        "status": "ok",
        "docs": "/docs",
        "studio": "/studio",
        "integrations": "/api/integrations/status",
    }


@app.get("/studio", include_in_schema=False)
def studio(settings: Settings = Depends(get_settings)):
    index_path = settings.frontend_dist_dir / "index.html"
    if index_path.exists():
        return FileResponse(index_path)
    return RedirectResponse(settings.public_frontend_base_url)


@app.get("/health")
def health(settings: Settings = Depends(get_settings)) -> dict[str, str]:
    return {
        "status": "ok",
        "environment": settings.app_env,
        "model": settings.llm_model,
        "generation_backend": settings.generation_backend,
    }


@app.get("/api/avatars")
def get_avatars(settings: Settings = Depends(get_settings)) -> list[dict[str, str]]:
    avatars = list_avatars(settings.avatar_dir)
    return [
        {
            "id": avatar.id,
            "name": avatar.name,
            "role": avatar.role,
            "tone": avatar.tone,
            "summary": avatar.summary,
        }
        for avatar in avatars
    ]


@app.get("/api/avatars/{avatar_id}", response_model=AvatarProfile)
def get_avatar(avatar_id: str, settings: Settings = Depends(get_settings)) -> AvatarProfile:
    try:
        return load_avatar(settings.avatar_dir, avatar_id)
    except AvatarNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.get("/api/chat/sessions/{avatar_id}/{session_id}", response_model=ChatSessionSnapshot)
def get_chat_session(
    avatar_id: str,
    session_id: str,
    settings: Settings = Depends(get_settings),
) -> ChatSessionSnapshot:
    try:
        avatar = load_avatar(settings.avatar_dir, avatar_id)
        session_snapshot = load_chat_session(settings.chat_session_dir, avatar_id, session_id)
    except AvatarNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ChatSessionNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    session_snapshot.avatar_name = avatar.name
    save_chat_session(settings.chat_session_dir, session_snapshot)
    return session_snapshot


@app.get("/api/styles", response_model=list[StyleCard])
def get_styles(settings: Settings = Depends(get_settings)) -> list[StyleCard]:
    return public_styles(settings.style_dir)


@app.get("/api/templates", response_model=list[StyleCard])
def get_templates(settings: Settings = Depends(get_settings)) -> list[StyleCard]:
    return public_styles(settings.style_dir)


@app.get("/api/me/face-profiles", response_model=FaceProfileListResponse)
def get_face_profiles(
    guest_session_id: str | None = Query(default=None),
    telegram_init_data: str | None = Query(default=None),
    session: Session = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> FaceProfileListResponse:
    guest_session_id, telegram_user_id = resolve_request_identity(settings, guest_session_id, telegram_init_data)
    profiles = list_face_profiles(session, guest_session_id, telegram_user_id)
    return FaceProfileListResponse(items=[build_face_profile_response(profile) for profile in profiles])


@app.post("/api/me/face-profiles", response_model=FaceProfileResponse)
async def create_face_profile_endpoint(
    photo: UploadFile = File(...),
    label: str = Form(default="My face"),
    guest_session_id: str | None = Form(default=None),
    telegram_init_data: str | None = Form(default=None),
    session: Session = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> FaceProfileResponse:
    guest_session_id, telegram_user_id = resolve_request_identity(settings, guest_session_id, telegram_init_data)
    content = await photo.read()
    try:
        profile = create_face_profile(session, settings, photo, content, label, guest_session_id, telegram_user_id)
    except FaceProfileValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return build_face_profile_response(profile)


@app.post("/api/jobs", response_model=JobCreateResponse)
async def create_generation_job(
    background_tasks: BackgroundTasks,
    photo: UploadFile | None = File(default=None),
    face_profile_id: str | None = Form(default=None),
    style_id: str = Form(...),
    source: JobSource = Form(default=JobSource.web),
    guest_session_id: str | None = Form(default=None),
    telegram_init_data: str | None = Form(default=None),
    session: Session = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> JobCreateResponse:
    guest_session_id, telegram_user_id = resolve_request_identity(settings, guest_session_id, telegram_init_data)

    if source == JobSource.telegram_webapp and telegram_user_id is None:
        raise HTTPException(status_code=400, detail="Telegram jobs require validated Telegram init data.")

    try:
        style = get_style(settings.style_dir, style_id)
    except StyleNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    if not style.enabled:
        raise HTTPException(status_code=400, detail=f"Style '{style_id}' is disabled.")

    effective_photo = photo
    if effective_photo is not None:
        content = await effective_photo.read()
    elif face_profile_id:
        profile = get_face_profile_or_404(session, face_profile_id, guest_session_id, telegram_user_id)
        try:
            asset = get_storage(settings).download(profile.image_key)
        except StorageError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        content = asset.content
        effective_photo = UploadFile(
            file=BytesIO(content),
            filename=Path(profile.image_key).name,
            headers=Headers({"content-type": asset.content_type or "image/png"}),
        )
    else:
        raise HTTPException(status_code=400, detail="Provide either a face photo or a saved face_profile_id.")

    try:
        job = create_job(
            session=session,
            settings=settings,
            photo=effective_photo,
            content=content,
            source=source,
            style=style,
            guest_session_id=guest_session_id,
            telegram_user_id=telegram_user_id,
        )
    except JobValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    background_tasks.add_task(process_next_job)
    return job


@app.get("/api/jobs/{job_id}", response_model=JobDetailResponse)
def get_job(
    job_id: str,
    session: Session = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> JobDetailResponse:
    return serialize_job(session, settings, get_job_or_404(session, job_id))


@app.get("/api/jobs/{job_id}/results", response_model=JobResultsResponse)
def get_job_results(
    job_id: str,
    session: Session = Depends(get_session),
) -> JobResultsResponse:
    return serialize_job_results(session, get_job_or_404(session, job_id))


@app.get("/api/me/jobs", response_model=JobListResponse)
def get_my_jobs(
    guest_session_id: str | None = Query(default=None),
    telegram_init_data: str | None = Query(default=None),
    session: Session = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> JobListResponse:
    guest_session_id, telegram_user_id = resolve_request_identity(settings, guest_session_id, telegram_init_data)
    return JobListResponse(
        items=list_jobs_for_identity(
            session=session,
            settings=settings,
            guest_session_id=guest_session_id,
            telegram_user_id=telegram_user_id,
        )
    )


@app.get("/api/files/{key:path}")
def get_file(
    key: str,
    settings: Settings = Depends(get_settings),
) -> Response:
    try:
        asset = get_storage(settings).download(key)
    except StorageError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return Response(content=asset.content, media_type=asset.content_type or "application/octet-stream")


@app.post("/api/chat", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    settings: Settings = Depends(get_settings),
) -> ChatResponse:
    try:
        avatar = load_avatar(settings.avatar_dir, request.avatar_id)
    except AvatarNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    session_snapshot: ChatSessionSnapshot | None = None
    conversation_messages = request.messages[-request.history_limit :]

    if request.message:
        session_snapshot = get_or_create_chat_session(settings.chat_session_dir, avatar, request.session_id)
        append_message(session_snapshot, "user", request.message)
        conversation_messages = session_snapshot.messages[-request.history_limit :]

    reply = await generate_reply(
        settings=settings,
        avatar=avatar,
        messages=conversation_messages,
        temperature=request.temperature,
        session_memory=session_snapshot.memory if session_snapshot else None,
    )

    if session_snapshot:
        append_message(session_snapshot, "assistant", reply)
        refresh_memory(session_snapshot, avatar)
        save_chat_session(settings.chat_session_dir, session_snapshot)

    return ChatResponse(
        avatar_id=avatar.id,
        avatar_name=avatar.name,
        reply=reply,
        session_id=session_snapshot.session_id if session_snapshot else request.session_id,
        session=session_snapshot,
    )


@app.get("/api/integrations/status")
async def integration_status(settings: Settings = Depends(get_settings)) -> dict[str, object]:
    github_service = GitHubService(settings)
    notion_service = NotionService(settings)
    research_service = ResearchToolingService(settings)
    server_service = ServerService(settings)

    return {
        "sources": [
            await github_service.status(),
            await notion_service.status(),
            *research_service.status(),
        ],
        "infrastructure": await server_service.status(),
        "monitoring": monitoring_status(settings),
    }


@app.get("/api/research/github/repos")
async def github_repo_search(
    query: str,
    limit: int = 10,
    settings: Settings = Depends(get_settings),
) -> dict[str, object]:
    github_service = GitHubService(settings)
    return {
        "query": query,
        "results": await github_service.search_repositories(query, limit),
    }


@app.get("/api/research/github/code")
async def github_code_search(
    query: str,
    limit: int = 10,
    settings: Settings = Depends(get_settings),
) -> dict[str, object]:
    github_service = GitHubService(settings)
    return {
        "query": query,
        "results": await github_service.search_code(query, limit),
    }


@app.get("/api/research/notion")
async def notion_search(
    query: str,
    limit: int = 10,
    settings: Settings = Depends(get_settings),
) -> dict[str, object]:
    notion_service = NotionService(settings)
    return {
        "query": query,
        "results": await notion_service.search(query, limit),
    }


@app.get("/api/servers/status")
async def server_status(settings: Settings = Depends(get_settings)) -> list[object]:
    server_service = ServerService(settings)
    return await server_service.status()


