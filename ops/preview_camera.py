import blf
import bpy
import gpu
from gpu_extras.presets import draw_texture_2d

from ..utils import get_operator_bl_idname


class PreviewCamera(bpy.types.Operator):
    """Camera Thumbnails\nLeft Click: Enable\nCtrl: Pin Selected Camera\nCtrl Shift Click: Send to Viewer"""
    bl_idname = get_operator_bl_idname("preview_camera")
    bl_label = "Preview Camera"

    camera_preview_enabled = False
    camera_preview_pin = False
    camera_preview_handle = None
    timer = None

    @classmethod
    def poll(cls, context):
        return context.space_data.type == "VIEW_3D"

    def invoke(self, context, event):
        if event.type == "LEFTMOUSE":
            if event.shift and event.ctrl:
                bpy.ops.camhp.pv_snap_shot()
                return {"FINISHED"}
            elif event.ctrl:
                self.camera_preview_pin = self.camera_preview_pin ^ True
                return {"FINISHED"}
            else:
                self.camera_preview_enabled = self.camera_preview_enabled ^ True
                if not self.camera_preview_enabled:
                    return {"FINISHED"}
                else:
                    self.camera_preview_handle = bpy.types.SpaceView3D.draw_handler_add(
                        self.draw_preview,
                        (context,),
                        'WINDOW',
                        "POST_PIXEL",
                    )

        # self.timer = context.window_manager.event_timer_add(0.01, window=context.window)
        context.window_manager.modal_handler_add(self)
        return {"RUNNING_MODAL", "PASS_THROUGH"}

    def modal(self, context, event):
        print("modal", event.value, event.type, self.camera_preview_enabled, self.camera_preview_pin, end="\r")
        if not self.camera_preview_enabled:
            self.exit(context)
            return {"FINISHED"}

        return {"PASS_THROUGH"}

    def exit(self, context):
        print("exit")
        if self.camera_preview_handle:
            bpy.types.SpaceView3D.draw_handler_remove(self.camera_preview_handle, "WINDOW")
            self.camera_preview_handle = None
        if self.timer:
            context.window_manager.event_timer_remove(self.timer)
            self.timer = None
        self.camera_preview_enabled = False
        self.camera_preview_pin = False

    def draw_preview(self, context):
        scene = context.scene
        WIDTH = 512
        HEIGHT = 256
        offscreen = gpu.types.GPUOffScreen(WIDTH, HEIGHT)
        if scene.camera:
            with gpu.matrix.push_pop():
                gpu.matrix.translate((100, 100))
                view_matrix = scene.camera.matrix_world.inverted()
                projection_matrix = scene.camera.calc_matrix_camera(
                    context.evaluated_depsgraph_get(),
                    x=WIDTH,
                    y=HEIGHT,
                )
                blf.draw(0, "AAA")
                print("draw preview")
                offscreen.draw_view3d(
                    scene,
                    context.view_layer,
                    context.space_data,
                    context.region,
                    view_matrix,
                    projection_matrix,
                    do_color_management=True)

                gpu.state.depth_mask_set(False)
                draw_texture_2d(offscreen.texture_color, (10, 10), WIDTH, HEIGHT)


def is_select_obj(context):
    return (
            context and
            hasattr(context, "object") and
            context.object and
            context.object.type in {"CAMERA", "EMPTY"}
    )
