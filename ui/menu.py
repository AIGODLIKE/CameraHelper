import bpy


class CAMERA_HELPER_MT_Switch_Camera(bpy.types.Menu):
    bl_label = 'SwitchCamera'
    bl_space_type = 'VIEW_3D'
    bl_region_type = "WINDOW"

    def draw(self, context):
        from ..ops.switch_camera import SwitchCamera
        layout = self.layout
        layout.operator_context = 'INVOKE_DEFAULT'
        for i, obj in enumerate(bpy.data.objects):
            if obj.type != 'CAMERA':
                continue
            name = obj.name
            if obj is context.scene.camera:
                icon = 'VIEW_CAMERA'
            else:
                icon = 'DOT'
            ops = layout.operator(SwitchCamera.bl_idname, text=name, icon=icon)
            ops.tg_cam = obj.name


class CAMHP_MT_popup_cam_settings(bpy.types.Menu):
    """Properties"""
    bl_label = 'Camera Settings'
    bl_space_type = 'VIEW_3D'
    bl_region_type = "WINDOW"

    def draw(self, context_):
        layout = self.layout
        layout.popover(panel='CAMHP_PT_pop_cam_lens')
        layout.popover(panel='CAMHP_PT_pop_cam_dof')
        layout.popover(panel='CAMHP_PT_pop_cam_comp_panel', text='Guide')


def register():
    bpy.utils.register_class(CAMERA_HELPER_MT_Switch_Camera)
    bpy.utils.register_class(CAMHP_MT_popup_cam_settings)


def unregister():
    bpy.utils.unregister_class(CAMERA_HELPER_MT_Switch_Camera)
    bpy.utils.unregister_class(CAMHP_MT_popup_cam_settings)
