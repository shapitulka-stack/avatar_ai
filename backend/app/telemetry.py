import logging

from app.config import Settings
from app.integrations.models import IntegrationStatus


def setup_logging(log_level: str) -> None:
    logging.basicConfig(
        level=getattr(logging, log_level.upper(), logging.INFO),
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )


def monitoring_status(settings: Settings) -> list[IntegrationStatus]:
    return [
        IntegrationStatus(
            name="logging",
            configured=True,
            reachable=True,
            detail=f"Application logging is active at {settings.log_level.upper()} level.",
        ),
        IntegrationStatus(
            name="sentry",
            configured=bool(settings.sentry_dsn),
            detail=(
                "Sentry DSN is configured."
                if settings.sentry_dsn
                else "Add SENTRY_DSN to enable error monitoring."
            ),
        ),
    ]
