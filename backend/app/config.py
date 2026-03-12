import hashlib
from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


ROOT_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT_DIR / "data"
DEFAULT_AVATAR_DIR = DATA_DIR / "avatars"
DEFAULT_STYLE_DIR = DATA_DIR / "styles"
DEFAULT_AVATAR_STYLE_DIR = DATA_DIR / "avatar_styles"
DEFAULT_WORKFLOW_TEMPLATE = DATA_DIR / "workflows" / "avatar_v1.template.json"
DEFAULT_RUNTIME_DIR = ROOT_DIR / "runtime"
DEFAULT_STORAGE_DIR = DEFAULT_RUNTIME_DIR / "storage"
DEFAULT_DB_PATH = DEFAULT_RUNTIME_DIR / "avatar_ai.db"
DEFAULT_JOB_DB_PATH = DEFAULT_RUNTIME_DIR / "avatar_jobs.db"
DEFAULT_CHAT_SESSION_DIR = DEFAULT_RUNTIME_DIR / "chat_sessions"
DEFAULT_FRONTEND_DIR = ROOT_DIR / "frontend"
DEFAULT_FRONTEND_PUBLIC_DIR = DEFAULT_FRONTEND_DIR / "public"
DEFAULT_FRONTEND_DIST_DIR = DEFAULT_FRONTEND_DIR / "dist"
DEFAULT_BOT_TEMP_DIR = DEFAULT_RUNTIME_DIR / "bot_uploads"


