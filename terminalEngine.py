import time
import os
import sys
import select
import threading
import atexit
from typing import Set, Optional
import numpy as np

if os.name == "nt":
    import msvcrt
else:
    import termios
    import tty


class TerminalEngine:
    def __init__(self, width: int, height: int, tickRate: int = 60, maxFps: int = 60):
        self.width: int = width
        self.height: int = height
        self.buffer: np.ndarray = np.full((height, width), " ", dtype=str)
        self.prevBuffer: np.ndarray = np.full((height, width), " ", dtype=str)
        self.running: bool = False
        self.tickRate: int = tickRate
        self.maxFps: int = maxFps
        self.tickDuration: float = 1.0 / tickRate
        self.frameDuration: float = 1.0 / maxFps
        self.keysPressed: Set[str] = set()
        self.keysReleased: Set[str] = set()
        self.inputThread: Optional[threading.Thread] = None

        if os.name != "nt":
            self.oldSettings = termios.tcgetattr(sys.stdin)
        else:
            self.oldSettings = None

    def clearScreen(self) -> None:
        os.system("cls" if os.name == "nt" else "clear")

    def drawPixel(self, x: int, y: int, char: str) -> None:
        if 0 <= x < self.width and 0 <= y < self.height:
            self.buffer[y, x] = char

    def drawText(self, x: int, y: int, text: str) -> None:
        for i, char in enumerate(text):
            self.drawPixel(x + i, y, char)

    def render(self) -> None:
        diff = self.buffer != self.prevBuffer
        yIndices, xIndices = np.where(diff)
        for y, x in zip(yIndices, xIndices):
            sys.stdout.write(f"\033[{y+1};{x+1}H{self.buffer[y, x]}")
        sys.stdout.flush()
        np.copyto(self.prevBuffer, self.buffer)

    def inputHandler(self) -> None:
        while self.running:
            if os.name == "nt":
                if msvcrt.kbhit():
                    key = msvcrt.getch().decode("utf-8").lower()
                    self.keysPressed.add(key)
            else:
                rlist, _, _ = select.select([sys.stdin], [], [], 0.1)
                if rlist:
                    key = sys.stdin.read(1).lower()
                    self.keysPressed.add(key)
            time.sleep(0.01)

    def startInputThread(self) -> None:
        self.inputThread = threading.Thread(target=self.inputHandler)
        self.inputThread.daemon = True
        self.inputThread.start()

    def stopInputThread(self) -> None:
        self.running = False
        if self.inputThread:
            self.inputThread.join()

    def isKeyPressed(self, key: str) -> bool:
        return key in self.keysPressed

    def isKeyReleased(self, key: str) -> bool:
        return key in self.keysReleased

    def clearKeyStates(self) -> None:
        self.keysReleased = self.keysPressed
        self.keysPressed = set()

    def update(self, dt: float) -> None:
        pass

    def setRawMode(self) -> None:
        if os.name != "nt":
            tty.setraw(sys.stdin.fileno())

    def restoreTerminal(self) -> None:
        if os.name != "nt":
            termios.tcsetattr(sys.stdin, termios.TCSADRAIN, self.oldSettings)
        print("\033[?25h", end="", flush=True)  # Show cursor

    def run(self) -> None:
        self.running = True
        self.clearScreen()
        print("\033[?25l", end="", flush=True)  # Hide cursor

        self.setRawMode()
        atexit.register(self.restoreTerminal)

        self.startInputThread()

        previousTime = time.perf_counter()
        lag = 0.0

        try:
            while self.running:
                currentTime = time.perf_counter()
                elapsed = currentTime - previousTime
                previousTime = currentTime
                lag += elapsed

                updateCount = 0
                while lag >= self.tickDuration and updateCount < 5:
                    self.update(self.tickDuration)
                    lag -= self.tickDuration
                    updateCount += 1

                self.render()  # Render first
                self.clearKeyStates()

                # Now clear the buffer for the next frame
                self.buffer.fill(" ")

                frameEnd = time.perf_counter()
                frameElapsed = frameEnd - currentTime
                if frameElapsed < self.frameDuration:
                    time.sleep(self.frameDuration - frameElapsed)
        finally:
            self.stopInputThread()
            self.restoreTerminal()
