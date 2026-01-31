import math


def distance_2d(x1: float, y1: float, x2: float, y2: float) -> float:
    return math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)


def clamp(value: float, min_val: float, max_val: float) -> float:
    return max(min_val, min(max_val, value))
