import os
from dataclasses import dataclass
from typing import Optional


@dataclass
class Config:
    api_key: str
    log_level: str = "DEBUG"
    log_file: Optional[str] = "werewolf.log"
    num_players: int = 5
    discussion_rounds: int = 2

    @classmethod
    def load(cls):
        return cls(
            api_key=os.getenv("OPENAI_API_KEY", ""),
            log_level=os.getenv("LOG_LEVEL", "DEBUG"),
            log_file=os.getenv("LOG_FILE", "werewolf.log"),
            num_players=int(os.getenv("NUM_PLAYERS", "5")),
            discussion_rounds=int(os.getenv("DISCUSSION_ROUNDS", "2")),
        )
