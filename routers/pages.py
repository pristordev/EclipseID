from fastapi import APIRouter, Request, Depends, Response, Query, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text, select
from pathlib import Path
import time

from database.db import get_db
from database import crud
from database.models import StatsHistory
from auth import get_current_user, create_access_token, ACCESS_TOKEN_EXPIRE_MINUTES, has_permission
from auth.discord import get_discord_oauth_url, get_discord_user
from utils.minecraft import get_minecraft_uuid
from utils.avatars import get_avatar_url
from utils.isb_insignia import generate_insignia_svg


router = APIRouter(tags=["Pages"])

BASE_DIR = Path(__file__).resolve().parent.parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))


async def get_rank_insignia_svg(db: AsyncSession, rank_name: str):
    if not rank_name:
        return None
    result = await db.execute(
        text("SELECT pattern FROM isb_rank_insignia WHERE rank_name = :name"),
        {"name": rank_name}
    )
    row = result.fetchone()
    if row and row[0]:
        return generate_insignia_svg(row[0])
    return None


# ============================================
#  ГЛАВНАЯ
# ============================================

@router.get("/", response_class=HTMLResponse)
async def root(request: Request, db: AsyncSession = Depends(get_db)):
    current_user = await get_current_user(request, db)
    avatar_url = get_avatar_url(current_user.minecraft_uuid) if current_user and current_user.minecraft_uuid else None

    start_time = time.perf_counter()
    citizens_count = await crud.get_citizens_count(db)
    ping_ms = round((time.perf_counter() - start_time) * 1000, 2)

    top_citizens = await crud.get_top_reputation(db, limit=3)
    first_citizen = top_citizens[0] if top_citizens else None

    main_role_display = "Гражданин"
    if current_user:
        roles = await crud.get_roles_by_ids(db, current_user.role_ids or [1])
        if roles:
            sorted_roles = sorted(roles, key=lambda r: r.level, reverse=True)
            main_role_display = sorted_roles[0].display_name

    context = {
        "current_user": current_user,
        "avatar_url": avatar_url,
        "citizens_count": citizens_count,
        "ping_ms": ping_ms,
        "top_citizen": first_citizen,
        "top_citizens": top_citizens,
        "main_role_display": main_role_display,
    }
    return templates.TemplateResponse(request=request, name="index.html", context=context)


# ============================================
#  ПРОФИЛЬ
# ============================================

@router.get("/profile", response_class=HTMLResponse)
async def profile(request: Request, db: AsyncSession = Depends(get_db)):
    current_user = await get_current_user(request, db)
    if not current_user:
        return RedirectResponse("/auth/discord")

    avatar_url = get_avatar_url(current_user.minecraft_uuid) if current_user.minecraft_uuid else None

    role_ids = current_user.role_ids or [1]
    roles_objects = await crud.get_roles_by_ids(db, role_ids)
    sorted_roles = sorted(roles_objects, key=lambda r: r.level, reverse=True)

    main_role = sorted_roles[0] if sorted_roles else None
    main_role_display = main_role.display_name if main_role else "Гражданин"

    role_names = {r.id: r.display_name for r in sorted_roles}
    sorted_role_ids = [r.id for r in sorted_roles]

    has_admin_access = any(r.level >= 95 for r in sorted_roles)

    isb_employee = await crud.get_isb_employee_by_citizen(db, current_user.id)
    isb_awards = []
    rank_insignia_svg = None
    if isb_employee:
        isb_awards = await crud.get_employee_awards(db, isb_employee.id)
        rank_insignia_svg = await get_rank_insignia_svg(db, isb_employee.rank_name)

    context = {
        "user": current_user,
        "current_user": current_user,
        "avatar_url": avatar_url,
        "has_admin_access": has_admin_access,
        "main_role_display": main_role_display,
        "role_names": role_names,
        "sorted_roles": sorted_role_ids,
        "isb_employee": isb_employee,
        "isb_awards": isb_awards,
        "rank_insignia_svg": rank_insignia_svg,
    }
    return templates.TemplateResponse(request=request, name="profile.html", context=context)


# ============================================
#  О СИСТЕМЕ
# ============================================

@router.get("/about", response_class=HTMLResponse)
async def about(request: Request, db: AsyncSession = Depends(get_db)):
    current_user = await get_current_user(request, db)
    avatar_url = get_avatar_url(current_user.minecraft_uuid) if current_user and current_user.minecraft_uuid else None

    context = {
        "current_user": current_user,
        "avatar_url": avatar_url,
    }
    return templates.TemplateResponse(request=request, name="about.html", context=context)


# ============================================
#  АВТОРИЗАЦИЯ
# ============================================

@router.get("/auth/discord")
async def auth_discord():
    url = await get_discord_oauth_url()
    return RedirectResponse(url)


