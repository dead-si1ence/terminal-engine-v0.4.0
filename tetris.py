from terminalEngine import TerminalEngine
import numpy as np
import time
import random
from typing import Optional, Tuple, List


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
        index = random.randint(0, len(self.shapes) - 1)
        shape = self.shapes[index]
        color = self.colors[index]
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

    #     def update(self, dt: float) -> None:
    #         if self.game_over:
    #             self.draw_text(self.width // 2 - 4, self.height // 2, "GAME OVER")
    #             self.draw_text(
    #                 self.width // 2 - 8, self.height // 2 + 1, "Press 'R' to restart"
    #             )
    #             if self.isKeyPressed("r"):
    #                 self.__init__(self.width, self.height)
    #             return
    #
    #         if self.isKeyPressed("q"):
    #             self.running = False
    #
    #         if self.isKeyPressed("a"):
    #             self.move_piece(-1)
    #         if self.isKeyPressed("d"):
    #             self.move_piece(1)
    #         if self.isKeyPressed("s"):
    #             self.drop_piece()
    #         if self.isKeyPressed("w"):
    #             self.rotate_piece()
    #
    #         current_time = time.time()
    #         if current_time - self.last_drop_time > self.drop_interval:
    #             self.drop_piece()
    #             self.last_drop_time = current_time
    #
    #         self.buffer.fill(" ")
    #         self.draw_board()
    #         self.draw_next_piece()
    #         self.draw_text(self.board_width + 3, 1, f"Score: {self.score}")
    #         self.draw_text(self.board_width + 3, 2, f"Level: {self.level}")
    #         self.draw_text(self.board_width + 3, 3, f"Lines: {self.lines_cleared}")
    #         self.draw_text(self.board_width + 3, 4, "Next:")
    #         self.draw_text(
    #             0, self.board_height + 2, "A: Left, D: Right, W: Rotate, S: Drop, Q: Quit"
    #         )

    def update(self, dt: float) -> None:
        # Clear the buffer (not the terminal screen, just the internal buffer)
        self.buffer.fill(" ")

        # Handle user input (e.g., move piece left, right, rotate)
        if self.isKeyPressed("a"):
            self.move_piece(-1, 0)  # Move left
        elif self.isKeyPressed("d"):
            self.move_piece(1, 0)  # Move right
        elif self.isKeyPressed("w"):
            self.rotate_piece()  # Rotate

        self.move_piece(0, 1)

        if self.check_collision(self.active_piece, self.piece_x, self.piece_y):
            self.move_piece(0, -1)
            self.lock_piece()
            self.clear_lines()
            self.new_piece()  

        self.draw_piece(self.active_piece, self.piece_x, self.piece_y)

        self.draw_fixed_pieces()

        self.draw_border()

        self.render()

        self.clearKeyStates()

    def run(self) -> None:
        self.new_piece()
        super().run()
