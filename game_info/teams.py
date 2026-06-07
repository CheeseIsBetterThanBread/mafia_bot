from enum import Enum


class Team(str, Enum):
    CITIZEN = "citizen"
    FLUID = "fluid"
    MAFIA = "mafia"
    MANIAC = "maniac"


ROLE_TO_TEAM = {
    "Мирный житель": Team.CITIZEN,
    "Мафия": Team.MAFIA,
    "Дон": Team.MAFIA,
    "Адвокат": Team.MAFIA,
    "Ниндзя": Team.MAFIA,
    "Вор": Team.CITIZEN,
    "Доктор": Team.CITIZEN,
    "Тула": Team.CITIZEN,
    "Шериф": Team.CITIZEN,
    "Маньяк без бинтов": Team.MANIAC,
    "Маньяк с бинтами": Team.MANIAC,
    "Двуликий": Team.FLUID,
    "Бессмертный": Team.CITIZEN,
}
