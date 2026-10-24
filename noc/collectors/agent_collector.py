from __future__ import annotations

import httpx


async def pull_agent(hostname: str, config: dict) -> dict:
    base = (config.get("pull_url") or f"http://{hostname}:{config.get('port', 9108)}").rstrip("/")
    async with httpx.AsyncClient(timeout=8) as client:
        response = await client.get(f"{base}/metrics", headers={"X-Agent-Token": config["agent_token"]})
        response.raise_for_status()
        return response.json()
