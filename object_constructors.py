import ezdxf
import numpy as np
from OpenGL.arrays import vbo
from pyglm import glm
import OpenGL.GL as gl

from collisions import CollisionBox
from object_meshes import ObjectMesh
from scene_objects import SceneObject


def load_dxf_vertices(file_path, scale=1.0, normalize=False):
    doc = ezdxf.readfile(file_path)
    msp = doc.modelspace()

    vertices = []
    indices_faces_t = []
    indices_faces_q = []
    indices_edges = []
    index_offset = 0
    for e in msp.query('3DFACE'):
        pts = [(vertex.x, vertex.z, vertex.y) for vertex in e.wcs_vertices(False)]

        pts = np.array(pts, dtype=np.float32) * scale
        # print(pts)
        vertices.extend(pts)

        n = len(pts)
        if n == 3:
            indices_faces_t.extend([index_offset, index_offset + 1, index_offset + 2])
            indices_edges.extend([index_offset, index_offset + 1, index_offset + 1, index_offset + 2, index_offset + 2, index_offset])
        elif n == 4:
            indices_faces_q.extend([index_offset, index_offset + 1, index_offset + 2, index_offset + 3])
            indices_edges.extend([index_offset, index_offset + 1, index_offset + 1, index_offset + 2, index_offset + 2, index_offset + 3, index_offset + 3, index_offset])
        index_offset += n

    vertices = np.array(vertices, dtype=np.float32)

    if normalize:
        min_coords = vertices.min(axis=0)
        max_coords = vertices.max(axis=0)
        vertices = (vertices - min_coords) / (max_coords - min_coords)

    indices_faces_t = np.array(indices_faces_t, dtype=np.uint32)
    indices_faces_q = np.array(indices_faces_q, dtype=np.uint32)
    indices_edges = np.array(indices_edges, dtype=np.uint32)

    return vertices, indices_faces_t, indices_faces_q, indices_edges

# загрузка моделей из DXF файлов
def create_dxf_object(file_path, normalize=False):
    vertices, indices_faces_t, indices_faces_q, indices_edges = load_dxf_vertices(file_path, 1.0, normalize)

    colors = np.tile(np.array([0.3, 0.3, 0.3, 0.1], dtype=np.float32), (len(vertices), 1))
    colors_edges = np.tile(np.array([1.0, 1.0, 1.0], dtype=np.float32), (len(vertices), 1))
    colors_hovered = np.tile(np.array([1.0, 0.5, 0.0], dtype=np.float32), (len(vertices), 1))

    vertVBO = vbo.VBO(vertices.flatten().astype(np.float32))
    colorVBO = vbo.VBO(colors.flatten().astype(np.float32))

    mesh = ObjectMesh(vertVBO, colorVBO, indices_faces_t, indices_faces_q, indices_edges)

    mesh.colorsEdgesVBO = vbo.VBO(colors_edges.flatten().astype(np.float32))
    mesh.colorsHoveredVBO = vbo.VBO(colors_hovered.flatten().astype(np.float32))
    mesh.colorsSelectedVBO = vbo.VBO(colors_hovered.flatten().astype(np.float32))
    mesh.colorsEdgesActiveVBO = vbo.VBO(colors_edges.flatten().astype(np.float32))
    mesh.enableFaces = True

    min_v = vertices.min(axis=0)
    max_v = vertices.max(axis=0)
    collision = CollisionBox(glm.vec3(min_v), glm.vec3(max_v))

    center = (min_v + max_v) / 2.0

    obj = SceneObject(mesh, collision, center)
    print(f"Created dxf object with {len(vertices)} vertices")
    return obj


