# import bgl
import blf
import bpy
import gpu
from gpu_extras.batch import batch_for_shader
from gpu_extras.presets import draw_texture_2d

WIDTH = 512
HEIGHT = 256
PADDING = 20

indices = ((0, 1, 2), (2, 1, 3))


def ui_scale():
    # return bpy.context.preferences.system.dpi * bpy.context.preferences.system.pixel_size / 72
    # since blender 4.0, the bpy.context.preferences.system.pixel_size will jump from 1~2 while the ui scale tweak from 1.18~1.19
    return bpy.context.preferences.system.dpi * 1 / 72


def get_shader(type='3d'):
    if bpy.app.version < (4, 0, 0):
        shader_3d = gpu.shader.from_builtin('3D_UNIFORM_COLOR')
        shader_2d = gpu.shader.from_builtin('2D_UNIFORM_COLOR')
        shader_debug = gpu.shader.from_builtin('2D_UNIFORM_COLOR')
        shader_tex = gpu.shader.from_builtin('2D_IMAGE')
    else:
        shader_3d = gpu.shader.from_builtin('UNIFORM_COLOR')
        shader_2d = gpu.shader.from_builtin('UNIFORM_COLOR')
        shader_debug = gpu.shader.from_builtin('UNIFORM_COLOR')
        shader_tex = gpu.shader.from_builtin('IMAGE')

    if type == '3d':
        return shader_3d
    elif type == '2d':
        return shader_2d
    elif type == 'debug':
        return shader_debug
    elif type == 'tex':
        return shader_tex


def wrap_blf_size(font_id: int, size):
    if bpy.app.version >= (4, 0, 0):
        blf.size(font_id, size)
    else:
        blf.size(font_id, size, 72)


def get_style_font_size() -> int:
    style = bpy.context.preferences.ui_styles[0]
    if widget_label := getattr(style, "widget_label", None):
        return int(widget_label.points * ui_scale())
    elif widget := getattr(style, "widget", None):
        return int(widget.points)
    return 10


def get_start_point(thumb_width, thumb_height, index=0):
    # const
    padding = int(10 * ui_scale())
    font_size = int(get_style_font_size())
    text_height = int(font_size * 3)  # 2 line text and padding
    stats_height = int(font_size * 6 + padding * 5)  # 5 line text and padding
    # get area
    area = bpy.context.area
    show_text = area.spaces[0].overlay.show_text
    show_stats = area.spaces[0].overlay.show_stats

    position = 'TOP_LEFT'

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

    ui_width = toolbar_width = header_height = tool_header_height = asset_shelf_width = 0
    if bpy.context.preferences.system.use_region_overlap:
        for region in area.regions:
            if region.type == 'UI':
                ui_width = region.width
            elif region.type == 'TOOLS':
                toolbar_width = region.width
            elif region.type == 'HEADER':
                header_height = region.height
            elif region.type == 'TOOL_HEADER':
                tool_header_height = region.height
            elif region.type == 'ASSET_shelf':
                asset_shelf_width = region.width

    header_height += tool_header_height
    if show_text:
        header_height += text_height
    if show_stats:
        header_height += stats_height

    if right:
        w = area.width - ui_width - thumb_width - padding
    else:
        w = padding + toolbar_width

    if top:
        h = area.height - header_height - thumb_height - padding
    else:
        h = padding

    if index != 0:
        h = h - index * (thumb_height + padding)

    return (w, h)


class CameraThumb:
    border_width = 5

    def __init__(self, context, deps):
        self.context = context
        self.deps = deps
        self.offscreen = gpu.types.GPUOffScreen(WIDTH, HEIGHT)
        self.cam = None
        self.buffer = None
        self.snapshot = context.window_manager.camhp_snap_shot_image

        self.max_width = get_pref().camera_thumb.max_width
        self.max_height = get_pref().camera_thumb.max_height

        self.update_cam(context)
        self.update_resolution(context)

    def __call__(self, context):
        self.draw(context)

    def draw(self, context):
        if context.window_manager.camhp_pv.enable:
            self.draw_border(context)
            self.draw_camera_thumb(context)

    def update_resolution(self, context):
        max_height = get_pref().camera_thumb.max_width
        max_width = get_pref().camera_thumb.max_height
        self.height = max_height
        self.ratio = context.scene.render.resolution_x / context.scene.render.resolution_y
        self.width = int(self.height * self.ratio)
        if self.width > max_width:
            self.width = max_width
            self.height = int(self.width / self.ratio)

    def update_cam(self, context):
        try:
            if context.window_manager.camhp_pv.pin:
                cam = context.window_manager.camhp_pv.pin_cam
            else:
                cam = context.object

            self.cam = cam
        except ReferenceError:
            # delete class
            context.window_manager.camhp_pv.pin = False

    def draw_camera_thumb(self, context):
        try:
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

            # color management, if version is >= 5.0.0, the screen color space will be linear by default
            do_color_management = (bpy.app.version >= (5, 0, 0))
            self.offscreen.draw_view3d(
                scene,
                context.view_layer,
                context.space_data,
                context.region,
                view_matrix,
                projection_matrix,
                do_color_management=do_color_management)
            gpu.state.depth_mask_set(False)
            context.space_data.overlay.show_overlays = ori_show_overlay
            start = get_start_point(self.width + self.border_width, self.height + self.border_width)
            draw_texture_2d(self.offscreen.texture_color, start, self.width, self.height)

            framebuffer = gpu.state.active_framebuffer_get()
            buffer = framebuffer.read_color(*start, self.width, self.height, 4, 0, 'FLOAT')
            buffer.dimensions = self.width * self.height * 4
            self.buffer = buffer

            # restore
            context.space_data.overlay.show_overlays = ori_show_overlay
        except Exception as e:
            print(e)

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
        start = get_start_point(self.width + self.border_width, self.height + self.border_width)
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
