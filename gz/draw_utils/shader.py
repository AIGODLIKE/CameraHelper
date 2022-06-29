import bgl
import gpu
import bpy

from gpu_extras.presets import draw_texture_2d
from gpu.shader import from_builtin as get_builtin_shader
from gpu_extras.batch import batch_for_shader

from mathutils import Vector
from gpu_extras.batch import batch_for_shader
from ...ops.utils import get_mesh_obj_coords
from ...prefs.get_pref import get_pref

shader_3d = gpu.shader.from_builtin('3D_UNIFORM_COLOR')

WIDTH = 512
HEIGHT = 256
PADDING = 20

offscreen = gpu.types.GPUOffScreen(WIDTH, HEIGHT)
indices = ((0, 1, 2), (2, 1, 3))


class CameraMotionPath():

    def __init__(self, context):
        self.context = context

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

        points = get_mesh_obj_coords(context, path_mesh)
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

        bgl.glEnable(bgl.GL_BLEND)
        bgl.glEnable(bgl.GL_LINE_SMOOTH)
        bgl.glEnable(bgl.GL_DEPTH_TEST)

        bgl.glLineWidth(get_pref().draw_motion_curve.width)
        shader_3d.bind()
        shader_3d.uniform_float("color", get_pref().draw_motion_curve.color)
        batch = batch_for_shader(shader_3d, 'LINES', {"pos": draw_points})
        batch.draw(shader_3d)

        # restore opengl defaults
        bgl.glLineWidth(1)
        bgl.glDisable(bgl.GL_BLEND)
        bgl.glDisable(bgl.GL_LINE_SMOOTH)
        bgl.glEnable(bgl.GL_DEPTH_TEST)


# class CameraThumb():
#
#     def __init__(self, context):
#         self.context = context
#
#     def __call__(self, context):
#         self.draw(context)
#
#     def draw(self, context):
#         if context.object and context.object.type == 'CAMERA':
#             scene = context.scene
#
#             view_matrix = scene.camera.matrix_world.inverted()
#
#             projection_matrix = scene.camera.calc_matrix_camera(
#                 context.evaluated_depsgraph_get(), x=WIDTH, y=HEIGHT)
#
#             offscreen.draw_view3d(
#                 scene,
#                 context.view_layer,
#                 context.space_data,
#                 context.region,
#                 view_matrix,
#                 projection_matrix,
#                 do_color_management=False)
#
#             gpu.state.depth_mask_set(False)
#             draw_texture_2d(offscreen.texture_color, (10, 10), WIDTH, HEIGHT)


from gpu.types import GPUOffScreen
from gpu_extras.presets import draw_texture_2d as draw_tex

from blf import (
    draw as text_draw,
    size as text_set_size,
    color as text_set_color,
    position as text_set_position,
    enable as text_enable,
    disable as text_disable,
    shadow as text_set_shadow,
    shadow_offset as text_set_shadow_offset,
    SHADOW as TEXT_FLAG_SHADOW
)

from enum import Enum


class TagUpdate(Enum):
    NONE = 0,
    FULL = 1,
    OFFSCREEN = 2,
    BATCH = 3,
    SHADER = 4,
    POSITION = 5,
    SIZE = 6


shader_2d = gpu.shader.from_builtin('2D_UNIFORM_COLOR')


