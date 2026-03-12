import httpx
from fastapi import HTTPException

from app.config import Settings
from app.integrations.models import IntegrationStatus


class NotionService:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.settings.notion_token}",
            "Notion-Version": self.settings.notion_version,
            "Content-Type": "application/json",
        }

    async def status(self) -> IntegrationStatus:
        if not self.settings.notion_token:
            return IntegrationStatus(
                name="notion",
                configured=False,
                detail="Add NOTION_TOKEN to enable Notion API access.",
            )

        try:
            async with httpx.AsyncClient(timeout=15) as client:
                response = await client.get(
                    f"{self.settings.notion_api_url.rstrip('/')}/users/me",
                    headers=self._headers(),
                )
                response.raise_for_status()
        except httpx.HTTPError as exc:
            return IntegrationStatus(
                name="notion",
                configured=True,
                reachable=False,
                detail="Notion is configured but could not be reached.",
                metadata={"error": str(exc)},
            )

        user = response.json()
        return IntegrationStatus(
            name="notion",
            configured=True,
            reachable=True,
            detail="Notion API is ready.",
            metadata={
                "bot_name": user.get("name", "notion-bot"),
                "api_url": self.settings.notion_api_url,
            },
        )

    async def search(self, query: str, limit: int = 10) -> list[dict[str, str | None]]:
        if not self.settings.notion_token:
            raise HTTPException(status_code=503, detail="NOTION_TOKEN is not configured.")

        payload = {"query": query, "page_size": max(1, min(limit, 20))}
        try:
            async with httpx.AsyncClient(timeout=20) as client:
                response = await client.post(
                    f"{self.settings.notion_api_url.rstrip('/')}/search",
                    headers=self._headers(),
                    json=payload,
                )
                response.raise_for_status()
        except httpx.HTTPError as exc:
            raise HTTPException(status_code=502, detail=f"Notion search failed: {exc}") from exc

        results = []
        for item in response.json().get("results", []):
            results.append(
                {
                    "id": item.get("id"),
                    "object": item.get("object"),
                    "title": _extract_title(item),
                    "url": item.get("url"),
                }
            )
        return results


def _extract_title(item: dict) -> str:
    if item.get("object") == "database":
        title = item.get("title", [])
        return "".join(block.get("plain_text", "") for block in title) or "Untitled database"

    properties = item.get("properties", {})
    for prop in properties.values():
        if prop.get("type") == "title":
            title = prop.get("title", [])
            return "".join(block.get("plain_text", "") for block in title) or "Untitled page"

    return "Untitled"
