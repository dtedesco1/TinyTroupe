import logging
from typing import Dict

from tinytroupe.agent import TinyPerson


class AIPersonaFactory:
    name_counter = 0

    @staticmethod
    def _generate_unique_name(role: str) -> str:
        AIPersonaFactory.name_counter += 1
        return f"Agent_{role}_{AIPersonaFactory.name_counter}"

    @staticmethod
    def create_persona(role: str, traits: Dict[str, float]) -> TinyPerson:
        """Create an AI persona with given traits"""
        unique_name = AIPersonaFactory._generate_unique_name(role)
        agent = TinyPerson(name=unique_name)

        # Log persona creation details
        logger = logging.getLogger("werewolf.ai_service")
        logger.debug(f"Creating persona for role: {role} with traits: {traits}")
        logger.debug(f"Assigned unique name: {unique_name}")

        personality_traits = {
            "Werewolf": {
                "speech_style": "casual and friendly",
                "mannerisms": "relaxed but alert",
                "social_tendency": "engaging but not overly so",
            },
            "Seer": {
                "speech_style": "thoughtful and measured",
                "mannerisms": "observant and careful",
                "social_tendency": "helpful but mysterious",
            },
            "Villager": {
                "speech_style": "direct and earnest",
                "mannerisms": "community-minded",
                "social_tendency": "cooperative and curious",
            },
        }

        agent._configuration.update(
            {
                "personality_traits": list(traits.items()),
                "speech_patterns": personality_traits[role],
                "current_context": [
                    "You are playing a social deduction game.",
                    f"Speak naturally as your character with a {personality_traits[role]['speech_style']} tone.",
                    "Focus on what your character would actually say out loud.",
                    "Keep your true role and thoughts private.",
                    "Use TinyTroupe's response schema to ensure responses include 'role' and 'content'.",
                    'Example: {"role": "assistant", "content": "I suspect Player X."}',
                ],
                "response_schema": {
                    "type": "object",
                    "properties": {
                        "role": {"type": "string"},
                        "content": {"type": "string"},
                    },
                    "required": ["role", "content"],
                },
            }
        )

        # Log updated configuration
        logger.debug(
            f"Updated agent configuration for {unique_name}: {agent._configuration}"
        )

        return agent

    @staticmethod
    def create_werewolf_persona() -> TinyPerson:
        return AIPersonaFactory.create_persona(
            role="Werewolf",
            traits={
                "honesty": 0.3,
                "suspicion": 0.8,
                "aggression": 0.6,
                "deception": 0.9,
            },
        )

    @staticmethod
    def create_villager_persona() -> TinyPerson:
        return AIPersonaFactory.create_persona(
            role="Villager",
            traits={
                "honesty": 0.8,
                "suspicion": 0.6,
                "aggression": 0.4,
                "deception": 0.2,
            },
        )

    @staticmethod
    def create_seer_persona() -> TinyPerson:
        return AIPersonaFactory.create_persona(
            role="Seer",
            traits={
                "honesty": 0.9,
                "suspicion": 0.7,
                "aggression": 0.3,
                "intuition": 0.8,
            },
        )
