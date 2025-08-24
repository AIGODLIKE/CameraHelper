import gpu
from gpu_extras.batch import batch_for_shader


def draw_box(x1, x2, y1, y2, color=[0, 0, 0, 0.5]):
    indices = ((0, 1, 2), (2, 1, 3))

    vertices = ((x1, y1), (x2, y1), (x1, y2), (x2, y2))
    # draw area
    shader = gpu.shader.from_builtin('UNIFORM_COLOR')
    batch = batch_for_shader(shader,
                             'TRIS', {"pos": vertices},
                             indices=indices)
    shader.bind()
    shader.uniform_float("color", color)
    batch.draw(shader)
