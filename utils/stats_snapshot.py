"""Создание снимка статистики для графиков"""
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from database.models import Citizen, ISBEmployee, ISBAwardGrant, StatsHistory


async def create_snapshot(db: AsyncSession) -> StatsHistory:
    """Создать снимок текущей статистики"""
    # Граждане
    citizens_result = await db.execute(select(func.count(Citizen.id)))
    citizens_count = citizens_result.scalar() or 0

    # Сотрудники ИСБ
    isb_result = await db.execute(
        select(func.count(ISBEmployee.id)).where(ISBEmployee.is_active == True)
    )
    isb_count = isb_result.scalar() or 0

    # Награды
    awards_result = await db.execute(select(func.count(ISBAwardGrant.id)))
    awards_count = awards_result.scalar() or 0

    # Общая репутация
    rep_result = await db.execute(select(func.sum(Citizen.reputation)))
    total_rep = rep_result.scalar() or 0

    # API-запросы (пока заглушка — счётчик добавим позже)
    api_requests = 0

    snapshot = StatsHistory(
        citizens_count=citizens_count,
        isb_employees_count=isb_count,
        awards_granted_count=awards_count,
        total_reputation=total_rep,
        api_requests=api_requests,
    )
    db.add(snapshot)
    await db.commit()
    await db.refresh(snapshot)
    return snapshot