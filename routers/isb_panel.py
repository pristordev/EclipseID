from fastapi import APIRouter, Request, Depends, HTTPException, Query
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession
from pathlib import Path

from database.db import get_db
from database import crud
from auth import get_current_user, has_permission, require_permission


router = APIRouter(tags=["ISB Panel"])

BASE_DIR = Path(__file__).resolve().parent.parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))


# ============================================
#  СТРАНИЦА ПАНЕЛИ
# ============================================

@router.get("/isb/panel", response_class=HTMLResponse)
async def isb_panel(request: Request, db: AsyncSession = Depends(get_db)):
    """Строгая панель управления ИСБ"""
    current_user = await get_current_user(request, db)
    if not current_user:
        return RedirectResponse("/auth/discord")

    isb_emp = await crud.get_isb_employee_by_citizen(db, current_user.id)
    has_manage = await has_permission(db, current_user, "manage_security")

    print(f"🔍 DEBUG /isb/panel: user={current_user.username}, isb_emp={isb_emp is not None}, has_manage={has_manage}")

    if not isb_emp and not has_manage:
        raise HTTPException(status_code=403, detail="Доступ только для ИСБ")

    context = {
        "current_user": current_user,
    }
    return templates.TemplateResponse(request=request, name="isb_panel.html", context=context)


# ============================================
#  API · СЕКТОРА
# ============================================

@router.get("/api/isb/sectors")
async def api_get_sectors(
    current_user = Depends(require_permission("manage_security")),
    db: AsyncSession = Depends(get_db)
):
    """Список секторов с назначениями"""
    from sqlalchemy import select
    from database.models import ISBEmployee, Citizen
    from utils.avatars import get_avatar_url

    sectors = await crud.get_all_sectors(db)

    result = []
    for s in sectors:
        assignments = await crud.get_sector_assignments(db, s.id)
        members = []
        for a in assignments:
            emp_result = await db.execute(
                select(ISBEmployee).where(ISBEmployee.id == a.employee_id)
            )
            emp = emp_result.scalar_one_or_none()
            if emp:
                cit_result = await db.execute(
                    select(Citizen).where(Citizen.id == emp.citizen_id)
                )
                cit = cit_result.scalar_one_or_none()
                members.append({
                    "assignment_id": a.id,
                    "employee_id": emp.id,
                    "username": cit.username if cit else "—",
                    "rank_name": emp.rank_name,
                    "service_number": emp.service_number,
                    "is_leader": a.is_leader,
                    "avatar_url": get_avatar_url(cit.minecraft_uuid) if cit and cit.minecraft_uuid else None,
                })

        result.append({
            "id": s.id,
            "number": s.number,
            "name": s.name,
            "description": s.description,
            "center_x": s.center_x,
            "center_z": s.center_z,
            "threat_level": s.threat_level,
            "is_active": s.is_active,
            "members": members,
            "members_count": len(members),
        })

    return {"status": "success", "count": len(result), "data": result}


@router.post("/api/isb/sectors/{sector_id}/assign")
async def api_assign_to_sector(
    sector_id: int,
    employee_id: int = Query(...),
    is_leader: bool = Query(False),
    current_user = Depends(require_permission("manage_security")),
    db: AsyncSession = Depends(get_db)
):
    """Назначить сотрудника на сектор"""
    sector = await crud.get_sector(db, sector_id)
    if not sector:
        raise HTTPException(status_code=404, detail="Сектор не найден")

    await crud.assign_employee_to_sector(db, sector_id, employee_id, is_leader)

    await crud.create_isb_log(
        db,
        message=f"СОТРУДНИК НАЗНАЧЕН НА СЕКТОР {sector.number} · {sector.name}",
        severity="info",
        category="order",
        actor_id=current_user.id,
        sector_id=sector_id,
    )

    return {"status": "success", "message": "Сотрудник назначен"}


@router.delete("/api/isb/sectors/assignments/{assignment_id}")
async def api_remove_sector_assignment(
    assignment_id: int,
    current_user = Depends(require_permission("manage_security")),
    db: AsyncSession = Depends(get_db)
):
    """Убрать сотрудника с сектора"""
    success = await crud.remove_sector_assignment(db, assignment_id)
    if not success:
        raise HTTPException(status_code=404, detail="Назначение не найдено")
    return {"status": "success", "message": "Сотрудник убран с сектора"}


# ============================================
#  API · ЛОГИ
# ============================================

@router.get("/api/isb/logs")
async def api_get_logs(
    limit: int = 100,
    severity: str = None,
    category: str = None,
    current_user = Depends(require_permission("manage_security")),
    db: AsyncSession = Depends(get_db)
):
    """Логи ИСБ"""
    logs = await crud.get_isb_logs(db, limit=limit, severity=severity, category=category)

    result = []
    for l in logs:
        actor = None
        if l.actor_id:
            actor = await crud.get_citizen(db, l.actor_id)

        sector = None
        if l.sector_id:
            sector = await crud.get_sector(db, l.sector_id)

        result.append({
            "id": l.id,
            "created_at": l.created_at.isoformat() if l.created_at else None,
            "severity": l.severity,
            "category": l.category,
            "message": l.message,
            "actor": actor.username if actor else None,
            "sector_number": sector.number if sector else None,
            "sector_name": sector.name if sector else None,
        })

    return {"status": "success", "count": len(result), "data": result}


