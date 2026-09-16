from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
from pathlib import Path

from database.db import async_engine, Base

# Импортируем все роутеры
from routers import pages, citizens, stats, system, admin_roles, admin_isb, search


# ============================================
#  LIFESPAN
# ============================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: создаём таблицы, если их нет
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    # Shutdown
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


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
