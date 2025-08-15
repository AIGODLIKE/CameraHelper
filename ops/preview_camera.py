import bpy

from ..camera_thumbnails import CameraThumbnails
from ..utils import get_operator_bl_idname, get_camera


class PreviewCamera(bpy.types.Operator):
    """Camera Thumbnails\nLeft Click: Enable\nCtrl: Pin Selected Camera\nCtrl Shift Click: Send to Viewer"""
    bl_idname = get_operator_bl_idname("preview_camera")
    bl_label = "Preview Camera"

    check_data = {}
    camera_data = {}

    @classmethod
    def poll(cls, context):
        return context.space_data.type == "VIEW_3D"

    def invoke(self, context, event):
        camera = get_camera(context)
        CameraThumbnails.update()
        if event.type == "LEFTMOUSE":
            if event.shift and event.ctrl:
                bpy.ops.camhp.pv_snap_shot("INVOKE_DEFAULT")
            elif event.ctrl:
                if camera:
                    CameraThumbnails.pin_selected_camera(context, camera)
            else:
                if camera:
                    CameraThumbnails.switch_preview(context, camera)
        CameraThumbnails.update()
        context.area.tag_redraw()
        return {"FINISHED"}