@router.post("/api/isb/logs")
async def api_create_log(
    message: str = Query(...),
    severity: str = Query("info"),
    category: str = Query(None),
    sector_id: int = Query(None),
    current_user = Depends(require_permission("manage_security")),
    db: AsyncSession = Depends(get_db)
):
    """Создать лог вручную"""
    await crud.create_isb_log(
        db, message=message, severity=severity, category=category,
        actor_id=current_user.id, sector_id=sector_id,
    )
    return {"status": "success"}


# ============================================
#  API · СТАТИСТИКА ДЛЯ ПАНЕЛИ
# ============================================

@router.get("/api/isb/panel/stats")
async def api_panel_stats(
    current_user = Depends(require_permission("manage_security")),
    db: AsyncSession = Depends(get_db)
):
    """Сводная статистика для панели"""
    from sqlalchemy import select, func as sql_func
    from database.models import ISBEmployee, ISBLog, ISBSector
    from datetime import datetime, timedelta

    emp_result = await db.execute(
        select(sql_func.count(ISBEmployee.id)).where(ISBEmployee.is_active == True)
    )
    employees_count = emp_result.scalar() or 0

    sector_result = await db.execute(select(sql_func.count(ISBSector.id)))
    sectors_count = sector_result.scalar() or 0

    yesterday = datetime.utcnow() - timedelta(hours=24)
    logs_result = await db.execute(
        select(sql_func.count(ISBLog.id)).where(ISBLog.created_at >= yesterday)
    )
    logs_24h = logs_result.scalar() or 0

    crit_result = await db.execute(
        select(sql_func.count(ISBLog.id)).where(
            ISBLog.created_at >= yesterday,
            ISBLog.severity == "critical"
        )
    )
    critical_24h = crit_result.scalar() or 0

    return {
        "status": "success",
        "data": {
            "employees_count": employees_count,
            "sectors_count": sectors_count,
            "logs_24h": logs_24h,
            "critical_24h": critical_24h,
        }
    }

  # ============================================
#  API · ГРАФИКИ
# ============================================

@router.get("/api/isb/graphs/sectors")
async def api_graphs_sectors(
    current_user = Depends(require_permission("manage_security")),
    db: AsyncSession = Depends(get_db)
):
    """Данные для графика: сотрудники по секторам"""
    from sqlalchemy import select, func as sql_func
    from database.models import ISBSector, ISBSectorAssignment

    result = await db.execute(select(ISBSector).order_by(ISBSector.number))
    sectors = list(result.scalars().all())

    data = []
    for s in sectors:
        cnt_result = await db.execute(
            select(sql_func.count(ISBSectorAssignment.id))
            .where(ISBSectorAssignment.sector_id == s.id)
        )
        cnt = cnt_result.scalar() or 0
        data.append({"label": f"S-{s.number:02d}", "name": s.name, "value": cnt})

    return {"status": "success", "data": data}


@router.get("/api/isb/graphs/logs-24h")
async def api_graphs_logs_24h(
    current_user = Depends(require_permission("manage_security")),
    db: AsyncSession = Depends(get_db)
):
    """Логи по часам за 24 часа"""
    from sqlalchemy import select, func as sql_func, and_
    from database.models import ISBLog
    from datetime import datetime, timedelta

    now = datetime.utcnow()
    start = now - timedelta(hours=24)

    result = await db.execute(
        select(
            sql_func.date_trunc('hour', ISBLog.created_at).label('hour'),
            sql_func.count(ISBLog.id).label('count')
        )
        .where(ISBLog.created_at >= start)
        .group_by('hour')
        .order_by('hour')
    )
    rows = result.all()

    # Заполняем все 24 часа
    hours = []
    for i in range(24):
        h = start + timedelta(hours=i)
        hours.append({"hour": h.strftime("%H:00"), "count": 0})

    for hour, count in rows:
        h_str = hour.strftime("%H:00")
        for item in hours:
            if item["hour"] == h_str:
                item["count"] = count
                break

    return {"status": "success", "data": hours}


@router.get("/api/isb/graphs/threat")
async def api_graphs_threat(
    current_user = Depends(require_permission("manage_security")),
    db: AsyncSession = Depends(get_db)
):
    """Топ-5 секторов по уровню угрозы"""
    from sqlalchemy import select
    from database.models import ISBSector

    result = await db.execute(
        select(ISBSector).order_by(ISBSector.threat_level.desc()).limit(5)
    )
    sectors = list(result.scalars().all())

    return {
        "status": "success",
        "data": [
            {"label": f"S-{s.number:02d}", "name": s.name, "value": s.threat_level}
            for s in sectors
        ]
    }



# ============================================
#  API · МОЙ УРОВЕНЬ ДОСТУПА
# ============================================

@router.get("/api/isb/me/access")
async def api_my_access(
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Информация о моём уровне доступа в ИСБ"""
    from database.isb_access import get_access_name

    isb_emp = await crud.get_isb_employee_by_citizen(db, current_user.id)

    if not isb_emp:
        level = 5
    else:
        level = isb_emp.access_level or 1

    return {
        "status": "success",
        "data": {
            "level": level,
            "name": get_access_name(level),
        }
    }