class CameraThumbnail:
    _offscreen_instance = None

    # camera_data_dict = {}

    def __init__(self, context):
        # print("WG::init")
        # prefs = get_prefs(context)

        color_border = (.92, .92, .92, 1.0)
        color_text = (.92, .92, .92, 1.0)

        self.sidebar_width = 0
        self.position = Vector((0, 0))
        self.dirty = TagUpdate.FULL

        self.width = 1920 * 0.16
        self.height = 1080 * 0.16

        render = context.scene.render
        self.resolution_x = render.resolution_x
        self.resolution_y = render.resolution_y

        self.region_width = context.region.width
        self.region_height = context.region.height

        self.set_scale()

        if context.object and context.object.type == 'CAMERA':
            self.camera = context.object

        # self.init_offscreen()
        self.frame_current = context.scene.frame_current
        self.color_border = color_border
        self.color_text = color_text
        self.update(context)
        self.update_camera_data_dict()
        self.update_space_data_dict(context)

    # @classmethod
    def update_camera_data_dict(self):
        if not self.camera:
            return
        cam = self.camera.data
        dof = cam.dof
        self.camera_data_dict = {
            'type': cam.type,
            'lens': cam.lens,
            'lens_unit': cam.lens_unit,
            'shift_x': cam.shift_x,
            'shift_y': cam.shift_y,
            'clip_start': cam.clip_start,
            'clip_end': cam.clip_end,
            'dof': {
                # 'is_active' : 'use_dof',
                'use_dof': dof.use_dof,
                'focus_object': dof.focus_object,
                'focus_distance': dof.focus_distance,
                'aperture_fstop': dof.aperture_fstop,
                'aperture_blades': dof.aperture_blades,
                'aperture_rotation': dof.aperture_rotation,
                'aperture_ratio': dof.aperture_ratio,
            },
            'sensor_fit': cam.sensor_fit,
            'sensor_width': cam.sensor_width,
        }

    def update_space_data_dict(self, context):
        if not self.camera:
            return
        space_data = context.space_data
        shading = space_data.shading
        self.space_data_dict = {
            # 'show_gizmo' : space_data.show_gizmo,
            'overlay': {
                'show_overlays': False,  # space_data.overlay.show_overlays
            },
            'shading': {
                'light': shading.light,
                'background_type': shading.background_type,
                'background_color': shading.background_color.copy(),
                'color_type': shading.color_type,
                'single_color': shading.single_color.copy(),
                'show_xray': shading.show_xray,
                'show_shadows': shading.show_shadows,
                'show_cavity': shading.show_cavity,
                'cavity_type': shading.cavity_type,
                'show_object_outline': shading.show_object_outline,
                'show_specular_highlight': shading.show_specular_highlight,
                'use_dof': shading.use_dof,
            }
        }

    def check_camera_data_change(self):
        if not self.camera:
            return

        def check_camera_data_props(data, _dict):
            for key, value in _dict.items():
                if isinstance(value, dict):
                    if check_camera_data_props(getattr(data, key), value):
                        return True
                else:
                    if getattr(data, key) != value:
                        self.update_camera_data_dict()
                        return True
            return False

        return check_camera_data_props(self.camera.data, self.camera_data_dict)

    def check_space_data_change(self, context):
        if not self.camera:
            return

        def check_space_data_props(data, _dict):
            for key, value in _dict.items():
                if isinstance(value, dict):
                    if check_space_data_props(getattr(data, key), value):
                        return True
                else:
                    if getattr(data, key) != value:
                        self.update_space_data_dict(context)
                        return True
            return False

        return check_space_data_props(context.space_data, self.space_data_dict)

    def init_offscreen(self) -> None:
        # print("WG::init_offscreen")
        if self.__class__._offscreen_instance:
            self.offscreen = self.__class__._offscreen_instance
        else:
            self.update_offscreen()

    def update_offscreen(self):
        self.offscreen = self.__class__._offscreen_instance = GPUOffScreen(self.width, self.height)
        # self.update_batch()

    def update_batch(self):
        def get_verts(x, y, w, h, t): return (
            (x - t, y - t), (x + w + t, y - t), (x - t, y + h + t), (x + w + t, y + h + t))

        indices = ((0, 1, 2), (2, 1, 3))

        self.batch = batch_for_shader(
            shader_2d, 'TRIS',
            {
                "pos": get_verts(*self.position, self.width, self.height, self.outline_thickness)
            },
            indices=indices)

    def update(self, context):
        # print("WG::update")
        if not context.object:
            return
        elif context.object.type != 'CAMERA':
            return
        # elif not context.scene.camera_preview.cam_obj:
        elif not self.camera:
            if not context.scene.camera:
                return
            self.camera = context.scene.camera  # context.scene.camera_preview.cam_obj = context.scene.camera
        # else:
        #    self.camera = context.scene.camera_preview.cam_obj
        # if context.object == 'CAMERA' and context.object != self.camera:
        #    self.camera = self.object
        # self.camera = context.object if context.object.type == 'CAMERA' else self.camera if self.camera else context.scene.camera if context.scene.camera else None
        # if not self.camera:
        #    print("WARN: No Camera available to preview")
        #    return
        self.camera_location = self.camera.location.copy()
        self.camera_rotation = self.camera.rotation_euler.copy()

        self.update_size(context)
        self.update_pos(context)

        # print(width, height)
        # print(self.position)

        self.update_batch()
        self.update_offscreen()

    def set_scale(self, context=None):

        only_scale_camera_view = False
        scale = 1

        self.scale = scale = scale
        self.min = 256 * scale
        scale = 1.0 if only_scale_camera_view else scale
        self.dpi = int(72 * scale)

        self.padding = 16 * scale
        self.outline_thickness = 5 * scale

        if context:
            self.update_size(context)
            self.update_pos(context)
            self.update_batch()
            self.update_offscreen()

        else:
            self.dirty = TagUpdate.FULL

    def update_size(self, context):
        width = self.resolution_x * 0.16 * self.scale
        height = self.resolution_y * 0.16 * self.scale

        if height < width < self.min or height < self.min < width:
            # 1. Sacar factor proporcional altura-anchura.
            fpropotional = width / height  # self.min / width - width / height
            # 2. Debe match height-min.
            height = self.min
            # 3. Aplico el fprop a la anchura.
            width = fpropotional * height

        elif width < height < self.min or width < self.min < height:
            # 1. Sacar factor proporcional altura-anchura.
            fpropotional = height / width  # self.min / height - height / width
            # 2. Debe match width-min.
            width = self.min
            # 3. Aplico el fprop a la altura.
            height = fpropotional * width

        reg_div = 2.5
        if height > context.region.height / reg_div:
            new_height = context.region.height / reg_div
            width *= (new_height / height)
            height = new_height
        if width > context.region.width / reg_div:
            new_width = context.region.width / reg_div
            height *= (new_width / width)
            width = new_width

        min_height = 100 if width > height else 100 * height / width
        min_width = 100 if height > width else 100 * width / height

        self.width = max(int(abs(width)), min_width)
        self.height = max(int(abs(height)), min_height)

    def update_pos(self, context):
        area = context.area
        off_x = 0
        off_y = 0

        for reg in area.regions:
            if reg.type == 'UI':
                off_x += reg.width
                self.sidebar_width = reg.width

        reg = context.region
        self.position = Vector((
            reg.width - off_x - self.width - self.padding,
            off_y + self.padding
        ))

    def have_region_dimensions_changed(self, context):
        if self.region_height != context.region.height:
            self.region_height = context.region.height
            return True
        if self.region_width != context.region.width:
            self.region_width = context.region.width
            return True

        for reg in context.area.regions:
            if reg.type == 'UI':
                if self.sidebar_width != reg.width:
                    self.sidebar_width = reg.width
                    return True
                return False

        return False

    def repaint(self, context):
        if self.have_region_dimensions_changed(context):
            if self.width < context.region.width / 2 or self.height < context.region.height / 2:
                self.update_size(context)

                # NOTE: HACK para evitar el flickering del thumbnail.
                # self.update_offscreen()
                self.dirty = TagUpdate.OFFSCREEN

            self.update_pos(context)
            self.update_batch()

        elif self.frame_current != context.scene.frame_current:
            self.frame_current = context.scene.frame_current
            pass

        elif not self.camera or self.camera != context.object:
            if context.object and context.object.type == 'CAMERA' and context.object != self.camera:
                self.camera = context.object
                self.update(context)
            else:
                # print("WARNING: No camera...")
                self.camera = None
                return

        elif self.dirty != TagUpdate.NONE:

            if self.dirty == TagUpdate.FULL:
                self.update(context)

            elif self.dirty == TagUpdate.OFFSCREEN:
                self.update_offscreen()

            elif self.dirty == TagUpdate.BATCH:
                self.update_batch()

            self.dirty = TagUpdate.NONE

        else:
            render = context.scene.render
            if self.resolution_x != render.resolution_x or self.resolution_y != render.resolution_y:
                self.resolution_x = render.resolution_x
                self.resolution_y = render.resolution_y
                self.update(context)
            elif self.camera.location != self.camera_location:
                self.camera_location = self.camera.location.copy()
            elif self.camera.rotation_euler != self.camera_rotation:
                self.camera_rotation = self.camera.rotation_euler.copy()
            elif self.check_camera_data_change() or self.check_space_data_change(context):
                pass
            else:
                return

        context.region.tag_redraw()
        self.offscreen.draw_view3d(
            context.scene,
            context.view_layer,
            context.space_data,
            context.region,
            self.camera.matrix_world.inverted(),
            self.camera.calc_matrix_camera(context.evaluated_depsgraph_get(), x=self.width, y=self.height)
        )

        return True

    def draw(self, context):
        shader_2d.bind()
        shader_2d.uniform_float('color', self.color_border)
        self.repaint(context)
        self.batch.draw(shader_2d)
        draw_tex(self.offscreen.color_texture, self.position, self.width, self.height)
        if not self.camera:
            return
        text = self.camera.name
        # if get_prefs(context).is_pinned:
        #     text = '[Pinned] ' + text

        text_set_position(0, *self.position + Vector((5, 5)), 0)
        text_set_size(0, 12, max(54, self.dpi))
        text_set_color(0, *self.color_text)
        text_enable(0, TEXT_FLAG_SHADOW)
        text_set_shadow(0, 0, 0, 0, 0, 1)
        text_set_shadow_offset(0, 2, -1)
        text_draw(0, text)
        text_disable(0, TEXT_FLAG_SHADOW)

    def __call__(self, context):
        self.draw(context)
