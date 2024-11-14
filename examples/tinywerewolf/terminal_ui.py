import os
from typing import List, Optional

from ai_service import AIPersonaFactory
from game import Game
from models import Player, Role


class TerminalUI:
    def __init__(self, game: Game):
        self.game = game

    def clear_screen(self):
        os.system("cls" if os.name == "nt" else "clear")

    def print_header(self, text: str):
        print("\n=== " + text + " ===")

    def select_player(
        self, message: str, eligible_players: List[Player]
    ) -> Optional[Player]:
        print("\n" + message)
        for i, player in enumerate(eligible_players, 1):
            print(f"{i}. {player.name}")

        while True:
            try:
                choice = input("Enter your choice (number) or 'q' to quit: ")
                if choice.lower() == "q":
                    return None
                choice_idx = int(choice) - 1
                if 0 <= choice_idx < len(eligible_players):
                    return eligible_players[choice_idx]
            except ValueError:
                pass
            print("Invalid choice. Please try again.")

    def handle_ai_discussion(
        self, player: Player, living_players: List[Player]
    ) -> None:
        agent = self.game.ai_agents[player.name]
        # Set the agent's context
        agent.agent.context = {
            "phase": "discussion",
            "living_players": [p.name for p in living_players],
            "current_day": self.game.state.current_day,
        }
        # Provide a prompt to the agent
        agent.agent.think(
            "It's your turn to speak during the discussion. Share your thoughts."
        )
        try:
            response = agent.agent.act()  # Removed validate=True

            # Log the AI response
            self.game.logger.debug(
                f"AI Discussion Response from {player.name}: {response}"
            )

            # Extract message content
            message = response.get("content", "...")
        except Exception as e:
            self.game.logger.error(f"AI discussion error for {player.name}: {e}")
            message = "..."
        print(f"\n{player.name}: {message}")
        self.game.add_event("speech", speaker=player.name, message=message)

    def handle_night_phase(self):
        self.clear_screen()
        self.print_header(f"Night {self.game.state.current_day}")
        print("The village falls asleep...")

        # Handle human player night actions
        human = next((p for p in self.game.players if not p.is_ai), None)
        if human and human.is_alive:
            if human.role == Role.WEREWOLF:
                self.handle_human_werewolf()
            elif human.role == Role.SEER:
                self.handle_human_seer()

        victim, investigated = self.game.handle_night_actions()
        if victim:
            print(f"\n{victim.name} was eliminated in the night!")
            self.game.logger.info(f"{victim.name} was eliminated in the night.")

    def handle_human_werewolf(self):
        """Handle human player's werewolf actions"""
        living_players = self.game.get_living_players()
        non_werewolves = [p for p in living_players if p.role != Role.WEREWOLF]

        print("\nYou are a Werewolf! Choose your victim:")
        victim = self.select_player("Select a player to eliminate:", non_werewolves)
        if victim:
            victim.is_alive = False
            print(f"\n{victim.name} was eliminated in the night!")

    def handle_human_seer(self):
        """Handle human player's seer actions"""
        living_players = self.game.get_living_players()
        human = next(p for p in self.game.players if not p.is_ai)
        eligible = [p for p in living_players if p != human]

        print("\nYou are the Seer! Choose a player to investigate:")
        investigated = self.select_player("Select a player to investigate:", eligible)
        if investigated:
            print(f"\n{investigated.name} is a {investigated.role.value}!")
            human.investigated_players.append(investigated)

    def handle_day_phase(self):
        self.clear_screen()
        self.print_header(f"Day {self.game.state.current_day}")
        print("The village wakes up...")

        # Add discussion phase
        self.game.handle_discussion()

        # Add pause to let players read the discussion
        input("\nPress Enter to continue to voting...")

        # Voting phase
        print("\n=== Voting Phase ===")
        living_players = self.game.get_living_players()
        votes = {}

        for player in living_players:
            if not player.is_ai:
                voted = self.select_player(
                    "Select a player to vote out:", living_players
                )
                if voted:
                    votes[player] = voted
            else:
                voted = self.game.get_ai_vote(player)
                if voted:
                    votes[player] = voted

        eliminated = self.game.handle_day_voting(votes)
        if eliminated:
            print(
                f"\n{eliminated.name} was voted out and was a {eliminated.role.value}!"
            )

        # Add pause before next phase
        input("\nPress Enter to continue...")

    def run(self):
        self.game.setup_game()

        # Show initial game state
        print("\nGame begins! Here are the players:")
        for player in self.game.players:
            if not player.is_ai:
                print(f"You are a {player.role.value}")
            else:
                print(f"{player.name} has joined the game")

        input("\nPress Enter to begin the first night...")

        while not self.game.is_game_over:
            self.handle_night_phase()
            self.handle_day_phase()

            result = self.game.check_game_over()
            if result:
                print(f"\nGame Over! {result}")
                self.game.is_game_over = True
                # Show game summary
                print("\nGame Summary:")
                print(f"Total days: {self.game.state.current_day}")
                living = [p.name for p in self.game.get_living_players()]
                print(f"Survivors: {', '.join(living)}")
                self.game.logger.info(f"Game Over: {result}")
                self.game.logger.info(
                    f"Game Summary: Days - {self.game.state.current_day}, Survivors - {', '.join(living)}"
                )

        if input("\nPlay again? (y/n): ").lower() == "y":
            self.game = Game(self.game.config)  # Pass the existing config
            self.run()
