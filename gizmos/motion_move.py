import blf
import bpy
import gpu.matrix
from mathutils import Vector

from .public_gizmo import PublicGizmo


class MotionCameraAdjustGizmo(bpy.types.Gizmo):
    bl_idname = "MOTION_CAMERA_ADJUST_GT_gizmo"
    bl_options = {"PERSISTENT", "SCALE", "SHOW_MODAL_ALL", "UNDO", "GRAB_CURSOR"}

    def invoke(self, context, event):
        print("invoke")
        return {"RUNNING_MODAL"}

    def modal(self, context, event, tweak):
        print(self.bl_idname, "modal", event.type, event.value)
        if event.type == "LEFTMOUSE":
            return {"FINISHED"}
        elif event.type in {"RIGHTMOUSE", "ESC"}:
            return {"CANCELLED"}
        mouse = Vector((event.mouse_region_x, event.mouse_region_y))
        diff = self.start_mouse - mouse
        self.offset_after = offset = self.start_offset + Vector((-diff.x, diff.y))
        context.area.tag_redraw()
        return {"RUNNING_MODAL"}

    def exit(self, context, cancel):
        print("exit", cancel)

    def draw(self, context):
        with gpu.matrix.push_pop():
            obj = context.object

            depsgraph = context.evaluated_depsgraph_get()
            evaluated_obj = context.object.evaluated_get(depsgraph)

            gpu.state.depth_mask_set(False)
            blf.draw(0, f"aaa {evaluated_obj.name} {len(evaluated_obj.data.vertices)}")

    # def test_select(self, context, mouse_pos):
    #     return False

    def refresh(self, context):
        print(self.bl_idname, "refresh")


class MotionCameraAdjustGizmos(bpy.types.GizmoGroup, PublicGizmo):
    bl_idname = "MOTION_CAMERA_ADJUST_GT_gizmos"
    bl_label = "Motion Camera Adjust Gizmos"

    @classmethod
    def poll(cls, context):
        obj = context.object
        return (
                obj and
                obj.type == "MESH" and
                obj.modifiers.active and
                obj.modifiers.active.type == "NODES" and
                obj.modifiers.active.name == "MotionCamera"
        )

    def setup(self, context):
        print("setup")
        gz = self.preview_camera = self.gizmos.new(MotionCameraAdjustGizmo.bl_idname)
        gz.use_draw_modal = True

    def refresh(self, context):
        context.area.tag_redraw()

    def draw_prepare(self, context):
        ...
