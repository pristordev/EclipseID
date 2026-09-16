from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from database.db import get_db
from database.models import Role, Permission
from auth import require_permission


router = APIRouter(prefix="/api/admin/roles", tags=["Admin Roles"])


# ============================================
#  СПИСОК РОЛЕЙ
# ============================================

@router.get("/")
async def get_all_roles(
    current_user = Depends(require_permission("full_access")),
    db: AsyncSession = Depends(get_db)
):
    """Получить все роли с правами"""
    result = await db.execute(
        select(Role)
        .options(selectinload(Role.permissions))
        .order_by(Role.level.desc())
    )
    roles = result.scalars().all()

    return {
        "status": "success",
        "data": [
            {
                "id": r.id,
                "name": r.name,
                "display_name": r.display_name,
                "level": r.level,
                "is_active": r.is_active,
                "permissions": [
                    {"id": p.id, "name": p.name, "display_name": p.display_name}
                    for p in r.permissions
                ]
            }
            for r in roles
        ]
    }


@router.get("/permissions")
async def get_all_permissions(
    current_user = Depends(require_permission("full_access")),
    db: AsyncSession = Depends(get_db)
):
    """Список всех доступных прав"""
    result = await db.execute(
        select(Permission).order_by(Permission.category, Permission.display_name)
    )
    permissions = result.scalars().all()

    return {
        "status": "success",
        "data": [
            {
                "id": p.id,
                "name": p.name,
                "display_name": p.display_name,
                "category": p.category
            }
            for p in permissions
        ]
    }


# ============================================
#  СОЗДАНИЕ РОЛИ
# ============================================

@router.post("/")
async def create_role(
    name: str = Query(...),
    display_name: str = Query(...),
    level: int = Query(0),
    permissions: str = Query(""),
    current_user = Depends(require_permission("full_access")),
    db: AsyncSession = Depends(get_db)
):
    """Создать новую роль"""
    # Проверка дубликата
    existing = await db.execute(select(Role).where(Role.name == name))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Роль с таким именем уже существует")

    # Создаём роль
    role = Role(name=name, display_name=display_name, level=level, is_active=True)
    db.add(role)
    await db.commit()
    await db.refresh(role)

    # Добавляем права
    if permissions:
        perm_ids = [int(p.strip()) for p in permissions.split(",") if p.strip()]
        result = await db.execute(
            select(Role)
            .options(selectinload(Role.permissions))
            .where(Role.id == role.id)
        )
        role = result.scalar_one()

        perm_result = await db.execute(
            select(Permission).where(Permission.id.in_(perm_ids))
        )
        perms = perm_result.scalars().all()
        role.permissions.extend(perms)
        await db.commit()

    return {
        "status": "success",
        "message": "Роль создана",
        "data": {"id": role.id, "name": role.name}
    }


# ============================================
#  ОБНОВЛЕНИЕ РОЛИ
# ============================================

@router.put("/{role_id}")
async def update_role(
    role_id: int,
    display_name: str = Query(None),
    level: int = Query(None),
    is_active: bool = Query(None),
    permissions: str = Query(None),
    current_user = Depends(require_permission("full_access")),
    db: AsyncSession = Depends(get_db)
):
    """Обновить роль (имя, уровень, права)"""
    result = await db.execute(select(Role).where(Role.id == role_id))
    role = result.scalar_one_or_none()
    if not role:
        raise HTTPException(status_code=404, detail="Роль не найдена")

    if display_name is not None:
        role.display_name = display_name
    if level is not None:
        role.level = level
    if is_active is not None:
        role.is_active = is_active

    await db.commit()

    # Обновляем права
    if permissions is not None:
        result = await db.execute(
            select(Role)
            .options(selectinload(Role.permissions))
            .where(Role.id == role_id)
        )
        role = result.scalar_one()

        role.permissions.clear()

        if permissions:
            perm_ids = [int(p.strip()) for p in permissions.split(",") if p.strip()]
            perm_result = await db.execute(
                select(Permission).where(Permission.id.in_(perm_ids))
            )
            perms = perm_result.scalars().all()
            role.permissions.extend(perms)

        await db.commit()

    return {"status": "success", "message": "Роль обновлена"}


# ============================================
#  УДАЛЕНИЕ РОЛИ
# ============================================

@router.delete("/{role_id}")
async def delete_role(
    role_id: int,
    current_user = Depends(require_permission("full_access")),
    db: AsyncSession = Depends(get_db)
):
    """Удалить роль (нельзя удалить базовые)"""
    result = await db.execute(select(Role).where(Role.id == role_id))
    role = result.scalar_one_or_none()
    if not role:
        raise HTTPException(status_code=404, detail="Роль не найдена")

    if role.name in ["citizen", "imperator"]:
        raise HTTPException(status_code=400, detail="Нельзя удалить базовую роль")

    await db.delete(role)
    await db.commit()

    return {"status": "success", "message": "Роль удалена"}
