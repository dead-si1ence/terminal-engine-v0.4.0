from terminalEngine import TerminalEngine
import math
import random
from typing import List, Tuple


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