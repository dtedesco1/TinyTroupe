import json
import logging
import random
from typing import List, Optional

from ai_service import AIPersonaFactory
from models import GameEvent, Player, Role

from tinytroupe.agent import TinyPerson


class AIAgent:
    def __init__(self, player: Player):
        self.player = player
        self.agent: TinyPerson = self._create_agent()

    def _create_agent(self) -> TinyPerson:
        if self.player.role == Role.WEREWOLF:
            return AIPersonaFactory.create_werewolf_persona()
        elif self.player.role == Role.SEER:
            return AIPersonaFactory.create_seer_persona()
        else:
            return AIPersonaFactory.create_villager_persona()

    def generate_accusation(self, players: List[Player]) -> str:
        context = {
            "role": self.player.role.value,
            "alive_players": [p.name for p in players],
            "game_phase": "discussion",
        }
        self.agent.context = context
        self.agent.think(
            "It's your turn to speak during the discussion. "
            "Based on your observations, make an accusation against one player by name "
            "and provide a brief reason."
        )
        response = self.agent.act()
        return response.get("content", self._get_fallback_response())

    def update_memory(self, event: "GameEvent", is_public: bool) -> None:
        if is_public or (
            self.player.role == Role.WEREWOLF and event.type == "werewolf_kill"
        ):
            self.agent.episodic_memory.store(
                {
                    "event_type": event.type,
                    "data": event.data,
                    "day": event.day,
                }
            )

    def get_vote_decision(self, players: List[Player]) -> Optional[Player]:
        candidates = [p.name for p in players if p != self.player]
        context = {
            "role": self.player.role.value,
            "candidates": candidates,
            "memory": self.agent.episodic_memory.retrieve_recent(5),
        }
        self.agent.context = context
        self.agent.think(
            "Analyze the current situation and decide who to vote for. "
            "From the following candidates, choose one by name: "
            f"{', '.join(candidates)}."
        )
        decision = self.agent.act()
        target_name = self.extract_target_from_decision(
            decision.get("content", ""), candidates
        )
        if target_name:
            for p in players:
                if p.name == target_name:
                    return p
        self.logger.warning(
            f"Invalid vote decision from {self.player.name}: {decision}"
        )
        return random.choice([p for p in players if p != self.player])

    def extract_target_from_decision(
        self, content: str, candidates: List[str]
    ) -> Optional[str]:
        for candidate in candidates:
            if candidate.lower() in content.lower():
                return candidate
        return None

    def _get_fallback_response(self) -> str:
        emotions = self.agent.get_current_emotions()
        if emotions.get("fear", 0) > 0.6:
            return "I need more time to think about this..."
        if emotions.get("suspicion", 0) > 0.7:
            return "Something doesn't seem right here..."
        return "Let's consider all possibilities..."

    def act(self) -> dict:
        logger = logging.getLogger("werewolf.ai_agent")
        logger.debug(
            f"Agent {self.agent.name} is about to act with context: {self.agent.context}"
        )

        response = self.agent.act()
        logger.debug(f"Agent response: {response}")

        return response
