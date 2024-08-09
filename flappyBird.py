from terminalEngine import TerminalEngine
import random
from typing import List, Tuple


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