@router.get("/auth/discord/callback")
async def auth_discord_callback(code: str, response: Response, db: AsyncSession = Depends(get_db)):
    user_data = await get_discord_user(code)
    discord_id = int(user_data.get("id"))
    discord_username = user_data.get("username")

    citizen = await crud.get_citizen_by_discord(db, discord_id)

    if not citizen:
        response = RedirectResponse("/application")
        response.set_cookie("pending_discord_id", str(discord_id), max_age=300)
        response.set_cookie("pending_discord_username", discord_username, max_age=300)
        return response

    await crud.update_last_login(db, citizen.id)
    token = create_access_token({"discord_id": discord_id})

    response = RedirectResponse("/")
    response.set_cookie("access_token", token, httponly=True, max_age=ACCESS_TOKEN_EXPIRE_MINUTES * 60, secure=False, samesite="lax")
    return response


@router.get("/logout")
async def logout(response: Response):
    response = RedirectResponse("/")
    response.delete_cookie("access_token")
    return response


# ============================================
#  ЗАЯВКА
# ============================================

@router.get("/application", response_class=HTMLResponse)
async def application_form(request: Request, db: AsyncSession = Depends(get_db)):
    current_user = await get_current_user(request, db)
    avatar_url = get_avatar_url(current_user.minecraft_uuid) if current_user and current_user.minecraft_uuid else None

    pending_discord_id = request.cookies.get("pending_discord_id")
    pending_discord_username = request.cookies.get("pending_discord_username")

    context = {
        "current_user": current_user,
        "avatar_url": avatar_url,
        "discord_id": pending_discord_id,
        "discord_username": pending_discord_username,
    }
    return templates.TemplateResponse(request=request, name="application.html", context=context)


@router.post("/api/application")
async def submit_application(
    username: str = Query(...),
    discord_id: int = Query(...),
    db: AsyncSession = Depends(get_db)
):
    existing = await crud.get_citizen_by_discord(db, discord_id)
    if existing:
        raise HTTPException(status_code=400, detail="Вы уже зарегистрированы")

    existing_username = await crud.get_citizen_by_username(db, username)
    if existing_username:
        raise HTTPException(status_code=400, detail="Этот никнейм уже занят")

    minecraft_uuid = await get_minecraft_uuid(username)
    if not minecraft_uuid:
        raise HTTPException(status_code=400, detail="Неверный никнейм Minecraft")

    citizen_role = await crud.get_role_by_name(db, "citizen")
    if not citizen_role:
        raise HTTPException(status_code=500, detail="Роль 'citizen' не найдена в БД")
    role_ids = [citizen_role.id]

    data = {
        "username": username,
        "discord_id": discord_id,
        "minecraft_uuid": minecraft_uuid,
        "role_ids": role_ids,
        "main_role_id": role_ids[0],
        "reputation": 0,
        "is_verified": True,
    }
    await crud.create_citizen(db, data)

    token = create_access_token({"discord_id": discord_id})
    response = RedirectResponse("/", status_code=303)
    response.set_cookie("access_token", token, httponly=True, max_age=ACCESS_TOKEN_EXPIRE_MINUTES * 60, secure=False, samesite="lax")
    response.delete_cookie("pending_discord_id")
    response.delete_cookie("pending_discord_username")
    return response


# ============================================
#  АДМИН-ПАНЕЛЬ (с реальными графиками)
# ============================================

@router.get("/admin", response_class=HTMLResponse)
async def admin_panel(request: Request, db: AsyncSession = Depends(get_db)):
    current_user = await get_current_user(request, db)
    if not current_user:
        return RedirectResponse("/auth/discord")

    role_ids = current_user.role_ids or [1]
    roles = await crud.get_roles_by_ids(db, role_ids)
    max_level = max((r.level for r in roles), default=0)
    if max_level < 95:
        raise HTTPException(status_code=403, detail="Доступ запрещён")

    avatar_url = get_avatar_url(current_user.minecraft_uuid) if current_user.minecraft_uuid else None

    citizens_count = await crud.get_citizens_count(db)
    top_citizens = await crud.get_top_reputation(db, limit=5)

    all_roles = await crud.get_all_roles(db)
    roles_stats = {}
    for role in all_roles:
        roles_stats[role.name] = {"count": 0, "name": role.display_name}

    all_citizens = await crud.get_all_citizens(db, limit=1000)
    for c in all_citizens:
        for rid in (c.role_ids or []):
            for role in all_roles:
                if role.id == rid:
                    roles_stats[role.name]["count"] += 1

    # ===== Реальная история из stats_history =====
    stats_result = await db.execute(
        select(StatsHistory).order_by(StatsHistory.snapshot_at.desc()).limit(24)
    )
    snapshots = list(reversed(stats_result.scalars().all()))

    if len(snapshots) < 2:
        citizens_history = [citizens_count] * 12
        requests_history = [0] * 9
        labels = ["—"] * 12
        requests_labels = ["—"] * 9
    else:
        citizens_history = [s.citizens_count for s in snapshots][-12:]
        requests_history = [s.api_requests for s in snapshots][-9:]
        labels = [s.snapshot_at.strftime("%H:%M") for s in snapshots][-12:]
        requests_labels = [s.snapshot_at.strftime("%H:%M") for s in snapshots][-9:]

    context = {
        "current_user": current_user,
        "avatar_url": avatar_url,
        "citizens_count": citizens_count,
        "top_citizens": top_citizens,
        "roles_stats": roles_stats,
        "citizens_history": citizens_history,
        "requests_history": requests_history,
        "labels": labels,
        "requests_labels": requests_labels,
        "total_requests": sum(requests_history) if requests_history else 0,
        "active_users": citizens_count,
    }
    return templates.TemplateResponse(request=request, name="admin.html", context=context)


