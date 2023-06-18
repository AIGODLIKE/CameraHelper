import gpu.state
import numpy as np
import os

import bmesh
import bpy

from bpy.types import Gizmo
from mathutils import Vector
from bpy_extras import view3d_utils

from dataclasses import dataclass
from pathlib import Path

from ..prefs.get_pref import get_pref
from ..ops.op_motion_cam import get_obj_2d_loc
from ..ops.draw_utils import wrap_bgl_restore


@dataclass
class GizmoInfo_2D():
    name: str
    type: str
    icon: str
    draw_options: set[str]

    alpha: float
    color: list[float]
    alpha_highlight: float
    color_highlight: list[float]

    scale_basis: float = (80 * 0.35) / 2
    use_tooltip: bool = True


def load_shape_geo_obj(obj_name='gz_shape_ROTATE'):
    """ 加载一个几何形状的模型，用于绘制几何形状的控件 """
    gz_shape_path = Path(__file__).parent.joinpath('custom_shape', 'gz_shape.blend')
    # print(str(gz_shape_path))
    with bpy.data.libraries.load(str(gz_shape_path)) as (data_from, data_to):
        data_to.objects = [obj_name]
    # print(data_to.objects)
    return data_to.objects[0]


def create_geo_shape(obj=None, type='TRIS', scale=1):
    """ 创建一个几何形状，默认创造球体

    :param obj:
    :return:
    """
    if obj:
        tmp_mesh = obj.data
    else:
        tmp_mesh = bpy.data.meshes.new('tmp')
        bm = bmesh.new()
        bmesh.ops.create_uvsphere(bm, u_segments=16, v_segments=8, radius=scale / 5, calc_uvs=True)
        bm.to_mesh(tmp_mesh)
        bm.free()

    mesh = tmp_mesh
    vertices = np.zeros((len(mesh.vertices), 3), 'f')
    mesh.vertices.foreach_get("co", vertices.ravel())
    mesh.calc_loop_triangles()

    if type == 'LINES':
        edges = np.zeros((len(mesh.edges), 2), 'i')
        mesh.edges.foreach_get("vertices", edges.ravel())
        custom_shape_verts = vertices[edges].reshape(-1, 3)
    else:
        tris = np.zeros((len(mesh.loop_triangles), 3), 'i')
        mesh.loop_triangles.foreach_get("vertices", tris.ravel())
        custom_shape_verts = vertices[tris].reshape(-1, 3)

    bpy.data.meshes.remove(mesh)

    return custom_shape_verts


class GizmoBase3D(Gizmo):
    bl_idname = "CAMHP_GT_custom_move_3d"
    # The id must be "offset"
    bl_target_properties = (
        {"id": "offset", "type": 'FLOAT', "array_length": 1},
    )
    __slots__ = (
        # Automatically add attributes for properties defined in the GizmoInfo above
        "draw_options",
        "draw_style",
        "gizmo_name",

        # Extra attributes used for intersection
        "custom_shape",
        "init_mouse",
        "init_value",
        "_index",
        "_camera",
    )

    def setup(self):
        if not hasattr(self, "custom_shape"):
            self.custom_shape = self.new_custom_shape('LINES', create_geo_shape())

    def draw(self, context):
        self._update_offset_matrix()
        self.draw_custom_shape(self.custom_shape)

    def draw_select(self, context, select_id):
        if self.custom_shape is None:
            self.custom_shape = create_geo_shape()

        self._update_offset_matrix()
        with wrap_bgl_restore(self.line_width):
            self.draw_custom_shape(self.custom_shape, select_id=select_id)

    def mouse_ray(self, context, event):
        """获取鼠标射线"""
        region = context.region
        rv3d = context.region_data
        coord = event.mouse_region_x, event.mouse_region_y
        ray_origin = view3d_utils.region_2d_to_origin_3d(region, rv3d, coord)
        ray_direction = view3d_utils.region_2d_to_vector_3d(region, rv3d, coord)
        return ray_origin, ray_direction

    def exit(self, context, cancel):
        context.area.header_text_set(None)
        if cancel:
            self.target_set_value("offset", self.init_value)

    def invoke(self, context, event):
        self.init_mouse = self._projected_value(context, event)
        self.init_value = self.target_get_value("offset")
        return {'RUNNING_MODAL'}


