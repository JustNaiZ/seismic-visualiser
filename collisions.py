import numpy as np

# простой ограничивающий прямоугольник для проверки столкновений
class CollisionBox:
    def __init__(self, poingBegin, pointEnd):
        self.enabled = True

        self.pointBegin = poingBegin
        self.pointEnd = pointEnd