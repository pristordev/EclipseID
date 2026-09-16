import httpx


async def get_minecraft_uuid(username: str) -> str:
    """Получить UUID по никнейму через Mojang API"""
    async with httpx.AsyncClient(timeout=5.0) as client:
        try:
            response = await client.get(
                f"https://api.mojang.com/users/profiles/minecraft/{username}"
            )
            if response.status_code == 200:
                data = response.json()
                return data.get("id")
        except Exception:
            pass
    return None


async def get_minecraft_username(uuid: str) -> str:
    """Получить никнейм по UUID"""
    clean_uuid = uuid.replace("-", "")
    async with httpx.AsyncClient(timeout=5.0) as client:
        try:
            response = await client.get(
                f"https://sessionserver.mojang.com/session/minecraft/profile/{clean_uuid}"
            )
            if response.status_code == 200:
                data = response.json()
                return data.get("name")
        except Exception:
            pass
    return None
