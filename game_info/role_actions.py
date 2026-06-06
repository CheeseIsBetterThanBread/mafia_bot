from enum import Enum


class NightAction(str, Enum):
    ALIBI = "alibi"
    DON_CHECK = "don_check"
    HEAL = "heal"
    MANIAC_HEAL = "maniac_heal"
    MANIAC_KILL = "maniac_kill"
    ROB = "rob"
    SHERIFF_CHECK = "sheriff_check"
    SHURIKEN = "shuriken"
    TULA = "tula"
    TWO_FACE_CHECK = "two_face_check"
    TWO_FACE_KILL = "two_face_kill"
    VOTE = "vote"


ROLE_NIGHT_ACTIONS = {
    "Мафия": [
        (
            NightAction.VOTE,
            "Выберите игрока для убийства",
        )
    ],
    "Дон": [
        (
            NightAction.VOTE,
            "Выберите игрока для убийства",
        ),
        (
            NightAction.DON_CHECK,
            "Выберите игрока для проверки на шерифа",
        ),
    ],
    "Адвокат": [
        (
            NightAction.VOTE,
            "Выберите игрока для убийства",
        ),
        (
            NightAction.ALIBI,
            "Выберите игрока, который получит алиби",
        ),
    ],
    "Ниндзя": [
        (
            NightAction.VOTE,
            "Выберите игрока для убийства",
        ),
        (
            NightAction.SHURIKEN,
            "Выберите игрока, в которого кинуть сюрикен",
        ),
    ],
    "Вор": [
        (
            NightAction.ROB,
            "Выберите игрока для склейки",
        )
    ],
    "Доктор": [
        (
            NightAction.HEAL,
            "Выберите игрока для лечения",
        )
    ],
    "Тула": [
        (
            NightAction.TULA,
            "Выберите игрока, к которому пойдете (хил + алиби)",
        )
    ],
    "Шериф": [
        (
            NightAction.SHERIFF_CHECK,
            "Выберите игрока для проверки на мафию",
        )
    ],
    "Маньяк без бинтов": [
        (
            NightAction.MANIAC_KILL,
            "Выберите игрока для убийства",
        )
    ],
    "Маньяк с бинтами": [
        (
            NightAction.MANIAC_KILL,
            "Выберите игрока для убийства",
        ),
        (
            NightAction.MANIAC_HEAL,
            "Лечить себя",
        ),
    ],
    "Двуликий": [
        (
            NightAction.TWO_FACE_CHECK,
            "Выберите игрока для проверки на мафию",
        ),
        (
            NightAction.TWO_FACE_KILL,
            "Выберите игрока для убийства",
        ),
    ],
}
