"""
Seed-скрипт: заполнение таблицы isb_awards наградами ИСБ.
Запуск: python -m seeds.awards  (из корня проекта)
"""
import sys
import os
import asyncio

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.db import AsyncSessionLocal
from database.models import ISBAward
from sqlalchemy import select


AWARDS = [
    # ---------- COMMON ----------
    {"name": "recruit_badge", "display_name": "Знак новобранца", "icon": "🎖️",
     "rarity": "common", "category": "За службу",
     "description": "Выдаётся каждому, кто вступил в ряды ИСБ и прошёл базовую подготовку."},
    {"name": "service_1y", "display_name": "Медаль «За год службы»", "icon": "🕐",
     "rarity": "common", "category": "За службу",
     "description": "Год верной службы на благо Империи."},
    {"name": "perfect_attendance", "display_name": "Знак «Без нареканий»", "icon": "✅",
     "rarity": "common", "category": "За службу",
     "description": "Ни одного замечания за последние 6 месяцев службы."},

    # ---------- UNCOMMON ----------
    {"name": "medal_of_valor", "display_name": "Медаль «За отвагу»", "icon": "⚔️",
     "rarity": "uncommon", "category": "Боевая",
     "description": "За проявленную отвагу в ходе боевой операции."},
    {"name": "marksman_badge", "display_name": "Знак «Снайпер»", "icon": "🎯",
     "rarity": "uncommon", "category": "Боевая",
     "description": "За выдающиеся навыки в стрельбе."},
    {"name": "service_5y", "display_name": "Медаль «За пять лет службы»", "icon": "🏅",
     "rarity": "uncommon", "category": "За службу",
     "description": "Пять лет верной службы Империи."},

    # ---------- RARE ----------
    {"name": "medal_of_honor", "display_name": "Орден Чести", "icon": "🏆",
     "rarity": "rare", "category": "Боевая",
     "description": "За исключительную храбрость и самопожертвование перед лицом врага."},
    {"name": "intelligence_star", "display_name": "Звезда разведки", "icon": "🌟",
     "rarity": "rare", "category": "Особая",
     "description": "За успешную разведывательную операцию государственного значения."},
    {"name": "order_of_merit", "display_name": "Орден «За заслуги»", "icon": "📜",
     "rarity": "rare", "category": "За службу",
     "description": "За значительный вклад в развитие ИСБ и защиту Империи."},

    # ---------- EPIC ----------
    {"name": "order_of_empire", "display_name": "Орден Империи", "icon": "👑",
     "rarity": "epic", "category": "Особая",
     "description": "Высшая награда за заслуги перед Империей. Вручается лично Императором."},
    {"name": "hero_of_pliera", "display_name": "Герой Плиера", "icon": "🔥",
     "rarity": "epic", "category": "Боевая",
     "description": "За подвиг, спасший жизни граждан или ключевые территории Империи."},

    # ---------- LEGENDARY ----------
    {"name": "grand_cross", "display_name": "Большой Крест ИСБ", "icon": "💎",
     "rarity": "legendary", "category": "Особая",
     "description": "Наивысшая награда Имперской службы безопасности. Вручается только один раз в поколение."},
]


async def seed_awards():
    async with AsyncSessionLocal() as db:
        for a in AWARDS:
            result = await db.execute(select(ISBAward).where(ISBAward.name == a["name"]))
            existing = result.scalar_one_or_none()
            if existing:
                for k, v in a.items():
                    setattr(existing, k, v)
            else:
                db.add(ISBAward(**a))
        await db.commit()
        print(f"✅ Загружено {len(AWARDS)} наград ИСБ")


if __name__ == "__main__":
    asyncio.run(seed_awards())
