from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from database.db import get_db
from database.models import Citizen, ISBEmployee, ISBAward, ISBAwardGrant
from auth import require_permission
from database.isb_ranks_data import ISB_RANKS


router = APIRouter(prefix="/api/admin/isb", tags=["Admin ISB"])


# ============================================
#  СПИСОК СОТРУДНИКОВ
# ============================================

@router.get("/employees")
async def get_all_employees(
    current_user = Depends(require_permission("manage_security")),
    db: AsyncSession = Depends(get_db)
):
    """Все сотрудники ИСБ (включая уволенных)"""
    result = await db.execute(select(ISBEmployee).order_by(ISBEmployee.level.desc()))
    employees = result.scalars().all()

    citizens_ids = [e.citizen_id for e in employees]
    citizens_map = {}
    if citizens_ids:
        c_result = await db.execute(select(Citizen).where(Citizen.id.in_(citizens_ids)))
        citizens_map = {c.id: c for c in c_result.scalars().all()}

    return {
        "status": "success",
        "data": [
            {
                "id": e.id,
                "citizen_id": e.citizen_id,
                "username": citizens_map.get(e.citizen_id).username if citizens_map.get(e.citizen_id) else "—",
                "service_number": e.service_number,
                "rank_name": e.rank_name,
                "rank_short": e.rank_short,
                "branch": e.branch,
                "level": e.level,
                "position": e.position,
                "is_active": e.is_active,
                "enlisted_at": e.enlisted_at.isoformat() if e.enlisted_at else None,
                "promoted_at": e.promoted_at.isoformat() if e.promoted_at else None,
                "discharged_at": e.discharged_at.isoformat() if e.discharged_at else None,
                "can_arrest": e.can_arrest,
                "can_conduct_searches": e.can_conduct_searches,
                "can_issue_warrants": e.can_issue_warrants,
                "can_command": e.can_command,
            }
            for e in employees
        ]
    }


# ============================================
#  ДОСТУПНЫЕ ГРАЖДАНЕ
# ============================================

@router.get("/available-citizens")
async def get_available_citizens(
    current_user = Depends(require_permission("manage_security")),
    db: AsyncSession = Depends(get_db)
):
    """Граждане, которых можно принять в ИСБ"""
    result = await db.execute(select(ISBEmployee.citizen_id))
    busy_ids = [row[0] for row in result.all()]

    query = select(Citizen).order_by(Citizen.username)
    if busy_ids:
        query = query.where(Citizen.id.notin_(busy_ids))

    result = await db.execute(query)
    citizens = result.scalars().all()

    return {
        "status": "success",
        "data": [
            {"id": c.id, "username": c.username, "minecraft_uuid": c.minecraft_uuid}
            for c in citizens
        ]
    }


# ============================================
#  СПИСОК ЗВАНИЙ
# ============================================

@router.get("/ranks")
async def get_ranks(
    current_user = Depends(require_permission("manage_security")),
):
    """Список званий ИСБ для выпадающего списка"""
    return {
        "status": "success",
        "data": [
            {
                "key": key,
                "rank_name": data["rank_name"],
                "rank_short": data.get("rank_short"),
                "branch": data["branch"],
                "level": data["level"],
                "can_arrest": data.get("can_arrest", False),
                "can_conduct_searches": data.get("can_conduct_searches", False),
                "can_issue_warrants": data.get("can_issue_warrants", False),
                "can_command": data.get("can_command", False),
            }
            for key, data in ISB_RANKS.items()
        ]
    }


# ============================================
#  ПРИЁМ НА СЛУЖБУ
# ============================================

