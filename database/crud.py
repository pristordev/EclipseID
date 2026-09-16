from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from database.models import Citizen, Role, ISBEmployee, ISBAward, ISBAwardGrant
from typing import Optional, List, Dict, Any


# =============================================
#  ГРАЖДАНЕ
# =============================================

async def create_citizen(db: AsyncSession, data: Dict[str, Any]) -> Citizen:
    citizen = Citizen(**data)
    db.add(citizen)
    await db.commit()
    await db.refresh(citizen)
    return citizen


async def get_citizen(db: AsyncSession, citizen_id: int) -> Optional[Citizen]:
    result = await db.execute(select(Citizen).where(Citizen.id == citizen_id))
    return result.scalar_one_or_none()


async def get_citizen_by_discord(db: AsyncSession, discord_id: int) -> Optional[Citizen]:
    result = await db.execute(select(Citizen).where(Citizen.discord_id == discord_id))
    return result.scalar_one_or_none()


async def get_citizen_by_uuid(db: AsyncSession, minecraft_uuid: str) -> Optional[Citizen]:
    result = await db.execute(select(Citizen).where(Citizen.minecraft_uuid == minecraft_uuid))
    return result.scalar_one_or_none()


async def get_citizen_by_username(db: AsyncSession, username: str) -> Optional[Citizen]:
    result = await db.execute(select(Citizen).where(Citizen.username == username))
    return result.scalar_one_or_none()


async def get_all_citizens(db: AsyncSession, skip: int = 0, limit: int = 100) -> List[Citizen]:
    result = await db.execute(
        select(Citizen).order_by(Citizen.citizenship_date.desc()).offset(skip).limit(limit)
    )
    return list(result.scalars().all())


async def update_citizen(db: AsyncSession, citizen_id: int, data: Dict[str, Any]) -> Optional[Citizen]:
    citizen = await get_citizen(db, citizen_id)
    if not citizen:
        return None
    for key, value in data.items():
        if hasattr(citizen, key):
            setattr(citizen, key, value)
    await db.commit()
    await db.refresh(citizen)
    return citizen


async def delete_citizen(db: AsyncSession, citizen_id: int) -> bool:
    citizen = await get_citizen(db, citizen_id)
    if not citizen:
        return False
    await db.delete(citizen)
    await db.commit()
    return True


async def update_last_login(db: AsyncSession, citizen_id: int) -> Optional[Citizen]:
    citizen = await get_citizen(db, citizen_id)
    if not citizen:
        return None
    citizen.last_login = func.now()
    await db.commit()
    await db.refresh(citizen)
    return citizen


async def update_reputation(db: AsyncSession, citizen_id: int, change: int) -> Optional[Citizen]:
    citizen = await get_citizen(db, citizen_id)
    if not citizen:
        return None
    citizen.reputation += change
    await db.commit()
    await db.refresh(citizen)
    return citizen


async def get_citizens_count(db: AsyncSession) -> int:
    result = await db.execute(select(func.count(Citizen.id)))
    return result.scalar() or 0


async def search_citizens(db: AsyncSession, query: str) -> List[Citizen]:
    like = f"%{query}%"
    result = await db.execute(
        select(Citizen).where(
            (Citizen.username.ilike(like)) | (Citizen.minecraft_uuid.ilike(like))
        )
    )
    return list(result.scalars().all())


async def get_top_reputation(db: AsyncSession, limit: int = 10) -> List[Citizen]:
    result = await db.execute(
        select(Citizen).order_by(Citizen.reputation.desc()).limit(limit)
    )
    return list(result.scalars().all())


# =============================================
#  РОЛИ И ПРАВА
# =============================================

async def get_all_roles(db: AsyncSession) -> List[Role]:
    result = await db.execute(
        select(Role).options(selectinload(Role.permissions)).order_by(Role.level.desc())
    )
    return list(result.scalars().all())


async def get_role_by_id(db: AsyncSession, role_id: int) -> Optional[Role]:
    result = await db.execute(
        select(Role).options(selectinload(Role.permissions)).where(Role.id == role_id)
    )
    return result.scalar_one_or_none()


async def get_role_by_name(db: AsyncSession, name: str) -> Optional[Role]:
    result = await db.execute(select(Role).where(Role.name == name))
    return result.scalar_one_or_none()


