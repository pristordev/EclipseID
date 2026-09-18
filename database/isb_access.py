"""Уровни доступа внутри ИСБ"""

RANK_TO_ACCESS = {
    # Вооружённые силы
    "Рядовой": 1, "Старшина": 1,
    "Лейтенант": 2, "Капитан": 2,
    "Майор": 3, "Полковник": 3,
    "Генерал": 4,

    # Флот
    "Кадет": 1, "Мичман": 1,
    "Лейтенант флота": 2, "Капитан флота": 2,
    "Коммодор": 3, "Младший Адмирал": 3,
    "Адмирал": 4, "Гранд-Адмирал": 4,

    # Разведка
    "Агент": 1, "Старший агент": 2,
    "Куратор": 3, "Начальник отдела": 4,

    # Идеология
    "Комиссар": 2, "Старший комиссар": 3,
    "Политический офицер": 4,

    # Командование
    "Мофф": 4, "Гранд-Мофф": 4,
    "Рейм-Претор": 5, "Верховный лидер": 5,
}

ACCESS_NAMES = {
    1: "РЯДОВОЙ",
    2: "ОФИЦЕР",
    3: "СТ. ОФИЦЕР",
    4: "КОМАНДУЮЩИЙ",
    5: "ВЕРХОВНЫЙ",
}


def get_access_level_for_rank(rank_name: str) -> int:
    return RANK_TO_ACCESS.get(rank_name, 1)


def get_access_name(level: int) -> str:
    return ACCESS_NAMES.get(level, "—")


def can_see_all_sectors(level: int) -> bool:
    return level >= 4


def can_see_logs(level: int) -> bool:
    return level >= 2


def can_see_graphs(level: int) -> bool:
    return level >= 3


def can_manage_sectors(level: int) -> bool:
    return level >= 5