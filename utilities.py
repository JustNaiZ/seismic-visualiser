import OpenGL.GL as gl
from pyglm import glm
from pyglm.glm import sin, cos, inverse

# создает матрицу полного 3D поворота
def full_rotation(ax, ay, az):
    return glm.mat3(cos(ay) * cos(az), sin(ax) * sin(ay) * cos(az) - cos(ax) * sin(az), cos(ax) * sin(ay) * cos(az) + sin(ax) * sin(az),
             cos(ay) * sin(az), sin(ax) * sin(ay) * sin(az) + cos(ax) * cos(az), cos(ax) * sin(ay) * sin(az) - sin(ax) * cos(az),
             -sin(ay), sin(ax) * cos(ay), cos(ax) * cos(ay))

# умножение матрицы 4x4 на вектор 4D
def mul_mat4_vec4(a, b):
    return glm.vec4(*[sum(a[i][j] * b[j] for j in range(4)) for i in range(4)])

# преобразует координаты мыши в 3D луч в мировом пространстве
def screen_pos_to_vector(x, y, width, height, camera, target):
    view = glm.transpose(glm.lookAt(camera, target, glm.vec3([0.0, 1.0, 0.0])))
    projection = gl.glGetDouble(gl.GL_PROJECTION_MATRIX)
    # print(view)
    # print(projection)
    ray_start = glm.vec4((x / width - 0.5) * 2.0,
                         (y / height - 0.5) * 2.0,
                         -1.0,
                         1.0)
    ray_end = glm.vec4((x / width - 0.5) * 2.0,
                         (y / height - 0.5) * 2.0,
                         0.0,
                         1.0)
    inverse_projection = glm.inverse(projection)
    inverse_view = glm.inverse(view)

    ray_start_cam = mul_mat4_vec4(inverse_projection, ray_start)
    ray_start_cam /= ray_start_cam.w
    ray_start_world = mul_mat4_vec4(inverse_view, ray_start_cam)
    ray_start_world /= ray_start_world.w

    ray_end_cam = mul_mat4_vec4(inverse_projection, ray_end)
    ray_end_cam /= ray_end_cam.w
    ray_end_world = mul_mat4_vec4(inverse_view, ray_end_cam)
    ray_end_world /= ray_start_world.w

    return glm.normalize(glm.vec3(ray_end_world - ray_start_world))
