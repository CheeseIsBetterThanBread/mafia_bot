from game_info.presets import ROOM_PRESETS, SPECIAL_PRESETS


def create_room_and_id_map() -> tuple[dict[tuple, int], dict[int, list[str]]]:
    current_id: int = 0
    room_to_id: dict[tuple, int] = {}
    id_to_room: dict[int, list[str]] = {}

    for room_array in ROOM_PRESETS.values():
        for room in room_array:
            key = tuple(sorted(room))
            if key not in room_to_id.keys():
                room_to_id[key] = current_id
                id_to_room[current_id] = room
                current_id += 1

    for room in SPECIAL_PRESETS.values():
        key = tuple(sorted(room))
        if key not in room_to_id.keys():
            room_to_id[key] = current_id
            id_to_room[current_id] = room
            current_id += 1

    return room_to_id, id_to_room


ROOM_TO_ID, ID_TO_ROOM = create_room_and_id_map()


def get_room_id(room: list[str]) -> int:
    key = tuple(sorted(room))
    assert key in ROOM_TO_ID.keys()
    return ROOM_TO_ID[key]


def get_room_by_id(room_id: int) -> list[str]:
    assert room_id in ID_TO_ROOM.keys()
    return ID_TO_ROOM[room_id]
