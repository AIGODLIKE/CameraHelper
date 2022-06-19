from bpy.types import Gizmo
from mathutils import Vector
from bpy_extras import view3d_utils
import bgl
from mathutils import Vector
import bmesh
import numpy as np
import bpy


def create_sphere_shape():
    tmp_mesh = bpy.data.meshes.new('tmp')
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=16, v_segments=8, radius=0.5, calc_uvs=True)
    bm.to_mesh(tmp_mesh)
    bm.free()

    mesh = tmp_mesh
    vertices = np.zeros((len(mesh.vertices), 3), 'f')
    vertices = np.zeros((len(mesh.vertices), 3), 'f')
    mesh.vertices.foreach_get("co", vertices.ravel())
    mesh.calc_loop_triangles()
    tris = np.zeros((len(mesh.loop_triangles), 3), 'i')
    mesh.loop_triangles.foreach_get("vertices", tris.ravel())
    custom_shape_verts = vertices[tris].reshape(-1, 3)

    bpy.data.meshes.remove(mesh)
    return custom_shape_verts


class CAMHP_GT_custom_move_3d(Gizmo):
    bl_idname = "CAMHP_GT_custom_move_3d"
    # The id must be "offset"
    bl_target_properties = (
        {"id": "offset", "type": 'FLOAT', "array_length": 3},
    )

    __slots__ = (
        # Automatically add attributes for properties defined in the GizmoInfo above
        "draw_options",
        "draw_style",
        "gizmo_name",

        # Extra attribtues used for insteraction
        "custom_shape",
        "init_mouse",
        "init_value",
        "_index",
        "_camera",
    )

    def _update_offset_matrix(self):
        x, y, z = self.target_get_value("offset")
        self.matrix_offset.col[3][0] = x
        self.matrix_offset.col[3][1] = y
        self.matrix_offset.col[3][2] = z

    def setup(self):
        if not hasattr(self, "custom_shape"):
            self.custom_shape = self.new_custom_shape('TRIS', create_sphere_shape())

    def _projected_value(self, context, event):
        ray_origin, ray_direction = self.mouse_ray(context, event)
        mat = self.matrix_basis.inverted()
        ray_origin = mat @ ray_origin
        ray_direction = mat.to_3x3() @ ray_direction

        dist = ray_origin.magnitude

        offset = ray_origin + dist * ray_direction
        return offset

    def invoke(self, context, event):
        self.init_mouse = self._projected_value(context, event)
        self.init_value = Vector(self.target_get_value("offset"))
        return {'RUNNING_MODAL'}

    def exit(self, context, cancel):
        context.area.header_text_set(None)
        if cancel:
            self.target_set_value("offset", self.init_value)

    def draw(self, context):
        self._update_offset_matrix()
        self.draw_custom_shape(self.custom_shape)

    def draw_select(self, context, select_id):
        if self.custom_shape is None:
            self.custom_shape = create_sphere_shape()

        self._update_offset_matrix()
        bgl.glLineWidth(self.line_width)
        self.draw_custom_shape(self.custom_shape, select_id=select_id)
        bgl.glLineWidth(1)

    def mouse_ray(self, context, event):
        region = context.region
        rv3d = context.region_data
        coord = event.mouse_region_x, event.mouse_region_y
        ray_origin = view3d_utils.region_2d_to_origin_3d(region, rv3d, coord)
        ray_direction = view3d_utils.region_2d_to_vector_3d(region, rv3d, coord)
        return ray_origin, ray_direction

    def modal(self, context, event, tweak):
        mouse = self._projected_value(context, event)
        delta = (mouse - self.init_mouse)
        if 'SNAP' in tweak:
            delta = Vector([round(d) for d in delta])
        if 'PRECISE' in tweak:
            delta /= 10.0
        value = self.init_value + delta
        self.target_set_value("offset", value)

        if context.object.motion_cam.path:
            spline = context.object.motion_cam.path.data.splines[0]
            spline.bezier_points[self._index].co = value
            spline.bezier_points[self._index].handle_left = value
            spline.bezier_points[self._index].handle_right = value

        # context.area.header_text_set(f"{self.gizmo_name}: {value[0]:.4f}, {value[1]:.4f}, {value[2]:.4f}")
        context.area.header_text_set(f"Moving!: {value[0]:.4f}, {value[1]:.4f}, {value[2]:.4f}")
        return {'RUNNING_MODAL'}
