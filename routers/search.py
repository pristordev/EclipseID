from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_
from database.db import get_db
from database.models import Citizen, Role, ISBEmployee, ISBAward


router = APIRouter(prefix="/api/search", tags=["Search"])


@router.get("")
async def global_search(
    q: str = Query(..., min_length=1, description="Поисковый запрос"),
    db: AsyncSession = Depends(get_db)
):
    """Глобальный поиск по гражданам, ролям, наградам и ИСБ"""
    query = q.strip()
    if not query:
        return {"status": "success", "results": []}

    like = f"%{query}%"
    results = []

    # 1. ГРАЖДАНЕ
    citizens_result = await db.execute(
        select(Citizen).where(
            or_(Citizen.username.ilike(like), Citizen.minecraft_uuid.ilike(like))
        ).limit(10)
    )
    for c in citizens_result.scalars().all():
        results.append({
            "type": "citizen",
            "icon": "👤",
            "title": c.username,
            "subtitle": f"⭐ {c.reputation} репутации",
            "url": f"/p/{c.username}",
        })

    # 2. РОЛИ
    roles_result = await db.execute(
        select(Role).where(
            or_(Role.name.ilike(like), Role.display_name.ilike(like))
        ).limit(5)
    )
    for r in roles_result.scalars().all():
        results.append({
            "type": "role",
            "icon": "🎖️",
            "title": r.display_name,
            "subtitle": f"Роль · уровень {r.level}",
            "url": "/admin/roles",
        })

    # 3. НАГРАДЫ ИСБ
    awards_result = await db.execute(
        select(ISBAward).where(
            or_(
                ISBAward.name.ilike(like),
                ISBAward.display_name.ilike(like),
                ISBAward.description.ilike(like),
            )
        ).limit(5)
    )
    for a in awards_result.scalars().all():
        results.append({
            "type": "award",
            "icon": a.icon or "🏅",
            "title": a.display_name,
            "subtitle": f"Награда ИСБ · {a.rarity}",
            "url": "/admin/isb",
        })

    # 4. СОТРУДНИКИ ИСБ
    isb_result = await db.execute(
        select(ISBEmployee).where(
            or_(
                ISBEmployee.service_number.ilike(like),
                ISBEmployee.rank_name.ilike(like),
                ISBEmployee.position.ilike(like),
            )
        ).limit(10)
    )
    for e in isb_result.scalars().all():
        c_result = await db.execute(select(Citizen).where(Citizen.id == e.citizen_id))
        c = c_result.scalar_one_or_none()
        username = c.username if c else "—"
        results.append({
            "type": "isb",
            "icon": "🛡️",
            "title": f"{username} · {e.service_number}",
            "subtitle": f"{e.rank_name} · {e.branch}",
            "url": f"/p/{username}",
        })

    return {
        "status": "success",
        "query": query,
        "count": len(results),
        "results": results,
    }
