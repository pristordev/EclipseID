"""
Seed-скрипт: заполнение таблицы isb_rank_insignia паттернами званий.
Запуск: python -m seeds.insignia  (из корня проекта)
"""
import sys
import os
import asyncio
import json

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.db import AsyncSessionLocal
from sqlalchemy import text


# Цвета: y = yellow (жёлтый), b = blue (синий), r = red (красный)
# Паттерн — список рядов, каждый ряд — список цветов

ISB_INSIGNIA = {
    # ---------- ВООРУЖЁННЫЕ СИЛЫ ----------
    "Рядовой":              [["b"]],
    "Старшина":             [["r"]],
    "Лейтенант":            [["r", "b"]],
    "Капитан":              [["b", "b"], ["b", "r"]],
    "Майор":                [["r", "r"], ["r", "b"]],
    "Полковник":            [["r", "r"], ["b", "b"]],
    "Генерал":              [["r", "r"], ["b", "b"]],

    # ---------- ФЛОТ ----------
    "Кадет":                [["b"]],
    "Мичман":               [["b", "b"]],
    "Лейтенант флота":      [["b", "r"]],
    "Капитан флота":        [["b", "b"], ["b", "r"]],
    "Коммодор":             [["b", "b"], ["r", "b"]],
    "Младший Адмирал":      [["b", "b"], ["b", "r"]],
    "Адмирал":              [["b", "b", "b"], ["y", "y", "r"]],
    "Гранд-Адмирал":        [["b", "b", "b"], ["y", "y", "r"]],

    # ---------- РАЗВЕДКА ----------
    "Агент":                [["b"]],
    "Старший агент":        [["b", "b"]],
    "Куратор":              [["b", "r"]],
    "Начальник отдела":     [["b", "b"], ["r", "b"]],

    # ---------- ИДЕОЛОГИЯ ----------
    "Комиссар":             [["r", "r"]],
    "Старший комиссар":     [["r", "b"]],
    "Политический офицер":  [["r", "r"], ["b", "r"]],

    # ---------- КОМАНДОВАНИЕ ----------
    "Мофф":                 [["r", "r", "r"], ["b", "y", "y"]],
    "Гранд-Мофф":           [["b", "b", "r", "r"], ["r", "r", "y", "y"]],
    "Рейм-Претор":          [["y", "b"], ["r", "r"]],

    # ---------- ЦЕНТРАЛЬНЫЙ КОМИТЕТ ----------
    "Верховный лидер":      [["y", "y", "b", "b"], ["r", "r", "y", "y"]],
}


async def seed_insignia():
    async with AsyncSessionLocal() as db:
        # Создаём таблицу, если нет
        await db.execute(text("""
            CREATE TABLE IF NOT EXISTS isb_rank_insignia (
                id SERIAL PRIMARY KEY,
                rank_name VARCHAR(100) UNIQUE NOT NULL,
                pattern JSONB NOT NULL,
                created_at TIMESTAMP DEFAULT NOW()
            )
        """))
        await db.commit()

        for rank_name, pattern in ISB_INSIGNIA.items():
            await db.execute(text("""
                INSERT INTO isb_rank_insignia (rank_name, pattern)
                VALUES (:rank_name, :pattern)
                ON CONFLICT (rank_name) DO UPDATE SET pattern = EXCLUDED.pattern
            """), {"rank_name": rank_name, "pattern": json.dumps(pattern)})
        await db.commit()
        print(f"✅ Загружено {len(ISB_INSIGNIA)} паттернов званий")


if __name__ == "__main__":
    asyncio.run(seed_insignia())
