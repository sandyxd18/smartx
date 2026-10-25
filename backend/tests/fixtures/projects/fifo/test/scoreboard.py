"""Reference model for the FIFO, kept apart so the testbench imports a helper module."""

from collections import deque


class FifoModel:
    def __init__(self, depth: int) -> None:
        self.depth = depth
        self.items: deque[int] = deque()

    @property
    def empty(self) -> bool:
        return not self.items

    @property
    def full(self) -> bool:
        return len(self.items) == self.depth

    def push(self, value: int) -> None:
        self.items.append(value)

    def pop(self) -> int:
        return self.items.popleft()
