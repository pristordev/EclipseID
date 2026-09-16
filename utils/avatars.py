import os
import httpx
from pathlib import Path

# Путь к папке с аватарками
BASE_DIR = Path(__file__).resolve().parent.parent
AVATARS_DIR = BASE_DIR / "static" / "avatars"
AVATARS_DIR.mkdir(parents=True, exist_ok=True)

CRAFTHEAD_URL = "https://crafthead.net/avatar/{uuid}/128"


def get_avatar_url(uuid: str) -> str:
    """
    Получить URL аватарки (для шаблона).
    Всегда ведёт на наш локальный endpoint /avatar/{uuid}.
    """
    if not uuid:
        return None
    clean_uuid = uuid.replace("-", "").lower()
    return f"/avatar/{clean_uuid}"


async def get_avatar_path(uuid: str) -> Path:
    """
    Получить путь к аватарке. Если её нет — скачать с crafthead.net и кэшировать.
    Возвращает Path или None.
    """
    if not uuid:
        # Заглушка
        default = AVATARS_DIR / "default.png"
        return default if default.exists() else None

    clean_uuid = uuid.replace("-", "").lower()
    avatar_file = AVATARS_DIR / f"{clean_uuid}.png"

    # Если файл уже есть — отдаём его
    if avatar_file.exists() and avatar_file.stat().st_size > 0:
        return avatar_file

    # Иначе — скачиваем
    url = CRAFTHEAD_URL.format(uuid=clean_uuid)

    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(url)
            if response.status_code == 200:
                with open(avatar_file, "wb") as f:
                    f.write(response.content)
                return avatar_file
    except Exception as e:
        print(f"⚠️ Не удалось загрузить аватарку для {uuid}: {e}")

    return None