class CAMHP_OT_insert_keyframe(bpy.types.Operator):
    bl_idname = 'camhp.insert_keyframe'
    bl_label = 'Insert Keyframe'

    def execute(self, context):
        context.object.motion_cam.keyframe_insert('offset_factor')

        for area in context.window.screen.areas:
            for region in area.regions:
                region.tag_redraw()

        return {'FINISHED'}


class CAMHP_GT_custom_move_1d(GizmoBase3D, Gizmo):
    bl_idname = "CAMHP_GT_custom_move_1d"
    # The id must be "offset"
    bl_target_properties = (
        {"id": "offset", "type": 'FLOAT', "array_length": 1},
    )

    def setup(self):
        if not hasattr(self, "custom_shape"):
            pref_gz = get_pref().gz_motion_camera
            shape_obj = load_shape_geo_obj('gz_shape_SLIDE')

            self.custom_shape = self.new_custom_shape('TRIS',
                                                      create_geo_shape(obj=shape_obj, scale=pref_gz.scale_basis))
            try:
                bpy.data.objects.remove(shape_obj)
            except:
                pass

    def _update_offset_matrix(self):
        # offset behind the light
        self.matrix_offset.col[3][2] = self.target_get_value("offset")

    def _projected_value(self, context, event):
        return event.mouse_x

    def modal(self, context, event, tweak):
        mouse = self._projected_value(context, event)
        delta = (mouse - self.init_mouse)
        if 'SNAP' in tweak:
            delta = round(delta)
        if 'PRECISE' in tweak:
            delta /= 10.0

        value = self.init_value - delta / 1000

        start_cam = context.object.motion_cam.list[0]
        end_cam = context.object.motion_cam.list[1]

        # 比较开始结束相机的屏幕位置以决定是否反向
        if start_cam.camera and end_cam.camera:
            start_x, start_y = get_obj_2d_loc(start_cam.camera, context)
            end_x, end_y = get_obj_2d_loc(end_cam.camera, context)

            if end_x > start_x:
                value = self.init_value + delta / 1000

        # loop
        if get_pref().gz_motion_camera.loop:
            if value > 1:
                value = abs(1 - value)
            elif value < 0:
                value = abs(value + 1)
        else:
            if value > 1:
                value = 1
            elif value < 0:
                value = 0

        self.target_set_value("offset", value)
        context.area.header_text_set(f"Move: {value:.4f}")
        return {'RUNNING_MODAL'}

    def invoke(self, context, event):
        self.init_mouse = self._projected_value(context, event)
        self.init_value = self.target_get_value("offset")

        if event.ctrl:
            def pop_up(cls, context):
                layout = cls.layout
                d = self._camera.data
                layout.popover(panel='CAMHP_PT_MotionCamPanel')

            context.window_manager.popup_menu(pop_up, title=f'{self._camera.name}', icon='CAMERA_DATA')
            # bpy.ops.wm.call_panel(name='CAMHP_PT_MotionCamPanel', keep_open=True)
            return {'INTERFACE'}

        return super().invoke(context, event)


# 创建3d gizmo
class CAMHP_GT_custom_move_3d(GizmoBase3D, Gizmo):
    bl_idname = "CAMHP_GT_custom_move_3d"
    # The id must be "offset"
    bl_target_properties = (
        {"id": "offset", "type": 'FLOAT', "array_length": 3},
    )

    def _update_offset_matrix(self):
        try:
            x, y, z = self.target_get_value("offset")
            self.matrix_offset.col[3][0] = x
            self.matrix_offset.col[3][1] = y
            self.matrix_offset.col[3][2] = z
        except ValueError:
            pass
    def setup(self):
        if not hasattr(self, "custom_shape"):
            pref_gz = get_pref().gz_motion_source
            self.custom_shape = self.new_custom_shape('TRIS', create_geo_shape(scale=pref_gz.scale_basis))

    def _projected_value(self, context, event):
        """用于光线投射

        :param context:
        :param event:
        :return: offset Vector
        """
        ray_origin, ray_direction = self.mouse_ray(context, event)
        mat = self.matrix_basis.inverted()
        ray_origin = mat @ ray_origin
        ray_direction = mat.to_3x3() @ ray_direction

        dist = ray_origin.magnitude

        offset = ray_origin + dist * ray_direction
        return offset

    def invoke(self, context, event):
        if event.ctrl:
            def pop_up(cls, context):
                layout = cls.layout
                d = self._camera.data
                layout.prop(d, 'lens')
                layout.prop(d.dof, 'focus_distance')
                layout.prop(d.dof, 'aperture_fstop')
                # layout.separator()
                # ob = self._camera
                # col = layout.column()
                # col.prop(ob, "rotation_euler", text="Rotation")
                # layout.popover(panel='CAMHP_PT_MotionCamPanel')

            context.window_manager.popup_menu(pop_up, title=f'{self._camera.name}', icon='CAMERA_DATA')

            return {'INTERFACE'}

        self.init_mouse = self._projected_value(context, event)
        self.init_value = Vector(self.target_get_value("offset"))

        return {'RUNNING_MODAL'}

    def modal(self, context, event, tweak):
        mouse = self._projected_value(context, event)
        delta = (mouse - self.init_mouse)
        if 'SNAP' in tweak:
            delta = Vector([round(d) for d in delta])
        if 'PRECISE' in tweak:
            delta /= 10.0
        value = self.init_value + delta
        self.target_set_value("offset", value)
        context.area.header_text_set(f"{self._camera.name}: {value[0]:.4f}, {value[1]:.4f}, {value[2]:.4f}")
        return {'RUNNING_MODAL'}

    def set_curve_pos(self):
        # print(tweak)
        # widget驱动曲线点
        # if context.object.motion_cam.path:
        # spline = context.object.motion_cam.path.data.splines[0]
        # spline.bezier_points[self._index].co = value
        # spline.bezier_points[self._index].handle_left = value
        # spline.bezier_points[self._index].handle_right = value

        # context.area.header_text_set(f"{self.gizmo_name}: {value[0]:.4f}, {value[1]:.4f}, {value[2]:.4f}")
        pass


