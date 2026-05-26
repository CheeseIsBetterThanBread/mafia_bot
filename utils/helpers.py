from collections import deque

from engine.models import Player


def rotate_queue(players: list[Player], start_number: int):
    queue = deque(players)

    for i, p in enumerate(players):
        if p.number >= start_number:
            queue.rotate(-i)
            return queue, p.number

    return queue, players[0].number


def alive_sorted(players: list[Player]):
    return sorted(players, key=lambda p: p.number)
