from fastapi import HTTPException, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from database.db import get_db
from database.models import Role, Permission, role_permissions
from auth.jwt import verify_token


# =============================================
#  БАЗОВЫЕ ФУНКЦИИ
# =============================================

async def get_current_user(request: Request, db: AsyncSession = Depends(get_db)):
    """Получить текущего пользователя из куки"""
    from database import crud

    token = request.cookies.get("access_token")
    discord_id = verify_token(token) if token else None
    if discord_id:
        return await crud.get_citizen_by_discord(db, int(discord_id))
    return None


async def get_user_roles(db: AsyncSession, citizen) -> list:
    """Получить объекты ролей пользователя (с правами)"""
    from database import crud

    role_ids = citizen.role_ids or [1]
    return await crud.get_roles_by_ids(db, role_ids)


async def get_user_permissions(db: AsyncSession, citizen) -> set:
    """Собрать все права пользователя из всех его ролей"""
    roles = await get_user_roles(db, citizen)
    permissions = set()

    for role in roles:
        result = await db.execute(
            select(Permission)
            .join(role_permissions, Permission.id == role_permissions.c.permission_id)
            .where(role_permissions.c.role_id == role.id)
        )
        for perm in result.scalars().all():
            permissions.add(perm.name)

    return permissions


async def has_permission(db: AsyncSession, citizen, permission: str) -> bool:
    """Проверить, есть ли у пользователя право"""
    perms = await get_user_permissions(db, citizen)
    if "full_access" in perms:
        return True
    return permission in perms


async def get_highest_role_level(db: AsyncSession, citizen) -> int:
    """Получить уровень самой старшей роли"""
    roles = await get_user_roles(db, citizen)
    if not roles:
        return 0
    return max(r.level for r in roles)


# =============================================
#  ДЕКОРАТОРЫ ДЛЯ FASTAPI
# =============================================

def require_permission(required_permission: str):
    """Декоратор для проверки прав доступа"""
    async def permission_dependency(
        request: Request,
        db: AsyncSession = Depends(get_db),
        current_user = Depends(get_current_user)
    ):
        if not current_user:
            raise HTTPException(status_code=401, detail="Необходима авторизация")

        if not await has_permission(db, current_user, required_permission):
            raise HTTPException(
                status_code=403,
                detail=f"Недостаточно прав. Требуется: {required_permission}"
            )
        return current_user
    return permission_dependency


def require_role_higher_than(min_level: int):
    """Декоратор для проверки минимального уровня роли"""
    async def role_dependency(
        request: Request,
        db: AsyncSession = Depends(get_db),
        current_user = Depends(get_current_user)
    ):
        if not current_user:
            raise HTTPException(status_code=401, detail="Необходима авторизация")

        level = await get_highest_role_level(db, current_user)
        if level < min_level:
            raise HTTPException(status_code=403, detail="Недостаточно прав")
        return current_user
    return role_dependency