@router.post("/hire")
async def hire_employee(
    citizen_id: int = Query(...),
    rank_key: str = Query(...),
    position: str = Query(""),
    current_user = Depends(require_permission("manage_security")),
    db: AsyncSession = Depends(get_db)
):
    """Принять гражданина в ИСБ"""
    # Проверяем гражданина
    citizen_result = await db.execute(select(Citizen).where(Citizen.id == citizen_id))
    citizen = citizen_result.scalar_one_or_none()
    if not citizen:
        raise HTTPException(status_code=404, detail="Гражданин не найден")

    # Проверяем, что ещё не в ИСБ
    existing = await db.execute(
        select(ISBEmployee).where(ISBEmployee.citizen_id == citizen_id)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Этот гражданин уже в ИСБ")

    # Проверяем звание
    if rank_key not in ISB_RANKS:
        raise HTTPException(status_code=400, detail=f"Неизвестное звание: {rank_key}")

    rank_data = ISB_RANKS[rank_key]

    # Генерируем служебный номер
    count_result = await db.execute(select(func.count(ISBEmployee.id)))
    count = count_result.scalar() or 0
    service_number = f"ISB-{(count + 1):06d}"

    # Создаём запись
    employee = ISBEmployee(
        citizen_id=citizen_id,
        service_number=service_number,
        rank_name=rank_data["rank_name"],
        rank_short=rank_data.get("rank_short"),
        branch=rank_data["branch"],
        level=rank_data["level"],
        position=position or None,
        can_arrest=rank_data.get("can_arrest", False),
        can_conduct_searches=rank_data.get("can_conduct_searches", False),
        can_issue_warrants=rank_data.get("can_issue_warrants", False),
        can_command=rank_data.get("can_command", False),
        is_active=True,
    )
    db.add(employee)
    await db.commit()
    await db.refresh(employee)

    return {
        "status": "success",
        "message": f"{citizen.username} принят в ИСБ. Номер: {service_number}",
        "data": {
            "id": employee.id,
            "service_number": employee.service_number,
            "rank_name": employee.rank_name,
        }
    }


# ============================================
#  ОБНОВЛЕНИЕ (повышение / должность)
# ============================================

@router.put("/employees/{employee_id}")
async def update_employee(
    employee_id: int,
    rank_key: str = Query(None),
    position: str = Query(None),
    current_user = Depends(require_permission("manage_security")),
    db: AsyncSession = Depends(get_db)
):
    """Обновить данные сотрудника ИСБ"""
    result = await db.execute(select(ISBEmployee).where(ISBEmployee.id == employee_id))
    employee = result.scalar_one_or_none()
    if not employee:
        raise HTTPException(status_code=404, detail="Сотрудник ИСБ не найден")

    # Обновляем звание
    if rank_key:
        if rank_key not in ISB_RANKS:
            raise HTTPException(status_code=400, detail=f"Неизвестное звание: {rank_key}")
        rank_data = ISB_RANKS[rank_key]
        employee.rank_name = rank_data["rank_name"]
        employee.rank_short = rank_data.get("rank_short")
        employee.branch = rank_data["branch"]
        employee.level = rank_data["level"]
        employee.can_arrest = rank_data.get("can_arrest", False)
        employee.can_conduct_searches = rank_data.get("can_conduct_searches", False)
        employee.can_issue_warrants = rank_data.get("can_issue_warrants", False)
        employee.can_command = rank_data.get("can_command", False)
        employee.promoted_at = func.now()

    # Обновляем должность
    if position is not None:
        employee.position = position or None

    await db.commit()
    await db.refresh(employee)

    return {
        "status": "success",
        "message": "Данные сотрудника обновлены",
        "data": {
            "id": employee.id,
            "rank_name": employee.rank_name,
            "position": employee.position,
        }
    }


# ============================================
#  УВОЛЬНЕНИЕ
# ============================================

@router.delete("/employees/{employee_id}")
async def fire_employee(
    employee_id: int,
    current_user = Depends(require_permission("manage_security")),
    db: AsyncSession = Depends(get_db)
):
    """Уволить сотрудника (мягкое удаление)"""
    result = await db.execute(select(ISBEmployee).where(ISBEmployee.id == employee_id))
    employee = result.scalar_one_or_none()
    if not employee:
        raise HTTPException(status_code=404, detail="Сотрудник ИСБ не найден")

    if not employee.is_active:
        raise HTTPException(status_code=400, detail="Этот сотрудник уже уволен")

    employee.is_active = False
    employee.discharged_at = func.now()
    await db.commit()

    return {"status": "success", "message": "Сотрудник уволен из ИСБ"}


# ============================================
#  ВОССТАНОВЛЕНИЕ
# ============================================

@router.post("/employees/{employee_id}/restore")
async def restore_employee(
    employee_id: int,
    current_user = Depends(require_permission("manage_security")),
    db: AsyncSession = Depends(get_db)
):
    """Восстановить уволенного сотрудника"""
    result = await db.execute(select(ISBEmployee).where(ISBEmployee.id == employee_id))
    employee = result.scalar_one_or_none()
    if not employee:
        raise HTTPException(status_code=404, detail="Сотрудник ИСБ не найден")

    if employee.is_active:
        raise HTTPException(status_code=400, detail="Этот сотрудник и так активен")

    employee.is_active = True
    employee.discharged_at = None
    await db.commit()

    return {"status": "success", "message": "Сотрудник восстановлен"}


# ============================================
#  НАГРАДЫ — список всех
# ============================================

@router.get("/awards")
async def get_all_awards(
    current_user = Depends(require_permission("manage_security")),
    db: AsyncSession = Depends(get_db)
):
    """Список всех доступных наград ИСБ"""
    result = await db.execute(
        select(ISBAward).where(ISBAward.is_active == True).order_by(ISBAward.rarity, ISBAward.display_name)
    )
    awards = result.scalars().all()

    return {
        "status": "success",
        "data": [
            {
                "id": a.id,
                "name": a.name,
                "display_name": a.display_name,
                "description": a.description,
                "icon": a.icon,
                "rarity": a.rarity,
                "category": a.category,
            }
            for a in awards
        ]
    }


# ============================================
#  НАГРАДЫ — награды сотрудника
# ============================================

@router.get("/employees/{employee_id}/awards")
async def get_employee_awards(
    employee_id: int,
    current_user = Depends(require_permission("manage_security")),
    db: AsyncSession = Depends(get_db)
):
    """Награды конкретного сотрудника"""
    result = await db.execute(
        select(ISBAwardGrant)
        .where(ISBAwardGrant.employee_id == employee_id)
        .order_by(ISBAwardGrant.granted_at.desc())
    )
    grants = result.scalars().all()

    award_ids = [g.award_id for g in grants]
    awards_map = {}
    if award_ids:
        a_result = await db.execute(select(ISBAward).where(ISBAward.id.in_(award_ids)))
        awards_map = {a.id: a for a in a_result.scalars().all()}

    return {
        "status": "success",
        "data": [
            {
                "grant_id": g.id,
                "award_id": g.award_id,
                "award_name": awards_map.get(g.award_id).display_name if awards_map.get(g.award_id) else "—",
                "award_icon": awards_map.get(g.award_id).icon if awards_map.get(g.award_id) else "🏅",
                "award_rarity": awards_map.get(g.award_id).rarity if awards_map.get(g.award_id) else "common",
                "granted_at": g.granted_at.isoformat() if g.granted_at else None,
                "reason": g.reason,
            }
            for g in grants
        ]
    }


# ============================================
#  НАГРАДЫ — выдача
# ============================================

@router.post("/employees/{employee_id}/awards")
async def grant_award(
    employee_id: int,
    award_id: int = Query(...),
    reason: str = Query(""),
    current_user = Depends(require_permission("manage_security")),
    db: AsyncSession = Depends(get_db)
):
    """Выдать награду сотруднику"""
    emp_result = await db.execute(select(ISBEmployee).where(ISBEmployee.id == employee_id))
    employee = emp_result.scalar_one_or_none()
    if not employee:
        raise HTTPException(status_code=404, detail="Сотрудник ИСБ не найден")
    if not employee.is_active:
        raise HTTPException(status_code=400, detail="Нельзя выдать награду уволенному")

    award_result = await db.execute(select(ISBAward).where(ISBAward.id == award_id))
    award = award_result.scalar_one_or_none()
    if not award:
        raise HTTPException(status_code=404, detail="Награда не найдена")

    grant = ISBAwardGrant(
        employee_id=employee_id,
        award_id=award_id,
        granted_by=current_user.id,
        reason=reason or None,
    )
    db.add(grant)
    await db.commit()
    await db.refresh(grant)

    return {
        "status": "success",
        "message": f"Награда «{award.display_name}» выдана",
        "data": {"grant_id": grant.id}
    }


# ============================================
#  НАГРАДЫ — отзыв
# ============================================

@router.delete("/awards/grant/{grant_id}")
async def revoke_award(
    grant_id: int,
    current_user = Depends(require_permission("manage_security")),
    db: AsyncSession = Depends(get_db)
):
    """Забрать (отозвать) награду"""
    result = await db.execute(select(ISBAwardGrant).where(ISBAwardGrant.id == grant_id))
    grant = result.scalar_one_or_none()
    if not grant:
        raise HTTPException(status_code=404, detail="Запись о награде не найдена")

    await db.delete(grant)
    await db.commit()

    return {"status": "success", "message": "Награда отозвана"}
