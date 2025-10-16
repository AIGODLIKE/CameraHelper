import bpy


class CAMERA_HELPER_MT_Switch_Camera(bpy.types.Menu):
    bl_label = "Switch Camera"
    bl_space_type = "VIEW_3D"
    bl_region_type = "WINDOW"

    def draw(self, context):
        from ..ops.switch_camera import SwitchCamera
        layout = self.layout
        layout.operator_context = "INVOKE_DEFAULT"
        for i, obj in enumerate(bpy.data.objects):
            if obj.type != "CAMERA":
                continue
            name = obj.name
            if obj is context.scene.camera:
                icon = "VIEW_CAMERA"
            else:
                icon = "CAMERA_DATA"
            layout.context_pointer_set("camera", obj)
            layout.operator(SwitchCamera.bl_idname, text=name, icon=icon, translate=False)


class CAMHP_MT_popup_cam_settings(bpy.types.Menu):
    """Properties"""
    bl_label = "Camera Settings"
    bl_space_type = "VIEW_3D"
    bl_region_type = "WINDOW"

    def draw(self, context):
        layout = self.layout
        camera_obj = context.space_data.camera
        if camera_obj:
            layout.context_pointer_set("camera", camera_obj.data)
            layout.popover("DATA_PT_camera")
            layout.popover("DATA_PT_lens")
            layout.popover("DATA_PT_camera_display")

            layout.separator()
            if context.engine == "CYCLES":
                layout.popover("CYCLES_CAMERA_PT_dof")
            else:
                layout.popover("DATA_PT_camera_dof")
            layout.separator()
            layout.popover("DATA_PT_camera_safe_areas")

        else:
            layout.label(text="No Camera Selected")


def register():
    bpy.utils.register_class(CAMERA_HELPER_MT_Switch_Camera)
    bpy.utils.register_class(CAMHP_MT_popup_cam_settings)


def unregister():
    bpy.utils.unregister_class(CAMERA_HELPER_MT_Switch_Camera)
    bpy.utils.unregister_class(CAMHP_MT_popup_cam_settings)
