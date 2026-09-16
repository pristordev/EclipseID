from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from database.db import get_db
from database import crud


router = APIRouter(prefix="/api", tags=["Statistics"])


@router.get("/stats")
async def get_stats(db: AsyncSession = Depends(get_db)):
    """Статистика государства: граждане, распределение по ролям"""
    citizens_count = await crud.get_citizens_count(db)

    all_roles = await crud.get_all_roles(db)
    roles_stats = {}
    for role in all_roles:
        roles_stats[role.name] = {
            "name": role.display_name,
            "count": 0,
        }

    all_citizens = await crud.get_all_citizens(db, limit=10000)
    for c in all_citizens:
        for rid in (c.role_ids or []):
            for role in all_roles:
                if role.id == rid:
                    roles_stats[role.name]["count"] += 1

    return {
        "status": "success",
        "data": {
            "total_citizens": citizens_count,
            "by_role": roles_stats,
        }
    }