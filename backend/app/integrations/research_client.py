from app.config import Settings
from app.integrations.models import IntegrationStatus


class ResearchToolingService:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def status(self) -> list[IntegrationStatus]:
        search_configured = bool(self.settings.search_api_url and self.settings.search_api_key)
        browser_configured = bool(self.settings.browser_api_url and self.settings.browser_api_key)

        return [
            IntegrationStatus(
                name="search_provider",
                configured=search_configured,
                detail=(
                    f"Search provider '{self.settings.search_provider}' is ready."
                    if search_configured
                    else "Add SEARCH_API_URL and SEARCH_API_KEY to enable web research."
                ),
                metadata={"provider": self.settings.search_provider},
            ),
            IntegrationStatus(
                name="browser_tool",
                configured=browser_configured,
                detail=(
                    "Remote browser tooling is configured."
                    if browser_configured
                    else "Add BROWSER_API_URL and BROWSER_API_KEY to enable browser automation."
                ),
            ),
        ]
