import sqlite3
from pathlib import Path

from app.image_models import StoredAvatarJob, StoredAvatarJobImage


CREATE_JOBS_TABLE = """
CREATE TABLE IF NOT EXISTS avatar_jobs (
    id TEXT PRIMARY KEY,
    style_id TEXT NOT NULL,
    prompt_override TEXT,
    resolved_prompt TEXT NOT NULL,
    negative_prompt TEXT NOT NULL,
    variations INTEGER NOT NULL,
    status TEXT NOT NULL,
    source_image_path TEXT NOT NULL,
    requester_channel TEXT NOT NULL,
    requester_id TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    error_message TEXT
)
"""

CREATE_IMAGES_TABLE = """
CREATE TABLE IF NOT EXISTS avatar_job_images (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    job_id TEXT NOT NULL,
    file_name TEXT NOT NULL,
    relative_path TEXT NOT NULL,
    created_at TEXT NOT NULL,
    FOREIGN KEY(job_id) REFERENCES avatar_jobs(id) ON DELETE CASCADE
)
"""


class AvatarJobStore:
    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.initialize()

    def initialize(self) -> None:
        with self._connect() as connection:
            connection.execute(CREATE_JOBS_TABLE)
            connection.execute(CREATE_IMAGES_TABLE)
            connection.commit()

    def create_job(self, job: StoredAvatarJob) -> StoredAvatarJob:
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO avatar_jobs (
                    id, style_id, prompt_override, resolved_prompt, negative_prompt,
                    variations, status, source_image_path, requester_channel,
                    requester_id, created_at, updated_at, error_message
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    job.id,
                    job.style_id,
                    job.prompt_override,
                    job.resolved_prompt,
                    job.negative_prompt,
                    job.variations,
                    job.status,
                    job.source_image_path,
                    job.requester_channel,
                    job.requester_id,
                    job.created_at,
                    job.updated_at,
                    job.error_message,
                ),
            )
            connection.commit()
        return job

    def get_job(self, job_id: str) -> StoredAvatarJob | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM avatar_jobs WHERE id = ?",
                (job_id,),
            ).fetchone()
            if row is None:
                return None

            images = self._images_for_job(connection, job_id)
            return self._row_to_job(row, images)

    def list_jobs(self, limit: int = 20) -> list[StoredAvatarJob]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT * FROM avatar_jobs
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()

            jobs: list[StoredAvatarJob] = []
            for row in rows:
                images = self._images_for_job(connection, row["id"])
                jobs.append(self._row_to_job(row, images))
            return jobs

    def update_status(
        self,
        job_id: str,
        status: str,
        updated_at: str,
        error_message: str | None = None,
    ) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                UPDATE avatar_jobs
                SET status = ?, updated_at = ?, error_message = ?
                WHERE id = ?
                """,
                (status, updated_at, error_message, job_id),
            )
            connection.commit()

    def replace_results(
        self,
        job_id: str,
        images: list[StoredAvatarJobImage],
        updated_at: str,
    ) -> None:
        with self._connect() as connection:
            connection.execute("DELETE FROM avatar_job_images WHERE job_id = ?", (job_id,))
            for image in images:
                connection.execute(
                    """
                    INSERT INTO avatar_job_images (job_id, file_name, relative_path, created_at)
                    VALUES (?, ?, ?, ?)
                    """,
                    (job_id, image.file_name, image.relative_path, updated_at),
                )
            connection.execute(
                """
                UPDATE avatar_jobs
                SET updated_at = ?, error_message = NULL
                WHERE id = ?
                """,
                (updated_at, job_id),
            )
            connection.commit()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        return connection

    def _images_for_job(
        self,
        connection: sqlite3.Connection,
        job_id: str,
    ) -> list[StoredAvatarJobImage]:
        rows = connection.execute(
            """
            SELECT file_name, relative_path
            FROM avatar_job_images
            WHERE job_id = ?
            ORDER BY id ASC
            """,
            (job_id,),
        ).fetchall()

        return [
            StoredAvatarJobImage(
                file_name=row["file_name"],
                relative_path=row["relative_path"],
            )
            for row in rows
        ]

    def _row_to_job(
        self,
        row: sqlite3.Row,
        images: list[StoredAvatarJobImage],
    ) -> StoredAvatarJob:
        payload = dict(row)
        payload["images"] = [image.model_dump() for image in images]
        return StoredAvatarJob.model_validate(payload)
