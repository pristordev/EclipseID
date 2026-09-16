"""Список званий ИСБ Империи Плиера"""

ISB_RANKS = {
    # ============== ВООРУЖЁННЫЕ СИЛЫ (АРМИЯ) ==============
    "army_private": {
        "rank_name": "Рядовой", "rank_short": "РЯД.",
        "branch": "army", "level": 10,
        "can_arrest": False, "can_conduct_searches": False,
        "can_issue_warrants": False, "can_command": False,
    },
    "army_sergeant": {
        "rank_name": "Старшина", "rank_short": "СТАР.",
        "branch": "army", "level": 20,
        "can_arrest": False, "can_conduct_searches": False,
        "can_issue_warrants": False, "can_command": False,
    },
    "army_lieutenant": {
        "rank_name": "Лейтенант", "rank_short": "ЛЕЙТ.",
        "branch": "army", "level": 30,
        "can_arrest": False, "can_conduct_searches": False,
        "can_issue_warrants": False, "can_command": False,
    },
    "army_captain": {
        "rank_name": "Капитан", "rank_short": "КАП.",
        "branch": "army", "level": 40,
        "can_arrest": True, "can_conduct_searches": False,
        "can_issue_warrants": False, "can_command": True,
    },
    "army_major": {
        "rank_name": "Майор", "rank_short": "МАЙОР",
        "branch": "army", "level": 50,
        "can_arrest": True, "can_conduct_searches": True,
        "can_issue_warrants": False, "can_command": True,
    },
    "army_colonel": {
        "rank_name": "Полковник", "rank_short": "ПОЛК.",
        "branch": "army", "level": 60,
        "can_arrest": True, "can_conduct_searches": True,
        "can_issue_warrants": True, "can_command": True,
    },
    "army_general": {
        "rank_name": "Генерал", "rank_short": "ГЕН.",
        "branch": "army", "level": 70,
        "can_arrest": True, "can_conduct_searches": True,
        "can_issue_warrants": True, "can_command": True,
    },

    # ============== ФЛОТ ==============
    "fleet_cadet": {
        "rank_name": "Кадет", "rank_short": "КАД.",
        "branch": "fleet", "level": 10,
        "can_arrest": False, "can_conduct_searches": False,
        "can_issue_warrants": False, "can_command": False,
    },
    "fleet_ensign": {
        "rank_name": "Мичман", "rank_short": "МИЧ.",
        "branch": "fleet", "level": 20,
        "can_arrest": False, "can_conduct_searches": False,
        "can_issue_warrants": False, "can_command": False,
    },
    "fleet_lieutenant": {
        "rank_name": "Лейтенант флота", "rank_short": "ЛЕЙТ.",
        "branch": "fleet", "level": 30,
        "can_arrest": False, "can_conduct_searches": False,
        "can_issue_warrants": False, "can_command": True,
    },
    "fleet_captain": {
        "rank_name": "Капитан флота", "rank_short": "КАП.",
        "branch": "fleet", "level": 40,
        "can_arrest": True, "can_conduct_searches": False,
        "can_issue_warrants": False, "can_command": True,
    },
    "fleet_commodore": {
        "rank_name": "Коммодор", "rank_short": "КОММ.",
        "branch": "fleet", "level": 50,
        "can_arrest": True, "can_conduct_searches": True,
        "can_issue_warrants": False, "can_command": True,
    },
    "fleet_ml_admiral": {
        "rank_name": "Младший Адмирал", "rank_short": "МЛ. АДМ.",
        "branch": "fleet", "level": 60,
        "can_arrest": True, "can_conduct_searches": True,
        "can_issue_warrants": True, "can_command": True,
    },
    "fleet_admiral": {
        "rank_name": "Адмирал", "rank_short": "АДМ.",
        "branch": "fleet", "level": 70,
        "can_arrest": True, "can_conduct_searches": True,
        "can_issue_warrants": True, "can_command": True,
    },
    "fleet_grand_admiral": {
        "rank_name": "Гранд-Адмирал", "rank_short": "ГРАНД-АДМ.",
        "branch": "fleet", "level": 80,
        "can_arrest": True, "can_conduct_searches": True,
        "can_issue_warrants": True, "can_command": True,
    },

    # ============== РАЗВЕДКА ==============
    "intel_agent": {
        "rank_name": "Агент", "rank_short": "АГ.",
        "branch": "intelligence", "level": 20,
        "can_arrest": False, "can_conduct_searches": False,
        "can_issue_warrants": False, "can_command": False,
    },
    "intel_senior_agent": {
        "rank_name": "Старший агент", "rank_short": "СТ. АГ.",
        "branch": "intelligence", "level": 30,
        "can_arrest": False, "can_conduct_searches": False,
        "can_issue_warrants": False, "can_command": False,
    },
    "intel_handler": {
        "rank_name": "Куратор", "rank_short": "КУР.",
        "branch": "intelligence", "level": 40,
        "can_arrest": False, "can_conduct_searches": False,
        "can_issue_warrants": False, "can_command": True,
    },
    "intel_chief": {
        "rank_name": "Начальник отдела", "rank_short": "НАЧ. ОТД.",
        "branch": "intelligence", "level": 60,
        "can_arrest": True, "can_conduct_searches": True,
        "can_issue_warrants": True, "can_command": True,
    },

    # ============== ИДЕОЛОГИЯ ==============
    "ideo_commissar": {
        "rank_name": "Комиссар", "rank_short": "КОМ.",
        "branch": "ideology", "level": 30,
        "can_arrest": True, "can_conduct_searches": False,
        "can_issue_warrants": False, "can_command": True,
    },
    "ideo_senior_commissar": {
        "rank_name": "Старший комиссар", "rank_short": "СТ. КОМ.",
        "branch": "ideology", "level": 50,
        "can_arrest": True, "can_conduct_searches": True,
        "can_issue_warrants": False, "can_command": True,
    },
    "ideo_political_officer": {
        "rank_name": "Политический офицер", "rank_short": "ПОЛИТ.",
        "branch": "ideology", "level": 60,
        "can_arrest": True, "can_conduct_searches": True,
        "can_issue_warrants": True, "can_command": True,
    },

    # ============== КОМАНДОВАНИЕ ИСБ ==============
    "isb_moff": {
        "rank_name": "Мофф", "rank_short": "МОФФ",
        "branch": "command", "level": 85,
        "can_arrest": True, "can_conduct_searches": True,
        "can_issue_warrants": True, "can_command": True,
    },
    "isb_grand_moff": {
        "rank_name": "Гранд-Мофф", "rank_short": "ГРАНД-МОФФ",
        "branch": "command", "level": 90,
        "can_arrest": True, "can_conduct_searches": True,
        "can_issue_warrants": True, "can_command": True,
    },
    "isb_reim_pretor": {
        "rank_name": "Рейм-Претор", "rank_short": "Р-ПРЕТОР",
        "branch": "command", "level": 100,
        "can_arrest": True, "can_conduct_searches": True,
        "can_issue_warrants": True, "can_command": True,
    },

    # ============== ЦЕНТРАЛЬНЫЙ КОМИТЕТ ==============
    "cc_leader": {
        "rank_name": "Верховный лидер", "rank_short": "ВЕРХ. ЛИД.",
        "branch": "cc", "level": 110,
        "can_arrest": True, "can_conduct_searches": True,
        "can_issue_warrants": True, "can_command": True,
    },
}


# Отображаемые названия веток
BRANCH_NAMES = {
    "army": "Вооружённые силы",
    "fleet": "Флот",
    "intelligence": "Разведка",
    "ideology": "Идеология",
    "command": "Командование",
    "cc": "Центральный комитет",
}

# Иконки веток
BRANCH_ICONS = {
    "army": "⚔️",
    "fleet": "🚀",
    "intelligence": "🕵️",
    "ideology": "📢",
    "command": "👑",
    "cc": "☄️",
}
