import numpy as np
from pyglm import glm
from pyglm.glm import sin, cos

# классы 3D объектов

# NEVER EVER interact with this var outside SceneObject class
OBJECT_COUNT = 0

# TODO : create methods to update SceneObject fields and automatically recalculate matrix
# OR : do something with matrices provided by OpenGL and make them work!!

# SceneObject - базовый класс всех объектов сцены
class SceneObject:
    def __init__(self, mesh, collision, origin=np.array([0.0, 0.0, 0.0]), obj_type="misc", data={}):
        self.enabled = True
        self.hover = False
        self.current_opacity = 1.0

        self.mesh = mesh
        self.collision = collision
        self.origin = origin
        self.obj_type = obj_type
        self.data = data.copy()

        self.scale = np.array([1.0, 1.0, 1.0])
        self.rotation = np.array([0.0, 0.0, 0.0])
        self.location = np.array([0.0, 0.0, 0.0])
        self.matrix = None
        self.calculate_matrix()

        global OBJECT_COUNT
        self.id = OBJECT_COUNT
        OBJECT_COUNT += 1

    # вычисляет итоговую матрицу преобразования
    def calculate_matrix(self):
        a, b, c = self.rotation
        x, y, z = self.location
        sx, sy, sz = self.scale
        ox, oy, oz = self.origin

        # Создаем матрицы преобразования
        T = glm.translate(glm.mat4(1.0), glm.vec3(x, y, z))
        R_x = glm.rotate(glm.mat4(1.0), a, glm.vec3(1.0, 0.0, 0.0))
        R_y = glm.rotate(glm.mat4(1.0), b, glm.vec3(0.0, 1.0, 0.0))
        R_z = glm.rotate(glm.mat4(1.0), c, glm.vec3(0.0, 0.0, 1.0))
        S = glm.scale(glm.mat4(1.0), glm.vec3(sx, sy, sz))
        O = glm.translate(glm.mat4(1.0), glm.vec3(-ox, -oy, -oz))

        # Композиция: T * R_z * R_y * R_x * S * O
        self.matrix = T * R_z * R_y * R_x * S * O

    # обработка наведения мыши
    def on_hover(self):
        self.hover = True
        self.mesh.on_hover()

    def on_unhover(self):
        self.hover = False
        self.mesh.on_unhover()


# SceneEvent - класс для событий землетрясений
# Хранит время, магнитуду, энергию, ошибку локализации
class SceneEvent(SceneObject):
    def __init__(self, time=0, magnitude=0, location_error=0, energy=0, l_param=0, event_type="Unknown"):
        # mesh = create_sphere()

        # SceneObject.__init__(self, mesh, collision, origin)
        self.time = 0
        self.magnitude = 0
        self.type = "Unknown"
        self.location_error = 0
        self.energy = 0
        self.L = 0