# ============================================
#  АДМИНКА: ГРАЖДАНЕ
# ============================================

@router.get("/admin/citizens", response_class=HTMLResponse)
async def admin_citizens(request: Request, db: AsyncSession = Depends(get_db)):
    current_user = await get_current_user(request, db)
    if not current_user:
        return RedirectResponse("/auth/discord")

    role_ids = current_user.role_ids or [1]
    roles = await crud.get_roles_by_ids(db, role_ids)
    max_level = max((r.level for r in roles), default=0)
    if max_level < 95:
        raise HTTPException(status_code=403, detail="Доступ запрещён")

    avatar_url = get_avatar_url(current_user.minecraft_uuid) if current_user.minecraft_uuid else None
    total_count = await crud.get_citizens_count(db)

    context = {
        "current_user": current_user,
        "avatar_url": avatar_url,
        "total_count": total_count,
    }
    return templates.TemplateResponse(request=request, name="admin_citizens.html", context=context)


# ============================================
#  АДМИНКА: РОЛИ
# ============================================

@router.get("/admin/roles", response_class=HTMLResponse)
async def admin_roles_page(request: Request, db: AsyncSession = Depends(get_db)):
    current_user = await get_current_user(request, db)
    if not current_user:
        return RedirectResponse("/auth/discord")

    role_ids = current_user.role_ids or [1]
    roles = await crud.get_roles_by_ids(db, role_ids)
    max_level = max((r.level for r in roles), default=0)
    if max_level < 95:
        raise HTTPException(status_code=403, detail="Доступ запрещён")

    avatar_url = get_avatar_url(current_user.minecraft_uuid) if current_user.minecraft_uuid else None

    context = {
        "current_user": current_user,
        "avatar_url": avatar_url,
    }
    return templates.TemplateResponse(request=request, name="admin_roles.html", context=context)

# ============================================
#  ПУБЛИЧНЫЙ ПРОФИЛЬ
# ============================================

@router.get("/p/{username}", response_class=HTMLResponse)
async def public_citizen_profile(username: str, request: Request, db: AsyncSession = Depends(get_db)):
    current_user = await get_current_user(request, db)
    avatar_url = get_avatar_url(current_user.minecraft_uuid) if current_user and current_user.minecraft_uuid else None

    citizen = await crud.get_citizen_by_username(db, username)
    if not citizen:
        raise HTTPException(status_code=404, detail="Гражданин не найден")

    citizen_avatar = get_avatar_url(citizen.minecraft_uuid) if citizen.minecraft_uuid else None

    role_ids = citizen.role_ids or []
    roles_objects = await crud.get_roles_by_ids(db, role_ids)
    sorted_roles = sorted(roles_objects, key=lambda r: r.level, reverse=True)

    main_role = sorted_roles[0] if sorted_roles else None
    main_role_display = main_role.display_name if main_role else "Гражданин"

    role_names = {r.id: r.display_name for r in sorted_roles}
    sorted_role_ids = [r.id for r in sorted_roles]

    isb_employee = None
    isb_awards = []
    rank_insignia_svg = None

    can_view_isb = False
    if current_user:
        if current_user.id == citizen.id:
            can_view_isb = True
        else:
            viewer_roles = await crud.get_roles_by_ids(db, current_user.role_ids or [1])
            viewer_max_level = max((r.level for r in viewer_roles), default=0)
            if viewer_max_level >= 100:
                can_view_isb = True

    if can_view_isb:
        isb_employee = await crud.get_isb_employee_by_citizen(db, citizen.id)
        if isb_employee:
            isb_awards = await crud.get_employee_awards(db, isb_employee.id)
            rank_insignia_svg = await get_rank_insignia_svg(db, isb_employee.rank_name)

    context = {
        "current_user": current_user,
        "avatar_url": avatar_url,
        "citizen": citizen,
        "citizen_avatar": citizen_avatar,
        "main_role_display": main_role_display,
        "role_names": role_names,
        "sorted_roles": sorted_role_ids,
        "isb_employee": isb_employee,
        "isb_awards": isb_awards,
        "rank_insignia_svg": rank_insignia_svg,
    }
    return templates.TemplateResponse(request=request, name="citizen_profile.html", context=context)


