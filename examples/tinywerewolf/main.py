import os
import sys

from config import Config
from game import Game
from logger import setup_logger
from terminal_ui import TerminalUI


def main():
    # Load configuration
    config = Config.load()

    # Check for API key
    if not config.api_key:
        print("Error: OPENAI_API_KEY environment variable not set")
        sys.exit(1)

    # Setup logging
    logger = setup_logger(config)
    logger.info("Starting Werewolf game")

    # Ensure the cache directory exists
    os.makedirs("./tinytroupe_cache", exist_ok=True)

    try:
        # Initialize game
        game = Game(config)
        ui = TerminalUI(game)

        # Start game loop
        ui.run()

    except KeyboardInterrupt:
        print("\nGame terminated by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        raise


if __name__ == "__main__":
    main()