def create_cube():
    colors = np.array(
        [[0.0, 0.0, 0.0, 1.0],
         [1.0, 0.0, 0.0, 1.0],
         [1.0, 1.0, 0.0, 1.0],
         [0.0, 1.0, 0.0, 1.0],
         [0.0, 0.0, 1.0, 1.0],
         [1.0, 0.0, 1.0, 1.0],
         [1.0, 1.0, 1.0, 1.0],
         [0.0, 1.0, 1.0, 1.0]])
    colorVBO = vbo.VBO(np.reshape(colors,
                                  (1, -1)).astype(np.float32))

    colors_edges = np.tile(np.array([0.5, 0.13, 0.13], dtype=np.float32), (8, 1))
    colors_hovered = np.tile(np.array([1.0, 0.5, 0.0], dtype=np.float32), (8, 1))

    vertices = np.array(
        [[0.0, 0.0, 0.0],
         [1.0, 0.0, 0.0],
         [1.0, 1.0, 0.0],
         [0.0, 1.0, 0.0],
         [0.0, 0.0, 1.0],
         [1.0, 0.0, 1.0],
         [1.0, 1.0, 1.0],
         [0.0, 1.0, 1.0]])
    vertVBO = vbo.VBO(np.reshape(vertices,
                                 (1, -1)).astype(np.float32))

    indices_triangles = None

    indices_quads = np.array(
        [0, 1, 2, 3,
         3, 2, 6, 7,
         1, 0, 4, 5,
         2, 1, 5, 6,
         0, 3, 7, 4,
         7, 6, 5, 4])

    indices_edges = np.array(
        [0, 1,
         1, 2,
         2, 3,
         3, 0,
         0, 4,
         1, 5,
         2, 6,
         3, 7,
         4, 5,
         5, 6,
         6, 7,
         7, 4]
    )

    mesh = ObjectMesh(vertVBO, colorVBO, indices_triangles, indices_quads, indices_edges)

    mesh.colorsEdgesVBO = vbo.VBO(colors_edges.flatten().astype(np.float32))
    mesh.colorsHoveredVBO = vbo.VBO(colors_hovered.flatten().astype(np.float32))
    mesh.colorsSelectedVBO = vbo.VBO(colors_hovered.flatten().astype(np.float32))
    mesh.colorsEdgesActiveVBO = vbo.VBO(colors_edges.flatten().astype(np.float32))

    mesh.enableFaces = True
    collision = CollisionBox(glm.vec3([0.0, 0.0, 0.0]), glm.vec3([1.0, 1.0, 1.0]))
    origin = np.array([0.5, 0.5, 0.5])

    obj = SceneObject(mesh, collision, origin)
    return obj


# Я сделал это через DeepSeek и мне почти не стыдно
def create_sphere(meridians=16, parallels=16, color=[1.0, 0.0, 0.0, 1.0]):
    vertices = []
    for i in range(parallels + 1):
        theta = i * np.pi / parallels
        for j in range(meridians):
            phi = j * 2 * np.pi / meridians
            x = np.sin(theta) * np.cos(phi)
            y = np.sin(theta) * np.sin(phi)
            z = np.cos(theta)
            vertices.append([x, y, z])

    vertices = np.array(vertices, dtype=np.float32)

    vertices = vertices / 2 + 0.5

    vertVBO = vbo.VBO(vertices.flatten().astype(np.float32))

    colors = np.zeros((len(vertices), 4), dtype=np.float32)
    for i in range(len(vertices)):
        colors[i] = color
    colorVBO = vbo.VBO(colors.flatten().astype(np.float32))

    indices_triangles = []
    for i in range(parallels):
        for j in range(meridians):
            a = i * meridians + j
            b = i * meridians + (j + 1) % meridians
            c = (i + 1) * meridians + j
            d = (i + 1) * meridians + (j + 1) % meridians

            indices_triangles.extend([a, b, c])
            indices_triangles.extend([b, d, c])

    indices_triangles = np.array(indices_triangles, dtype=np.uint32)

    indices_edges = []
    for i in range(parallels):
        for j in range(meridians):
            current = i * meridians + j
            next_j = i * meridians + (j + 1) % meridians
            next_i = (i + 1) * meridians + j if i < parallels - 1 else None

            indices_edges.extend([current, next_j])

            if next_i is not None:
                indices_edges.extend([current, next_i])

    indices_edges = np.array(indices_edges, dtype=np.uint32)

    mesh = ObjectMesh(vertVBO, colorVBO, indices_triangles, None, indices_edges)

    colors_edges = np.tile(np.array([1.0, 1.0, 1.0], dtype=np.float32), (len(vertices), 1))
    colors_hovered = np.tile(np.array([1.0, 0.5, 0.0], dtype=np.float32), (len(vertices), 1))

    mesh.colorsEdgesVBO = vbo.VBO(colors_edges.flatten().astype(np.float32))
    mesh.colorsHoveredVBO = vbo.VBO(colors_hovered.flatten().astype(np.float32))
    mesh.colorsSelectedVBO = vbo.VBO(colors_hovered.flatten().astype(np.float32))
    mesh.colorsEdgesActiveVBO = vbo.VBO(colors_edges.flatten().astype(np.float32))

    mesh.enableFaces = True
    mesh.enableEdges = False

    collision = CollisionBox(glm.vec3([0.0, 0.0, 0.0]), glm.vec3([1.0, 1.0, 1.0]))
    origin = np.array([0.5, 0.5, 0.5])

    obj = SceneObject(mesh, collision, origin)
    return obj