# ============================================
#  СПИСОК ГРАЖДАН
# ============================================

@router.get("/citizens", response_class=HTMLResponse)
async def citizens_list(request: Request, db: AsyncSession = Depends(get_db)):
    current_user = await get_current_user(request, db)
    avatar_url = get_avatar_url(current_user.minecraft_uuid) if current_user and current_user.minecraft_uuid else None

    citizens = await crud.get_all_citizens(db, skip=0, limit=1000)
    all_roles = await crud.get_all_roles(db)
    roles_map = {r.id: r for r in all_roles}

    citizens_data = []
    for c in citizens:
        citizen_roles = [roles_map[rid] for rid in (c.role_ids or []) if rid in roles_map]
        citizen_roles.sort(key=lambda r: r.level, reverse=True)
        main_role = citizen_roles[0] if citizen_roles else None

        citizens_data.append({
            "id": c.id,
            "username": c.username,
            "reputation": c.reputation,
            "main_role": main_role.display_name if main_role else "Гражданин",
            "main_role_level": main_role.level if main_role else 0,
            "avatar_url": get_avatar_url(c.minecraft_uuid) if c.minecraft_uuid else None,
        })

    citizens_data.sort(key=lambda c: (c["main_role_level"], c["reputation"]), reverse=True)

    context = {
        "current_user": current_user,
        "avatar_url": avatar_url,
        "citizens": citizens_data,
        "total": len(citizens_data),
    }
    return templates.TemplateResponse(request=request, name="citizens.html", context=context)

  # ============================================
#  АЛГОРИТМЫ
# ============================================

@router.get("/algorithms", response_class=HTMLResponse)
async def algorithms_list(request: Request, db: AsyncSession = Depends(get_db)):
    """Список алгоритмов"""
    current_user = await get_current_user(request, db)
    avatar_url = get_avatar_url(current_user.minecraft_uuid) if current_user and current_user.minecraft_uuid else None

    context = {
        "current_user": current_user,
        "avatar_url": avatar_url,
    }
    return templates.TemplateResponse(request=request, name="algorithms.html", context=context)


@router.get("/algorithms/{number}", response_class=HTMLResponse)
async def algorithm_detail(number: str, request: Request, db: AsyncSession = Depends(get_db)):
    """Детали алгоритма"""
    current_user = await get_current_user(request, db)
    if not current_user:
        return RedirectResponse("/auth/discord")

    avatar_url = get_avatar_url(current_user.minecraft_uuid) if current_user.minecraft_uuid else None

    # Проверяем существование
    from database import crud_algorithms as algo_crud
    algo = await algo_crud.get_algorithm_by_number(db, number)
    if not algo:
        raise HTTPException(status_code=404, detail="Алгоритм не найден")

    context = {
        "current_user": current_user,
        "avatar_url": avatar_url,
        "algorithm_number": number,
    }
    return templates.TemplateResponse(request=request, name="algorithm_detail.html", context=context)


@router.get("/admin/algorithms", response_class=HTMLResponse)
async def admin_algorithms_page(request: Request, db: AsyncSession = Depends(get_db)):
    """Админка алгоритмов"""
    current_user = await get_current_user(request, db)
    if not current_user:
        return RedirectResponse("/auth/discord")

    # Проверка права
    from auth import has_permission
    if not await has_permission(db, current_user, "view_all_algorithms"):
        raise HTTPException(status_code=403, detail="Доступ запрещён")

    avatar_url = get_avatar_url(current_user.minecraft_uuid) if current_user.minecraft_uuid else None

    context = {
        "current_user": current_user,
        "avatar_url": avatar_url,
    }
    return templates.TemplateResponse(request=request, name="admin_algorithms.html", context=context)

@router.get("/isb/awards", response_class=HTMLResponse)
async def isb_awards_page(request: Request, db: AsyncSession = Depends(get_db)):
    """Публичная витрина наград ИСБ"""
    current_user = await get_current_user(request, db)
    avatar_url = get_avatar_url(current_user.minecraft_uuid) if current_user and current_user.minecraft_uuid else None

    context = {
        "current_user": current_user,
        "avatar_url": avatar_url,
    }
    return templates.TemplateResponse(request=request, name="isb_awards.html", context=context)