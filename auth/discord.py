from authlib.integrations.httpx_client import AsyncOAuth2Client
from fastapi import HTTPException
import os
from dotenv import load_dotenv

load_dotenv()

DISCORD_CLIENT_ID = os.getenv("DISCORD_CLIENT_ID")
DISCORD_CLIENT_SECRET = os.getenv("DISCORD_CLIENT_SECRET")
DISCORD_REDIRECT_URI = os.getenv("DISCORD_REDIRECT_URI")


async def get_discord_oauth_url():
    """Получить URL для редиректа на Discord"""
    oauth = AsyncOAuth2Client(
        client_id=DISCORD_CLIENT_ID,
        client_secret=DISCORD_CLIENT_SECRET,
        redirect_uri=DISCORD_REDIRECT_URI,
        scope="identify"
    )
    url, state = oauth.create_authorization_url(
        "https://discord.com/api/oauth2/authorize"
    )
    return url


async def get_discord_user(code: str):
    """Получить данные пользователя Discord по коду авторизации"""
    oauth = AsyncOAuth2Client(
        client_id=DISCORD_CLIENT_ID,
        client_secret=DISCORD_CLIENT_SECRET,
        redirect_uri=DISCORD_REDIRECT_URI,
        scope="identify"
    )

    try:
        token = await oauth.fetch_token(
            "https://discord.com/api/oauth2/token",
            authorization_response=f"{DISCORD_REDIRECT_URI}?code={code}"
        )

        async with AsyncOAuth2Client(
            client_id=DISCORD_CLIENT_ID,
            client_secret=DISCORD_CLIENT_SECRET,
            token=token
        ) as client:
            resp = await client.get("https://discord.com/api/users/@me")
            return resp.json()
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Ошибка авторизации: {str(e)}")
