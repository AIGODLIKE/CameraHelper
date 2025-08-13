import bpy
import gpu

from .public_gizmo import PublicGizmo


class PreviewCameraGizmo(bpy.types.Gizmo):
    bl_idname = "PREVIEW_CAMERA_GT_gizmo"

    def setup(self):
        ...

    def invoke(self, context, event):
        if event.type in {'RIGHTMOUSE', 'ESC'}:
            self.exit(context)
            return {'CANCELLED'}
        return {'RUNNING_MODAL'}

    def modal(self, context, event, tweak):
        if event.type == "LEFTMOUSE":
            return {"FINISHED"}
        return {'RUNNING_MODAL'}

    def draw(self, context):
        from gpu_extras.batch import batch_for_shader

        vertices = ((100, 100), (300, 100), (100, 200), (300, 200))
        indices = ((0, 1, 2), (2, 1, 3))

        shader = gpu.shader.from_builtin('UNIFORM_COLOR')
        batch = batch_for_shader(shader, 'TRIS', {"pos": vertices}, indices=indices)

        shader.uniform_float("color", (0, 0.5, 0.5, 1.0))
        batch.draw(shader)
        # Camera.draw_texture(context)

    def test_select(self, context, mouse_pos):
        if self.draw_points is None:
            return -1
        x, y = mouse_pos
        (x1, y1), (x2, y2) = self.draw_points
        x_ok = x1 < x < x2
        y_ok = y1 < y < y2
        is_hover = 0 if x_ok and y_ok else -1
        self.is_hover = is_hover == 0
        return is_hover

    def refresh(self, context):
        print(self.bl_idname, "refresh")


class PreviewCameraGizmos(bpy.types.GizmoGroup, PublicGizmo):
    bl_idname = "Preview_Camera_UI_gizmos"
    bl_label = "Preview Camera Gizmos"

    def setup(self, context):
        self.preview_camera = self.gizmos.new(PreviewCameraGizmo.bl_idname)

    def refresh(self, context):
        context.area.tag_redraw()
        print(self.bl_idname, "refresh")

    def draw_prepare(self, context):
        print("draw_prepare", self.bl_idname)
