import time
import os
import sys
import select
import threading
import math
import atexit
import random
from typing import List, Tuple, Optional, Set
import numpy as np

if os.name == "nt":
    import msvcrt
else:
    import termios
    import tty


class TerminalEngine:
    def __init__(self, width: int, height: int, tick_rate: int = 60, max_fps: int = 60):
        self.width: int = width
        self.height: int = height
        self.buffer: np.ndarray = np.full((height, width), " ", dtype=str)
        self.prev_buffer: np.ndarray = np.full((height, width), " ", dtype=str)
        self.running: bool = False
        self.tick_rate: int = tick_rate
        self.max_fps: int = max_fps
        self.tick_duration: float = 1.0 / tick_rate
        self.frame_duration: float = 1.0 / max_fps
        self.keys_pressed: Set[str] = set()
        self.keys_released: Set[str] = set()
        self.input_thread: Optional[threading.Thread] = None

        if os.name != "nt":
            self.old_settings = termios.tcgetattr(sys.stdin)
        else:
            self.old_settings = None

    def clear_screen(self) -> None:
        os.system("cls" if os.name == "nt" else "clear")

    def draw_pixel(self, x: int, y: int, char: str) -> None:
        if 0 <= x < self.width and 0 <= y < self.height:
            self.buffer[y, x] = char

    def draw_text(self, x: int, y: int, text: str) -> None:
        for i, char in enumerate(text):
            self.draw_pixel(x + i, y, char)

    def render(self) -> None:
        diff = self.buffer != self.prev_buffer
        y_indices, x_indices = np.where(diff)
        for y, x in zip(y_indices, x_indices):
            sys.stdout.write(f"\033[{y+1};{x+1}H{self.buffer[y, x]}")
        sys.stdout.flush()
        np.copyto(self.prev_buffer, self.buffer)

    def input_handler(self) -> None:
        while self.running:
            if os.name == "nt":
                if msvcrt.kbhit():
                    key = msvcrt.getch().decode("utf-8").lower()
                    self.keys_pressed.add(key)
            else:
                rlist, _, _ = select.select([sys.stdin], [], [], 0.1)
                if rlist:
                    key = sys.stdin.read(1).lower()
                    self.keys_pressed.add(key)
            time.sleep(0.01)

    def start_input_thread(self) -> None:
        self.input_thread = threading.Thread(target=self.input_handler)
        self.input_thread.daemon = True
        self.input_thread.start()

    def stop_input_thread(self) -> None:
        self.running = False
        if self.input_thread:
            self.input_thread.join()

    def is_key_pressed(self, key: str) -> bool:
        return key in self.keys_pressed

    def is_key_released(self, key: str) -> bool:
        return key in self.keys_released

    def clear_key_states(self) -> None:
        self.keys_released = self.keys_pressed
        self.keys_pressed = set()

    def update(self, dt: float) -> None:
        pass

    def set_raw_mode(self) -> None:
        if os.name != "nt":
            tty.setraw(sys.stdin.fileno())

    def restore_terminal(self) -> None:
        if os.name != "nt":
            termios.tcsetattr(sys.stdin, termios.TCSADRAIN, self.old_settings)
        print("\033[?25h", end="", flush=True)  # Show cursor

    def run(self) -> None:
        self.running = True
        self.clear_screen()
        print("\033[?25l", end="", flush=True)  # Hide cursor

        self.set_raw_mode()
        atexit.register(self.restore_terminal)

        self.start_input_thread()

        previous_time = time.perf_counter()
        lag = 0.0

        try:
            while self.running:
                current_time = time.perf_counter()
                elapsed = current_time - previous_time
                previous_time = current_time
                lag += elapsed

                update_count = 0
                while lag >= self.tick_duration and update_count < 5:
                    self.update(self.tick_duration)
                    lag -= self.tick_duration
                    update_count += 1

                self.buffer.fill(" ")
                self.render()
                self.clear_key_states()

                frame_end = time.perf_counter()
                frame_elapsed = frame_end - current_time
                if frame_elapsed < self.frame_duration:
                    time.sleep(self.frame_duration - frame_elapsed)
        finally:
            self.stop_input_thread()
            self.restore_terminal()


