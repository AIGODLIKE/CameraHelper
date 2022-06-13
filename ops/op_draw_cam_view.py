import bpy
import gpu

from gpu_extras.presets import draw_texture_2d
from gpu.shader import from_builtin as get_builtin_shader
from gpu_extras.batch import batch_for_shader
from mathutils import Vector

WIDTH = 512
HEIGHT = 256
PADDING = 20

offscreen = gpu.types.GPUOffScreen(WIDTH, HEIGHT)
indices = ((0, 1, 2), (2, 1, 3))


def get_verts(x, y, w, h, t):
    return ((x - t, y - t), (x + w + t, y - t), (x - t, y + h + t), (x + w + t, y + h + t))


def draw():
    context = bpy.context
    scene = context.scene
    # draw camera view
    view_matrix = scene.camera.matrix_world.inverted()

    projection_matrix = scene.camera.calc_matrix_camera(
        context.evaluated_depsgraph_get(), x=WIDTH, y=HEIGHT)

    offscreen.draw_view3d(
        scene,
        context.view_layer,
        context.space_data,
        context.region,
        view_matrix,
        projection_matrix,
        do_color_management=False)

    gpu.state.depth_mask_set(False)
    draw_texture_2d(offscreen.texture_color, (10, 10), WIDTH, HEIGHT)

def draw_shadow():
    # draw shadow
    shader = get_builtin_shader('2D_UNIFORM_COLOR')
    shader.bind()
    shader.uniform_float('color', (0.5, 0.5, 0.5, 0.5))

    position = Vector((
        0 - WIDTH - PADDING,
        0 + PADDING
    ))

    b = batch_for_shader(
        shader, 'TRIS',
        {
            "pos": get_verts(*position, WIDTH, HEIGHT, PADDING)
        },
        indices=indices)

    b.draw(shader)

if __name__ == '__main__':
    bpy.types.SpaceView3D.draw_handler_add(draw, (), 'WINDOW', 'POST_PIXEL')
    bpy.types.SpaceView3D.draw_handler_add(draw_shadow, (), 'WINDOW', 'POST_PIXEL')
