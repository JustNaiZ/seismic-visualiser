import math
import os

import ezdxf
import numpy as np
from OpenGL.arrays import vbo
from pyglm import glm
import OpenGL.GL as gl

from collisions import CollisionBox
from object_meshes import ObjectMesh
from scene_objects import SceneObject

def load_dxf_vertices(file_path, scale=1.0, normalize=False):
    try:
        doc = ezdxf.readfile(file_path)
    except Exception as e:
        print(f"Ошибка чтения DXF файла {file_path}: {e}")
        return (np.array([], dtype=np.float32),
                np.array([], dtype=np.uint32),
                np.array([], dtype=np.uint32),
                np.array([], dtype=np.uint32))

    msp = doc.modelspace()

    vertices = []
    indices_faces_t = []
    indices_faces_q = []
    indices_edges = []
    index_offset = 0

    print(f"=== ДИАГНОСТИКА DXF: {os.path.basename(file_path)} ===")

    # Собираем статистику по типам объектов
    entity_types = {}
    for entity in msp:
        entity_type = entity.dxftype()
        entity_types[entity_type] = entity_types.get(entity_type, 0) + 1

    print(f"Найдены объекты: {entity_types}")

    # Обрабатываем ВСЕ типы объектов
    for entity in msp:
        try:
            entity_type = entity.dxftype()

            # 1. ОБЫЧНЫЕ 3DFACE
            if entity_type == '3DFACE':
                pts = [(vertex.x, vertex.z, vertex.y) for vertex in entity.wcs_vertices(False)]
                if len(pts) > 0:
                    pts = np.array(pts, dtype=np.float32) * scale
                    vertices.extend(pts)

                    n = len(pts)
                    if n == 3:
                        indices_faces_t.extend([index_offset, index_offset + 1, index_offset + 2])
                        indices_edges.extend(
                            [index_offset, index_offset + 1, index_offset + 1, index_offset + 2, index_offset + 2,
                             index_offset])
                    elif n == 4:
                        indices_faces_q.extend([index_offset, index_offset + 1, index_offset + 2, index_offset + 3])
                        indices_edges.extend(
                            [index_offset, index_offset + 1, index_offset + 1, index_offset + 2, index_offset + 2,
                             index_offset + 3, index_offset + 3, index_offset])
                    index_offset += n

            # 2. INSERT + POLYLINE (ОСНОВНАЯ ПРОБЛЕМА - УЛУЧШАЕМ ОБРАБОТКУ)
            elif entity_type == 'INSERT':
                block_name = entity.dxf.name
                insert_location = entity.dxf.insert

                # УЧИТЫВАЕМ МАСШТАБ И ВРАЩЕНИЕ БЛОКА
                xscale = entity.dxf.xscale if hasattr(entity.dxf, 'xscale') else 1.0
                yscale = entity.dxf.yscale if hasattr(entity.dxf, 'yscale') else 1.0
                zscale = entity.dxf.zscale if hasattr(entity.dxf, 'zscale') else 1.0

                if block_name in doc.blocks:
                    block = doc.blocks[block_name]
                    block_vertices_count = 0

                    for block_entity in block:
                        block_type = block_entity.dxftype()
                        points = []

                        # ОБРАБАТЫВАЕМ РАЗНЫЕ ТИПЫ ОБЪЕКТОВ В БЛОКЕ
                        if block_type == 'POLYLINE':
                            if hasattr(block_entity, 'vertices'):
                                for vertex in block_entity.vertices:
                                    location = vertex.dxf.location
                                    # УЧИТЫВАЕМ ПОЗИЦИЮ, МАСШТАБ И ПОВОРОТ БЛОКА
                                    x = insert_location.x + location.x * xscale
                                    y = insert_location.y + location.y * yscale
                                    z = insert_location.z + (location.z if hasattr(location, 'z') else 0) * zscale
                                    points.append((x, z, y))

                        elif block_type == 'LWPOLYLINE':
                            if hasattr(block_entity, 'points'):
                                for point in block_entity.points():
                                    x = insert_location.x + point[0] * xscale
                                    y = insert_location.y + point[1] * yscale
                                    z = insert_location.z + (point[2] if len(point) > 2 else 0) * zscale
                                    points.append((x, z, y))

                        elif block_type == 'LINE':
                            start = block_entity.dxf.start
                            end = block_entity.dxf.end
                            points = [
                                (insert_location.x + start.x * xscale, insert_location.z + start.z * zscale,
                                 insert_location.y + start.y * yscale),
                                (insert_location.x + end.x * xscale, insert_location.z + end.z * zscale,
                                 insert_location.y + end.y * yscale)
                            ]

                        # ДОБАВЛЯЕМ ТОЧКИ В ОБЩИЙ МАССИВ
                        if points:
                            pts = np.array(points, dtype=np.float32) * scale
                            vertices.extend(pts)

                            # СОЗДАЕМ РЕБРА МЕЖДУ ТОЧКАМИ
                            if block_type in ['POLYLINE', 'LWPOLYLINE']:
                                for i in range(len(pts) - 1):
                                    indices_edges.extend([index_offset + i, index_offset + i + 1])

                                # ЗАМЫКАЕМ ЕСЛИ ПОЛИЛИНИЯ ЗАМКНУТА
                                if ((block_type == 'POLYLINE' and hasattr(block_entity,
                                                                          'is_closed') and block_entity.is_closed) or
                                    (block_type == 'LWPOLYLINE' and block_entity.closed)) and len(pts) > 2:
                                    indices_edges.extend([index_offset + len(pts) - 1, index_offset])

                            elif block_type == 'LINE':
                                indices_edges.extend([index_offset, index_offset + 1])

                            block_vertices_count += len(pts)
                            index_offset += len(pts)

                    if block_vertices_count > 0:
                        print(f"Обработан блок {block_name} с {block_vertices_count} вершинами")

            # 3. ОБЫЧНЫЕ LWPOLYLINE
            elif entity_type == 'LWPOLYLINE':
                try:
                    points = []
                    if hasattr(entity, 'points'):
                        for point in entity.points():
                            x = point[0]
                            y = point[1]
                            z = point[2] if len(point) > 2 else 0
                            points.append((x, z, y))

                    if points:
                        pts = np.array(points, dtype=np.float32) * scale
                        vertices.extend(pts)

                        # Создаем ребра между точками
                        for i in range(len(pts) - 1):
                            indices_edges.extend([index_offset + i, index_offset + i + 1])

                        # Замыкаем если полилиния замкнута
                        if entity.closed and len(pts) > 2:
                            indices_edges.extend([index_offset + len(pts) - 1, index_offset])

                        index_offset += len(pts)

                except Exception as lw_e:
                    print(f"Ошибка обработки LWPOLYLINE: {lw_e}")
                    continue

            # 4. ОБЫЧНЫЕ LINE
            elif entity_type == 'LINE':
                start = entity.dxf.start
                end = entity.dxf.end
                pts = [(start.x, start.z, start.y), (end.x, end.z, end.y)]
                pts = np.array(pts, dtype=np.float32) * scale
                vertices.extend(pts)
                indices_edges.extend([index_offset, index_offset + 1])
                index_offset += 2

        except Exception as e:
            print(f"Ошибка обработки объекта {entity_type}: {e}")
            continue

    print(
        f"Итог: вершин={len(vertices)}, граней={len(indices_faces_t) + len(indices_faces_q)}, ребер={len(indices_edges)}")

    if len(vertices) > 0:
        vertices_array = np.array(vertices, dtype=np.float32)
        min_coords = vertices_array.min(axis=0)
        max_coords = vertices_array.max(axis=0)
        center = (min_coords + max_coords) / 2.0

        print(f"Координаты: Min({min_coords[0]:.1f}, {min_coords[1]:.1f}, {min_coords[2]:.1f}) "
              f"Max({max_coords[0]:.1f}, {max_coords[1]:.1f}, {max_coords[2]:.1f})")
        print(
            f"Размер области: {max_coords[0] - min_coords[0]:.1f} x {max_coords[1] - min_coords[1]:.1f} x {max_coords[2] - min_coords[2]:.1f}")

    print("=" * 50)

    # Создаем заглушку только если совсем нет геометрии
    if len(vertices) == 0:
        print("Создаем объект-заглушку")
        vertices = np.array([
            [0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [1.0, 1.0, 0.0], [0.0, 1.0, 0.0],
            [0.0, 0.0, 1.0], [1.0, 0.0, 1.0], [1.0, 1.0, 1.0], [0.0, 1.0, 1.0]
        ], dtype=np.float32) * scale

        indices_faces_q = np.array([
            0, 1, 2, 3, 3, 2, 6, 7, 1, 0, 4, 5,
            2, 1, 5, 6, 0, 3, 7, 4, 7, 6, 5, 4
        ], dtype=np.uint32)

        indices_edges = np.array([
            0, 1, 1, 2, 2, 3, 3, 0, 0, 4, 1, 5,
            2, 6, 3, 7, 4, 5, 5, 6, 6, 7, 7, 4
        ], dtype=np.uint32)
    else:
        vertices = np.array(vertices, dtype=np.float32)
        indices_faces_t = np.array(indices_faces_t, dtype=np.uint32) if indices_faces_t else np.array([],
                                                                                                      dtype=np.uint32)
        indices_faces_q = np.array(indices_faces_q, dtype=np.uint32) if indices_faces_q else np.array([],
                                                                                                      dtype=np.uint32)
        indices_edges = np.array(indices_edges, dtype=np.uint32) if indices_edges else np.array([], dtype=np.uint32)

    if normalize and len(vertices) > 0:
        min_coords = vertices.min(axis=0)
        max_coords = vertices.max(axis=0)
        size = max_coords - min_coords
        if np.any(size > 0):
            vertices = (vertices - min_coords) / size

    return vertices, indices_faces_t, indices_faces_q, indices_edges

# загрузка моделей из DXF файлов
def create_dxf_object(file_path, normalize=False):
    vertices, indices_faces_t, indices_faces_q, indices_edges = load_dxf_vertices(file_path, 1.0, normalize)

    colors_edges = np.tile(np.array([0.9, 0.9, 0.9], dtype=np.float32), (len(vertices), 1))  # БЕЛЫЙ
    colors_faces = np.tile(np.array([0.3, 0.3, 0.3, 1.0], dtype=np.float32), (len(vertices), 1))
    colors_hovered = np.tile(np.array([1.0, 0.5, 0.0], dtype=np.float32), (len(vertices), 1))

    vertVBO = vbo.VBO(vertices.flatten().astype(np.float32))
    colorVBO = vbo.VBO(colors_faces.flatten().astype(np.float32))

    mesh = ObjectMesh(vertVBO, colorVBO, indices_faces_t, indices_faces_q, indices_edges)

    mesh.colorsEdgesVBO = vbo.VBO(colors_edges.flatten().astype(np.float32))
    mesh.colorsHoveredVBO = vbo.VBO(colors_hovered.flatten().astype(np.float32))
    mesh.colorsSelectedVBO = vbo.VBO(colors_hovered.flatten().astype(np.float32))
    mesh.colorsEdgesActiveVBO = vbo.VBO(colors_edges.flatten().astype(np.float32))

    mesh.enableFaces = len(indices_faces_t) + len(indices_faces_q) > 0
    mesh.enableEdges = True

    min_v = vertices.min(axis=0) if len(vertices) > 0 else np.array([0, 0, 0])
    max_v = vertices.max(axis=0) if len(vertices) > 0 else np.array([1, 1, 1])
    collision = CollisionBox(glm.vec3(min_v), glm.vec3(max_v))

    center = (min_v + max_v) / 2.0

    obj = SceneObject(mesh, collision, center)
    print(f"Создан DXF объект с ID: {obj.id}")
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
    mesh.enableEdges = False  # Оставляем как было

    collision = CollisionBox(glm.vec3([0.0, 0.0, 0.0]), glm.vec3([1.0, 1.0, 1.0]))
    origin = np.array([0.5, 0.5, 0.5])

    obj = SceneObject(mesh, collision, origin)
    return obj


def create_enhanced_sphere(meridians=32, parallels=32, base_color=[1.0, 0.0, 0.0, 1.0]):
    """Создает сферу со статическим двусторонним освещением"""
    if len(base_color) == 3:
        base_color = base_color + [1.0]

    # Извлекаем прозрачность ОДИН РАЗ
    sphere_alpha = base_color[3] if len(base_color) > 3 else 1.0  # ⚠️ ИЗМЕНИЛ ИМЯ

    vertices = []
    normals = []

    for i in range(parallels + 1):
        theta = i * np.pi / parallels
        for j in range(meridians):
            phi = j * 2 * np.pi / meridians
            x = np.sin(theta) * np.cos(phi)
            y = np.sin(theta) * np.sin(phi)
            z = np.cos(theta)
            vertices.append([x, y, z])
            normals.append([x, y, z])

    vertices = np.array(vertices, dtype=np.float32)
    normals = np.array(normals, dtype=np.float32)

    normals_length = np.linalg.norm(normals, axis=1)
    normals = normals / normals_length[:, np.newaxis]

    # СТАТИЧЕСКОЕ ДВУСТОРОННЕЕ ОСВЕЩЕНИЕ
    light_dir1 = np.array([0.7, 0.7, 0.3], dtype=np.float32)  # Сверху слева
    light_dir1 = light_dir1 / np.linalg.norm(light_dir1)

    light_dir2 = np.array([-0.7, -0.7, -0.3], dtype=np.float32)  # Снизу справа (противоположный)
    light_dir2 = light_dir2 / np.linalg.norm(light_dir2)

    colors_faces = []
    for normal in normals:
        # Первый источник света
        intensity1 = max(0.0, np.dot(normal, light_dir1))
        # Второй источник света (такая же интенсивность)
        intensity2 = max(0.0, np.dot(normal, light_dir2))

        # Комбинируем оба источника
        total_intensity = intensity1 + intensity2

        # Базовый цвет с освещением
        r = base_color[0] * (0.3 + 0.7 * total_intensity)
        g = base_color[1] * (0.3 + 0.7 * total_intensity)
        b = base_color[2] * (0.3 + 0.7 * total_intensity)

        # Добавляем блики от обоих источников
        specular1 = intensity1 ** 4 * 0.15
        specular2 = intensity2 ** 4 * 0.15

        r = min(1.0, r + specular1 + specular2)
        g = min(1.0, g + specular1 + specular2)
        b = min(1.0, b + specular1 + specular2)

        # ⚠️ ИСПОЛЬЗУЕМ sphere_alpha (сохраненную прозрачность)
        colors_faces.append([r, g, b, sphere_alpha])

    colors_faces = np.array(colors_faces, dtype=np.float32)

    vertVBO = vbo.VBO(vertices.flatten().astype(np.float32))
    colorVBO = vbo.VBO(colors_faces.flatten().astype(np.float32))

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

    indices_edges = np.array([], dtype=np.uint32)

    mesh = ObjectMesh(vertVBO, colorVBO, indices_triangles, None, indices_edges)

    colors_edges = np.tile(np.array([1.0, 1.0, 1.0], dtype=np.float32), (len(vertices), 1))
    colors_hovered = np.tile(np.array([1.0, 0.5, 0.0], dtype=np.float32), (len(vertices), 1))

    mesh.colorsEdgesVBO = vbo.VBO(colors_edges.flatten().astype(np.float32))
    mesh.colorsHoveredVBO = vbo.VBO(colors_hovered.flatten().astype(np.float32))
    mesh.colorsSelectedVBO = vbo.VBO(colors_hovered.flatten().astype(np.float32))
    mesh.colorsEdgesActiveVBO = vbo.VBO(colors_edges.flatten().astype(np.float32))

    mesh.enableFaces = True
    mesh.enableEdges = False

    collision = CollisionBox(glm.vec3([-0.5, -0.5, -0.5]), glm.vec3([0.5, 0.5, 0.5]))
    origin = np.array([0.0, 0.0, 0.0])

    obj = SceneObject(mesh, collision, origin)

    # ⚠️ СОХРАНЯЕМ ПРАВИЛЬНУЮ ПРОЗРАЧНОСТЬ
    obj.current_opacity = sphere_alpha
    if hasattr(obj, 'base_color'):
        obj.base_color = list(base_color[:3]) + [sphere_alpha]

    return obj

def create_beach_ball_hosohedron(base_color=[1.0, 0.0, 0.0, 1.0]):
    """Создает квадратный осоэдр {2,4} с шейдерами - С ПРОЗРАЧНОСТЬЮ"""
    # Гарантируем RGBA формат с прозрачностью
    if len(base_color) == 3:
        base_color = base_color + [1.0]

    ball_alpha = base_color[3]

    segments = 32
    vertices = []
    normals = []
    colors_faces = []

    # Создаем сферу с нормалями
    for i in range(segments + 1):
        theta = i * np.pi / segments
        for j in range(segments):
            phi = j * 2 * np.pi / segments

            x = np.sin(theta) * np.cos(phi)
            y = np.sin(theta) * np.sin(phi)
            z = np.cos(theta)

            vertices.append([x, y, z])
            normals.append([x, y, z])

            # Определяем долю по долготе (4 доли)
            sector = int(phi / (np.pi / 2)) % 4

            # Четные доли - белые, нечетные - цвет события
            if sector % 2 == 0:
                face_color = [1.0, 1.0, 1.0, ball_alpha]  # ⚠️ БЕЛЫЙ С ПРОЗРАЧНОСТЬЮ
            else:
                face_color = [base_color[0], base_color[1], base_color[2], ball_alpha]  # ЦВЕТ С ПРОЗРАЧНОСТЬЮ

            # Применяем освещение
            light_dir = np.array([0.7, 0.7, 0.3], dtype=np.float32)
            light_dir = light_dir / np.linalg.norm(light_dir)

            normal = np.array([x, y, z])
            normal = normal / np.linalg.norm(normal)

            intensity = max(0.2, np.dot(normal, light_dir))

            r = face_color[0] * (0.4 + 0.6 * intensity)
            g = face_color[1] * (0.4 + 0.6 * intensity)
            b = face_color[2] * (0.4 + 0.6 * intensity)

            specular = intensity ** 4 * 0.3

            r = min(1.0, r + specular)
            g = min(1.0, g + specular)
            b = min(1.0, b + specular)
            a = ball_alpha  # ⚠️ СОХРАНЯЕМ ПРОЗРАЧНОСТЬ

            colors_faces.append([r, g, b, ball_alpha])

    vertices = np.array(vertices, dtype=np.float32)
    colors_faces = np.array(colors_faces, dtype=np.float32)

    # Создаем индексы
    indices_triangles = []
    for i in range(segments):
        for j in range(segments):
            a = i * segments + j
            b = i * segments + (j + 1) % segments
            c = (i + 1) * segments + j
            d = (i + 1) * segments + (j + 1) % segments

            indices_triangles.extend([a, b, c])
            indices_triangles.extend([b, d, c])

    indices_triangles = np.array(indices_triangles, dtype=np.uint32)
    indices_edges = np.array([], dtype=np.uint32)

    # Создаем VBO
    vertVBO = vbo.VBO(vertices.flatten().astype(np.float32))
    colorVBO = vbo.VBO(colors_faces.flatten().astype(np.float32))

    mesh = ObjectMesh(vertVBO, colorVBO, indices_triangles, None, indices_edges)

    colors_edges = np.tile(np.array([0.0, 0.0, 0.0], dtype=np.float32), (len(vertices), 1))
    colors_hovered = np.tile(np.array([1.0, 0.5, 0.0], dtype=np.float32), (len(vertices), 1))

    mesh.colorsEdgesVBO = vbo.VBO(colors_edges.flatten().astype(np.float32))
    mesh.colorsHoveredVBO = vbo.VBO(colors_hovered.flatten().astype(np.float32))
    mesh.colorsSelectedVBO = vbo.VBO(colors_hovered.flatten().astype(np.float32))
    mesh.colorsEdgesActiveVBO = vbo.VBO(colors_edges.flatten().astype(np.float32))

    mesh.enableFaces = True
    mesh.enableEdges = False

    collision = CollisionBox(glm.vec3([-0.5, -0.5, -0.5]), glm.vec3([0.5, 0.5, 0.5]))
    origin = np.array([0.0, 0.0, 0.0])

    obj = SceneObject(mesh, collision, origin)

    # Сохраняем цвет и прозрачность
    obj.base_color = base_color
    obj.current_opacity = ball_alpha

    return obj

def create_enhanced_beach_ball(base_color=[1.0, 0.0, 0.0, 1.0]):
    """Создает квадратный осоэдр {2,4} с шейдерами но БЕЗ градиентов"""

    vertices = []
    normals = []
    colors_faces = []

    segments = 32

    # Создаем сферу с нормалями для освещения
    for i in range(segments + 1):
        theta = i * np.pi / segments
        for j in range(segments):
            phi = j * 2 * np.pi / segments

            x = np.sin(theta) * np.cos(phi)
            y = np.sin(theta) * np.sin(phi)
            z = np.cos(theta)

            vertices.append([x, y, z])
            normals.append([x, y, z])

            # Определяем долю по долготе (4 доли)
            sector = int(phi / (np.pi / 2)) % 4  # 0,1,2,3

            # Четные доли - белые, нечетные - цвет события
            # ЖЕСТКИЙ ПЕРЕХОД - без градиентов между цветами!
            if sector % 2 == 0:
                face_color = [1.0, 1.0, 1.0, 1.0]  # Чисто белый
            else:
                face_color = base_color  # Чистый цвет события

            # Применяем шейдеры К КАЖДОМУ ЦВЕТУ ОТДЕЛЬНО
            light_dir = np.array([0.7, 0.7, 0.3], dtype=np.float32)
            light_dir = light_dir / np.linalg.norm(light_dir)

            normal = np.array([x, y, z])
            normal = normal / np.linalg.norm(normal)

            intensity = max(0.2, np.dot(normal, light_dir))

            # Применяем освещение к выбранному цвету
            r = face_color[0] * (0.4 + 0.6 * intensity)
            g = face_color[1] * (0.4 + 0.6 * intensity)
            b = face_color[2] * (0.4 + 0.6 * intensity)

            specular = intensity ** 4 * 0.3

            r = min(1.0, r + specular)
            g = min(1.0, g + specular)
            b = min(1.0, b + specular)

            colors_faces.append([r, g, b, face_color[3]])

    vertices = np.array(vertices, dtype=np.float32)
    colors_faces = np.array(colors_faces, dtype=np.float32)

    # Создаем индексы для треугольников
    indices_triangles = []
    for i in range(segments):
        for j in range(segments):
            a = i * segments + j
            b = i * segments + (j + 1) % segments
            c = (i + 1) * segments + j
            d = (i + 1) * segments + (j + 1) % segments

            indices_triangles.extend([a, b, c])
            indices_triangles.extend([b, d, c])

    indices_triangles = np.array(indices_triangles, dtype=np.uint32)

    # Индексы для черных линий на стыках долей
    indices_edges = []

    # 4 вертикальных линии меридианов (стыки долей)
    for k in range(4):
        meridian_angle = k * np.pi / 2  # 0°, 90°, 180°, 270°
        meridian_idx = int(meridian_angle * segments / (2 * np.pi))

        # Меридиан от северного полюса к южному
        for i in range(segments):
            current = i * segments + meridian_idx
            next_i = (i + 1) * segments + meridian_idx
            indices_edges.extend([current, next_i])

    indices_edges = np.array(indices_edges, dtype=np.uint32)

    # Создаем VBO
    vertVBO = vbo.VBO(vertices.flatten().astype(np.float32))
    colorVBO = vbo.VBO(colors_faces.flatten().astype(np.float32))

    mesh = ObjectMesh(vertVBO, colorVBO, indices_triangles, None, indices_edges)

    # Черные ребра для контраста
    colors_edges = np.tile(np.array([0.0, 0.0, 0.0], dtype=np.float32), (len(vertices), 1))
    colors_hovered = np.tile(np.array([1.0, 0.5, 0.0], dtype=np.float32), (len(vertices), 1))

    mesh.colorsEdgesVBO = vbo.VBO(colors_edges.flatten().astype(np.float32))
    mesh.colorsHoveredVBO = vbo.VBO(colors_hovered.flatten().astype(np.float32))
    mesh.colorsSelectedVBO = vbo.VBO(colors_hovered.flatten().astype(np.float32))
    mesh.colorsEdgesActiveVBO = vbo.VBO(colors_edges.flatten().astype(np.float32))

    mesh.enableFaces = True
    mesh.enableEdges = True  # Включаем отображение черных линий

    collision = CollisionBox(glm.vec3([-0.5, -0.5, -0.5]), glm.vec3([0.5, 0.5, 0.5]))
    origin = np.array([0.0, 0.0, 0.0])

    obj = SceneObject(mesh, collision, origin)
    return obj


def create_point(base_color=[1.0, 0.0, 0.0, 1.0]):
    """Создает маленькую точку для отображения событий - С ПРОЗРАЧНОСТЬЮ"""
    # Гарантируем RGBA формат
    if len(base_color) == 3:
        base_color = base_color + [1.0]

    # Используем enhanced_sphere с прозрачностью
    obj = create_enhanced_sphere(8, 8, base_color)

    # Сохраняем прозрачность
    if hasattr(obj, 'base_color'):
        obj.base_color = base_color
    if hasattr(obj, 'current_opacity'):
        obj.current_opacity = base_color[3] if len(base_color) > 3 else 1.0

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

def create_event(x, y, z, event_type, energy, custom_color=None, opacity=1.0):
    """Создает событие с возможностью указать цвет и прозрачность"""
    if custom_color is not None:
        # Если передан custom_color, используем его как есть (должен быть RGBA)
        if len(custom_color) == 4:
            base_color = custom_color  # Уже RGBA
        elif len(custom_color) == 3:
            base_color = custom_color + [1.0]  # Добавляем альфа
        else:
            # На всякий случай
            base_color = [1.0, 0.0, 0.0, 1.0]
    else:
        # Цвет по энергии с прозрачностью (по умолчанию opacity=1.0)
        if energy > 100000000000:
            base_color = [1.0, 0.0, 0.0, opacity]
        elif energy > 1000000000:
            base_color = [1.0, 0.5, 0.0, opacity]
        elif energy > 100000000:
            base_color = [1.0, 1.0, 0.0, opacity]
        elif energy > 1000000:
            base_color = [0.0, 1.0, 0.0, opacity]
        elif energy > 1000:
            base_color = [0.0, 0.0, 1.0, opacity]
        else:
            base_color = [0.5, 0.5, 0.5, opacity]

    # ИСПОЛЬЗУЕМ УЛУЧШЕННУЮ СФЕРУ И ПЕРЕДАЕМ ЕЙ RGBA ЦВЕТ
    obj = create_enhanced_sphere(32, 32, base_color)

    obj.location = np.array([x, y, z])
    obj.obj_type = "event"
    obj.data["type"] = event_type
    obj.data["energy"] = energy
    obj.base_color = base_color  # Сохраняем цвет
    obj.current_opacity = base_color[3] if len(base_color) > 3 else 1.0  # Сохраняем прозрачность

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

    return obj