from bpy.types import Gizmo
from mathutils import Vector
from bpy_extras import view3d_utils
import bgl
from mathutils import Vector
import bmesh
import numpy as np
import bpy


class GizmoInfo_2D():
    def __init__(self, name, type, icon,
                 draw_options: set,
                 use_tooltip: bool,
                 alpha: float, color: list[float],
                 alpha_highlight: float, color_highlight: list[float],
                 scale_basis=(80 * 0.35) / 2):
        self.name = name
        self.type = type
        self.icon = icon
        self.draw_options = draw_options
        self.use_tooltip = use_tooltip
        self.alpha = alpha
        self.color = color
        self.alpha_highlight = alpha_highlight
        self.color_highlight = color_highlight
        self.scale_basis = scale_basis


def create_geo_shape(obj=None, type='TRIS'):
    """ 创建一个几何形状，默认创造球体

    :param obj:
    :return:
    """
    if obj:
        tmp_mesh = obj.data
    else:
        tmp_mesh = bpy.data.meshes.new('tmp')
        bm = bmesh.new()
        bmesh.ops.create_uvsphere(bm, u_segments=16, v_segments=8, radius=0.5, calc_uvs=True)
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


class GizmoBase(Gizmo):
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
        bgl.glLineWidth(self.line_width)
        self.draw_custom_shape(self.custom_shape, select_id=select_id)
        bgl.glLineWidth(1)

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


class CAMHP_GT_custom_move_1d(GizmoBase, Gizmo):
    bl_idname = "CAMHP_GT_custom_move_1d"
    # The id must be "offset"
    bl_target_properties = (
        {"id": "offset", "type": 'FLOAT', "array_length": 1},
    )

    def setup(self):
        if not hasattr(self, "custom_shape"):
            self.custom_shape = self.new_custom_shape('TRIS', create_geo_shape())

    def _update_offset_matrix(self):
        # offset behind the light
        self.matrix_offset.col[3][2] = self.target_get_value("offset")

    # def _projected_value(self, context, event):
    #     ray_origin, ray_direction = self.mouse_ray(context, event)
    #     axis_origin = self.matrix_basis.col[3].to_3d()  # origin
    #     axis_direction = self.matrix_basis.col[2].to_3d()  # direction
    #
    #     n = axis_direction.cross(ray_direction)
    #     n_ray = ray_direction.cross(n)
    #     value = (ray_origin - axis_origin).dot(n_ray) / axis_direction.dot(n_ray)
    #     # c = axis_origin + value * axis_direction
    #     return value

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
        if value > 1:
            value = abs(1 - value)
        elif value < 0:
            value = abs(value + 1)
        if event.ctrl:
            value = 1 - value

        self.target_set_value("offset", value)
        context.area.header_text_set(f"Move: {value:.4f}")
        return {'RUNNING_MODAL'}

    def invoke(self, context, event):
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
class CAMHP_GT_custom_move_3d(GizmoBase, Gizmo):
    bl_idname = "CAMHP_GT_custom_move_3d"
    # The id must be "offset"
    bl_target_properties = (
        {"id": "offset", "type": 'FLOAT', "array_length": 3},
    )

    def _update_offset_matrix(self):
        x, y, z = self.target_get_value("offset")
        self.matrix_offset.col[3][0] = x
        self.matrix_offset.col[3][1] = y
        self.matrix_offset.col[3][2] = z

    def setup(self):
        if not hasattr(self, "custom_shape"):
            self.custom_shape = self.new_custom_shape('TRIS', create_geo_shape())

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
