# import bgl
import gpu
import bpy

from gpu_extras.presets import draw_texture_2d
from gpu.shader import from_builtin as get_builtin_shader
from gpu_extras.batch import batch_for_shader

from mathutils import Vector
from gpu_extras.batch import batch_for_shader
from ..utils import get_mesh_obj_coords
from ...prefs.get_pref import get_pref


WIDTH = 512
HEIGHT = 256
PADDING = 20

indices = ((0, 1, 2), (2, 1, 3))

from . import wrap_bgl_restore

def get_shader(type = '3d'):
    shader_3d = gpu.shader.from_builtin('3D_UNIFORM_COLOR')
    shader_2d = gpu.shader.from_builtin('2D_UNIFORM_COLOR')
    shader_debug = gpu.shader.from_builtin('2D_UNIFORM_COLOR')
    shader_tex = gpu.shader.from_builtin('2D_IMAGE')

    if type == '3d':
        return shader_3d
    elif type == '2d':
        return shader_2d
    elif type == 'debug':
        return shader_debug
    elif type == 'tex':
        return shader_tex

def get_start_point(thumb_width, thumb_height):
    padding = 10
    area = bpy.context.area
    position = get_pref().camera_thumb.position

    if position == 'TOP_LEFT':
        right = False
        top = True
    elif position == 'TOP_RIGHT':
        right = True
        top = True
    elif position == 'BOTTOM_LEFT':
        right = False
        top = False
    else:
        right = True
        top = False

    ui_width = toolbar_width = header_height = tool_header_height = 0
    if area.spaces[0].show_region_toolbar and bpy.context.preferences.system.use_region_overlap:
        for region in area.regions:
            if region.type == 'UI':
                ui_width = region.width
            elif region.type == 'TOOLS':
                toolbar_width = region.width
            elif region.type == 'HEADER':
                header_height = region.height
            elif region.type == 'TOOL_HEADER':
                tool_header_height = region.height

    header_height += tool_header_height

    if right:
        w = area.width - ui_width - thumb_width - padding
    else:
        w = padding + toolbar_width

    if top:
        h = area.height - header_height - thumb_height - padding
    else:
        h = padding
    return (w, h)


class CameraMotionPath():

    def __init__(self, context, deps):
        self.context = context
        self.deps = deps

    def __call__(self, context):
        self.draw(context)

    def draw(self, context):
        self.draw_callback_bezier_3d(context)

    def draw_callback_bezier_3d(self, context):
        if context.object is None: return

        path = context.object.motion_cam.path
        path_attr = context.object.motion_cam.path_attr
        path_mesh = context.object.motion_cam.path_mesh

        if path is None or path_attr is None or path_mesh is None:
            return

        points = get_mesh_obj_coords(context, path_mesh, self.deps)
        # print(points)
        if len(points) == 0:
            return
        # 从点绘制连续线条
        draw_points = list()
        for i, p in enumerate(points):
            if i == 0 or i == len(points) - 1:
                draw_points.append(p)
            else:
                draw_points.append(p)
                draw_points.append(p)

        # if context.object.motion_cam.path_points == '': return

        with wrap_bgl_restore(width=get_pref().draw_motion_curve.width):

            shader_3d =get_shader('3d')
            shader_3d.bind()
            shader_3d.uniform_float("color", get_pref().draw_motion_curve.color)
            batch = batch_for_shader(shader_3d, 'LINES', {"pos": draw_points})
            batch.draw(shader_3d)


class CameraThumb():

    def __init__(self, context, deps):
        self.context = context
        self.deps = deps
        self.offscreen = gpu.types.GPUOffScreen(WIDTH, HEIGHT)
        self.cam = None
        self.buffer = None
        self.snapshot = context.scene.camhp_snap_shot_image

        self.max_width = get_pref().camera_thumb.max_width
        self.max_height = get_pref().camera_thumb.max_height

        self.update_cam(context)
        self.update_resolution(context)

    def __call__(self, context):
        self.draw(context)

    def draw(self, context):
        if context.scene.camhp_pv.enable:
            self.draw_border(context)
            self.draw_camera_thumb(context)

    def update_resolution(self, context):
        max_height = self.max_width
        max_width = self.max_height
        self.height = max_height
        self.ratio = context.scene.render.resolution_x / context.scene.render.resolution_y
        self.width = int(self.height * self.ratio)
        if self.width > max_width:
            self.width = max_width
            self.height = int(self.width / self.ratio)

    def update_cam(self, context):
        if context.scene.camhp_pv.pin:
            cam = context.scene.camhp_pv.pin_cam
        else:
            cam = context.object

        self.cam = cam

    def draw_camera_thumb(self, context):
        self.update_cam(context)
        self.update_resolution(context)

        show_overlay = False
        scene = context.scene
        # matrix
        view_matrix = self.cam.matrix_world.inverted()
        projection_matrix = self.cam.calc_matrix_camera(self.deps, x=self.width, y=self.height)
        # set space data
        ori_show_overlay = context.space_data.overlay.show_overlays
        context.space_data.overlay.show_overlays = show_overlay

        self.offscreen.draw_view3d(
            scene,
            context.view_layer,
            context.space_data,
            context.region,
            view_matrix,
            projection_matrix,
            do_color_management=False)
        gpu.state.depth_mask_set(False)
        context.space_data.overlay.show_overlays = ori_show_overlay
        start = get_start_point(self.width, self.height)
        draw_texture_2d(self.offscreen.texture_color, start, self.width, self.height)

        framebuffer = gpu.state.active_framebuffer_get()
        buffer = framebuffer.read_color(*start, self.width, self.height, 4, 0, 'FLOAT')
        buffer.dimensions = self.width * self.height * 4
        self.buffer = buffer

        # restore
        context.space_data.overlay.show_overlays = ori_show_overlay

    def draw_border(self, context):
        border_color = (0.5, 0.5, 0.5, 1)

        def get_verts(x, y, w, h, t): return (
            (x - t, y - t), (x + w + t, y - t), (x - t, y + h + t), (x + w + t, y + h + t))

        indices = ((0, 1, 2), (2, 1, 3))

        # bgl.glEnable(bgl.GL_BLEND)
        # bgl.glEnable(bgl.GL_LINE_SMOOTH)
        # bgl.glEnable(bgl.GL_DEPTH_TEST)
        shader_2d = get_shader('2d')
        shader_2d.bind()
        start = get_start_point(self.width, self.height)
        # shadow
        shader_2d.uniform_float('color', (0.15, 0.15, 0.15, 0.15))
        batch = batch_for_shader(
            shader_2d, 'TRIS',
            {
                "pos": get_verts(*start, self.width, self.height, 5)
            },
            indices=indices)
        batch.draw(shader_2d)

        # border
        shader_2d.uniform_float('color', border_color)
        border_batch = batch_for_shader(
            shader_2d, 'TRIS',
            {
                "pos": get_verts(*start, self.width, self.height, 1)
            },
            indices=indices)
        border_batch.draw(shader_2d)

        # bgl.glDisable(bgl.GL_BLEND)
        # bgl.glDisable(bgl.GL_LINE_SMOOTH)
        # bgl.glEnable(bgl.GL_DEPTH_TEST)
