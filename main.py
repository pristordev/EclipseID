from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from contextlib import asynccontextmanager
from pathlib import Path
from contextlib import asynccontextmanager
import asyncio

from database.db import async_engine, Base
from database import crud

# Импортируем все роутеры
from routers import pages, citizens, stats, system, admin_roles, admin_isb, search, algorithms, isb_panel

from fastapi.templating import Jinja2Templates


# ============================================
#  LIFESPAN
# ============================================
async def snapshot_loop():
    """Фоновый цикл: снимок каждые 30 минут"""
    from database.db import AsyncSessionLocal
    from utils.stats_snapshot import create_snapshot

    while True:
        try:
            async with AsyncSessionLocal() as db:
                await create_snapshot(db)
                print("📊 Снимок статистики создан")
        except Exception as e:
            print(f"⚠️ Ошибка снимка: {e}")

        await asyncio.sleep(30 * 60)  # 30 минут


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Запускаем фоновый цикл
    task = asyncio.create_task(snapshot_loop())

    # Пишем лог о старте системы
    try:
        async with AsyncSessionLocal() as db:
            await crud.create_isb_log(
                db,
                message="СИСТЕМА ИНИЦИАЛИЗИРОВАНА · ПАНЕЛЬ ИСБ АКТИВНА",
                severity="info",
                category="system",
            )
    except Exception as e:
        print(f"⚠️ Не удалось записать стартовый лог: {e}")
  
    yield

    # Shutdown
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass

    await async_engine.dispose()


# ============================================
#  APP
# ============================================

app = FastAPI(
    title="EclipseID API",
    description="Цифровая экосистема Империи Плиера",
    version="1.0.0",
    lifespan=lifespan,
)

BASE_DIR = Path(__file__).resolve().parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

# Подключаем статику
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")

# Подключаем роутеры
app.include_router(pages.router)
app.include_router(citizens.router)
app.include_router(stats.router)
app.include_router(system.router)
app.include_router(admin_roles.router)
app.include_router(admin_isb.router)
app.include_router(search.router)
app.include_router(algorithms.router)
app.include_router(isb_panel.router)

# ============================================
#  ОБРАБОТКА ОШИБОК
# ============================================

@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    """Обработка HTTP-ошибок (404, 403, 500 и т.д.)"""
    # Если это API-запрос — отдаём JSON
    if request.url.path.startswith("/api/"):
        return JSONResponse(
            status_code=exc.status_code,
            content={"status": "error", "detail": exc.detail}
        )

    if exc.status_code == 404:
        user, avatar = await get_user_for_error(request)
        return templates.TemplateResponse(
            request=request, name="404.html",
            context={"current_user": user, "avatar_url": avatar}, status_code=404
    )

    if exc.status_code == 500:
        user, avatar = await get_user_for_error(request)
        return templates.TemplateResponse(
            request=request, name="500.html",
            context={"current_user": user, "avatar_url": avatar}, status_code=500
        )

    # Для остальных кодов (403, 401 и т.д.) — стандартный ответ
    return JSONResponse(
        status_code=exc.status_code,
        content={"status": "error", "detail": exc.detail}
    )

async def get_user_for_error(request: Request):
    """Получить пользователя и аватар для страниц ошибок"""
    from database.db import AsyncSessionLocal
    from database import crud
    from auth.jwt import verify_token
    from utils.avatars import get_avatar_url

    token = request.cookies.get("access_token")
    discord_id = verify_token(token) if token else None
    if not discord_id:
        return None, None

    async with AsyncSessionLocal() as db:
        citizen = await crud.get_citizen_by_discord(db, int(discord_id))
        if not citizen:
            return None, None
        avatar_url = get_avatar_url(citizen.minecraft_uuid) if citizen.minecraft_uuid else None
        return citizen, avatar_url

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Обработка ошибок валидации (неправильные параметры)"""
    if request.url.path.startswith("/api/"):
        return JSONResponse(
            status_code=422,
            content={"status": "error", "detail": exc.errors()}
        )
    return JSONResponse(
        status_code=422,
        content={"status": "error", "detail": exc.errors()}
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
