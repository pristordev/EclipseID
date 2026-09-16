from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from database.db import get_db
from database import crud
from auth import require_permission, has_permission
from utils.minecraft import get_minecraft_uuid


router = APIRouter(prefix="/api/citizens", tags=["Citizens"])


# ---------- ВАЖНО: lookup-uuid идёт ПЕРВЫМ, до /{citizen_id} ----------

@router.get("/lookup-uuid")
async def lookup_minecraft_uuid(
    username: str = Query(..., description="Никнейм Minecraft"),
    current_user = Depends(require_permission("create_citizen")),
):
    """Получить UUID по никнейму Minecraft через Mojang API"""
    uuid = await get_minecraft_uuid(username)
    if not uuid:
        raise HTTPException(status_code=404, detail="Игрок с таким никнеймом не найден")
    return {
        "status": "success",
        "data": {"username": username, "uuid": uuid}
    }


@router.get("/search")
async def search_citizens(
    query: str = Query(..., description="Поисковый запрос"),
    current_user = Depends(require_permission("search_citizens")),
    db: AsyncSession = Depends(get_db)
):
    citizens = await crud.search_citizens(db, query)
    return {
        "status": "success",
        "count": len(citizens),
        "data": [
            {"id": c.id, "username": c.username, "role_ids": c.role_ids, "reputation": c.reputation}
            for c in citizens
        ]
    }


@router.get("/top/reputation")
async def get_top_reputation(
    limit: int = 10,
    current_user = Depends(require_permission("view_public_info")),
    db: AsyncSession = Depends(get_db)
):
    citizens = await crud.get_top_reputation(db, limit)
    return {
        "status": "success",
        "data": [
            {"id": c.id, "username": c.username, "role_ids": c.role_ids, "reputation": c.reputation}
            for c in citizens
        ]
    }


@router.get("/")
async def get_all_citizens(
    skip: int = 0,
    limit: int = 100,
    current_user = Depends(require_permission("view_all_citizens")),
    db: AsyncSession = Depends(get_db)
):
    citizens = await crud.get_all_citizens(db, skip, limit)
    all_roles = await crud.get_all_roles(db)
    roles_map = {r.id: r.display_name for r in all_roles}

    return {
        "status": "success",
        "count": len(citizens),
        "data": [
            {
                "id": c.id,
                "username": c.username,
                "discord_id": c.discord_id,
                "minecraft_uuid": c.minecraft_uuid,
                "role_ids": c.role_ids,
                "role_display": ", ".join([roles_map.get(rid, f"#{rid}") for rid in (c.role_ids or [])]),
                "main_role_id": c.main_role_id,
                "citizenship_date": c.citizenship_date.isoformat() if c.citizenship_date else None,
                "reputation": c.reputation,
                "is_active": c.is_active
            }
            for c in citizens
        ]
    }


@router.get("/{citizen_id}")
async def get_citizen(
    citizen_id: int,
    current_user = Depends(require_permission("view_citizen_details")),
    db: AsyncSession = Depends(get_db)
):
    citizen = await crud.get_citizen(db, citizen_id)
    if not citizen:
        raise HTTPException(status_code=404, detail="Гражданин не найден")
    return {
        "status": "success",
        "data": {
            "id": citizen.id,
            "username": citizen.username,
            "discord_id": citizen.discord_id,
            "minecraft_uuid": citizen.minecraft_uuid,
            "role_ids": citizen.role_ids,
            "main_role_id": citizen.main_role_id,
            "citizenship_date": citizen.citizenship_date.isoformat() if citizen.citizenship_date else None,
            "reputation": citizen.reputation,
            "is_active": citizen.is_active,
            "last_login": citizen.last_login.isoformat() if citizen.last_login else None
        }
    }


