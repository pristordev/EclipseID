import time
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession
from database.db import get_db
from database import crud
from utils.avatars import get_avatar_path


router = APIRouter(tags=["System"])


@router.get("/health")
async def health_check():
    """Проверка работоспособности API"""
    return {"status": "ok", "message": "EclipseID API работает"}


@router.get("/api/ping")
async def get_ping(db: AsyncSession = Depends(get_db)):
    """Текущий пинг до сервера (время ответа БД)"""
    start_time = time.perf_counter()
    await crud.get_citizens_count(db)
    ping_ms = round((time.perf_counter() - start_time) * 1000, 2)
    return {"ping": ping_ms}


@router.get("/avatar/{uuid}")
async def get_avatar(uuid: str):
    """
    Отдаёт аватарку из локального кэша.
    Если файла нет — скачивает с crafthead.net и кэширует.
    """
    avatar_path = await get_avatar_path(uuid)

    if not avatar_path:
        raise HTTPException(status_code=404, detail="Аватарка не найдена")

    return FileResponse(
        avatar_path,
        media_type="image/png",
        headers={"Cache-Control": "public, max-age=86400"}
    )
