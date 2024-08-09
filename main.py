from tetris import TetrisGame
from flappyBird import FlappyBirdGame
from rogueLikeShooter import ShooterRoguelike


def main():
    game_choice = input("Select a game (Tetris, FlappyBird, Shooter): ").strip().lower()

    if game_choice == "tetris":
        game = TetrisGame(20, 24)
    elif game_choice == "flappybird":
        game = FlappyBirdGame(40, 20)
    elif game_choice == "shooter":
        game = ShooterRoguelike(40, 24)
    else:
        print("Unknown game selected.")
        return

    game.run()


if __name__ == "__main__":
    main()
