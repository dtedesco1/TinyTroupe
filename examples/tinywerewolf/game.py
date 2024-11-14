import logging
import random
from typing import Dict, List, Optional, Tuple

from ai_agent import AIAgent
from models import GameEvent, Player, Role

from tinytroupe.agent import TinyPerson
from tinytroupe.control import Simulation, begin, end


class GameState:
    def __init__(self):
        self.current_day: int = 1
        self.events: List[GameEvent] = []
        self.last_eliminated: Optional[Player] = None
        self.votes: Dict[Player, Player] = {}


class Game:
    def __init__(self, config):
        self.players: List[Player] = []
        self.state = GameState()
        self.is_game_over = False
        self.ai_agents: Dict[str, AIAgent] = {}
        self.logger = logging.getLogger("werewolf")
        self.discussion_rounds = 2

        self.config = config

        # Initialize TinyTroupe Simulation
        self.simulation = Simulation()  # Uses "default" as ID
        begin(auto_checkpoint=True)
        TinyPerson.clear_agents()  # Ensure no leftover agents

    def get_living_players(self) -> List[Player]:
        return [p for p in self.players if p.is_alive]

    def setup_game(self):
        human_name = input("Enter your name: ")
        self.players = [Player(human_name, Role.VILLAGER, is_ai=False)]

        # Add 4 AI players with appropriate roles
        roles = [Role.WEREWOLF, Role.WEREWOLF, Role.SEER] + [Role.VILLAGER] * (
            self.config.num_players - 3
        )
        random.shuffle(roles)

        for i in range(4):
            role = roles[i]
            ai_player = Player(f"AI_{i+1}", role)
            self.players.append(ai_player)

        # Initialize AI agents using AIAgent and TinyTroupe's Simulation
        for player in self.players:
            if player.is_ai:
                agent = AIAgent(player)
                self.ai_agents[player.name] = agent
                self.simulation.add_agent(agent.agent)  # Add TinyPerson to simulation

    def add_event(self, event_type: str, **data) -> None:
        event = GameEvent(event_type, data, self.state.current_day)
        self.state.events.append(event)

        # Update AI agent memories appropriately
        for agent in self.ai_agents.values():
            is_public = event_type in [
                "accusation",
                "defense",
                "death",
                "voting_results",
                "speech",
                "ai_response",
                "information",
                "response",
                "werewolf_kill",  # Werewolf kill is known to werewolves
            ]
            agent.update_memory(event, is_public)

        # Log for debugging only
        self.logger.debug(f"Day {self.state.current_day}: {event_type} - {data}")

    def handle_night_actions(self) -> Tuple[Optional[Player], Optional[Player]]:
        """Returns (victim, investigated_player)"""
        living_players = self.get_living_players()
        werewolves = [p for p in living_players if p.role == Role.WEREWOLF]
        non_werewolves = [p for p in living_players if p.role != Role.WEREWOLF]

        victim = None
        investigated = None

        if werewolves and non_werewolves:
            wolf_players = [w for w in werewolves if w.is_ai]
            if wolf_players:
                # Get collective werewolf decision through their agents
                votes = {}
                for wolf in wolf_players:
                    agent = self.ai_agents[wolf.name]
                    voted = agent.get_vote_decision(non_werewolves)
                    votes[voted] = votes.get(voted, 0) + 1

                if votes:
                    victim = max(votes.items(), key=lambda x: x[1])[0]
                    victim.is_alive = False
                    self.add_event("werewolf_kill", victim=victim.name)

        seer = next((p for p in living_players if p.role == Role.SEER), None)
        if seer and seer.is_alive and seer.is_ai:
            investigated = random.choice([p for p in living_players if p != seer])
            seer.investigated_players.append(investigated)

        return victim, investigated

    def handle_day_voting(self, votes: Dict[Player, Player]) -> Player:
        """Process votes and return the eliminated player"""
        self.state.votes = votes
        vote_count = {}

        # Count votes properly
        for voter, voted in votes.items():
            if voted not in vote_count:
                vote_count[voted] = []
            vote_count[voted].append(voter)

        # Find player with most votes
        eliminated = max(vote_count.items(), key=lambda x: len(x[1]))[0]

        # Log voting results
        vote_summary = {
            player.name: [v.name for v in voters]
            for player, voters in vote_count.items()
        }
        self.add_event("voting_results", votes=vote_summary)

        # Mark player as eliminated
        eliminated.is_alive = False
        self.state.last_eliminated = eliminated

        return eliminated

    def handle_discussion(self) -> None:
        """Handle the discussion phase before voting"""
        print("\n=== Discussion Phase ===")
        print(f"Day {self.state.current_day} - Each player will speak in turn.")
        print(f"There will be {self.discussion_rounds} rounds of discussion.")

        living_players = self.get_living_players()
        for round_num in range(self.discussion_rounds):
            print(f"\n--- Discussion Round {round_num + 1} ---")

            # Shuffle players to randomize speaking order
            random.shuffle(living_players)

            for speaker in living_players:
                print(f"\n{speaker.name}'s turn to speak:")

                if not speaker.is_ai:
                    self._handle_human_discussion(speaker, living_players)
                else:
                    self._handle_ai_discussion(speaker, living_players)

                # Allow others to respond
                self._handle_responses(speaker, living_players)

    def _handle_human_discussion(
        self, player: Player, living_players: List[Player]
    ) -> None:
        """Handle human player's discussion options"""
        print("\nChoose your action:")
        print("1. Make an accusation")
        print("2. Defend yourself")
        print("3. Share information")
        print("4. Pass")

        choice = input("Your choice (1-4): ")
        if choice == "1":
            target = self.select_player("Who do you accuse?", living_players)
            message = input("State your accusation: ")
            self.add_event(
                "accusation", accuser=player.name, target=target.name, message=message
            )
        elif choice == "2":
            message = input("State your defense: ")
            self.add_event("defense", player=player.name, message=message)
        elif choice == "3":
            message = input("What information do you want to share? ")
            self.add_event("information", player=player.name, message=message)

    def _handle_ai_discussion(
        self, player: Player, living_players: List[Player]
    ) -> None:
        agent = self.ai_agents[player.name]
        # Set the agent's context
        agent.agent.context = {
            "phase": "discussion",
            "living_players": [p.name for p in living_players],
            "current_day": self.state.current_day,
        }
        # Provide a prompt to the agent
        agent.agent.think(
            "It's your turn to speak during the discussion. Share your thoughts."
        )
        try:
            agent_response = agent.act()  # Response is already validated

            message = agent_response.get("content", "...")
            print(f"\n{player.name}: {message}")
            self.add_event("speech", speaker=player.name, message=message)
        except Exception as e:
            self.logger.error(f"AI discussion error for {player.name}: {e}")
            print(f"\n{player.name}: [Error in AI response]")
            self.add_event(
                "speech", speaker=player.name, message="[Error in AI response]"
            )

    def _handle_responses(self, speaker: Player, living_players: List[Player]) -> None:
        for responder in [p for p in living_players if p != speaker]:
            if not responder.is_ai:
                print(f"\nWould you like to respond to {speaker.name}?")
                if input("Respond? (y/n): ").lower() == "y":
                    message = input("Your response: ")
                    self.add_event(
                        "response",
                        responder=responder.name,
                        target=speaker.name,
                        message=message,
                    )
                continue

            # Decide whether the AI should respond (e.g., 30% chance)
            if random.random() < 0.3:
                agent = self.ai_agents[responder.name]
                # Set the agent's context
                agent.agent.context = {
                    "phase": "discussion",
                    "speaker": speaker.name,
                    "speaker_message": self.get_last_message_from(speaker.name),
                    "current_day": self.state.current_day,
                }
                # Provide a prompt to the agent
                agent.agent.think(f"{speaker.name} just spoke. Do you have a response?")
                try:
                    agent_response = agent.act()

                    # Log the AI response structure
                    self.logger.debug(
                        f"AI Response from {responder.name}: {agent_response}"
                    )

                    if not isinstance(agent_response, dict):
                        self.logger.error(
                            f"Invalid AI response format from {responder.name}: {agent_response}"
                        )
                        raise ValueError("Invalid AI response format")

                    message = agent_response.get("content", "...")
                    print(f"{responder.name} responds: {message}")
                    self.add_event(
                        "ai_response",
                        responder=responder.name,
                        target=speaker.name,
                        message=message,
                    )
                except KeyError as e:
                    self.logger.error(
                        f"Missing key in AI response from {responder.name}: {e}"
                    )
                    print(f"{responder.name} responds: [Error in AI response]")
                    self.add_event(
                        "ai_response",
                        responder=responder.name,
                        target=speaker.name,
                        message="[Error in AI response]",
                    )
                except ValueError as e:
                    self.logger.error(
                        f"ValueError in AI response from {responder.name}: {e}"
                    )
                    print(f"{responder.name} responds: [Error in AI response]")
                    self.add_event(
                        "ai_response",
                        responder=responder.name,
                        target=speaker.name,
                        message="[Error in AI response]",
                    )

    def get_last_message_from(self, player_name: str) -> str:
        """Retrieve the last message from a specified player."""
        for event in reversed(self.state.events):
            if (
                event.type in ["speech", "ai_response", "response"]
                and event.data.get("speaker") == player_name
            ):
                return event.data.get("message", "")
        return ""

    def day_phase(self):
        print(f"\n=== Day {self.state.current_day} ===")
        print("The village wakes up...")

        living_players = self.get_living_players()
        if not living_players:
            return

        # Add discussion phase before voting
        self.handle_discussion()

        # Voting phase
        print("\n=== Voting Phase ===")
        votes = {}

        # Simple voting mechanism
        print("\nTime to vote someone out!")
        votes = {}

        for player in living_players:
            if not player.is_ai:
                voted = self.select_player(
                    "Select a player to vote out:", living_players
                )
                votes[voted] = votes.get(voted, 0) + 1
            else:
                # Simple AI voting: random
                voted = random.choice(living_players)
                votes[voted] = votes.get(voted, 0) + 1

        # Find player with most votes
        voted_out = max(votes.items(), key=lambda x: x[1])[0]
        voted_out.is_alive = False
        print(f"\n{voted_out.name} was voted out and was a {voted_out.role.value}!")

        self.state.current_day += 1

    def check_game_over(self) -> Optional[str]:
        werewolves = sum(
            1 for p in self.players if p.is_alive and p.role == Role.WEREWOLF
        )
        villagers = sum(
            1 for p in self.players if p.is_alive and p.role != Role.WEREWOLF
        )

        if werewolves == 0:
            return "Villagers win!"
        if werewolves >= villagers:
            return "Werewolves win!"
        return None

    def cleanup(self):
        """Clean up TinyPerson agents when game ends"""
        try:
            end()  # Uses "default" by default
        finally:
            TinyPerson.clear_agents()
            self.ai_agents.clear()

    def run(self):
        try:
            self.setup_game()
            while not self.is_game_over:
                self.night_phase()
                self.day_phase()

                result = self.check_game_over()
                if result:
                    print(f"\nGame Over! {result}")
                    self.is_game_over = True
        finally:
            self.cleanup()

    def get_ai_vote(self, player: Player) -> Player:
        """Get vote decision from AI agent"""
        if player.name in self.ai_agents:
            return self.ai_agents[player.name].get_vote_decision(
                self.get_living_players()
            )
        return random.choice(self.get_living_players())