class TetrisGame(TerminalEngine):
    def __init__(self, width: int, height: int):
        super().__init__(width, height)
        self.board_width: int = 10
        self.board_height: int = 20
        self.board: np.ndarray = np.full(
            (self.board_height, self.board_width), " ", dtype=str
        )
        self.current_piece: Optional[Tuple[np.ndarray, str]] = None
        self.next_piece: Optional[Tuple[np.ndarray, str]] = None
        self.score: int = 0
        self.level: int = 1
        self.lines_cleared: int = 0
        self.game_over: bool = False
        self.drop_interval: float = 1.0
        self.last_drop_time: float = time.time()

        self.shapes: List[np.ndarray] = [
            np.array([[1, 1, 1, 1]]),
            np.array([[1, 1], [1, 1]]),
            np.array([[1, 1, 1], [0, 1, 0]]),
            np.array([[1, 1, 1], [1, 0, 0]]),
            np.array([[1, 1, 1], [0, 0, 1]]),
            np.array([[1, 1, 0], [0, 1, 1]]),
            np.array([[0, 1, 1], [1, 1, 0]]),
        ]
        self.colors: List[str] = [
            "\033[91m",
            "\033[93m",
            "\033[92m",
            "\033[94m",
            "\033[95m",
            "\033[96m",
            "\033[97m",
        ]

    def new_piece(self) -> None:
        if not self.next_piece:
            self.next_piece = self.random_piece()
        self.current_piece = self.next_piece
        self.next_piece = self.random_piece()
        self.current_x = self.board_width // 2 - self.current_piece[0].shape[1] // 2
        self.current_y = 0

        if self.collision():
            self.game_over = True

    def random_piece(self) -> Tuple[np.ndarray, str]:
        shape = random.choice(self.shapes)
        color = self.colors[self.shapes.index(shape)]
        return shape, color

    def collision(self) -> bool:
        for y, row in enumerate(self.current_piece[0]):
            for x, cell in enumerate(row):
                if cell:
                    if (
                        self.current_y + y >= self.board_height
                        or self.current_x + x < 0
                        or self.current_x + x >= self.board_width
                        or self.board[self.current_y + y, self.current_x + x] != " "
                    ):
                        return True
        return False

    def merge_piece(self) -> None:
        for y, row in enumerate(self.current_piece[0]):
            for x, cell in enumerate(row):
                if cell:
                    self.board[self.current_y + y, self.current_x + x] = (
                        self.current_piece[1]
                    )

    def rotate_piece(self) -> None:
        rotated = np.rot90(self.current_piece[0], k=-1)
        old_piece = self.current_piece
        self.current_piece = (rotated, self.current_piece[1])
        if self.collision():
            self.current_piece = old_piece

    def move_piece(self, dx: int) -> None:
        self.current_x += dx
        if self.collision():
            self.current_x -= dx

    def drop_piece(self) -> None:
        self.current_y += 1
        if self.collision():
            self.current_y -= 1
            self.merge_piece()
            self.new_piece()
            self.clear_lines()

    def clear_lines(self) -> None:
        lines_to_clear = np.all(self.board != " ", axis=1)
        num_cleared = np.sum(lines_to_clear)
        if num_cleared:
            self.board = np.vstack(
                (
                    np.full((num_cleared, self.board_width), " "),
                    self.board[~lines_to_clear],
                )
            )
            self.lines_cleared += num_cleared
            self.score += (num_cleared**2) * 100
            self.level = self.lines_cleared // 10 + 1
            self.drop_interval = max(0.1, 1.0 - (self.level - 1) * 0.1)

    def draw_pixel(
        self, x: int, y: int, char: str, color: Optional[str] = None
    ) -> None:
        if 0 <= x < self.width and 0 <= y < self.height:
            if color:
                self.buffer[y, x] = f"{color}{char}\033[0m"
            else:
                self.buffer[y, x] = char

    def draw_board(self) -> None:
        for y, row in enumerate(self.board):
            for x, cell in enumerate(row):
                if cell != " ":
                    self.draw_pixel(x + 1, y + 1, "█", cell)
                else:
                    self.draw_pixel(x + 1, y + 1, "·")

        if self.current_piece:
            ghost_y = self.current_y
            while not self.collision():
                ghost_y += 1
            ghost_y -= 1

            for y, row in enumerate(self.current_piece[0]):
                for x, cell in enumerate(row):
                    if cell:
                        self.draw_pixel(
                            self.current_x + x + 1,
                            ghost_y + y + 1,
                            "□",
                            self.current_piece[1],
                        )
                        self.draw_pixel(
                            self.current_x + x + 1,
                            self.current_y + y + 1,
                            "█",
                            self.current_piece[1],
                        )

    def draw_next_piece(self) -> None:
        if self.next_piece:
            for y, row in enumerate(self.next_piece[0]):
                for x, cell in enumerate(row):
                    if cell:
                        self.draw_pixel(
                            self.board_width + 5 + x,
                            5 + y,
                            "█",
                            self.next_piece[1],
                        )

    def update(self, dt: float) -> None:
        if self.game_over:
            self.draw_text(self.width // 2 - 4, self.height // 2, "GAME OVER")
            self.draw_text(
                self.width // 2 - 8, self.height // 2 + 1, "Press 'R' to restart"
            )
            if self.is_key_pressed("r"):
                self.__init__(self.width, self.height)
            return

        if self.is_key_pressed("q"):
            self.running = False

        if self.is_key_pressed("a"):
            self.move_piece(-1)
        if self.is_key_pressed("d"):
            self.move_piece(1)
        if self.is_key_pressed("s"):
            self.drop_piece()
        if self.is_key_pressed("w"):
            self.rotate_piece()

        current_time = time.time()
        if current_time - self.last_drop_time > self.drop_interval:
            self.drop_piece()
            self.last_drop_time = current_time

        self.buffer.fill(" ")
        self.draw_board()
        self.draw_next_piece()
        self.draw_text(self.board_width + 3, 1, f"Score: {self.score}")
        self.draw_text(self.board_width + 3, 2, f"Level: {self.level}")
        self.draw_text(self.board_width + 3, 3, f"Lines: {self.lines_cleared}")
        self.draw_text(self.board_width + 3, 4, "Next:")
        self.draw_text(
            0, self.board_height + 2, "A: Left, D: Right, W: Rotate, S: Drop, Q: Quit"
        )

    def run(self) -> None:
        self.new_piece()
        super().run()


class FlappyBirdGame(TerminalEngine):
    def __init__(self, width: int, height: int):
        super().__init__(width, height)
        self.bird_y: float = height // 2
        self.bird_velocity: float = 0
        self.gravity: float = 20
        self.jump_strength: float = -5
        self.pipes: List[Tuple[float, int]] = []
        self.pipe_gap: int = 8
        self.pipe_interval: int = 20
        self.score: int = 0
        self.game_over: bool = False
        self.background: List[str] = [" ", ".", "+", "*"]
        self.bg_positions: List[float] = [0, 0, 0, 0]
        self.bg_speeds: List[float] = [5, 10, 15, 20]

    def update(self, dt: float) -> None:
        if self.game_over:
            self.draw_text(self.width // 2 - 4, self.height // 2, "GAME OVER")
            self.draw_text(
                self.width // 2 - 8, self.height // 2 + 1, "Press 'R' to restart"
            )
            if self.is_key_pressed("r"):
                self.__init__(self.width, self.height)
            return

        if self.is_key_pressed("q"):
            self.running = False

        if self.is_key_pressed(" "):
            self.bird_velocity = self.jump_strength

        self.bird_velocity += self.gravity * dt
        self.bird_y += self.bird_velocity * dt

        if self.bird_y < 0 or self.bird_y >= self.height:
            self.game_over = True

        if not self.pipes or self.pipes[-1][0] < self.width - self.pipe_interval:
            gap_start = random.randint(4, self.height - 4 - self.pipe_gap)
            self.pipes.append([self.width, gap_start])

        for pipe in self.pipes:
            pipe[0] -= 30 * dt
            if pipe[0] < 0:
                self.pipes.remove(pipe)
                self.score += 1

            if 0 < pipe[0] < 5 and (
                self.bird_y < pipe[1] or self.bird_y > pipe[1] + self.pipe_gap
            ):
                self.game_over = True

        # Update parallax background
        for i in range(len(self.bg_positions)):
            self.bg_positions[i] -= self.bg_speeds[i] * dt
            if self.bg_positions[i] <= -self.width:
                self.bg_positions[i] = 0

        self.buffer.fill(" ")
        self.draw_background()
        self.draw_bird()
        self.draw_pipes()
        self.draw_text(1, 1, f"Score: {self.score}")

    def draw_background(self) -> None:
        for i, char in enumerate(self.background):
            pos = int(self.bg_positions[i])
            for x in range(self.width):
                self.draw_pixel((x + pos) % self.width, self.height - i - 1, char)

    def draw_bird(self) -> None:
        self.draw_pixel(5, int(self.bird_y), ">")

    def draw_pipes(self) -> None:
        for pipe in self.pipes:
            x, gap_start = int(pipe[0]), pipe[1]
            for y in range(self.height):
                if y < gap_start or y >= gap_start + self.pipe_gap:
                    self.draw_pixel(x, y, "|")

    def run(self) -> None:
        super().run()


class Bullet:
    def __init__(self, x: float, y: float, dx: float, dy: float):
        self.x = x
        self.y = y
        self.dx = dx
        self.dy = dy

    def update(self, dt: float) -> None:
        self.x += self.dx * dt
        self.y += self.dy * dt

    def draw(self, engine: "ShooterRoguelike") -> None:
        engine.draw_pixel(int(self.x), int(self.y), "*")


class Enemy:
    def __init__(self, x: float, y: float):
        self.x = x
        self.y = y
        self.health = 3

    def update(self, dt: float, player_x: float, player_y: float) -> None:
        dx = player_x - self.x
        dy = player_y - self.y
        length = math.sqrt(dx * dx + dy * dy)
        if length > 0:
            dx /= length
            dy /= length
        self.x += dx * 10 * dt
        self.y += dy * 10 * dt

    def draw(self, engine: "ShooterRoguelike") -> None:
        engine.draw_pixel(int(self.x), int(self.y), "E")


class Player:
    def __init__(self, x: float, y: float):
        self.x = x
        self.y = y
        self.health = 100

    def update(self, dt: float, dx: float, dy: float) -> None:
        self.x += dx * 20 * dt
        self.y += dy * 20 * dt

    def draw(self, engine: "ShooterRoguelike") -> None:
        engine.draw_pixel(int(self.x), int(self.y), "@")


class ShooterRoguelike(TerminalEngine):
    def __init__(self, width: int, height: int):
        super().__init__(width, height)
        self.player = Player(width // 2, height - 5)
        self.enemies: List[Enemy] = []
        self.bullets: List[Bullet] = []
        self.level: int = 1
        self.score: int = 0
        self.game_over: bool = False

    def update(self, dt: float) -> None:
        if self.game_over:
            self.draw_text(self.width // 2 - 4, self.height // 2, "GAME OVER")
            self.draw_text(
                self.width // 2 - 8, self.height // 2 + 1, "Press 'R' to restart"
            )
            if self.is_key_pressed("r"):
                self.__init__(self.width, self.height)
            return

        if self.is_key_pressed("q"):
            self.running = False

        dx = dy = 0
        if self.is_key_pressed("a"):
            dx -= 1
        if self.is_key_pressed("d"):
            dx += 1
        if self.is_key_pressed("w"):
            dy -= 1
        if self.is_key_pressed("s"):
            dy += 1

        self.player.update(dt, dx, dy)

        if self.is_key_pressed(" "):
            self.bullets.append(Bullet(self.player.x, self.player.y, 0, -50))

        for enemy in self.enemies:
            enemy.update(dt, self.player.x, self.player.y)

        for bullet in self.bullets:
            bullet.update(dt)

        self.check_collisions()
        self.spawn_enemies()

        self.buffer.fill(" ")
        self.player.draw(self)
        for enemy in self.enemies:
            enemy.draw(self)
        for bullet in self.bullets:
            bullet.draw(self)
        self.draw_text(1, 1, f"Score: {self.score}")
        self.draw_text(1, 2, f"Health: {self.player.health}")
        self.draw_text(1, 3, f"Level: {self.level}")

    def check_collisions(self) -> None:
        # Check bullet-enemy collisions
        for bullet in self.bullets[:]:
            for enemy in self.enemies[:]:
                if abs(bullet.x - enemy.x) < 1 and abs(bullet.y - enemy.y) < 1:
                    self.bullets.remove(bullet)
                    enemy.health -= 1
                    if enemy.health <= 0:
                        self.enemies.remove(enemy)
                        self.score += 10
                    break

        # Check player-enemy collisions
        for enemy in self.enemies[:]:
            if abs(self.player.x - enemy.x) < 1 and abs(self.player.y - enemy.y) < 1:
                self.enemies.remove(enemy)
                self.player.health -= 10
                if self.player.health <= 0:
                    self.game_over = True

        # Remove bullets that are out of bounds
        self.bullets = [b for b in self.bullets if 0 <= b.y < self.height]

    def spawn_enemies(self) -> None:
        if random.random() < 0.02 * self.level:
            x = random.randint(0, self.width - 1)
            self.enemies.append(Enemy(x, 0))

        if len(self.enemies) == 0:
            self.level += 1
            for _ in range(self.level):
                x = random.randint(0, self.width - 1)
                self.enemies.append(Enemy(x, 0))

    def run(self) -> None:
        super().run()


def select_game(games: List[str]) -> None:
    while True:
        print("\nSelect a game to play:")
        for i, game in enumerate(games):
            print(f"{i + 1}. {game}")
        print("0. Exit")

        try:
            choice = int(input("Enter your choice: "))
            if choice == 0:
                print("Thank you for playing!")
                sys.exit()
            elif 1 <= choice <= len(games):
                if games[choice - 1] == "Tetris":
                    game = TetrisGame(40, 40)
                elif games[choice - 1] == "Flappy Bird":
                    game = FlappyBirdGame(40, 20)
                elif games[choice - 1] == "Shooter Roguelike":
                    game = ShooterRoguelike(40, 20)

                game.run()
                # After the game ends, it will loop back to game selection
            else:
                print("Invalid choice. Please try again.")
        except ValueError:
            print("Invalid input. Please enter a number.")


def main() -> None:
    games: List[str] = [
        "Tetris",
        "Flappy Bird",
        "Shooter Roguelike",
    ]

    select_game(games)


if __name__ == "__main__":
    main()
