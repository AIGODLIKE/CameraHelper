import gpu
# import bgl
from contextlib import contextmanager

@contextmanager
def wrap_gpu_state():
    gpu.state.blend_set('ALPHA')
    yield
    gpu.state.blend_set('NONE')

@contextmanager
def wrap_bgl_restore(width):
    # bgl.glEnable(bgl.GL_BLEND)
    # bgl.glEnable(bgl.GL_LINE_SMOOTH)
    # bgl.glEnable(bgl.GL_DEPTH_TEST)
    # bgl.glLineWidth(width)
    # bgl.glPointSize(8)
    ori_blend = gpu.state.blend_get()
    gpu.state.blend_set('ALPHA')
    gpu.state.line_width_set(width)
    gpu.state.point_size_set(8)

    yield  # do the work
    # restore opengl defaults
    # bgl.glDisable(bgl.GL_BLEND)
    # bgl.glDisable(bgl.GL_LINE_SMOOTH)
    # bgl.glEnable(bgl.GL_DEPTH_TEST)
    # bgl.glLineWidth(1)
    # bgl.glPointSize(5)
    gpu.state.blend_set(ori_blend)
    gpu.state.line_width_set(1)
    gpu.state.point_size_set(5)