@router.post("/")
async def create_citizen(
    username: str = Query(...),
    discord_id: int = Query(...),
    minecraft_uuid: str = Query(""),
    role_ids: str = Query(""),
    reputation: int = Query(0),
    is_active: bool = Query(True),
    current_user = Depends(require_permission("create_citizen")),
    db: AsyncSession = Depends(get_db)
):
    existing = await crud.get_citizen_by_discord(db, discord_id)
    if existing:
        raise HTTPException(status_code=400, detail="Гражданин с таким Discord ID уже существует")

    ids = []
    if role_ids:
        ids = [int(r.strip()) for r in role_ids.split(",") if r.strip()]

    if not ids:
        citizen_role = await crud.get_role_by_name(db, "citizen")
        if not citizen_role:
            raise HTTPException(status_code=500, detail="Роль 'citizen' не найдена в БД")
        ids = [citizen_role.id]

    for rid in ids:
        role = await crud.get_role_by_id(db, rid)
        if not role:
            raise HTTPException(status_code=400, detail=f"Роль с ID {rid} не найдена")

    data = {
        "username": username,
        "discord_id": discord_id,
        "minecraft_uuid": minecraft_uuid if minecraft_uuid else None,
        "role_ids": ids,
        "main_role_id": ids[0] if ids else None,
        "reputation": reputation,
        "is_active": is_active,
    }
    citizen = await crud.create_citizen(db, data)
    return {
        "status": "success",
        "message": "Гражданин успешно создан",
        "data": {"id": citizen.id, "username": citizen.username, "role_ids": citizen.role_ids}
    }


@router.put("/{citizen_id}")
async def update_citizen(
    citizen_id: int,
    username: str = Query(""),
    minecraft_uuid: str = Query(""),
    role_ids: str = Query(""),
    reputation: int = Query(None),
    is_active: bool = Query(None),
    current_user = Depends(require_permission("update_citizen_basic")),
    db: AsyncSession = Depends(get_db)
):
    data = {}
    if username:
        data["username"] = username
    if minecraft_uuid:
        data["minecraft_uuid"] = minecraft_uuid
    if reputation is not None:
        data["reputation"] = reputation
    if is_active is not None:
        data["is_active"] = is_active

    if role_ids:
        if not await has_permission(db, current_user, "update_citizen_role"):
            raise HTTPException(status_code=403, detail="Недостаточно прав для смены ролей")

        ids = [int(r.strip()) for r in role_ids.split(",") if r.strip()]
        for rid in ids:
            role = await crud.get_role_by_id(db, rid)
            if not role:
                raise HTTPException(status_code=400, detail=f"Роль с ID {rid} не найдена")

        data["role_ids"] = ids
        data["main_role_id"] = ids[0] if ids else None

    citizen = await crud.update_citizen(db, citizen_id, data)
    if not citizen:
        raise HTTPException(status_code=404, detail="Гражданин не найден")
    return {
        "status": "success",
        "message": "Данные обновлены",
        "data": {"id": citizen.id, "username": citizen.username, "role_ids": citizen.role_ids}
    }


@router.delete("/{citizen_id}")
async def delete_citizen(
    citizen_id: int,
    current_user = Depends(require_permission("delete_citizen")),
    db: AsyncSession = Depends(get_db)
):
    success = await crud.delete_citizen(db, citizen_id)
    if not success:
        raise HTTPException(status_code=404, detail="Гражданин не найден")
    return {"status": "success", "message": "Гражданин удален"}


@router.patch("/{citizen_id}/reputation")
async def change_reputation(
    citizen_id: int,
    change: int = Query(...),
    current_user = Depends(require_permission("update_reputation")),
    db: AsyncSession = Depends(get_db)
):
    citizen = await crud.update_reputation(db, citizen_id, change)
    if not citizen:
        raise HTTPException(status_code=404, detail="Гражданин не найден")
    return {
        "status": "success",
        "message": f"Репутация изменена на {change}",
        "data": {"id": citizen.id, "username": citizen.username, "reputation": citizen.reputation}
    }
