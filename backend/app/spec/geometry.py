"""Small geometry helpers for checking positions on the card canvas (mm)."""
from dataclasses import dataclass

from app.spec.constants import SAFE_BOX


@dataclass(frozen=True)
class Box:
    """A rectangle on the canvas. x, y is the top-left corner."""
    x: float
    y: float
    w: float
    h: float

    @property
    def x1(self) -> float:
        return self.x + self.w

    @property
    def y1(self) -> float:
        return self.y + self.h


def inside_safe_area(box: Box) -> bool:
    """True if the whole box lies inside the safe area."""
    sx0, sy0, sx1, sy1 = SAFE_BOX
    return box.x >= sx0 and box.y >= sy0 and box.x1 <= sx1 and box.y1 <= sy1
