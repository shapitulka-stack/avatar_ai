import httpx
from fastapi import HTTPException

from app.config import Settings
from app.integrations.models import IntegrationStatus


class GitHubService:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def _headers(self) -> dict[str, str]:
        headers = {"Accept": "application/vnd.github+json"}
        if self.settings.github_token:
            headers["Authorization"] = f"Bearer {self.settings.github_token}"
        return headers

    async def status(self) -> IntegrationStatus:
        if not self.settings.github_token:
            return IntegrationStatus(
                name="github",
                configured=False,
                detail="Add GITHUB_TOKEN to enable GitHub API access.",
            )

        try:
            async with httpx.AsyncClient(timeout=15) as client:
                response = await client.get(
                    f"{self.settings.github_api_url.rstrip('/')}/user",
                    headers=self._headers(),
                )
                response.raise_for_status()
        except httpx.HTTPError as exc:
            return IntegrationStatus(
                name="github",
                configured=True,
                reachable=False,
                detail="GitHub is configured but could not be reached.",
                metadata={"error": str(exc)},
            )

        user = response.json()
        return IntegrationStatus(
            name="github",
            configured=True,
            reachable=True,
            detail="GitHub API is ready.",
            metadata={
                "login": user.get("login", "unknown"),
                "api_url": self.settings.github_api_url,
            },
        )

    async def search_repositories(self, query: str, limit: int = 10) -> list[dict[str, str | int | None]]:
        params = {"q": query, "per_page": max(1, min(limit, 20))}
        try:
            async with httpx.AsyncClient(timeout=20) as client:
                response = await client.get(
                    f"{self.settings.github_api_url.rstrip('/')}/search/repositories",
                    params=params,
                    headers=self._headers(),
                )
                response.raise_for_status()
        except httpx.HTTPError as exc:
            raise HTTPException(status_code=502, detail=f"GitHub search failed: {exc}") from exc

        items = response.json().get("items", [])
        return [
            {
                "name": item.get("name"),
                "full_name": item.get("full_name"),
                "url": item.get("html_url"),
                "description": item.get("description"),
                "stars": item.get("stargazers_count"),
            }
            for item in items
        ]

    async def search_code(self, query: str, limit: int = 10) -> list[dict[str, str | None]]:
        params = {"q": query, "per_page": max(1, min(limit, 20))}
        try:
            async with httpx.AsyncClient(timeout=20) as client:
                response = await client.get(
                    f"{self.settings.github_api_url.rstrip('/')}/search/code",
                    params=params,
                    headers=self._headers(),
                )
                response.raise_for_status()
        except httpx.HTTPError as exc:
            raise HTTPException(status_code=502, detail=f"GitHub code search failed: {exc}") from exc

        items = response.json().get("items", [])
        return [
            {
                "name": item.get("name"),
                "path": item.get("path"),
                "repository": item.get("repository", {}).get("full_name"),
                "url": item.get("html_url"),
            }
            for item in items
        ]
