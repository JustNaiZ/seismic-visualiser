from OpenGL.arrays import vbo
from PyQt5 import QtCore, QtWidgets  # core Qt functionality
from PyQt5 import QtGui  # extends QtCore with GUI functionality
from PyQt5 import QtOpenGL  # provides QGLWidget, a special OpenGL QWidget

import OpenGL.GL as gl  # python wrapping of OpenGL
from OpenGL import GLU  # OpenGL Utility Library, extends OpenGL functionality

# from OpenGL.arrays import vbo
# from ezdxf.entities import Face3d

from pyglm import glm

import numpy as np

from AppWindow import MainWindow
import math
import sys  # we'll need this later to run our Qt application

from object_constructors import create_dxf_object, create_sphere, create_pyramid, create_detector, \
    create_event, create_point, create_beach_ball_hosohedron, create_enhanced_sphere
from utilities import screen_pos_to_vector

# Камера работает как орбитальная - вращается вокруг целевого объекта (viewTarget)

# основной виджет для 3D отображения
class GLWidget(QtOpenGL.QGLWidget):
    ROT_Y_MIN = math.pi * (0.1 / 360)
    ROT_Y_MAX = math.pi * (359.9 / 360)

    ARM_MIN = 5
    ARM_MAX = 10000

    SENSITIVITY_X = 360
    SENSITIVITY_Y = 480
    SENSITIVITY_ARM = 5

    FIELD_OF_VIEW = 60.0
    ASPECT_RATIO = 1.0
    RENDER_DISTANCE_NEAR = 1.0
    RENDER_DISTANCE_FAR = 1000000.0

    ENABLE_EDGES = True
    ENABLE_FACES = True
    ENABLE_HOVER = False

    def __init__(self, parent=None):
        self.parent = parent

        self.armLength = 20

        self.rotX = 0.0
        self.rotY = self.ROT_Y_MIN

        self.camX = 0.0
        self.camY = 0.0
        self.camZ = 0.0

        self.objects = {}
        self.pickedObjects = []
        self.hoveredObject = -1
        self.viewTarget = None

        self.mousePos = (0, 0)
        self.mouseCaptured = False
        self.mouseCapturedEvent = None
        self.mousePrevEvent = None

        QtOpenGL.QGLWidget.__init__(self, parent)

    # инициализация OpenGL, настройка фона и глубины
    def initializeGL(self):
        self.qglClearColor(QtGui.QColor(152, 221, 250))
        gl.glEnable(gl.GL_DEPTH_TEST)
        gl.glEnable(gl.GL_BLEND)
        gl.glBlendFunc(gl.GL_SRC_ALPHA, gl.GL_ONE_MINUS_SRC_ALPHA)

        # self._init_geometry("../korkino_model.dxf")
        gl.glPushMatrix()

    # обработка изменения размера окна, настройка перспективы
    def resizeGL(self, width, height):
        gl.glViewport(0, 0, width, height)
        gl.glMatrixMode(gl.GL_PROJECTION)
        gl.glLoadIdentity()
        self.ASPECT_RATIO = width / float(height)

        GLU.gluPerspective(self.FIELD_OF_VIEW, self.ASPECT_RATIO, self.RENDER_DISTANCE_NEAR, self.RENDER_DISTANCE_FAR)
        gl.glMatrixMode(gl.GL_MODELVIEW)


    def mousePressEvent(self, a0):
        self.mouseCaptured = True

        self.mouseCapturedEvent = (a0.x(), a0.y())
        self.mousePrevEvent = (a0.x(), a0.y())
        # print("Pressed", a0.x(), a0.y())

    def mouseMoveEvent(self, a0):
        self.mousePos = (a0.x(), a0.y())
        if self.mouseCaptured:
            dx, dy = a0.x() - self.mousePrevEvent[0], a0.y() - self.mousePrevEvent[1]

            if max(abs(dx), abs(dy)) > 0:
                # print("Moved", dx, dy)
                self.addRotX(dx)
                self.addRotY(dy)
                self.mousePrevEvent = (a0.x(), a0.y())

    def mouseReleaseEvent(self, a0):
        clicked = self.mousePrevEvent == self.mouseCapturedEvent

        self.mouseCaptured = False

        self.mouseCapturedEvent = None
        self.mousePrevEvent = None

        if clicked:
            self.mouseClickEvent(a0)
        # print("Released", a0.x(), a0.y())

    def mouseClickEvent(self, a0):
        pass

    def wheelEvent(self, a0):
        da = a0.angleDelta().y() / 15 / 8 * self.SENSITIVITY_ARM
        self.armLength = max(self.ARM_MIN, min(self.ARM_MAX, int(self.armLength - max(da * 0.02 * self.armLength, da / 5, key=math.fabs))))

    def check_collision_object(self, direction, obj):
        tMin = self.RENDER_DISTANCE_NEAR
        tMax = self.RENDER_DISTANCE_FAR
        obj_pos = glm.vec3([obj.matrix[3].x, obj.matrix[3].y, obj.matrix[3].z])
        loc = glm.vec3([self.camX, self.camY, self.camZ])
        delta = obj_pos - loc

        pts_beg = obj.collision.pointBegin
        pts_end = obj.collision.pointEnd
        for i in range(3):
            axis = glm.vec3([obj.matrix[i].x, obj.matrix[i].y, obj.matrix[i].z])
            e = glm.dot(axis, delta)
            f = glm.dot(direction, axis)

            if math.fabs(f) > 0:
                t1 = (e + pts_beg[i]) / f
                t2 = (e + pts_end[i] * obj.scale[i]) / f

                if t1 > t2:
                    t1, t2 = t2, t1
                if t2 < tMax:
                    tMax = t2
                if t1 > tMin:
                    tMin = t1
                if tMax < tMin:
                    return -1.0
            else:
                if -e + pts_beg[i] > 0.0 or -e + pts_end[i] < 0.0:
                    return -1.0
        return tMin

    # проверка столкновений луча мыши с объектами
    def check_collision(self):
        cam = glm.vec3([self.camX, self.camY, self.camZ])
        direction = screen_pos_to_vector(self.mousePos[0], self.mousePos[1], self.width(), self.height(), cam,
                                         glm.vec3(self.viewTarget.location))

        obj_id = -1
        dist = self.RENDER_DISTANCE_FAR * 2

        for obj in self.objects:
            if self.objects[obj].enabled and self.objects[obj].collision.enabled:
                cur = self.check_collision_object(direction, self.objects[obj])
                if 0.0 < cur < dist:
                    obj_id = obj
                    dist = cur


        if obj_id == -1 and self.hoveredObject != -1:
            self.objects[self.hoveredObject].on_unhover()
            self.hoveredObject = -1
        elif obj_id != self.hoveredObject and self.hoveredObject != -1:
            self.objects[self.hoveredObject].on_unhover()
            self.hoveredObject = obj_id
            self.objects[obj_id].on_hover()
        elif obj_id != self.hoveredObject and self.hoveredObject == -1:
            self.hoveredObject = obj_id
            self.objects[obj_id].on_hover()

    # отрисовка отдельного 3D объекта
    def draw_object(self, obj):
        gl.glPushMatrix()

        gl.glTranslate(*obj.location)
        gl.glRotatef(obj.rotation[0], 1.0, 0.0, 0.0)
        gl.glRotatef(obj.rotation[1], 0.0, 1.0, 0.0)
        gl.glRotatef(obj.rotation[2], 0.0, 0.0, 1.0)
        gl.glScale(*obj.scale)

        obj.mesh.verticesVBO.bind()
        gl.glVertexPointer(3, gl.GL_FLOAT, 0, obj.mesh.verticesVBO)

        # Сначала грани (если включено)
        if self.ENABLE_FACES and obj.mesh.enableFaces:
            obj.mesh.colorsFacesVBO.bind()
            gl.glColorPointer(4, gl.GL_FLOAT, 0, obj.mesh.colorsFacesVBO)

            if obj.mesh.facesTriangles is not None:
                gl.glDrawElements(gl.GL_TRIANGLES, len(obj.mesh.facesTriangles), gl.GL_UNSIGNED_INT,
                                  obj.mesh.facesTriangles)

            if obj.mesh.facesQuads is not None:
                gl.glDrawElements(gl.GL_QUADS, len(obj.mesh.facesQuads), gl.GL_UNSIGNED_INT,
                                  obj.mesh.facesQuads)

            obj.mesh.colorsFacesVBO.unbind()

        # Затем ребра (если включено) - ТОЛЬКО ДЛЯ DXF, НЕ ДЛЯ СОБЫТИЙ
        if self.ENABLE_EDGES and obj.mesh.enableEdges and obj.mesh.edges is not None and obj.obj_type != "event":
            obj.mesh.colorsEdgesActiveVBO.bind()
            gl.glColorPointer(3, gl.GL_FLOAT, 0, obj.mesh.colorsEdgesActiveVBO)
            gl.glDrawElements(gl.GL_LINES, len(obj.mesh.edges), gl.GL_UNSIGNED_INT, obj.mesh.edges)
            obj.mesh.colorsEdgesActiveVBO.unbind()

        obj.mesh.verticesVBO.unbind()
        gl.glPopMatrix()

    # вычисление позиции камеры вокруг целевого объекта
    def _compute_camera(self):
        if self.viewTarget is not None:
            x, y, z = self.viewTarget.location + self.viewTarget.origin
            self.camX = x + self.armLength * math.sin(self.rotY) * math.cos(self.rotX)
            self.camY = y + self.armLength * math.cos(self.rotY)
            self.camZ = z + self.armLength * math.sin(self.rotY) * math.sin(self.rotX)

    # позиционирование камеры в сцене
    def _position_camera(self):
        if self.viewTarget is not None:
            x, y, z = self.viewTarget.location + self.viewTarget.origin
            GLU.gluLookAt(self.camX, self.camY, self.camZ, x, y, z, 0.0, 1.0, 0.0)

    # основной цикл отрисовки всех объектов
    def paintGL(self):
        gl.glClear(gl.GL_COLOR_BUFFER_BIT | gl.GL_DEPTH_BUFFER_BIT)

        self._compute_camera()
        if self.ENABLE_HOVER:
            self.check_collision()

        gl.glEnableClientState(gl.GL_VERTEX_ARRAY)
        gl.glEnableClientState(gl.GL_COLOR_ARRAY)

        # УВЕЛИЧИВАЕМ ТОЛЩИНУ ЛИНИЙ ДЛЯ ЛУЧШЕЙ ВИДИМОСТИ
        gl.glLineWidth(2.0)

        # РАЗДЕЛЯЕМ ОБЪЕКТЫ НА НЕПРОЗРАЧНЫЕ И ПРОЗРАЧНЫЕ
        opaque_objects = []
        transparent_objects = []

        camera_pos = np.array([self.camX, self.camY, self.camZ])

        for obj in self.objects.values():
            if obj.enabled and obj.mesh.enabled:
                # Определяем прозрачность объекта
                is_transparent = False
                if hasattr(obj, 'current_opacity'):
                    is_transparent = obj.current_opacity < 0.99

                if is_transparent:
                    # Вычисляем расстояние до камеры для сортировки
                    obj_pos = np.array([obj.matrix[3].x, obj.matrix[3].y, obj.matrix[3].z])
                    distance = np.linalg.norm(camera_pos - obj_pos)
                    transparent_objects.append((distance, obj))
                else:
                    opaque_objects.append(obj)

        # Сначала рисуем все непрозрачные объекты
        for obj in opaque_objects:
            if obj.obj_type == "event" and hasattr(obj, 'draw_outline'):
                gl.glPushMatrix()
                gl.glTranslate(*obj.location)
                gl.glRotatef(obj.rotation[0], 1.0, 0.0, 0.0)
                gl.glRotatef(obj.rotation[1], 0.0, 1.0, 0.0)
                gl.glRotatef(obj.rotation[2], 0.0, 0.0, 1.0)
                obj.draw_outline()
                gl.glPopMatrix()

            self.draw_object(obj)

        # Включаем смешивание для прозрачных объектов
        gl.glEnable(gl.GL_BLEND)
        gl.glBlendFunc(gl.GL_SRC_ALPHA, gl.GL_ONE_MINUS_SRC_ALPHA)

        # Отключаем запись глубины для прозрачных объектов
        gl.glDepthMask(gl.GL_FALSE)

        # Сортируем прозрачные объекты по расстоянию (от дальних к ближним)
        transparent_objects.sort(key=lambda x: x[0], reverse=True)

        # Рисуем прозрачные объекты
        for distance, obj in transparent_objects:
            if obj.obj_type == "event" and hasattr(obj, 'draw_outline'):
                gl.glPushMatrix()
                gl.glTranslate(*obj.location)
                gl.glRotatef(obj.rotation[0], 1.0, 0.0, 0.0)
                gl.glRotatef(obj.rotation[1], 0.0, 1.0, 0.0)
                gl.glRotatef(obj.rotation[2], 0.0, 0.0, 1.0)
                obj.draw_outline()
                gl.glPopMatrix()

            self.draw_object(obj)

        # Восстанавливаем запись глубины
        gl.glDepthMask(gl.GL_TRUE)
        gl.glDisable(gl.GL_BLEND)

        # ВОССТАНАВЛИВАЕМ ТОЛЩИНУ ЛИНИЙ ПО УМОЛЧАНИЮ
        gl.glLineWidth(1.0)

        gl.glDisableClientState(gl.GL_VERTEX_ARRAY)
        gl.glDisableClientState(gl.GL_COLOR_ARRAY)

        gl.glPopMatrix()
        gl.glPushMatrix()

        self._position_camera()

    def add_object_dxf(self, filepath):
        obj = create_dxf_object(filepath, False)
        obj.scale = np.array([1.0, 1.0, 1.0])
        obj.calculate_matrix()

        self.objects[obj.id] = obj
        self.viewTarget = obj

    def add_object_detector(self, det_id, x, y, z):
        obj = create_detector(det_id, x, y, z)
        obj.scale = np.array([50.0, 50.0, 50.0])
        obj.calculate_matrix()

        self.objects[obj.id] = obj

    def add_object_event(self, x, y, z, event_type, energy, custom_color=None):
        print(f"Добавление события: X={x}, Y={y}, Z={z}, тип={event_type}, энергия={energy}")

        # Передаем кастомный цвет если указан
        if custom_color is not None:
            # custom_color должен быть в формате RGBA [r, g, b, a]
            if len(custom_color) == 3:
                # Если только RGB, добавляем альфа=1.0
                rgba_color = custom_color + [1.0]
            else:
                rgba_color = custom_color
            obj = create_event(x, y, z, event_type, energy, rgba_color)
        else:
            obj = create_event(x, y, z, event_type, energy)

        # Базовые множители для разных типов событий
        type_multipliers = {
            "explosion": 3.0,  # Взрывы - самые большие
            "earthquake": 1.5,  # Землетрясения - средние
            "microseismic": 0.8,  # Микросейсмика - маленькие
            "unknown": 0.5  # По умолчанию
        }

        # Получаем множитель для типа события
        multiplier = type_multipliers.get(event_type, 1.5)

        # Формула размера: логарифм энергии * множитель типа
        s = math.fabs(math.log(energy)) * multiplier if energy > 0 else 1.0

        # Ограничиваем максимальный размер (например, 30 единиц)
        s = min(s, 100.0)

        print(f"Размер шара: {s} (тип: {event_type}, множитель: {multiplier})")

        obj.scale = np.array([s, s, s])
        obj.calculate_matrix()

        # СОХРАНЯЕМ БАЗОВЫЙ ЦВЕТ И ПРОЗРАЧНОСТЬ ДЛЯ ДИНАМИЧЕСКОГО ОСВЕЩЕНИЯ
        obj.base_color = [1.0, 0.0, 0.0]  # будет переопределено свойствами
        obj.current_opacity = 1.0

        # Добавляем объект
        self.objects[obj.id] = obj
        print(f"Объект добавлен с ID: {obj.id}, всего объектов: {len(self.objects)}\n")

    def add_object_beach_ball(self, x, y, z, event_type, energy, custom_color=None):
        """Добавляет пляжный мячик с возможностью указать цвет и прозрачность"""
        print(f"Добавление пляжного мячика: X={x}, Y={y}, Z={z}")

        # Используем кастомный цвет или цвет по энергии
        if custom_color is not None:
            base_color = custom_color
        else:
            # Определяем цвет по энергии
            if energy > 100000000000:
                base_color = [1.0, 0.0, 0.0, 1.0]
            elif energy > 1000000000:
                base_color = [1.0, 0.5, 0.0, 1.0]
            elif energy > 100000000:
                base_color = [1.0, 1.0, 0.0, 1.0]
            elif energy > 1000000:
                base_color = [0.0, 1.0, 0.0, 1.0]
            elif energy > 1000:
                base_color = [0.0, 0.0, 1.0, 1.0]
            else:
                base_color = [0.5, 0.5, 0.5, 1.0]

        # ⚠️ ГАРАНТИРУЕМ ЧТО ЦВЕТ В RGBA ФОРМАТЕ
        if len(base_color) == 3:
            base_color = base_color + [1.0]

        obj = create_beach_ball_hosohedron(base_color)
        obj.location = np.array([x, y, z])
        obj.obj_type = "event"
        obj.data["type"] = event_type
        obj.data["energy"] = energy
        obj.data["visualization"] = "beach_ball"

        # Размер пляжного мячика
        type_multipliers = {
            "explosion": 3.0,
            "earthquake": 1.5,
            "microseismic": 0.8,
            "unknown": 0.5
        }

        multiplier = type_multipliers.get(event_type, 1.5)
        s = math.fabs(math.log(energy)) * multiplier if energy > 0 else 1.0
        s = min(s, 100.0)

        obj.scale = np.array([s, s, s])
        obj.calculate_matrix()

        self.objects[obj.id] = obj
        print(f"✅ Пляжный мячик с прозрачностью {base_color[3]} добавлен с ID: {obj.id}")
        return obj

    def add_object_point(self, x, y, z, event_type, energy, custom_color=None):
        """Добавляет точку с возможностью указать цвет и прозрачность"""
        print(f"Добавление точки: X={x}, Y={y}, Z={z}")

        # Используем кастомный цвет или цвет по энергии
        if custom_color is not None:
            base_color = custom_color
        else:
            # Определяем цвет по энергии
            if energy > 100000000000:
                base_color = [1.0, 0.0, 0.0, 1.0]
            elif energy > 1000000000:
                base_color = [1.0, 0.5, 0.0, 1.0]
            elif energy > 100000000:
                base_color = [1.0, 1.0, 0.0, 1.0]
            elif energy > 1000000:
                base_color = [0.0, 1.0, 0.0, 1.0]
            elif energy > 1000:
                base_color = [0.0, 0.0, 1.0, 1.0]
            else:
                base_color = [0.5, 0.5, 0.5, 1.0]

        # ⚠️ ГАРАНТИРУЕМ ЧТО ЦВЕТ В RGBA ФОРМАТЕ
        if len(base_color) == 3:
            base_color = base_color + [1.0]

        obj = create_point(base_color)
        obj.location = np.array([x, y, z])
        obj.obj_type = "event"
        obj.data["type"] = event_type
        obj.data["energy"] = energy
        obj.data["visualization"] = "point"

        # Фиксированный размер для точек
        s = 5.0
        obj.scale = np.array([s, s, s])
        obj.calculate_matrix()

        self.objects[obj.id] = obj
        print(f"✅ Точка с прозрачностью {base_color[3]} добавлена с ID: {obj.id}")
        return obj

    def add_object_point(self, x, y, z, event_type, energy, custom_color=None):
        """Добавляет событие в виде точки"""
        print(f"Добавление точки: X={x}, Y={y}, Z={z}")

        if custom_color is not None:
            base_color = custom_color
        else:
            # Определяем цвет по энергии
            if energy > 100000000000:
                base_color = [1.0, 0.0, 0.0, 1.0]
            elif energy > 1000000000:
                base_color = [1.0, 0.5, 0.0, 1.0]
            elif energy > 100000000:
                base_color = [1.0, 1.0, 0.0, 1.0]
            elif energy > 1000000:
                base_color = [0.0, 1.0, 0.0, 1.0]
            elif energy > 1000:
                base_color = [0.0, 0.0, 1.0, 1.0]
            else:
                base_color = [0.5, 0.5, 0.5, 1.0]

        obj = create_point(base_color)
        obj.location = np.array([x, y, z])
        obj.obj_type = "event"
        obj.data["type"] = event_type
        obj.data["energy"] = energy
        obj.data["visualization"] = "point"  # Сохраняем тип визуализации

        # Фиксированный маленький размер для точек
        s = 5.0  # Все точки одинакового маленького размера

        obj.scale = np.array([s, s, s])
        obj.calculate_matrix()

        self.objects[obj.id] = obj
        print(f"Точка добавлена с ID: {obj.id}")
        return obj

    def _init_geometry(self, filepath):
        obj1 = create_dxf_object(filepath, False)
        obj1.scale = np.array([1.0, 1.0, 1.0])
        obj1.location = np.array([0.0, 0.0, -50.00])
        obj1.calculate_matrix()

        obj2 = create_pyramid()
        obj2.scale = np.array([1.0, 1.0, 1.0])
        obj2.location = np.array([2.0, 0.0, -50.0])
        obj2.calculate_matrix()
        '''
        obj3 = create_sphere()
        obj3.scale = np.array([1.0, 1.0, 1.0])
        obj3.location = np.array([4.0, 0.0, -50.0])
        obj3.calculate_matrix()'''

        self.objects = {obj1.id : obj1,
                        obj2.id : obj2,}

        self.viewTarget = obj1

    def set_perspective_top(self):
        self.rotX = 0.0
        self.rotY = self.ROT_Y_MIN

    def set_perspective_side(self, side=0):
        self.rotX = math.pi * side / 2
        self.rotY = math.pi / 2

    def set_perspective_bottom(self):
        self.rotX = 0.0
        self.rotY = self.ROT_Y_MAX

    def setRotX(self, val):
        self.rotX = math.pi * (val / 180)

    def setRotY(self, val):
        self.rotY = math.pi * (val / 360)

    def addRotX(self, val):
        self.rotX += math.pi * (val / self.SENSITIVITY_X)

    def addRotY(self, val):
        self.rotY = max(self.ROT_Y_MIN, min(self.ROT_Y_MAX, self.rotY - math.pi * (val / self.SENSITIVITY_Y)))

    def setArm(self, val):
        self.armLength = 20 + val

if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)
    win = MainWindow(GLWidget())
    win.show()

    sys.exit(app.exec_())