async def get_roles_by_ids(db: AsyncSession, role_ids: list) -> List[Role]:
    if not role_ids:
        return []
    result = await db.execute(select(Role).where(Role.id.in_(role_ids)))
    return list(result.scalars().all())


# =============================================
#  ИСБ — СОТРУДНИКИ
# =============================================

async def generate_isb_service_number(db: AsyncSession) -> str:
    """Сгенерировать следующий служебный номер ИСБ"""
    result = await db.execute(select(func.count(ISBEmployee.id)))
    count = result.scalar() or 0
    return f"ISB-{(count + 1):06d}"


async def create_isb_employee(db: AsyncSession, data: dict) -> ISBEmployee:
    if "service_number" not in data:
        data["service_number"] = await generate_isb_service_number(db)
    employee = ISBEmployee(**data)
    db.add(employee)
    await db.commit()
    await db.refresh(employee)
    return employee


async def get_isb_employee_by_citizen(db: AsyncSession, citizen_id: int) -> Optional[ISBEmployee]:
    result = await db.execute(
        select(ISBEmployee).where(ISBEmployee.citizen_id == citizen_id)
    )
    return result.scalar_one_or_none()


async def get_isb_employee_by_number(db: AsyncSession, number: str) -> Optional[ISBEmployee]:
    result = await db.execute(
        select(ISBEmployee).where(ISBEmployee.service_number == number)
    )
    return result.scalar_one_or_none()


async def get_all_isb_employees(db: AsyncSession, active_only: bool = True) -> List[ISBEmployee]:
    query = select(ISBEmployee)
    if active_only:
        query = query.where(ISBEmployee.is_active == True)
    query = query.order_by(ISBEmployee.level.desc())
    result = await db.execute(query)
    return list(result.scalars().all())


async def update_isb_employee(db: AsyncSession, employee_id: int, data: dict) -> Optional[ISBEmployee]:
    result = await db.execute(select(ISBEmployee).where(ISBEmployee.id == employee_id))
    employee = result.scalar_one_or_none()
    if not employee:
        return None
    for key, value in data.items():
        if hasattr(employee, key):
            setattr(employee, key, value)
    await db.commit()
    await db.refresh(employee)
    return employee


async def discharge_isb_employee(db: AsyncSession, employee_id: int) -> Optional[ISBEmployee]:
    result = await db.execute(select(ISBEmployee).where(ISBEmployee.id == employee_id))
    employee = result.scalar_one_or_none()
    if not employee:
        return None
    employee.is_active = False
    employee.discharged_at = func.now()
    await db.commit()
    await db.refresh(employee)
    return employee


# =============================================
#  ИСБ — НАГРАДЫ
# =============================================

async def get_all_awards(db: AsyncSession) -> List[ISBAward]:
    result = await db.execute(
        select(ISBAward).where(ISBAward.is_active == True).order_by(ISBAward.rarity)
    )
    return list(result.scalars().all())


async def get_award_by_name(db: AsyncSession, name: str) -> Optional[ISBAward]:
    result = await db.execute(select(ISBAward).where(ISBAward.name == name))
    return result.scalar_one_or_none()


async def grant_award(
    db: AsyncSession,
    employee_id: int,
    award_id: int,
    granted_by: int = None,
    reason: str = None
) -> ISBAwardGrant:
    grant = ISBAwardGrant(
        employee_id=employee_id,
        award_id=award_id,
        granted_by=granted_by,
        reason=reason
    )
    db.add(grant)
    await db.commit()
    await db.refresh(grant)
    return grant


async def revoke_award(db: AsyncSession, grant_id: int) -> bool:
    result = await db.execute(select(ISBAwardGrant).where(ISBAwardGrant.id == grant_id))
    grant = result.scalar_one_or_none()
    if not grant:
        return False
    await db.delete(grant)
    await db.commit()
    return True


async def get_employee_awards(db: AsyncSession, employee_id: int) -> list:
    """Получить все награды сотрудника"""
    result = await db.execute(
        select(ISBAwardGrant)
        .where(ISBAwardGrant.employee_id == employee_id)
        .order_by(ISBAwardGrant.granted_at.desc())
    )
    grants = list(result.scalars().all())

    awards = []
    for g in grants:
        award_result = await db.execute(select(ISBAward).where(ISBAward.id == g.award_id))
        award = award_result.scalar_one_or_none()
        if award:
            awards.append({"grant": g, "award": award})
    return awards
