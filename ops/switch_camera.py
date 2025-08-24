import bpy


class SwitchCamera(bpy.types.Operator):
    bl_idname = 'camhp.switch_camera'
    bl_label = 'Switch Camera'

    @classmethod
    def poll(cls, context):
        camera = getattr(context, "camera", None)
        return camera and camera.type == "CAMERA"

    def invoke(self, context, event):
        if camera := getattr(context, "camera", None):
            context.space_data.camera = camera
        return {"FINISHED"}
