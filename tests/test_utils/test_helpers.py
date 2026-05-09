from random import shuffle

import pytest

from utils.helpers import (
    alive_sorted,
    rotate_queue,
    Player
)


@pytest.fixture
def raw_players():
    ids_and_usernames = [
        (3, "Chuck"),
        (2, "Bob"),
        (5, "Eve"),
        (1, "Alice"),
        (4, "Daniel")
    ]
    return ids_and_usernames

@pytest.fixture
def players(raw_players):
    array = []
    for index, (id_, name) in enumerate(raw_players):
        array.append(Player(id_, name, index + 1))

    return array


def test_alive_sorted(players):
    players_copy = players.copy()
    attempts = 10

    for _ in range(attempts):
        shuffle(players_copy)
        assert alive_sorted(players_copy) == players


def test_rotate_queue(players):
    def next_number(number: int):
        number += 1
        if number > len(players):
            number = 1
        return number

    # nothing should change
    _, start = rotate_queue(players, len(players) + 1)
    assert start == players[0].number

    # check rotation
    expected_start = 2
    queue, start = rotate_queue(players, expected_start)
    assert expected_start == start
    last = queue.popleft()
    while queue:
        current = queue.popleft()
        assert current.number == next_number(last.number)
        last = current

    # check start
    expected_start = 3
    sparse_players = [p for p in players if p.number != expected_start]
    _, start = rotate_queue(sparse_players, expected_start)
    assert start > expected_start