class CAMHP_GT_custom_rotate_1d(Gizmo):
    bl_idname = "CAMHP_GT_custom_rotate_1d"

    def draw(self, context):
        self.draw_custom_shape(self.custom_shape)

    def draw_select(self, context, select_id):
        self.draw_custom_shape(self.custom_shape, select_id=select_id)

    def setup(self):
        if not hasattr(self, "custom_shape"):
            pref_gz = get_pref().gz_motion_source
            shape_obj = load_shape_geo_obj('gz_shape_ROTATE')
            self.custom_shape = self.new_custom_shape('TRIS',
                                                      create_geo_shape(obj=shape_obj, scale=pref_gz.scale_basis * 3))

            try:
                bpy.data.objects.remove(shape_obj)
            except:
                pass


class CAMHP_OT_rotate_object(bpy.types.Operator):
    bl_idname = 'camhp.rotate_object'
    bl_label = 'Rotate Object'
    # bl_options = {'REGISTER', 'UNDO'}

    obj_name: bpy.props.StringProperty(name='Object Name')
    axis: bpy.props.EnumProperty(items=[('X', 'X', 'X'), ('Y', 'Y', 'Y'), ('Z', 'Z', 'Z')])

    def append_handles(self):
        self.cursor_set = True
        bpy.context.window.cursor_modal_set('MOVE_X')
        bpy.context.window_manager.modal_handler_add(self)

    def remove_handles(self):
        bpy.context.window.cursor_modal_restore()

    def modal(self, context, event):
        if event.type == 'MOUSEMOVE':
            self.mouseDX = self.mouseDX - event.mouse_x
            # shift 减速
            multiplier = 0.005 if event.shift else 0.01
            offset = multiplier * self.mouseDX

            # 校正
            loc_x, loc_y = get_obj_2d_loc(self.obj, context)
            if self.startX > loc_x and self.axis != 'Z':
                offset *= -1

            rotate_mode = {'Z': 'ZYX', 'X': 'XYZ', 'Y': 'YXZ'}[self.axis]

            # 设置旋转矩阵（缩放为负数时失效）
            rot = self.obj.rotation_euler.to_matrix().to_euler(rotate_mode)
            axis = self.axis.lower()
            setattr(rot, axis, getattr(rot, axis) + offset)
            self.obj.rotation_euler = rot.to_matrix().to_euler(self.obj.rotation_mode)

            # 重置
            self.mouseDX = event.mouse_x

        elif event.type == 'LEFTMOUSE':
            self.remove_handles()
            return {'FINISHED'}

        elif event.type in {'RIGHTMOUSE', 'ESC'}:
            return {'CANCELLED'}

        return {'RUNNING_MODAL'}

    def invoke(self, context, event):
        self.obj = bpy.data.objects[self.obj_name]

        self.mouseDX = event.mouse_x
        self.startX = event.mouse_x

        # add handles
        self.append_handles()

        return {"RUNNING_MODAL"}
