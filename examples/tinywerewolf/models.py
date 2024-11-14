from dataclasses import dataclass
from enum import Enum
from typing import List


class Role(Enum):
    VILLAGER = "Villager"
    WEREWOLF = "Werewolf"
    SEER = "Seer"


class Player:
    def __init__(self, name: str, role: Role, is_ai: bool = True):
        self.name = name
        self.role = role
        self.is_ai = is_ai
        self.is_alive = True
        self.events_memory: List["GameEvent"] = []
        self.investigated_players: List[Player] = []


@dataclass
class GameEvent:
    type: str
    data: dict
    day: int
