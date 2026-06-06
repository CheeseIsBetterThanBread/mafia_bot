from game_info.presets import ROOM_PRESETS, SPECIAL_PRESETS


def create_room_to_id_map() -> dict[tuple, int]:
    current_id: int = 0
    result: dict[tuple, int] = {}

    for room_array in ROOM_PRESETS.values():
        for room in room_array:
            key = tuple(sorted(room))
            if key not in result.keys():
                result[key] = current_id
                current_id += 1

    for room in SPECIAL_PRESETS.values():
        key = tuple(sorted(room))
        if key not in result.keys():
            result[key] = current_id
            current_id += 1

    return result


ROOM_TO_ID: dict[tuple, int] = create_room_to_id_map()


def get_room_id(room: list[str]) -> int:
    key = tuple(sorted(room))
    assert key in ROOM_TO_ID.keys()
    return ROOM_TO_ID[key]