def create_pyramid():
    colors = np.tile(np.array([1.0, 0.0, 1.0, 0.1], dtype=np.float32), (5, 1))
    colorVBO = vbo.VBO(np.reshape(colors,(1, -1)).astype(np.float32))

    colors_edges = np.tile(np.array([0.5, 0.13, 0.13], dtype=np.float32), (5, 1))
    colors_hovered = np.tile(np.array([1.0, 0.5, 0.0], dtype=np.float32), (5, 1))

    vertices = np.array(
        [[0.0, 0.0, 0.0],
         [1.0, 0.0, 0.0],
         [1.0, 0.0, 1.0],
         [0.0, 0.0, 1.0],
         [0.5, 1.0, 0.5]])
    vertVBO = vbo.VBO(np.reshape(vertices,
                                 (1, -1)).astype(np.float32))

    indices_triangles = np.array(
        [0, 1, 2,
         0, 2, 3,
         0, 1, 4,
         1, 2, 4,
         2, 3, 4,
         3, 0, 4])

    indices_quads = None

    indices_edges = np.array(
        [0, 1,
         1, 2,
         2, 3,
         3, 0,
         0, 4,
         1, 4,
         2, 4,
         3, 4]
    )

    mesh = ObjectMesh(vertVBO, colorVBO, indices_triangles, indices_quads, indices_edges)

    mesh.colorsEdgesVBO = vbo.VBO(colors_edges.flatten().astype(np.float32))
    mesh.colorsHoveredVBO = vbo.VBO(colors_hovered.flatten().astype(np.float32))
    mesh.colorsSelectedVBO = vbo.VBO(colors_hovered.flatten().astype(np.float32))
    mesh.colorsEdgesActiveVBO = vbo.VBO(colors_edges.flatten().astype(np.float32))

    mesh.enableFaces = True

    collision = CollisionBox(glm.vec3([0.0, 0.0, 0.0]), glm.vec3([1.0, 1.0, 1.0]))
    origin = np.array([0.5, 0.5, 0.5])

    obj = SceneObject(mesh, collision, origin)
    return obj

# создание детекторов и событий
def create_detector(id, x, y, z):
    obj = create_pyramid()
    obj.location = np.array([x, y, z])
    obj.obj_type = "detector"
    obj.data["id"] = id
    return obj


def create_event(x, y, z, event_type, energy):
    # Цвет зависит от энергии (скорректированные пороги для больших значений)
    if energy > 100000000000:  # > 100 млрд
        color = [1.0, 0.0, 0.0, 1.0]  # Красный - очень высокая энергия
    elif energy > 1000000000:   # > 1 млрд
        color = [1.0, 0.5, 0.0, 1.0]  # Оранжевый
    elif energy > 100000000:    # > 100 млн
        color = [1.0, 1.0, 0.0, 1.0]  # Желтый
    elif energy > 1000000:      # > 1 млн
        color = [0.0, 1.0, 0.0, 1.0]  # Зеленый
    elif energy > 1000:         # > 1 тыс
        color = [0.0, 0.0, 1.0, 1.0]  # Синий - низкая энергия
    else:
        color = [0.5, 0.5, 0.5, 1.0]  # Серый - очень низкая энергия

    obj = create_sphere(32, 32, color)
    obj.location = np.array([x, y, z])
    obj.obj_type = "event"
    obj.data["type"] = event_type
    obj.data["energy"] = energy
    return obj

