from game_info.presets import ROOM_PRESETS, SPECIAL_PRESETS


def create_room_and_id_map() -> dict[tuple, int]:
    current_id: int = 0
    room_to_id: dict[tuple, int] = {}

    for room_array in ROOM_PRESETS.values():
        for room in room_array:
            key = tuple(sorted(room))
            if key not in room_to_id.keys():
                room_to_id[key] = current_id
                current_id += 1

    for room in SPECIAL_PRESETS.values():
        key = tuple(sorted(room))
        if key not in room_to_id.keys():
            room_to_id[key] = current_id
            current_id += 1

    return room_to_id


ROOM_TO_ID = create_room_and_id_map()


def get_room_id(room: list[str]) -> int:
    key = tuple(sorted(room))
    assert key in ROOM_TO_ID.keys()
    return ROOM_TO_ID[key]