class Settings(BaseSettings):
    app_name: str = "avatar_ai"
    app_env: str = "local"
    app_host: str = "127.0.0.1"
    app_port: int = 8000
    frontend_base_url: str = "http://127.0.0.1:5173"
    cors_allowed_origins: str = ""
    frontend_public_dir: Path = DEFAULT_FRONTEND_PUBLIC_DIR
    frontend_dist_dir: Path = DEFAULT_FRONTEND_DIST_DIR
    backend_base_url: str = "http://127.0.0.1:8000"
    render_external_url: str | None = None

    avatar_dir: Path = DEFAULT_AVATAR_DIR
    avatar_style_dir: Path = DEFAULT_AVATAR_STYLE_DIR
    llm_base_url: str = "http://127.0.0.1:11434/v1"
    llm_api_key: str = "ollama"
    llm_model: str = "llama3.2:latest"
    llm_timeout_seconds: int = 90

    database_url: str = f"sqlite:///{DEFAULT_DB_PATH.as_posix()}"
    job_db_path: Path = DEFAULT_JOB_DB_PATH
    chat_session_dir: Path = DEFAULT_CHAT_SESSION_DIR
    style_dir: Path = DEFAULT_STYLE_DIR
    runtime_dir: Path = DEFAULT_RUNTIME_DIR
    upload_dir: Path = DEFAULT_RUNTIME_DIR / "uploads"
    generated_dir: Path = DEFAULT_RUNTIME_DIR / "generated"
    max_upload_bytes: int = 10_000_000
    max_upload_size_mb: int = 10
    poll_interval_seconds: int = 3
    output_count: int = 4
    output_width: int = 1024
    output_height: int = 1024
    image_default_variations: int = 4
    queue_max_concurrent_jobs: int = 1
    queue_max_pending_total: int = 20
    queue_max_pending_per_user: int = 2
    queue_estimated_seconds_per_job: int = 90

    storage_backend: str = "local"
    storage_root: Path = DEFAULT_STORAGE_DIR
    s3_endpoint_url: str | None = None
    s3_bucket_name: str | None = None
    s3_region_name: str | None = None
    s3_access_key_id: str | None = None
    s3_secret_access_key: str | None = None

    generation_backend: str = "mock"
    image_provider: str = "mock"
    image_generation_timeout_seconds: int = 180
    remote_image_generate_path: str = "/api/v1/avatar-renders"
    comfyui_base_url: str | None = None
    comfyui_client_id: str = "avatar-ai-worker"
    comfyui_workflow_template: Path = DEFAULT_WORKFLOW_TEMPLATE
    comfyui_poll_seconds: int = 3
    worker_poll_seconds: int = 3

    telegram_bot_token: str | None = None
    telegram_webapp_url: str | None = None
    telegram_webhook_secret: str | None = None
    telegram_webhook_path: str = '/api/telegram/webhook'
    telegram_init_data_ttl_seconds: int = 86_400
    telegram_bot_polling_enabled: bool = False
    bot_temp_dir: Path = DEFAULT_BOT_TEMP_DIR

    github_api_url: str = "https://api.github.com"
    github_token: str | None = None
    github_default_owner: str | None = None

    notion_api_url: str = "https://api.notion.com/v1"
    notion_version: str = "2022-06-28"
    notion_token: str | None = None
    notion_parent_page_id: str | None = None

    search_provider: str = "none"
    search_api_url: str | None = None
    search_api_key: str | None = None
    browser_api_url: str | None = None
    browser_api_key: str | None = None

    gpu_api_base_url: str | None = None
    gpu_api_key: str | None = None
    gpu_health_path: str = "/health"
    gpu_ssh_host: str | None = None
    gpu_ssh_user: str | None = None
    gpu_ssh_port: int = 22

    log_level: str = "INFO"
    sentry_dsn: str | None = None

    model_config = SettingsConfigDict(
        env_file=str(ROOT_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    def _normalize_public_url(self, value: str | None) -> str | None:
        if value is None:
            return None
        candidate = value.strip().rstrip("/")
        if not candidate:
            return None
        if "://" not in candidate:
            candidate = f"https://{candidate}"
        return candidate

    @property
    def public_frontend_base_url(self) -> str:
        explicit_frontend = self._normalize_public_url(self.frontend_base_url)
        render_url = self._normalize_public_url(self.render_external_url)
        if explicit_frontend and explicit_frontend not in {"http://127.0.0.1:5173", "http://localhost:5173"}:
            return explicit_frontend
        return render_url or explicit_frontend or "http://127.0.0.1:5173"

    @property
    def public_backend_base_url(self) -> str:
        explicit_backend = self._normalize_public_url(self.backend_base_url)
        render_url = self._normalize_public_url(self.render_external_url)
        if explicit_backend and explicit_backend not in {"http://127.0.0.1:8000", "http://localhost:8000"}:
            return explicit_backend
        return render_url or explicit_backend or "http://127.0.0.1:8000"

    @property
    def public_telegram_webapp_url(self) -> str:
        explicit_webapp = self._normalize_public_url(self.telegram_webapp_url)
        if explicit_webapp:
            return explicit_webapp
        render_url = self._normalize_public_url(self.render_external_url)
        if render_url:
            return f"{render_url}/studio"
        return self.public_frontend_base_url

    @property
    def telegram_webhook_enabled(self) -> bool:
        if self.telegram_bot_polling_enabled or not self.telegram_bot_token:
            return False
        return self.public_backend_base_url.startswith('https://')

    @property
    def telegram_webhook_secret_value(self) -> str | None:
        explicit_secret = (self.telegram_webhook_secret or '').strip()
        if explicit_secret:
            return explicit_secret
        if not self.telegram_bot_token:
            return None
        return hashlib.sha256(self.telegram_bot_token.encode('utf-8')).hexdigest()

    @property
    def telegram_webhook_url(self) -> str | None:
        if not self.telegram_webhook_enabled:
            return None
        return f"{self.public_backend_base_url}{self.telegram_webhook_path}"

    def allowed_cors_origins(self) -> list[str]:
        defaults = {
            self.public_frontend_base_url.rstrip("/"),
            self.public_backend_base_url.rstrip("/"),
            "http://127.0.0.1:3000",
            "http://localhost:3000",
            "http://127.0.0.1:4173",
            "http://localhost:4173",
            "http://127.0.0.1:5173",
            "http://localhost:5173",
        }
        extra = {
            origin.strip().rstrip("/")
            for origin in self.cors_allowed_origins.split(",")
            if origin.strip()
        }
        return sorted(defaults | extra)

    def ensure_runtime_directories(self) -> None:
        self.avatar_dir.mkdir(parents=True, exist_ok=True)
        self.avatar_style_dir.mkdir(parents=True, exist_ok=True)
        self.style_dir.mkdir(parents=True, exist_ok=True)
        self.runtime_dir.mkdir(parents=True, exist_ok=True)
        self.storage_root.mkdir(parents=True, exist_ok=True)
        self.upload_dir.mkdir(parents=True, exist_ok=True)
        self.generated_dir.mkdir(parents=True, exist_ok=True)
        self.bot_temp_dir.mkdir(parents=True, exist_ok=True)
        self.chat_session_dir.mkdir(parents=True, exist_ok=True)
        self.frontend_public_dir.mkdir(parents=True, exist_ok=True)
        self.comfyui_workflow_template.parent.mkdir(parents=True, exist_ok=True)
        self.job_db_path.parent.mkdir(parents=True, exist_ok=True)


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    settings.ensure_runtime_directories()
    return settings
